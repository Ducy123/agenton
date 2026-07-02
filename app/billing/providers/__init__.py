from app.billing.providers.base import PaymentFailedError, PaymentProvider
from app.billing.providers.mock_provider import MockPaymentProvider
from app.config import get_settings

_PROVIDERS: dict[str, PaymentProvider] = {
    "mock": MockPaymentProvider(),
}


def get_payment_provider() -> PaymentProvider:
    """Reads PAYMENT_PROVIDER from settings and returns the matching
    implementation. Register a real one (Stripe, a crypto processor, ...)
    by adding it to `_PROVIDERS` — nothing else in billing/ needs to change."""
    settings = get_settings()
    provider = _PROVIDERS.get(settings.payment_provider)
    if provider is None:
        raise ValueError(f"Unknown PAYMENT_PROVIDER '{settings.payment_provider}'")
    return provider


__all__ = ["PaymentFailedError", "PaymentProvider", "get_payment_provider"]
