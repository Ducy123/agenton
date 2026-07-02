import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

from app.common.enums import OrderStatus, PricingUnit, TransactionKind


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Wallet(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: str = Field(unique=True, index=True)
    balance_cents: int = 0
    auto_renew_enabled: bool = False
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Transaction(SQLModel, table=True):
    """Append-only ledger entry. Never mutated or deleted — corrections are
    new offsetting entries (kind=refund), so `list_transactions` always
    reflects the true consumption history."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    wallet_id: str = Field(index=True)
    kind: TransactionKind
    amount_cents: int  # positive = credit, negative = debit
    reference: str = ""  # order_id or instance_id this entry relates to
    description: str = ""
    created_at: datetime = Field(default_factory=_now)


class Order(SQLModel, table=True):
    """Snapshots pricing at purchase time so later template price changes
    never rewrite history."""

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: str = Field(index=True)
    template_id: str = Field(index=True)
    pricing_unit: PricingUnit
    unit_price_cents: int
    quantity: int = 1
    amount_cents: int
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = Field(default_factory=_now)
    paid_at: datetime | None = None
