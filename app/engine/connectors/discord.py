import httpx

from app.config import get_settings
from app.engine.connectors.base import TaskConnector, TaskContext, TaskResult

_API_BASE = "https://discord.com/api/v10"


class DiscordJoinConnector(TaskConnector):
    """Adds a renter's Discord account to a target guild.

    Uses Discord's documented "add guild member" flow: the renter completes
    OAuth2 with the `guilds.join` scope (outside this connector) to produce
    a user access token, and AgentOn's own bot (with `CREATE_INSTANT_INVITE`
    / member-management permission in that guild) performs the join on
    their behalf. No bot ever DMs, scrapes, or acts without that per-user
    consent token.
    """

    task_type = "discord_join"

    async def run(self, ctx: TaskContext) -> TaskResult:
        settings = get_settings()
        if not settings.discord_bot_token:
            return TaskResult(success=False, message="DISCORD_BOT_TOKEN is not configured on this server")

        guild_id = ctx.params.get("guild_id")
        discord_user_id = ctx.params.get("discord_user_id")
        user_access_token = ctx.params.get("user_access_token")
        if not guild_id or not discord_user_id or not user_access_token:
            return TaskResult(
                success=False,
                message=(
                    "Missing 'guild_id', 'discord_user_id', or 'user_access_token' — the renter must "
                    "complete Discord OAuth with the guilds.join scope before this task can run"
                ),
            )

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.put(
                f"{_API_BASE}/guilds/{guild_id}/members/{discord_user_id}",
                headers={"Authorization": f"Bot {settings.discord_bot_token}"},
                json={"access_token": user_access_token},
            )
        if resp.status_code in (201, 204):  # 201 joined, 204 already a member
            return TaskResult(success=True, message="Joined Discord server")
        return TaskResult(success=False, message=f"Discord API error {resp.status_code}: {resp.text}")

    async def verify(self, ctx: TaskContext, result: TaskResult) -> TaskResult:
        if not result.success:
            return result
        settings = get_settings()
        guild_id = ctx.params.get("guild_id")
        discord_user_id = ctx.params.get("discord_user_id")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{_API_BASE}/guilds/{guild_id}/members/{discord_user_id}",
                headers={"Authorization": f"Bot {settings.discord_bot_token}"},
            )
        if resp.status_code == 200:
            return result
        return TaskResult(success=False, message="Verification failed: user not found in guild member list")


connector = DiscordJoinConnector()
