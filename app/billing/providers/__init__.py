from app.billing.providers.base import CheckoutProvider, PaymentFailedError, PaymentProvider, WebhookVerificationError
from app.billing.providers.mock_provider import MockPaymentProvider
from app.billing.providers.stripe_provider import StripeProvider
from app.config import get_settings

_PROVIDERS: dict[str, PaymentProvider] = {
    "mock": MockPaymentProvider(),
    "stripe": StripeProvider(),
}


def get_payment_provider() -> PaymentProvider:
    """Reads PAYMENT_PROVIDER from settings and returns the matching
    implementation. Register a real one by adding it to `_PROVIDERS` —
    nothing else in billing/ needs to change."""
    settings = get_settings()
    provider = _PROVIDERS.get(settings.payment_provider)
    if provider is None:
        raise ValueError(f"Unknown PAYMENT_PROVIDER '{settings.payment_provider}'")
    return provider


def get_checkout_provider() -> CheckoutProvider:
    """Same lookup as get_payment_provider(), but asserts the configured
    provider also implements the hosted-checkout capability (mock does
    not — recharge it via the simple immediate endpoint instead)."""
    provider = get_payment_provider()
    if not isinstance(provider, CheckoutProvider):
        settings = get_settings()
        raise ValueError(f"Provider '{settings.payment_provider}' does not support hosted checkout")
    return provider


__all__ = [
    "CheckoutProvider",
    "PaymentFailedError",
    "PaymentProvider",
    "WebhookVerificationError",
    "get_checkout_provider",
    "get_payment_provider",
]
