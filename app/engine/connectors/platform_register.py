import httpx

from app.engine.connectors.base import TaskConnector, TaskContext, TaskResult


class PlatformRegisterConnector(TaskConnector):
    """Generic "register on an external platform" task.

    Covers the common case of a target platform exposing a plain HTTP
    signup endpoint that accepts a JSON payload (waitlist/referral signups,
    quest-platform registrations, etc). Platforms that require solving a
    real multi-step signup UI or CAPTCHA need a dedicated, bespoke
    connector — this one deliberately stays generic instead of guessing at
    fragile, ToS-risky browser automation.
    """

    task_type = "platform_register"

    async def run(self, ctx: TaskContext) -> TaskResult:
        endpoint = ctx.params.get("registration_endpoint")
        payload = ctx.params.get("payload")
        if not endpoint or payload is None:
            return TaskResult(success=False, message="Missing 'registration_endpoint' or 'payload'")

        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.post(endpoint, json=payload)
            except httpx.HTTPError as exc:
                return TaskResult(success=False, message=f"{endpoint} returned HTTP {resp.status_code}: {resp.text}")

        if resp.status_code >= 400:
            return TaskResult(success=False, message=f"{endpoint} returned HTTP {resp.status_code}: {resp.text}")
        return TaskResult(success=True, message="Registration submitted", data={"status_code": resp.status_code})


connector = PlatformRegisterConnector()
