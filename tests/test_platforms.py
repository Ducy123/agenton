import base64
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.auth.schemas import UserCreate
from app.auth.service import register_user
from app.config import get_settings
from app.platforms import service as platforms_service
from app.platforms.crypto import decrypt_token, encrypt_token
from app.platforms.oauth_twitter import _pkce_pair, build_authorize_url
from app.platforms.state_token import InvalidStateError, create_state_token, decode_state_token


def test_encrypt_decrypt_round_trip():
    ciphertext = encrypt_token("super-secret-access-token")
    assert ciphertext != "super-secret-access-token"
    assert decrypt_token(ciphertext) == "super-secret-access-token"


def test_pkce_pair_challenge_matches_verifier():
    verifier, challenge = _pkce_pair()
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    assert challenge == expected


def test_build_authorize_url_contains_pkce_and_state():
    url, state = build_authorize_url("user-1", "http://localhost/callback")
    assert "code_challenge=" in url
    assert "code_challenge_method=S256" in url
    assert state in url


def test_state_token_round_trip():
    token = create_state_token("user-1", "twitter", {"code_verifier": "abc"})
    payload = decode_state_token(token, "twitter")
    assert payload["user_id"] == "user-1"
    assert payload["code_verifier"] == "abc"


def test_state_token_rejects_wrong_provider():
    token = create_state_token("user-1", "twitter")
    with pytest.raises(InvalidStateError):
        decode_state_token(token, "discord")


def test_state_token_rejects_expired():
    settings = get_settings()
    expired_payload = {
        "user_id": "user-1",
        "provider": "twitter",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    token = jwt.encode(expired_payload, settings.secret_key, algorithm="HS256")
    with pytest.raises(InvalidStateError):
        decode_state_token(token, "twitter")


def test_connection_crud(session):
    user = register_user(session, UserCreate(email="platform@test.dev", password="password123"))

    assert platforms_service.get_connection(session, user.id, "twitter") is None

    connection = platforms_service.upsert_connection(
        session,
        user_id=user.id,
        provider="twitter",
        provider_user_id="tw-123",
        access_token="tok-abc",
        refresh_token="ref-abc",
        scopes="follows.write",
        expires_at=None,
    )
    assert connection.provider_user_id == "tw-123"
    assert platforms_service.get_decrypted_access_token(connection) == "tok-abc"

    connections = platforms_service.list_connections(session, user.id)
    assert len(connections) == 1

    # Reconnecting overwrites rather than duplicating.
    platforms_service.upsert_connection(
        session,
        user_id=user.id,
        provider="twitter",
        provider_user_id="tw-456",
        access_token="tok-new",
        refresh_token=None,
        scopes="follows.write",
        expires_at=None,
    )
    connections = platforms_service.list_connections(session, user.id)
    assert len(connections) == 1
    assert connections[0].provider_user_id == "tw-456"

    platforms_service.delete_connection(session, user.id, "twitter")
    assert platforms_service.get_connection(session, user.id, "twitter") is None


def test_inject_credentials_fills_from_stored_connection(session):
    user = register_user(session, UserCreate(email="inject@test.dev", password="password123"))
    platforms_service.upsert_connection(
        session,
        user_id=user.id,
        provider="twitter",
        provider_user_id="tw-999",
        access_token="tok-999",
        refresh_token=None,
        scopes="follows.write",
        expires_at=None,
    )

    params = platforms_service.inject_credentials(session, user.id, "twitter_follow", {"target_user_id": "target-1"})
    assert params["user_access_token"] == "tok-999"
    assert params["twitter_user_id"] == "tw-999"
    assert params["target_user_id"] == "target-1"


def test_inject_credentials_explicit_override_wins(session):
    user = register_user(session, UserCreate(email="override@test.dev", password="password123"))
    platforms_service.upsert_connection(
        session,
        user_id=user.id,
        provider="twitter",
        provider_user_id="tw-1",
        access_token="tok-1",
        refresh_token=None,
        scopes="",
        expires_at=None,
    )

    params = platforms_service.inject_credentials(session, user.id, "twitter_follow", {"user_access_token": "manual-override"})
    assert params["user_access_token"] == "manual-override"


def test_inject_credentials_noop_without_connection(session):
    user = register_user(session, UserCreate(email="noconn@test.dev", password="password123"))
    params = platforms_service.inject_credentials(session, user.id, "twitter_follow", {"target_user_id": "t1"})
    assert "user_access_token" not in params


def test_inject_credentials_noop_for_unrelated_task_type(session):
    user = register_user(session, UserCreate(email="unrelated@test.dev", password="password123"))
    params = platforms_service.inject_credentials(session, user.id, "webvisit", {"url": "https://example.com"})
    assert params == {"url": "https://example.com"}


def test_twitter_authorize_requires_auth(client):
    resp = client.get("/platforms/twitter/authorize")
    assert resp.status_code == 401


def test_twitter_callback_stores_connection(client, register_and_login, monkeypatch):
    headers = register_and_login("twcallback@test.dev")

    authorize = client.get("/platforms/twitter/authorize", headers=headers).json()
    state = authorize["state"]

    async def fake_exchange_code(code, redirect_uri, code_verifier):
        assert code == "auth-code-123"
        return {"access_token": "tok-live", "refresh_token": "ref-live", "expires_in": 7200, "scope": "follows.write"}

    async def fake_fetch_user_id(access_token):
        assert access_token == "tok-live"
        return "twitter-uid-live"

    monkeypatch.setattr("app.platforms.router.oauth_twitter.exchange_code", fake_exchange_code)
    monkeypatch.setattr("app.platforms.router.oauth_twitter.fetch_user_id", fake_fetch_user_id)

    resp = client.get("/platforms/twitter/callback", params={"code": "auth-code-123", "state": state})
    assert resp.status_code == 200
    assert resp.json() == {"connected": True, "provider": "twitter"}

    connections = client.get("/platforms", headers=headers).json()
    assert len(connections) == 1
    assert connections[0]["provider"] == "twitter"
    assert connections[0]["provider_user_id"] == "twitter-uid-live"


def test_callback_rejects_bad_state(client):
    resp = client.get("/platforms/twitter/callback", params={"code": "x", "state": "not-a-real-token"})
    assert resp.status_code == 400


def test_disconnect_platform(client, register_and_login, monkeypatch):
    headers = register_and_login("disconnect@test.dev")
    authorize = client.get("/platforms/discord/authorize", headers=headers).json()
    state = authorize["state"]

    async def fake_exchange_code(code, redirect_uri):
        return {"access_token": "dc-tok", "refresh_token": None, "expires_in": 604800, "scope": "identify guilds.join"}

    async def fake_fetch_user_id(access_token):
        return "discord-uid-1"

    monkeypatch.setattr("app.platforms.router.oauth_discord.exchange_code", fake_exchange_code)
    monkeypatch.setattr("app.platforms.router.oauth_discord.fetch_user_id", fake_fetch_user_id)

    client.get("/platforms/discord/callback", params={"code": "y", "state": state})
    assert len(client.get("/platforms", headers=headers).json()) == 1

    resp = client.delete("/platforms/discord", headers=headers)
    assert resp.status_code == 204
    assert client.get("/platforms", headers=headers).json() == []
