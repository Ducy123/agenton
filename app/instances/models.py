import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.common.enums import InstanceStatus, PricingUnit


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AgentInstance(SQLModel, table=True):
    """A rented, running copy of an AgentTemplate.

    Time-based rentals (hour/day/month) are billed up front via the Order
    that created this instance and simply expire at `expires_at`. Token and
    package pricing meter usage per `execute` call instead — see
    billing.service.meter_consumption, invoked from instances.service.
    """

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: str = Field(index=True)
    template_id: str = Field(index=True)
    order_id: str = Field(index=True, unique=True)

    status: InstanceStatus = InstanceStatus.CREATED
    pricing_unit: PricingUnit
    unit_price_cents: int
    quantity_purchased: int = 1

    task_params: dict = Field(default_factory=dict, sa_column=Column(JSON))

    expires_at: datetime | None = None
    last_run_at: datetime | None = None
    last_result_success: bool | None = None
    last_result_message: str = ""
    fail_streak: int = 0
    auto_paused_reason: str = ""

    created_at: datetime = Field(default_factory=_now)
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    released_at: datetime | None = None
