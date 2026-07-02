from abc import ABC, abstractmethod

from pydantic import BaseModel


class PaymentFailedError(RuntimeError):
    pass


class WebhookVerificationError(RuntimeError):
    pass


class PaymentProvider(ABC):
    """Charges a user's external payment method (card, crypto wallet, ...)
    to fund a recharge. Wallet crediting itself always happens in
    billing.service — providers only ever move money on the outside and
    hand back a reference for the ledger entry.

    This synchronous `charge()` method models a provider that can debit an
    already-on-file payment method directly (or a test/mock provider). Real
    card processors like Stripe can't do that for a first-time online
    recharge — see `CheckoutProvider` below for that flow instead.
    """

    @abstractmethod
    async def charge(self, user_id: str, amount_cents: int) -> str:
        """Returns a provider-side transaction reference on success.

        Raises PaymentFailedError on any failure (declined card, network
        error, ...) — callers must not assume charges silently succeed.
        """
        ...


class CheckoutSession(BaseModel):
    checkout_url: str
    session_id: str


class WebhookEvent(BaseModel):
    """Normalized result of verifying+parsing a provider webhook payload.

    `kind` is "checkout_completed" for a successful payment notification;
    any other value means the caller should acknowledge and ignore it
    (Stripe sends many event types AgentOn doesn't care about).
    """

    kind: str
    session_id: str | None = None
    amount_cents: int | None = None


class CheckoutProvider(ABC):
    """Optional capability for providers whose real payment flow requires
    the renter to complete a hosted checkout page rather than an immediate
    server-side charge — this is how Stripe (and most real card
    processors) actually work for a first-time online recharge.
    """

    @abstractmethod
    async def create_checkout_session(self, user_id: str, amount_cents: int, success_url: str, cancel_url: str) -> CheckoutSession: ...

    @abstractmethod
    def parse_webhook(self, payload: bytes, signature_header: str) -> WebhookEvent:
        """Verifies the webhook signature and extracts the fields billing.service
        needs. Raises WebhookVerificationError if the signature doesn't check out —
        callers must reject the request (never trust an unverified webhook body)."""
        ...
