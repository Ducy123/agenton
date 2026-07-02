import httpx

from app.engine.connectors.base import TaskConnector, TaskContext, TaskResult


class WebVisitConnector(TaskConnector):
    """Fetches a URL to fulfil "visit this page" tasks (referral/quest
    tracking links, landing-page warmup, etc).

    Deliberately a plain HTTP GET rather than a headless browser — add a
    Playwright-backed variant as a separate connector if a target requires
    JS execution or click-through tracking pixels; don't grow this one into
    two responsibilities.
    """

    task_type = "webvisit"

    async def run(self, ctx: TaskContext) -> TaskResult:
        url = ctx.params.get("url")
        if not url:
            return TaskResult(success=False, message="Missing required param 'url'")

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            try:
                resp = await client.get(url)
            except httpx.HTTPError as exc:
                return TaskResult(success=False, message=f"Failed to reach {url}: {exc}")

        if resp.status_code >= 400:
            return TaskResult(success=False, message=f"{url} returned HTTP {resp.status_code}")
        return TaskResult(success=True, message=f"Visited {url}", data={"status_code": resp.status_code})


connector = WebVisitConnector()
