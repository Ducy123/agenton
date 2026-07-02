from datetime import datetime

from pydantic import BaseModel

from app.common.enums import PricingUnit


class AgentTemplateCreate(BaseModel):
    slug: str
    name: str
    category: str
    task_type: str
    short_description: str = ""
    long_description: str = ""
    capabilities: list[str] = []
    base_price_cents: int
    pricing_unit: PricingUnit = PricingUnit.HOUR
    icon_url: str = ""


class AgentTemplateRead(BaseModel):
    id: str
    slug: str
    name: str
    category: str
    task_type: str
    short_description: str
    long_description: str
    capabilities: list[str]
    base_price_cents: int
    pricing_unit: PricingUnit
    icon_url: str
    is_active: bool
    created_at: datetime


class AgentTemplateSummary(BaseModel):
    id: str
    slug: str
    name: str
    category: str
    short_description: str
    base_price_cents: int
    pricing_unit: PricingUnit
    icon_url: str
