from datetime import datetime, timezone

from sqlmodel import Session, select

from app.billing.models import Order
from app.billing.service import meter_consumption
from app.common.enums import InstanceStatus, OrderStatus, PricingUnit
from app.common.errors import ConflictError, ForbiddenError, NotFoundError
from app.engine.connectors.base import TaskContext
from app.engine.connectors.registry import get_connector
from app.engine.verify import execute_with_verification
from app.instances.lifecycle import assert_transition_allowed
from app.instances.models import AgentInstance
from app.instances.pricing import TIME_BASED_DURATIONS
from app.marketplace.service import get_template

_MAX_FAIL_STREAK = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _compute_expiry(pricing_unit: PricingUnit, quantity: int) -> datetime | None:
    unit_duration = TIME_BASED_DURATIONS.get(pricing_unit)
    if unit_duration is None:
        return None
    return _now() + (unit_duration * quantity)


def create_instance_from_order(session: Session, user_id: str, order_id: str, task_params: dict) -> AgentInstance:
    order = session.get(Order, order_id)
    if not order or order.user_id != user_id:
        raise NotFoundError(f"Order '{order_id}' not found")
    if order.status != OrderStatus.PAID:
        raise ConflictError("Order must be paid before an instance can be created")

    existing = session.exec(select(AgentInstance).where(AgentInstance.order_id == order_id)).first()
    if existing:
        raise ConflictError(f"Order '{order_id}' already has an instance")

    template = get_template(session, order.template_id)  # 404s if template was deactivated since purchase

    instance = AgentInstance(
        user_id=user_id,
        template_id=template.id,
        order_id=order.id,
        pricing_unit=order.pricing_unit,
        unit_price_cents=order.unit_price_cents,
        quantity_purchased=order.quantity,
        task_params=task_params,
        expires_at=_compute_expiry(order.pricing_unit, order.quantity),
    )
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance


def _get_owned_instance(session: Session, instance_id: str, user_id: str) -> AgentInstance:
    instance = session.get(AgentInstance, instance_id)
    if not instance:
        raise NotFoundError(f"Instance '{instance_id}' not found")
    if instance.user_id != user_id:
        raise ForbiddenError("This instance belongs to another user")
    return instance


def _transition(session: Session, instance: AgentInstance, target: InstanceStatus) -> AgentInstance:
    assert_transition_allowed(instance.status, target)
    instance.status = target
    now = _now()
    if target == InstanceStatus.RUNNING and instance.started_at is None:
        instance.started_at = now
    elif target == InstanceStatus.STOPPED:
        instance.stopped_at = now
    elif target == InstanceStatus.RELEASED:
        instance.released_at = now
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance


def start_instance(session: Session, instance_id: str, user_id: str) -> AgentInstance:
    instance = _get_owned_instance(session, instance_id, user_id)
    return _transition(session, instance, InstanceStatus.RUNNING)


def pause_instance(session: Session, instance_id: str, user_id: str) -> AgentInstance:
    instance = _get_owned_instance(session, instance_id, user_id)
    return _transition(session, instance, InstanceStatus.PAUSED)


def stop_instance(session: Session, instance_id: str, user_id: str) -> AgentInstance:
    instance = _get_owned_instance(session, instance_id, user_id)
    return _transition(session, instance, InstanceStatus.STOPPED)


def release_instance(session: Session, instance_id: str, user_id: str) -> AgentInstance:
    instance = _get_owned_instance(session, instance_id, user_id)
    return _transition(session, instance, InstanceStatus.RELEASED)


def get_instance(session: Session, instance_id: str, user_id: str) -> AgentInstance:
    return _get_owned_instance(session, instance_id, user_id)


def list_instances(session: Session, user_id: str) -> list[AgentInstance]:
    stmt = select(AgentInstance).where(AgentInstance.user_id == user_id).order_by(AgentInstance.created_at.desc())
    return list(session.exec(stmt).all())


async def execute_instance_task(
    session: Session,
    instance_id: str,
    user_id: str,
    params_override: dict | None = None,
):
    """Runs one task cycle on a RUNNING instance.

    Applies the javis-os "verify before trusting" pattern (see
    engine.verify) and the "3 failures in a row -> auto-pause" self-
    protection pattern from its self-improvement loop, so a broken
    connector or expired external credential can't silently burn through a
    renter's balance forever.
    """
    instance = _get_owned_instance(session, instance_id, user_id)
    if instance.status != InstanceStatus.RUNNING:
        raise ConflictError(f"Instance must be RUNNING to execute a task, currently '{instance.status.value}'")

    template = get_template(session, instance.template_id)
    connector = get_connector(template.task_type)

    params = {**instance.task_params, **(params_override or {})}
    ctx = TaskContext(instance_id=instance.id, user_id=user_id, params=params)
    result = await execute_with_verification(connector, ctx)

    instance.last_run_at = _now()
    instance.last_result_success = result.success
    instance.last_result_message = result.message

    if result.success:
        instance.fail_streak = 0
        if instance.pricing_unit in (PricingUnit.TOKEN, PricingUnit.PACKAGE):
            meter_consumption(
                session,
                user_id,
                instance.unit_price_cents,
                instance.id,
                description=f"Task execution on instance {instance.id}",
            )
    else:
        instance.fail_streak += 1
        if instance.fail_streak >= _MAX_FAIL_STREAK:
            instance.status = InstanceStatus.PAUSED
            instance.auto_paused_reason = f"Auto-paused after {_MAX_FAIL_STREAK} consecutive failures: {result.message}"

    session.add(instance)
    session.commit()
    session.refresh(instance)
    return result, instance
