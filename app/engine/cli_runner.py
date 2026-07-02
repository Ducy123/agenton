import asyncio
import json
import shutil

from app.config import get_settings


class CliRunnerError(RuntimeError):
    pass


async def run_claude_prompt(
    prompt: str,
    *,
    system_prompt: str | None = None,
    allowed_tools: list[str] | None = None,
    disallowed_tools: list[str] | None = None,
) -> str:
    """Run one Claude Code CLI turn and return its final text output.

    This is the "CLI-as-brain" pattern from javis-os's claude_cli.py: shell
    out to the `claude` binary instead of calling the Anthropic SDK, so
    instances inherit whatever MCP/tool configuration the CLI already has.
    Each call is a fresh, isolated turn (no --resume) since AgentOn
    instances are one-shot task executions, not open-ended chat sessions.

    Uses a flat total timeout rather than javis-os's idle-reset watchdog —
    simpler to reason about for short, bounded rental tasks; revisit if
    AgentOn ever needs long-running interactive CLI sessions.
    """
    settings = get_settings()
    binary = shutil.which(settings.claude_cli_path) or settings.claude_cli_path

    cmd = [binary, "-p", prompt, "--output-format", "json"]
    if system_prompt:
        cmd += ["--append-system-prompt", system_prompt]
    if allowed_tools:
        cmd += ["--allowedTools", ",".join(allowed_tools)]
    if disallowed_tools:
        cmd += ["--disallowedTools", ",".join(disallowed_tools)]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=settings.claude_cli_idle_timeout_seconds
        )
    except asyncio.TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise CliRunnerError("claude CLI timed out") from exc

    if proc.returncode != 0:
        raise CliRunnerError(f"claude CLI exited {proc.returncode}: {stderr.decode(errors='replace')}")

    try:
        payload = json.loads(stdout.decode())
    except json.JSONDecodeError as exc:
        raise CliRunnerError("claude CLI returned non-JSON output") from exc

    return payload.get("result", "")
