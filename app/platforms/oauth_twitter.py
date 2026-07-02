import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx

from app.config import get_settings
from app.platforms.state_token import create_state_token

_AUTHORIZE_URL = "https://twitter.com/i/oauth2/authorize"
_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
_ME_URL = "https://api.twitter.com/2/users/me"

# Matches exactly the connector actions this backend actually performs
# (follow/like/retweet/post) plus offline_access for refresh tokens.
SCOPES = "follows.read follows.write like.read like.write tweet.read tweet.write users.read offline.access"


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(40)).rstrip(b"=").decode("ascii")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verifier, challenge


def build_authorize_url(user_id: str, redirect_uri: str) -> tuple[str, str]:
    """Returns (authorize_url, state). The caller (router) hands the URL
    back as JSON rather than issuing a redirect itself, since this is an
    API-first backend — a frontend renders its own "Connect X" button and
    navigates the browser to `authorize_url`."""
    settings = get_settings()
    verifier, challenge = _pkce_pair()
    state = create_state_token(user_id, "twitter", {"code_verifier": verifier})
    params = {
        "response_type": "code",
        "client_id": settings.twitter_client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"{_AUTHORIZE_URL}?{urlencode(params)}", state


async def exchange_code(code: str, redirect_uri: str, code_verifier: str) -> dict:
    """Returns Twitter's token response: access_token, refresh_token,
    expires_in, scope, token_type."""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
                "client_id": settings.twitter_client_id,
            },
            auth=(settings.twitter_client_id, settings.twitter_client_secret),
        )
    resp.raise_for_status()
    return resp.json()


async def fetch_user_id(access_token: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(_ME_URL, headers={"Authorization": f"Bearer {access_token}"})
    resp.raise_for_status()
    return resp.json()["data"]["id"]
