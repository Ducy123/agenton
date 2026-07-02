from datetime import datetime

from pydantic import BaseModel


class PlatformConnectionRead(BaseModel):
    provider: str
    provider_user_id: str
    scopes: str
    created_at: datetime
    expires_at: datetime | None


class AuthorizeUrlResponse(BaseModel):
    authorize_url: str
    state: str


class CallbackResult(BaseModel):
    connected: bool
    provider: str
