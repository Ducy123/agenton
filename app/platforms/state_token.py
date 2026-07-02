from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.config import get_settings

_ALGORITHM = "HS256"
_STATE_TTL_MINUTES = 10


class InvalidStateError(ValueError):
    pass


def create_state_token(user_id: str, provider: str, extra: dict[str, Any] | None = None) -> str:
    """Packs the OAuth `state` param with everything the callback needs
    (which user started the flow, a PKCE code_verifier if any) instead of
    keeping server-side session storage — this backend is stateless between
    requests, so the state token itself has to carry that context, signed
    with the same SECRET_KEY already used for JWTs so it can't be forged."""
    settings = get_settings()
    payload: dict[str, Any] = {
        "user_id": user_id,
        "provider": provider,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_STATE_TTL_MINUTES),
        **(extra or {}),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)


def decode_state_token(token: str, expected_provider: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
    except JWTError as exc:
        raise InvalidStateError("OAuth state is invalid or expired — restart the connect flow") from exc
    if payload.get("provider") != expected_provider:
        raise InvalidStateError("OAuth state does not match the callback provider")
    return payload
