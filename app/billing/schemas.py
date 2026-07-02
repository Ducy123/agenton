from datetime import datetime

from pydantic import BaseModel

from app.common.enums import OrderStatus, PricingUnit, TransactionKind


class WalletRead(BaseModel):
    balance_cents: int
    auto_renew_enabled: bool
    is_low_balance: bool


class RechargeRequest(BaseModel):
    amount_cents: int


class WalletSettingsUpdate(BaseModel):
    auto_renew_enabled: bool


class RechargeCheckoutRequest(BaseModel):
    amount_cents: int
    success_url: str
    cancel_url: str


class CheckoutSessionRead(BaseModel):
    checkout_url: str
    session_id: str


class TransactionRead(BaseModel):
    id: str
    kind: TransactionKind
    amount_cents: int
    reference: str
    description: str
    created_at: datetime


class OrderCreate(BaseModel):
    template_id: str
    quantity: int = 1


class OrderRead(BaseModel):
    id: str
    template_id: str
    pricing_unit: PricingUnit
    unit_price_cents: int
    quantity: int
    amount_cents: int
    status: OrderStatus
    created_at: datetime
    paid_at: datetime | None
