import uuid
from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PlatformConnection(SQLModel, table=True):
    """One renter's OAuth grant for one external platform (twitter, discord, ...).

    This table is the only place raw OAuth tokens ever touch disk, and
    always in encrypted form (see crypto.py). Connectors never read it
    directly — instances.service looks up the connection, decrypts the
    token in memory, and injects it into a TaskContext that lives only for
    the duration of one task run.
    """

    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_platform_connection_user_provider"),)

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: str = Field(index=True)
    provider: str = Field(index=True)  # "twitter" | "discord"
    provider_user_id: str
    encrypted_access_token: str
    encrypted_refresh_token: str | None = None
    scopes: str = ""
    expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
