import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.common.enums import PricingUnit


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AgentTemplate(SQLModel, table=True):
    """A rentable agent product listed in the marketplace.

    `task_type` must match a key registered in
    app.engine.connectors.registry so the execution kernel knows how to run
    instances created from this template.
    """

    id: str = Field(default_factory=_uuid, primary_key=True)
    slug: str = Field(unique=True, index=True)
    name: str
    category: str = Field(index=True)
    task_type: str = Field(index=True)

    short_description: str = ""
    long_description: str = ""
    capabilities: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    base_price_cents: int = 0
    pricing_unit: PricingUnit = PricingUnit.HOUR

    icon_url: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)
