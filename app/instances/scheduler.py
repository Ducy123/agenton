import asyncio
import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.billing.service import charge_for_renewal, get_or_create_wallet
from app.common.enums import InstanceStatus
from app.config import get_settings
from app.db import engine
from app.instances.models import AgentInstance
from app.instances.pricing import TIME_BASED_DURATIONS

logger = logging.getLogger(__name__)


def _handle_expiry(session: Session, instance: AgentInstance, now: datetime) -> None:
    wallet = get_or_create_wallet(session, instance.user_id)
    renewal_cost = instance.unit_price_cents * instance.quantity_purchased
    unit_duration = TIME_BASED_DURATIONS.get(instance.pricing_unit)

    if wallet.auto_renew_enabled and unit_duration and wallet.balance_cents >= renewal_cost:
        charge_for_renewal(session, instance.user_id, renewal_cost, instance.id)
        instance.expires_at = now + (unit_duration * instance.quantity_purchased)
        logger.info("Auto-renewed instance %s for %s cents", instance.id, renewal_cost)
    else:
        instance.status = InstanceStatus.EXPIRED
        logger.info("Instance %s expired (rental period ended)", instance.id)

    session.add(instance)
    session.commit()


def tick_once() -> int:
    """Runs one scheduler pass. Returns how many instances it touched.

    Synchronous by design (plain SQLModel Session, no async driver) — kept
    separate from `run_scheduler_forever` so tests can call it directly
    without spinning up the asyncio loop.
    """
    now = datetime.now(timezone.utc)
    touched = 0
    with Session(engine) as session:
        stmt = select(AgentInstance).where(
            AgentInstance.status == InstanceStatus.RUNNING,
            AgentInstance.expires_at.is_not(None),
            AgentInstance.expires_at <= now,
        )
        for instance in session.exec(stmt).all():
            _handle_expiry(session, instance, now)
            touched += 1
    return touched


async def run_scheduler_forever() -> None:
    settings = get_settings()
    while True:
        try:
            tick_once()
        except Exception:
            logger.exception("Instance scheduler tick failed")
        await asyncio.sleep(settings.instance_tick_seconds)
