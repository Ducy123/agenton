# Execution engine

This package is AgentOn's task-execution kernel. It is adapted from
architectural patterns found in [javis-os](https://github.com/blogminhquy/javis-os)
(see `/ANALYSIS-javis-os.md` at the repo root for the full writeup), reshaped
for a multi-tenant rental platform instead of a single-user personal
assistant:

- **`cli_runner.py`** — the "CLI-as-brain" pattern: instead of calling the
  Anthropic SDK directly, it shells out to the `claude` CLI as a subprocess.
  This gives every AI-generation task instance-level tool access, streaming
  output, and an idle-timeout watchdog, without re-implementing any of that
  in AgentOn itself.
- **`connectors/`** — the pluggable task-type abstraction. Each task type the
  marketplace can sell (AI content generation, X/Twitter actions, Discord
  join, web visits, platform registration, ...) is one `TaskConnector`
  implementation registered under a string key. Adding a new sellable task
  type never touches billing, marketplace, or instance code — you add one
  file here and register it in `connectors/bootstrap.py`.
- **`verify.py`** — the independent-verification pattern from javis-os's
  self-improvement loop: a second, read-only pass that checks whether a task
  actually completed instead of trusting the connector's own report.

None of this package talks to the database directly — it receives a
`TaskContext` and returns a `TaskResult`. The `instances` module is the only
caller.
