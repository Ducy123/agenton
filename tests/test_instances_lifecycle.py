import asyncio

import pytest

from app.auth.schemas import UserCreate
from app.auth.service import register_user
from app.billing.service import create_order, get_or_create_wallet, pay_order, recharge
from app.common.enums import InstanceStatus, PricingUnit
from app.engine.connectors.base import TaskContext, TaskResult
from app.instances import service as instances_service
from app.instances.lifecycle import InvalidTransitionError, assert_transition_allowed
from app.marketplace.models import AgentTemplate


@pytest.mark.parametrize(
    "current,target",
    [
        (InstanceStatus.CREATED, InstanceStatus.RUNNING),
        (InstanceStatus.RUNNING, InstanceStatus.PAUSED),
        (InstanceStatus.RUNNING, InstanceStatus.STOPPED),
        (InstanceStatus.PAUSED, InstanceStatus.RUNNING),
        (InstanceStatus.STOPPED, InstanceStatus.RELEASED),
        (InstanceStatus.EXPIRED, InstanceStatus.RELEASED),
    ],
)
def test_allowed_transitions_pass(current, target):
    assert_transition_allowed(current, target)  # should not raise


@pytest.mark.parametrize(
    "current,target",
    [
        (InstanceStatus.CREATED, InstanceStatus.STOPPED),
        (InstanceStatus.RELEASED, InstanceStatus.RUNNING),
        (InstanceStatus.STOPPED, InstanceStatus.RUNNING),
        (InstanceStatus.EXPIRED, InstanceStatus.RUNNING),
    ],
)
def test_disallowed_transitions_raise(current, target):
    with pytest.raises(InvalidTransitionError):
        assert_transition_allowed(current, target)


class _FakeConnector:
    task_type = "fake"

    def __init__(self, outcomes: list[TaskResult]):
        self._outcomes = outcomes
        self.calls = 0

    async def run(self, ctx: TaskContext) -> TaskResult:
        result = self._outcomes[self.calls]
        self.calls += 1
        return result

    async def verify(self, ctx: TaskContext, result: TaskResult) -> TaskResult:
        return result


async def _setup_paid_order(session, quantity=1, pricing_unit=PricingUnit.TOKEN, price=100, wallet_cents=10_000):
    user = register_user(session, UserCreate(email="svc@test.dev", password="password123"))
    template = AgentTemplate(
        slug="fake-agent",
        name="Fake",
        category="test",
        task_type="fake",
        base_price_cents=price,
        pricing_unit=pricing_unit,
    )
    session.add(template)
    session.commit()
    session.refresh(template)

    await recharge(session, user.id, wallet_cents)
    order = create_order(session, user.id, template.id, quantity)
    order = pay_order(session, order.id, user.id)
    return user, template, order


@pytest.mark.asyncio
async def test_execute_instance_task_meters_token_pricing(session, monkeypatch):
    user, _template, order = await _setup_paid_order(session)
    fake = _FakeConnector([TaskResult(success=True, message="ok")])
    monkeypatch.setattr(instances_service, "get_connector", lambda task_type: fake)

    instance = instances_service.create_instance_from_order(session, user.id, order.id, {})
    instances_service.start_instance(session, instance.id, user.id)

    result, instance = await instances_service.execute_instance_task(session, instance.id, user.id)

    assert result.success is True
    assert instance.fail_streak == 0
    wallet = get_or_create_wallet(session, user.id)
    assert wallet.balance_cents == 10_000 - 100 - 100  # order payment (qty 1) + one metered call


@pytest.mark.asyncio
async def test_execute_instance_task_auto_pauses_after_repeated_failures(session, monkeypatch):
    user, _template, order = await _setup_paid_order(session)
    fake = _FakeConnector([TaskResult(success=False, message="boom")] * 3)
    monkeypatch.setattr(instances_service, "get_connector", lambda task_type: fake)

    instance = instances_service.create_instance_from_order(session, user.id, order.id, {})
    instances_service.start_instance(session, instance.id, user.id)

    for _ in range(3):
        _, instance = await instances_service.execute_instance_task(session, instance.id, user.id)

    assert instance.status == InstanceStatus.PAUSED
    assert instance.fail_streak == 3
    assert "Auto-paused" in instance.auto_paused_reason


@pytest.mark.asyncio
async def test_execute_requires_running_status(session, monkeypatch):
    user, _template, order = await _setup_paid_order(session)
    fake = _FakeConnector([TaskResult(success=True, message="ok")])
    monkeypatch.setattr(instances_service, "get_connector", lambda task_type: fake)

    instance = instances_service.create_instance_from_order(session, user.id, order.id, {})

    with pytest.raises(Exception):
        await instances_service.execute_instance_task(session, instance.id, user.id)


def test_start_stop_release_flow_updates_timestamps(session):
    user, _template, order = asyncio.run(_setup_paid_order(session))
    instance = instances_service.create_instance_from_order(session, user.id, order.id, {})
    assert instance.started_at is None

    instance = instances_service.start_instance(session, instance.id, user.id)
    assert instance.started_at is not None

    instance = instances_service.stop_instance(session, instance.id, user.id)
    assert instance.stopped_at is not None

    instance = instances_service.release_instance(session, instance.id, user.id)
    assert instance.released_at is not None
