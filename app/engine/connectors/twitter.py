import httpx

from app.engine.connectors.base import TaskConnector, TaskContext, TaskResult

_API_BASE = "https://api.twitter.com/2"


class _TwitterConnectorBase(TaskConnector):
    """Shared plumbing for X (Twitter) connectors.

    All actions run under the *renter's own* OAuth2 user-context access
    token (passed in via `ctx.params["user_access_token"]`), never a
    platform-wide credential — this is delegated automation the account
    owner explicitly authorized, the same model Buffer/Hootsuite use, not
    credential-based scraping or bot login.

    The three-legged OAuth authorize/callback flow that produces that token
    lives outside the execution kernel (it belongs in a future
    `platform/oauth` router); this connector only consumes an already-issued
    token.
    """

    def _token(self, ctx: TaskContext) -> str | None:
        return ctx.params.get("user_access_token")

    def _missing_token_result(self) -> TaskResult:
        return TaskResult(
            success=False,
            message="Missing 'user_access_token' — the renter must complete the X OAuth flow before this task can run",
        )


class TwitterFollowConnector(_TwitterConnectorBase):
    task_type = "twitter_follow"

    async def run(self, ctx: TaskContext) -> TaskResult:
        token = self._token(ctx)
        acting_user_id = ctx.params.get("twitter_user_id")
        target_user_id = ctx.params.get("target_user_id")
        if not token:
            return self._missing_token_result()
        if not acting_user_id or not target_user_id:
            return TaskResult(success=False, message="Missing 'twitter_user_id' or 'target_user_id'")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{_API_BASE}/users/{acting_user_id}/following",
                headers={"Authorization": f"Bearer {token}"},
                json={"target_user_id": target_user_id},
            )
        if resp.status_code >= 400:
            return TaskResult(success=False, message=f"X API error {resp.status_code}: {resp.text}")
        return TaskResult(success=True, message="Followed", data=resp.json())

    async def verify(self, ctx: TaskContext, result: TaskResult) -> TaskResult:
        if not result.success:
            return result
        token = self._token(ctx)
        acting_user_id = ctx.params.get("twitter_user_id")
        target_user_id = ctx.params.get("target_user_id")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{_API_BASE}/users/{acting_user_id}/following",
                headers={"Authorization": f"Bearer {token}"},
                params={"max_results": 1000},
            )
        if resp.status_code >= 400:
            return TaskResult(success=False, message=f"Verification call failed: {resp.status_code}")
        following_ids = {u["id"] for u in resp.json().get("data", [])}
        if target_user_id in following_ids:
            return result
        return TaskResult(success=False, message="Verification failed: target not found in following list")


class TwitterLikeConnector(_TwitterConnectorBase):
    task_type = "twitter_like"

    async def run(self, ctx: TaskContext) -> TaskResult:
        token = self._token(ctx)
        acting_user_id = ctx.params.get("twitter_user_id")
        tweet_id = ctx.params.get("tweet_id")
        if not token:
            return self._missing_token_result()
        if not acting_user_id or not tweet_id:
            return TaskResult(success=False, message="Missing 'twitter_user_id' or 'tweet_id'")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{_API_BASE}/users/{acting_user_id}/likes",
                headers={"Authorization": f"Bearer {token}"},
                json={"tweet_id": tweet_id},
            )
        if resp.status_code >= 400:
            return TaskResult(success=False, message=f"X API error {resp.status_code}: {resp.text}")
        return TaskResult(success=True, message="Liked", data=resp.json())


class TwitterRetweetConnector(_TwitterConnectorBase):
    task_type = "twitter_retweet"

    async def run(self, ctx: TaskContext) -> TaskResult:
        token = self._token(ctx)
        acting_user_id = ctx.params.get("twitter_user_id")
        tweet_id = ctx.params.get("tweet_id")
        if not token:
            return self._missing_token_result()
        if not acting_user_id or not tweet_id:
            return TaskResult(success=False, message="Missing 'twitter_user_id' or 'tweet_id'")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{_API_BASE}/users/{acting_user_id}/retweets",
                headers={"Authorization": f"Bearer {token}"},
                json={"tweet_id": tweet_id},
            )
        if resp.status_code >= 400:
            return TaskResult(success=False, message=f"X API error {resp.status_code}: {resp.text}")
        return TaskResult(success=True, message="Retweeted", data=resp.json())


class TwitterPostConnector(_TwitterConnectorBase):
    task_type = "twitter_post"

    async def run(self, ctx: TaskContext) -> TaskResult:
        token = self._token(ctx)
        text = ctx.params.get("text")
        if not token:
            return self._missing_token_result()
        if not text:
            return TaskResult(success=False, message="Missing 'text'")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{_API_BASE}/tweets",
                headers={"Authorization": f"Bearer {token}"},
                json={"text": text},
            )
        if resp.status_code >= 400:
            return TaskResult(success=False, message=f"X API error {resp.status_code}: {resp.text}")
        return TaskResult(success=True, message="Posted", data=resp.json())


follow_connector = TwitterFollowConnector()
like_connector = TwitterLikeConnector()
retweet_connector = TwitterRetweetConnector()
post_connector = TwitterPostConnector()
