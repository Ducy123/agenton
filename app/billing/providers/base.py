from abc import ABC, abstractmethod


class PaymentFailedError(RuntimeError):
    pass


class PaymentProvider(ABC):
    """Charges a user's external payment method (card, crypto wallet, ...)
    to fund a recharge. Wallet crediting itself always happens in
    billing.service — providers only ever move money on the outside and
    hand back a reference for the ledger entry."""

    @abstractmethod
    async def charge(self, user_id: str, amount_cents: int) -> str:
        """Returns a provider-side transaction reference on success.

        Raises PaymentFailedError on any failure (declined card, network
        error, ...) — callers must not assume charges silently succeed.
        """
        ...
