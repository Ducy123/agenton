import hashlib
import hmac
import json
import time

import pytest

from app.auth.schemas import UserCreate
from app.auth.service import register_user
from app.billing import service as billing_service
from app.billing.providers.base import CheckoutSession, WebhookEvent, WebhookVerificationError
from app.billing.providers.stripe_provider import StripeProvider
from app.common.enums import RechargeStatus
from app.config import get_settings


def _sign(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    timestamp = timestamp if timestamp is not None else int(time.time())
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    signature = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def test_verify_signature_accepts_valid_signature():
    settings = get_settings()
    settings.stripe_webhook_secret = "whsec_test"
    payload = b'{"type": "checkout.session.completed"}'
    header = _sign(payload, "whsec_test")

    StripeProvider._verify_signature(payload, header, "whsec_test")  # should not raise


def test_verify_signature_rejects_tampered_payload():
    payload = b'{"type": "checkout.session.completed"}'
    header = _sign(payload, "whsec_test")
    tampered = payload + b"tampered"

    with pytest.raises(WebhookVerificationError):
        StripeProvider._verify_signature(tampered, header, "whsec_test")


def test_verify_signature_rejects_missing_header():
    with pytest.raises(WebhookVerificationError):
        StripeProvider._verify_signature(b"{}", "", "whsec_test")


def test_verify_signature_rejects_old_timestamp():
    payload = b"{}"
    old_header = _sign(payload, "whsec_test", timestamp=int(time.time()) - 10_000)
    with pytest.raises(WebhookVerificationError):
        StripeProvider._verify_signature(payload, old_header, "whsec_test")


def test_parse_webhook_extracts_checkout_completed_event():
    settings = get_settings()
    settings.stripe_webhook_secret = "whsec_test"
    provider = StripeProvider()

    event_payload = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_test_123", "amount_total": 2500}},
    }
    payload = json.dumps(event_payload).encode("utf-8")
    header = _sign(payload, "whsec_test")

    event = provider.parse_webhook(payload, header)
    assert event.kind == "checkout_completed"
    assert event.session_id == "cs_test_123"
    assert event.amount_cents == 2500


def test_parse_webhook_ignores_unrelated_event_types():
    settings = get_settings()
    settings.stripe_webhook_secret = "whsec_test"
    provider = StripeProvider()

    payload = json.dumps({"type": "payment_intent.created", "data": {"object": {}}}).encode("utf-8")
    header = _sign(payload, "whsec_test")

    event = provider.parse_webhook(payload, header)
    assert event.kind == "ignored"


class _FakeCheckoutProvider:
    async def create_checkout_session(self, user_id, amount_cents, success_url, cancel_url):
        return CheckoutSession(checkout_url=f"https://fake-checkout.test/{user_id}", session_id="sess_fake_1")

    def parse_webhook(self, payload, signature_header):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_create_recharge_checkout_creates_pending_row(session, monkeypatch):
    user = register_user(session, UserCreate(email="checkout@test.dev", password="password123"))
    fake = _FakeCheckoutProvider()
    monkeypatch.setattr(billing_service, "get_checkout_provider", lambda: fake)

    pending, checkout_url = await billing_service.create_recharge_checkout(
        session, user.id, 2500, "https://app.example/success", "https://app.example/cancel"
    )

    assert pending.status == RechargeStatus.PENDING
    assert pending.amount_cents == 2500
    assert checkout_url == f"https://fake-checkout.test/{user.id}"


@pytest.mark.asyncio
async def test_create_recharge_checkout_rejects_non_positive_amount(session, monkeypatch):
    user = register_user(session, UserCreate(email="checkout2@test.dev", password="password123"))
    monkeypatch.setattr(billing_service, "get_checkout_provider", lambda: _FakeCheckoutProvider())

    with pytest.raises(Exception):
        await billing_service.create_recharge_checkout(session, user.id, 0, "https://a", "https://b")


@pytest.mark.asyncio
async def test_complete_pending_recharge_is_idempotent(session, monkeypatch):
    user = register_user(session, UserCreate(email="webhook@test.dev", password="password123"))
    monkeypatch.setattr(billing_service, "get_checkout_provider", lambda: _FakeCheckoutProvider())

    pending, _url = await billing_service.create_recharge_checkout(session, user.id, 3000, "https://a", "https://b")

    event = WebhookEvent(kind="checkout_completed", session_id=pending.provider_reference, amount_cents=3000)
    billing_service.complete_pending_recharge(session, event)

    wallet = billing_service.get_or_create_wallet(session, user.id)
    assert wallet.balance_cents == 3000

    # A retried/duplicate webhook delivery must not double-credit.
    billing_service.complete_pending_recharge(session, event)
    wallet_again = billing_service.get_or_create_wallet(session, user.id)
    assert wallet_again.balance_cents == 3000


def test_complete_pending_recharge_ignores_unknown_session(session):
    event = WebhookEvent(kind="checkout_completed", session_id="does-not-exist", amount_cents=1000)
    billing_service.complete_pending_recharge(session, event)  # should not raise


def test_complete_pending_recharge_ignores_non_checkout_events(session):
    event = WebhookEvent(kind="ignored")
    billing_service.complete_pending_recharge(session, event)  # should not raise
