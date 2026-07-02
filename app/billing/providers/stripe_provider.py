import hashlib
import hmac
import json
import time

import httpx

from app.billing.providers.base import (
    CheckoutProvider,
    CheckoutSession,
    PaymentFailedError,
    PaymentProvider,
    WebhookEvent,
    WebhookVerificationError,
)
from app.config import get_settings

_API_BASE = "https://api.stripe.com/v1"
_WEBHOOK_TOLERANCE_SECONDS = 300


class StripeProvider(PaymentProvider, CheckoutProvider):
    """Talks to Stripe's REST API directly over httpx instead of adding the
    `stripe` SDK as a dependency — Checkout Sessions and webhook signature
    verification are both simple enough to implement against the documented
    HTTP API with stdlib `hmac`, and it keeps this project's dependency
    footprint the same regardless of which payment processor is configured.
    """

    async def charge(self, user_id: str, amount_cents: int) -> str:
        # Stripe has no "charge this user id" primitive for a first-time
        # online recharge without an already-saved payment method — real
        # money always goes through create_checkout_session() below. Being
        # explicit here beats silently pretending a direct charge worked.
        raise PaymentFailedError(
            "Stripe does not support a direct server-side charge for online recharge; "
            "use POST /billing/wallet/recharge/checkout instead"
        )

    async def create_checkout_session(self, user_id: str, amount_cents: int, success_url: str, cancel_url: str) -> CheckoutSession:
        settings = get_settings()
        form = {
            "mode": "payment",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "line_items[0][price_data][currency]": "usd",
            "line_items[0][price_data][product_data][name]": "AgentOn wallet recharge",
            "line_items[0][price_data][unit_amount]": str(amount_cents),
            "line_items[0][quantity]": "1",
            "metadata[user_id]": user_id,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{_API_BASE}/checkout/sessions",
                data=form,
                auth=(settings.stripe_secret_key, ""),
            )
        if resp.status_code >= 400:
            raise PaymentFailedError(f"Stripe checkout session creation failed: {resp.text}")

        body = resp.json()
        return CheckoutSession(checkout_url=body["url"], session_id=body["id"])

    def parse_webhook(self, payload: bytes, signature_header: str) -> WebhookEvent:
        settings = get_settings()
        self._verify_signature(payload, signature_header, settings.stripe_webhook_secret)

        event = json.loads(payload)
        if event.get("type") != "checkout.session.completed":
            return WebhookEvent(kind="ignored")

        session_obj = event["data"]["object"]
        return WebhookEvent(
            kind="checkout_completed",
            session_id=session_obj["id"],
            amount_cents=session_obj.get("amount_total"),
        )

    @staticmethod
    def _verify_signature(payload: bytes, signature_header: str, webhook_secret: str) -> None:
        """Implements Stripe's documented webhook signature scheme by hand:
        the header is `t=<timestamp>,v1=<hex hmac>`, and the signed
        message is `f"{timestamp}.{payload}"` under HMAC-SHA256 with the
        webhook signing secret. See
        https://docs.stripe.com/webhooks#verify-manually
        """
        if not signature_header:
            raise WebhookVerificationError("Missing Stripe-Signature header")

        parts = dict(item.split("=", 1) for item in signature_header.split(",") if "=" in item)
        timestamp = parts.get("t")
        signature = parts.get("v1")
        if not timestamp or not signature:
            raise WebhookVerificationError("Malformed Stripe-Signature header")

        if abs(time.time() - int(timestamp)) > _WEBHOOK_TOLERANCE_SECONDS:
            raise WebhookVerificationError("Stripe webhook timestamp is outside the tolerance window")

        signed_payload = f"{timestamp}.".encode("utf-8") + payload
        expected = hmac.new(webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise WebhookVerificationError("Stripe webhook signature mismatch")
