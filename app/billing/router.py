from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.billing import service
from app.billing.schemas import OrderCreate, OrderRead, RechargeRequest, TransactionRead, WalletRead
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


@router.post("/wallet/recharge", response_model=TransactionRead)
async def recharge_wallet(
    data: RechargeRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return await service.recharge(session, current_user.id, data.amount_cents)


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
