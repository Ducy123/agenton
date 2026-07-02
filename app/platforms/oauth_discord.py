from urllib.parse import urlencode

import httpx

from app.config import get_settings
from app.platforms.state_token import create_state_token

_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
_TOKEN_URL = "https://discord.com/api/oauth2/token"
_ME_URL = "https://discord.com/api/users/@me"

# guilds.join is what lets AgentOn's bot add the renter to a guild later
# via discord_join — see engine/connectors/discord.py.
SCOPES = "identify guilds.join"


def build_authorize_url(user_id: str, redirect_uri: str) -> tuple[str, str]:
    settings = get_settings()
    state = create_state_token(user_id, "discord")
    params = {
        "response_type": "code",
        "client_id": settings.discord_client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
    }
    return f"{_AUTHORIZE_URL}?{urlencode(params)}", state


async def exchange_code(code: str, redirect_uri: str) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    resp.raise_for_status()
    return resp.json()


async def fetch_user_id(access_token: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(_ME_URL, headers={"Authorization": f"Bearer {access_token}"})
    resp.raise_for_status()
    return resp.json()["id"]
