from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.common.errors import BadRequestError
from app.config import get_settings
from app.db import get_session
from app.deps import get_current_user
from app.platforms import oauth_discord, oauth_twitter, service
from app.platforms.schemas import AuthorizeUrlResponse, CallbackResult, PlatformConnectionRead
from app.platforms.state_token import InvalidStateError, decode_state_token

router = APIRouter(prefix="/platforms", tags=["platforms"])

# Default token lifetimes used when a provider's token response omits
# expires_in (Discord bot-scoped tokens, mainly).
_DEFAULT_TWITTER_TOKEN_TTL_SECONDS = 7200
_DEFAULT_DISCORD_TOKEN_TTL_SECONDS = 604800


@router.get("", response_model=list[PlatformConnectionRead])
def list_connections(session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return service.list_connections(session, current_user.id)


@router.delete("/{provider}", status_code=204)
def disconnect(provider: str, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    service.delete_connection(session, current_user.id, provider)


@router.get("/twitter/authorize", response_model=AuthorizeUrlResponse)
def twitter_authorize(current_user=Depends(get_current_user)):
    settings = get_settings()
    url, state = oauth_twitter.build_authorize_url(current_user.id, settings.twitter_redirect_uri)
    return AuthorizeUrlResponse(authorize_url=url, state=state)


@router.get("/twitter/callback", response_model=CallbackResult)
async def twitter_callback(code: str, state: str, session: Session = Depends(get_session)):
    settings = get_settings()
    try:
        payload = decode_state_token(state, "twitter")
    except InvalidStateError as exc:
        raise BadRequestError(str(exc)) from exc

    token_data = await oauth_twitter.exchange_code(code, settings.twitter_redirect_uri, payload["code_verifier"])
    twitter_user_id = await oauth_twitter.fetch_user_id(token_data["access_token"])
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", _DEFAULT_TWITTER_TOKEN_TTL_SECONDS))

    service.upsert_connection(
        session,
        user_id=payload["user_id"],
        provider="twitter",
        provider_user_id=twitter_user_id,
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        scopes=token_data.get("scope", ""),
        expires_at=expires_at,
    )
    return CallbackResult(connected=True, provider="twitter")


@router.get("/discord/authorize", response_model=AuthorizeUrlResponse)
def discord_authorize(current_user=Depends(get_current_user)):
    settings = get_settings()
    url, state = oauth_discord.build_authorize_url(current_user.id, settings.discord_redirect_uri)
    return AuthorizeUrlResponse(authorize_url=url, state=state)


@router.get("/discord/callback", response_model=CallbackResult)
async def discord_callback(code: str, state: str, session: Session = Depends(get_session)):
    settings = get_settings()
    try:
        payload = decode_state_token(state, "discord")
    except InvalidStateError as exc:
        raise BadRequestError(str(exc)) from exc

    token_data = await oauth_discord.exchange_code(code, settings.discord_redirect_uri)
    discord_user_id = await oauth_discord.fetch_user_id(token_data["access_token"])
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", _DEFAULT_DISCORD_TOKEN_TTL_SECONDS))

    service.upsert_connection(
        session,
        user_id=payload["user_id"],
        provider="discord",
        provider_user_id=discord_user_id,
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        scopes=token_data.get("scope", ""),
        expires_at=expires_at,
    )
    return CallbackResult(connected=True, provider="discord")
