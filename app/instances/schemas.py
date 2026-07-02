from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.common.enums import InstanceStatus, PricingUnit


class InstanceCreate(BaseModel):
    order_id: str
    task_params: dict[str, Any] = {}


class InstanceRead(BaseModel):
    id: str
    template_id: str
    order_id: str
    status: InstanceStatus
    pricing_unit: PricingUnit
    unit_price_cents: int
    quantity_purchased: int
    expires_at: datetime | None
    last_run_at: datetime | None
    last_result_success: bool | None
    last_result_message: str
    fail_streak: int
    auto_paused_reason: str
    created_at: datetime
    started_at: datetime | None
    stopped_at: datetime | None
    released_at: datetime | None


class InstanceExecuteRequest(BaseModel):
    params_override: dict[str, Any] = {}


class InstanceExecuteResponse(BaseModel):
    success: bool
    message: str
    data: dict[str, Any] = {}
    instance_status: InstanceStatus
