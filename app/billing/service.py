from datetime import datetime, timezone

from sqlmodel import Session, select

from app.billing.models import Order, PendingRecharge, Transaction, Wallet
from app.billing.providers import PaymentFailedError, get_checkout_provider, get_payment_provider
from app.billing.providers.base import WebhookEvent
from app.common.enums import OrderStatus, RechargeStatus, TransactionKind
from app.common.errors import ConflictError, InsufficientBalanceError, NotFoundError
from app.config import get_settings
from app.marketplace.service import get_template


def get_or_create_wallet(session: Session, user_id: str) -> Wallet:
    wallet = session.exec(select(Wallet).where(Wallet.user_id == user_id)).first()
    if wallet:
        return wallet
    wallet = Wallet(user_id=user_id)
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return wallet


def is_low_balance(wallet: Wallet) -> bool:
    return wallet.balance_cents < get_settings().low_balance_threshold_cents


def set_auto_renew(session: Session, user_id: str, enabled: bool) -> Wallet:
    wallet = get_or_create_wallet(session, user_id)
    wallet.auto_renew_enabled = enabled
    wallet.updated_at = datetime.now(timezone.utc)
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return wallet


async def recharge(session: Session, user_id: str, amount_cents: int) -> Transaction:
    if amount_cents <= 0:
        raise ConflictError("Recharge amount must be positive")

    wallet = get_or_create_wallet(session, user_id)
    provider = get_payment_provider()
    try:
        provider_ref = await provider.charge(user_id, amount_cents)
    except PaymentFailedError as exc:
        raise ConflictError(f"Payment failed: {exc}") from exc

    wallet.balance_cents += amount_cents
    wallet.updated_at = datetime.now(timezone.utc)
    txn = Transaction(
        wallet_id=wallet.id,
        kind=TransactionKind.RECHARGE,
        amount_cents=amount_cents,
        reference=provider_ref,
        description="Wallet recharge",
    )
    session.add(wallet)
    session.add(txn)
    session.commit()
    session.refresh(txn)
    return txn


def create_order(session: Session, user_id: str, template_id: str, quantity: int) -> Order:
    if quantity <= 0:
        raise ConflictError("Quantity must be positive")

    template = get_template(session, template_id)
    order = Order(
        user_id=user_id,
        template_id=template.id,
        pricing_unit=template.pricing_unit,
        unit_price_cents=template.base_price_cents,
        quantity=quantity,
        amount_cents=template.base_price_cents * quantity,
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def pay_order(session: Session, order_id: str, user_id: str) -> Order:
    order = session.get(Order, order_id)
    if not order or order.user_id != user_id:
        raise NotFoundError(f"Order '{order_id}' not found")
    if order.status != OrderStatus.PENDING:
        raise ConflictError(f"Order is already '{order.status.value}'")

    wallet = get_or_create_wallet(session, user_id)
    if wallet.balance_cents < order.amount_cents:
        raise InsufficientBalanceError(
            f"Wallet balance {wallet.balance_cents} cents is less than order amount {order.amount_cents} cents — recharge first"
        )

    wallet.balance_cents -= order.amount_cents
    wallet.updated_at = datetime.now(timezone.utc)
    order.status = OrderStatus.PAID
    order.paid_at = datetime.now(timezone.utc)
    txn = Transaction(
        wallet_id=wallet.id,
        kind=TransactionKind.ORDER_PAYMENT,
        amount_cents=-order.amount_cents,
        reference=order.id,
        description=f"Rental order for template {order.template_id}",
    )
    session.add(wallet)
    session.add(order)
    session.add(txn)
    session.commit()
    session.refresh(order)
    return order


def get_order(session: Session, order_id: str, user_id: str) -> Order:
    order = session.get(Order, order_id)
    if not order or order.user_id != user_id:
        raise NotFoundError(f"Order '{order_id}' not found")
    return order


def _debit(session: Session, user_id: str, amount_cents: int, kind: TransactionKind, reference: str, description: str) -> Transaction:
    wallet = get_or_create_wallet(session, user_id)
    wallet.balance_cents -= amount_cents
    wallet.updated_at = datetime.now(timezone.utc)
    txn = Transaction(
        wallet_id=wallet.id,
        kind=kind,
        amount_cents=-amount_cents,
        reference=reference,
        description=description,
    )
    session.add(wallet)
    session.add(txn)
    session.commit()
    session.refresh(txn)
    return txn


def meter_consumption(session: Session, user_id: str, amount_cents: int, instance_id: str, description: str = "") -> Transaction:
    """Debits ongoing token/compute usage from the wallet.

    Allowed to push the balance negative on purpose: metering happens after
    the fact (usage already occurred), so the instance scheduler is
    responsible for stopping/pausing an instance once balance turns negative
    rather than this function refusing to record real usage.
    """
    return _debit(session, user_id, amount_cents, TransactionKind.CONSUMPTION, instance_id, description or "Agent instance usage")


def charge_for_renewal(session: Session, user_id: str, amount_cents: int, instance_id: str) -> Transaction:
    """Debits a time-based rental renewal. Callers must check
    `wallet.balance_cents >= amount_cents` themselves first — unlike
    metered consumption, a renewal is a fresh purchase, not unavoidable
    already-happened usage, so it should never be allowed to go negative."""
    return _debit(session, user_id, amount_cents, TransactionKind.ORDER_PAYMENT, instance_id, "Auto-renewal charge")


def list_transactions(session: Session, user_id: str, page: int = 1, page_size: int = 50) -> tuple[list[Transaction], int]:
    wallet = get_or_create_wallet(session, user_id)
    stmt = select(Transaction).where(Transaction.wallet_id == wallet.id).order_by(Transaction.created_at.desc())
    all_rows = session.exec(stmt).all()
    total = len(all_rows)
    start = max(page - 1, 0) * page_size
    return all_rows[start : start + page_size], total


async def create_recharge_checkout(session: Session, user_id: str, amount_cents: int, success_url: str, cancel_url: str) -> tuple[PendingRecharge, str]:
    """Starts the hosted-checkout recharge flow (Stripe etc.) — unlike
    `recharge()` above, the wallet is NOT credited here. It's credited only
    once `complete_pending_recharge` runs from a verified webhook, since
    the renter still has to actually complete payment on the provider's
    page after this call returns. Returns (pending record, checkout URL) —
    the URL itself is provider state, not persisted on our side.
    """
    if amount_cents <= 0:
        raise ConflictError("Recharge amount must be positive")

    settings = get_settings()
    provider = get_checkout_provider()
    checkout = await provider.create_checkout_session(user_id, amount_cents, success_url, cancel_url)

    pending = PendingRecharge(
        user_id=user_id,
        amount_cents=amount_cents,
        provider=settings.payment_provider,
        provider_reference=checkout.session_id,
    )
    session.add(pending)
    session.commit()
    session.refresh(pending)
    return pending, checkout.checkout_url


def complete_pending_recharge(session: Session, event: WebhookEvent) -> None:
    """Credits the wallet for a completed checkout session. Idempotent by
    design: a webhook the provider retries (or a replayed/duplicate
    delivery) looks up the same PendingRecharge row and no-ops once its
    status is already COMPLETED, so the wallet is never double-credited.
    """
    if event.kind != "checkout_completed" or not event.session_id:
        return

    pending = session.exec(select(PendingRecharge).where(PendingRecharge.provider_reference == event.session_id)).first()
    if not pending or pending.status == RechargeStatus.COMPLETED:
        return

    wallet = get_or_create_wallet(session, pending.user_id)
    wallet.balance_cents += pending.amount_cents
    wallet.updated_at = datetime.now(timezone.utc)
    txn = Transaction(
        wallet_id=wallet.id,
        kind=TransactionKind.RECHARGE,
        amount_cents=pending.amount_cents,
        reference=pending.provider_reference,
        description="Hosted checkout recharge",
    )
    pending.status = RechargeStatus.COMPLETED
    pending.completed_at = datetime.now(timezone.utc)

    session.add(wallet)
    session.add(txn)
    session.add(pending)
    session.commit()


def handle_stripe_webhook(session: Session, payload: bytes, signature_header: str) -> None:
    provider = get_checkout_provider()
    event = provider.parse_webhook(payload, signature_header)
    complete_pending_recharge(session, event)
