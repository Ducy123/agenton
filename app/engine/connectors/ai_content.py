from app.engine.cli_runner import CliRunnerError, run_claude_prompt
from app.engine.connectors.base import TaskConnector, TaskContext, TaskResult


class AiContentConnector(TaskConnector):
    """Generates text content via the CLI-as-brain runner.

    Image/video generation is a distinct concern (different provider APIs,
    async job polling) — left as a TODO extension point rather than faked
    here; `run()` reports clearly when a requested kind isn't implemented.
    """

    task_type = "ai_content_generation"

    async def run(self, ctx: TaskContext) -> TaskResult:
        brief = ctx.params.get("brief")
        if not brief:
            return TaskResult(success=False, message="Missing required param 'brief'")

        kind = ctx.params.get("kind", "text")
        if kind != "text":
            return TaskResult(
                success=False,
                message=f"Content kind '{kind}' is not implemented yet — only 'text' runs today",
            )

        try:
            output = await run_claude_prompt(
                brief,
                system_prompt=(
                    "You are a content generation worker for a rented AI agent. "
                    "Return only the requested content, no commentary."
                ),
                disallowed_tools=["Bash", "WebFetch", "WebSearch"],
            )
        except CliRunnerError as exc:
            return TaskResult(success=False, message=str(exc))

        return TaskResult(success=True, message="Content generated", data={"content": output})


connector = AiContentConnector()
