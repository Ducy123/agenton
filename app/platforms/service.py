from datetime import datetime, timezone

from sqlmodel import Session, select

from app.common.errors import NotFoundError
from app.platforms.crypto import decrypt_token, encrypt_token
from app.platforms.models import PlatformConnection


def get_connection(session: Session, user_id: str, provider: str) -> PlatformConnection | None:
    return session.exec(
        select(PlatformConnection).where(PlatformConnection.user_id == user_id, PlatformConnection.provider == provider)
    ).first()


def upsert_connection(
    session: Session,
    user_id: str,
    provider: str,
    provider_user_id: str,
    access_token: str,
    refresh_token: str | None,
    scopes: str,
    expires_at: datetime | None,
) -> PlatformConnection:
    connection = get_connection(session, user_id, provider)
    if connection is None:
        connection = PlatformConnection(user_id=user_id, provider=provider, provider_user_id=provider_user_id, encrypted_access_token="")

    connection.provider_user_id = provider_user_id
    connection.encrypted_access_token = encrypt_token(access_token)
    connection.encrypted_refresh_token = encrypt_token(refresh_token) if refresh_token else None
    connection.scopes = scopes
    connection.expires_at = expires_at
    connection.updated_at = datetime.now(timezone.utc)

    session.add(connection)
    session.commit()
    session.refresh(connection)
    return connection


def list_connections(session: Session, user_id: str) -> list[PlatformConnection]:
    return list(session.exec(select(PlatformConnection).where(PlatformConnection.user_id == user_id)).all())


def delete_connection(session: Session, user_id: str, provider: str) -> None:
    connection = get_connection(session, user_id, provider)
    if not connection:
        raise NotFoundError(f"No '{provider}' connection found for this user")
    session.delete(connection)
    session.commit()


def get_decrypted_access_token(connection: PlatformConnection) -> str:
    return decrypt_token(connection.encrypted_access_token)


_TASK_TYPE_PROVIDER = {
    "twitter_follow": "twitter",
    "twitter_like": "twitter",
    "twitter_retweet": "twitter",
    "twitter_post": "twitter",
    "discord_join": "discord",
}


def inject_credentials(session: Session, user_id: str, task_type: str, params: dict) -> dict:
    """Auto-fills `user_access_token` (and the provider's user id) from a
    stored PlatformConnection so a renter connects once via OAuth instead
    of passing tokens on every `/instances/{id}/execute` call.

    Values already present in `params` always win, so callers (tests,
    multi-account setups) can still override explicitly.
    """
    provider = _TASK_TYPE_PROVIDER.get(task_type)
    if not provider:
        return params

    connection = get_connection(session, user_id, provider)
    if not connection:
        return params

    merged = dict(params)
    merged.setdefault("user_access_token", get_decrypted_access_token(connection))
    if provider == "twitter":
        merged.setdefault("twitter_user_id", connection.provider_user_id)
    elif provider == "discord":
        merged.setdefault("discord_user_id", connection.provider_user_id)
    return merged
