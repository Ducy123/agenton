import uuid

from app.billing.providers.base import PaymentProvider


class MockPaymentProvider(PaymentProvider):
    """Always succeeds. For local development and tests only — swap
    PAYMENT_PROVIDER to a real adapter (Stripe, a crypto processor, ...)
    before accepting real money."""

    async def charge(self, user_id: str, amount_cents: int) -> str:
        return f"mock_{uuid.uuid4().hex[:12]}"
