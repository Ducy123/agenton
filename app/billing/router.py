from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.billing import service
from app.billing.providers.base import WebhookVerificationError
from app.billing.schemas import (
    CheckoutSessionRead,
    OrderCreate,
    OrderRead,
    RechargeCheckoutRequest,
    RechargeRequest,
    TransactionRead,
    WalletRead,
    WalletSettingsUpdate,
)
from app.common.errors import BadRequestError
from app.common.pagination import Page
from app.db import get_session
from app.deps import get_current_user

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/wallet", response_model=WalletRead)
def get_wallet(session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    wallet = service.get_or_create_wallet(session, current_user.id)
    return WalletRead(
        balance_cents=wallet.balance_cents,
        auto_renew_enabled=wallet.auto_renew_enabled,
        is_low_balance=service.is_low_balance(wallet),
    )


@router.patch("/wallet/settings", response_model=WalletRead)
def update_wallet_settings(
    data: WalletSettingsUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    wallet = service.set_auto_renew(session, current_user.id, data.auto_renew_enabled)
    return WalletRead(
        balance_cents=wallet.balance_cents,
        auto_renew_enabled=wallet.auto_renew_enabled,
        is_low_balance=service.is_low_balance(wallet),
    )


@router.post("/wallet/recharge", response_model=TransactionRead)
async def recharge_wallet(
    data: RechargeRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return await service.recharge(session, current_user.id, data.amount_cents)


@router.post("/wallet/recharge/checkout", response_model=CheckoutSessionRead)
async def create_recharge_checkout(
    data: RechargeCheckoutRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Starts a hosted-checkout recharge (Stripe etc.) — the wallet is
    credited later by the webhook once payment actually completes, not by
    this call. See POST /billing/webhooks/stripe."""
    pending, checkout_url = await service.create_recharge_checkout(
        session, current_user.id, data.amount_cents, data.success_url, data.cancel_url
    )
    return CheckoutSessionRead(checkout_url=checkout_url, session_id=pending.provider_reference)


@router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(request: Request, session: Session = Depends(get_session)):
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        service.handle_stripe_webhook(session, payload, signature)
    except WebhookVerificationError as exc:
        raise BadRequestError(str(exc)) from exc
    return {"received": True}


@router.get("/transactions", response_model=Page[TransactionRead])
def get_transactions(
    page: int = 1,
    page_size: int = 50,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    items, total = service.list_transactions(session, current_user.id, page, page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/orders", response_model=OrderRead, status_code=201)
def create_order(
    data: OrderCreate,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return service.create_order(session, current_user.id, data.template_id, data.quantity)


@router.get("/orders/{order_id}", response_model=OrderRead)
def get_order(
    order_id: str,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return service.get_order(session, order_id, current_user.id)


@router.post("/orders/{order_id}/pay", response_model=OrderRead)
def pay_order(
    order_id: str,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return service.pay_order(session, order_id, current_user.id)
