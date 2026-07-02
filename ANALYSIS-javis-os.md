# Javis OS Analysis — reference document for building agenton

> Source: https://github.com/blogminhquy/javis-os (cloned into `_reference-javis-os/`, gitignored)
> Analysis date: 2026-07-02

---

## PART 1 — PRODUCT & FEATURES

### 1.1 Product concept

Javis OS is not a chatbot — it's an **"AI operating layer"** that runs on a personal machine or VPS. The core differentiator: it **never calls the Anthropic/OpenAI API directly**. Instead it "rides on top of" an already-installed **Claude Code CLI** or **Codex CLI**, reusing the Pro/Max subscription the user already pays for (no extra API cost), while inheriting that CLI's file read/write access, MCP tools, skills, and sessions for free.

Wrapped around that CLI "brain," the product packages: a dashboard with a 3D knowledge graph, Vietnamese voice control, a "Second Brain" that accumulates durable knowledge over time (Sources → Wiki), and a self-improvement loop that runs in the background.

A philosophy repeated throughout the docs: *"distill raw knowledge into a Wiki once, then keep it alive with every new source"* — knowledge accumulates instead of being rediscovered on every question.

### 1.2 Full feature list (15 groups)

| Group | Key features |
|---|---|
| **Chat & Voice** | Push-to-talk (hold Space), hands-free mode (auto VAD ~1.5s silence), Edge TTS with 2 Vietnamese voices, file/image attachments (read-only by default — must explicitly ask to save), Esc to stop playback |
| **3D knowledge graph** | Every `.md` file is a node, every `[[wikilink]]` is an edge, reacts to voice/thinking activity, auto-pauses when the tab is hidden (saves resources), real-time new nodes |
| **Sessions** | SQLite + full-text search, rename/delete, auto-titled from the first question, scoped per brain |
| **File manager** | Browse/edit/upload/download within the selected brain's scope, path-traversal guard, 2MB limit for inline editing |
| **Skills** | `.claude/skills/<slug>/SKILL.md`, disabling = moving into `.disabled/`, only works when the engine is Claude Code CLI |
| **Agents/Workflows (Studio)** | Multi-step, a verification agent that self-corrects up to N times, per-agent model selection, but background execution always forces Claude Code (safety) |
| **Self-improvement loop** | Multi-loop, 3 permission levels (suggest/auto/full), auto-pauses after 3 consecutive failures, read-only Wiki linter |
| **MCP & metrics** | Multiple shops behind the same URL with different tokens, tool denylist → read-only mode, data cache for closed periods (saves cost) |
| **Model/Engine** | 5 providers (Claude CLI, Codex CLI, OpenRouter, Anthropic API, OpenAI API), separate Main + Auxiliary + reasoning-level settings |
| **Telegram bot** | Long-polling, chat-ID whitelist, commands `/cli /or /model /stop`, explicit warning that "test message sent OK" ≠ "bot is actually receiving messages" |
| **Automation/Scheduling** | Mostly just a registry (doesn't run itself) — what actually runs is the internal loop + cloud routine sync |
| **Second Brain** | `sources/` → `wiki/` + `memory/`, multi-brain, memory facts carry provenance, auto-learns every 6 turns |
| **Security** | PBKDF2-HMAC-SHA256 with 120k rounds, fail-closed (host ≠ loopback → login forced on), dual rate-limiting (8 failed attempts / 5 minutes) |
| **Branding/Domain** | Caddy On-Demand TLS (regular VPS) vs. Traefik (Hostinger) — two entirely different mechanisms |
| **GitHub backup** | Force-push mirror of the entire `brains/` directory, a "clean mirror" (strips logs/locks/nested `.git`) before pushing |

### 1.3 Installation/deployment paths (7 routes)

| # | Path | File | Notes |
|---|---|---|---|
| 1 | Hostinger Docker Manager | `docker-compose.hostinger.yml` | Traefik labels built in, `DOMAIN_NAME` for free HTTPS, updates via Redeploy |
| 2 | Docker on any VPS (pull) | `docker-compose.yml` | GHCR image, healthcheck, Watchtower (`update` profile, off by default), Cloudflare Tunnel (`tunnel` profile) |
| 3 | Docker build from source | `docker-compose.build.yml` | `--build`, used when forking/modifying code |
| 4 | Automatic HTTPS via Caddy | `docker-compose.https.yml` | On-Demand TLS, domain entered in the app UI, gated through `/tls-check` |
| 5 | Native Linux/macOS | `install.sh` | Auto-installs Python/Node 22/Claude CLI, registers systemd, falls back to nohup |
| 6 | Windows | `setup.bat`/`start-javis.vbs`/`stop-javis.bat` | Foreground vs. hidden background, auto-kills the old process on port 7777 |
| 7 | Direct systemd | `javis.service` | A template requiring `sed` to substitute placeholders |

### 1.4 The 20 most important "hidden corner" details

1. **SETUP TOKEN** — generated once when running publicly with no admin account yet, readable from a log line or the `.setup_token` file, self-destructs after first use.
2. **Voice requires HTTPS** — the Web Speech API never grants microphone access over a bare IP, only over `https://` or `localhost`, hence the hard requirement for a domain or tunnel.
3. **Telegram 409 error** — the same bot token is running in two places at once; "send test succeeded" does **not** prove the bot is actually receiving messages.
4. **Codex model auto-"coercion"** — if configured to a regular API model while running under a Codex subscription, the system silently swaps in a valid Codex model.
5. **Safe agent execution in the background** — Studio lets you pick Codex/GPT for an agent, but the background dispatcher always forces Claude Code.
6. **3 loop permission levels** — a loop created via chat always defaults to `suggest` + disabled; `full` is only ever set when the user explicitly and unambiguously asks for it.
7. **Em dash (—) is banned** from every output — it makes the TTS engine stumble; this is a hard rule baked into the system prompt.
8. **Data cache for closed periods** — only re-queries MCP for the current period; past periods are served from cache.
9. **Safe brain-structure normalization** — only moves files when the destination doesn't already exist, so re-running it is harmless.
10. **Login reset** — delete the `"auth"` block in `settings.json`; `reset-auth.bat` automates this on Windows.
11. **GitHub backup = force-push mirror** — only one machine should ever push to a given repo.
12. **Fail-closed security** — host ≠ loopback automatically forces login on, no configuration required.
13. **Secure cookies can cause a login loop** when running behind an HTTP-only proxy — called out explicitly as a common mistake.
14. **Dual rate-limiting** — a 5-minute lockout after 8 consecutive failures, plus a 0.5s delay added to every failed attempt.
15. **Watchtower lives in its own profile** (off by default) because it needs the Docker socket, which Hostinger often blocks.
16. **Quick tunnel vs. named tunnel** (Cloudflare) — quick tunnels get a new URL on every restart; a fixed URL needs a named tunnel with a `TUNNEL_TOKEN`.
17. **Traefik on Hostinger: do NOT declare `networks:`/`external`** — this used to cause "network not found" errors.
18. **On-Demand TLS has its own gatekeeper** (`/tls-check`) to prevent abuse of Let's Encrypt's rate limits.
19. **`automations.json` contains personal data** (chat IDs, trigger IDs) — be careful when sharing a brain.
20. **One-time auto-migration** — an old `loop_config.json` auto-generates `Javis/loops/vong-lap-goc.md` (keeping the original `custom_goal`) and the old JSON file is kept as a backup.

### 1.5 Vietnamese-to-technical glossary

| Vietnamese term | Technical meaning |
|---|---|
| Bộ não (brain) | The CLI engine (Claude Code/Codex) acting as the AI backend |
| Second Brain | External knowledge base — a Markdown vault (Sources + Wiki + Memory) |
| Wikilink | `[[Note name]]` Obsidian-style syntax → an edge in the graph |
| INGEST | The pipeline that turns a raw file into a note, then distills it into the Wiki |
| Self-improvement loop | A scheduled, agentic background task |
| Self-learning / rewire | Memory consolidation from conversation logs |
| Suggest / Auto+verify / Full | The `suggest` / `auto` / `full` loop modes |
| SETUP TOKEN | A one-time-use secret token |
| Tool denylist → read-only | Blocking specific tools → read-only mode for an MCP server |
| Brain | One independent second-brain vault (multi-brain = multi-vault) |
| Verifier | An independent agent that plays devil's advocate in a workflow |
| Wiki linter | A read-only health check — reports issues without auto-fixing them |

---

## PART 2 — TECHNICAL ARCHITECTURE

### 2.1 Tech stack

**Backend**: FastAPI + Uvicorn (ASGI, single process), httpx (async, used for every outbound call), hand-rolled auth (PBKDF2-HMAC-SHA256, 120k rounds), `edge-tts` for text-to-speech, PyYAML for frontmatter. **No ORM, no vector DB, no Redis.**

**Storage — entirely filesystem + git**:
- SQLite (the only real database in use) — sessions, WAL mode + FTS5
- Markdown + YAML frontmatter — the source of truth for memory/wiki/agents/workflows/loops/skills
- JSON — all configuration (settings, mcp_servers, loop_config, kanban, automations)
- Git (via subprocess, not GitPython) — versioning/undo for memory data, **not** used for code
- Knowledge graph — no database at all; rebuilt from scratch on every request by regex-scanning `.md` files

**Frontend**: vanilla JS (ES6 classes + IIFEs), **no build step**, **no SPA framework**. Alpine.js 3.14 (only for the Console navigation), Three.js + 3d-force-graph (the 3D graph), plain CSS, Web Speech API. Every `.js` file is its own `<script>` tag, cache-busted manually with `?v=N`.

**Deployment**: Docker multi-stage build (node:22-slim → python:3.12-slim), Node is copied into the Python stage to install the Claude Code CLI + Codex CLI via npm, `tini` acts as PID 1 to reap the Node subprocesses Claude spawns.

### 2.2 The central architectural principle

> *"Javis never calls the Anthropic API directly. All reasoning and tool-calling goes through the `claude` CLI installed on the machine."* (docstring in `main.py`)

The server **shells out to the `claude` binary** as a subprocess instead of using the Anthropic SDK — this single decision drives the entire design.

### 2.3 Data flow diagram

```
Browser ─ WS /ws ─► main.py:websocket_endpoint()
                      ├─ routes by provider (settings.model.main):
                      │   anthropic-cli → claude_cli.ClaudeCLI (subprocess `claude`)
                      │   openai-oauth  → claude_cli.CodexCLI (subprocess `codex`)
                      │   openrouter/openai/anthropic-api → engine.py (direct httpx)
                      ├─ build_system_prompt(brain) = CLAUDE.md + MEMORY.md
                      ├─ sessions.SessionStore (SQLite)
                      ├─ log_conversation() → memory/conversations/*.md (secrets redacted)
                      └─ learn_feature.enqueue() — non-blocking

Background scheduler (asyncio, 30s tick):
  1. loop_feature.tick()   → self_improve.py: picks the most overdue loop, runs it
  2. learn_feature.tick()  → learn.py: debounces, runs a learning batch
  3. tasks_feature.tick()  → tasks.py: dispatches one Kanban task
  4. backup tick           → git_brain.backup_brains() pushes to GitHub
```

### 2.4 One chat message, in detail

1. Browser sends `{message, brain, session_id}` over the WebSocket.
2. `main.py` reads `settings.json` to determine the effective provider.
3. Default provider `anthropic-cli`: builds `ClaudeCLI(system_prompt=..., cwd=CLAUDE_CWD)`, calls `.query(message)`.
4. `ClaudeCLI.query()` spawns a subprocess:
   ```
   claude -p "<msg>" --output-format stream-json --verbose --dangerously-skip-permissions
     [--model] [--allowedTools] [--disallowedTools]
     [--mcp-config <path>] [--strict-mcp-config]
     [--append-system-prompt "<CLAUDE.md+MEMORY.md>"] [--resume <session_id>]
   ```
5. Reads stdout line by line on a dedicated thread (for Windows compatibility), pushes it through an `asyncio.Queue`, parses each JSON event into a normalized `{type: text|tool_call|tool_result|final|error}`.
6. Forwards each event over the WebSocket in real time; the frontend renders it and plays TTS.
7. Saves to SQLite, logs to a `.md` file (secrets redacted), and fires `enqueue()` for background learning without blocking the response.

### 2.5 The background learning flow (learn.py)

1. `enqueue()` runs after every turn → bumps a pending counter per brain (classified cheaply via regex, no API cost).
2. A 30s tick calls `learn_feature.tick()` → checks a debounce condition (K turns, OR an idle timeout, OR "urgent" if the user said "remember this") → if satisfied, runs `run_once()`.
3. `run_once()`: builds a prompt asking for a **single JSON manifest** — run inside a **fully isolated, read-only fork**: `allowed_tools=[Read,Glob,Grep,LS]`, an empty MCP config plus `--strict-mcp-config`, `disallowed_tools=[Bash,WebFetch,WebSearch,Task]`, `max_wall_s=240`.
4. The JSON output is then handled by **trusted Python code** (not the AI) as the only party allowed to write files: it scans for secrets, scans for prompt injection, checks confidence/density thresholds, and dedupes.
5. If the brain is a git repo: `git add` only the exact paths touched, then commit `learn: +N fact...` — enabling one-click undo via `git revert`.
6. Hard rate limits: `min_interval_s`, `fork_day`, `token_day`.

**The key pattern**: the AI only ever proposes changes via JSON; trusted code decides what actually gets written — eliminating the risk of a model overwriting files on its own initiative.

### 2.6 The self-improvement loop (the most distinctive feature)

Multi-loop: each loop is a file at `Javis/loops/<slug>.md` (frontmatter: `enabled/goal/mode/interval_min/workspace/tools_profile/quiet_hours/max_runs_per_day`), with runtime state kept separately in `Javis/loop-state.json`.

- **Trigger**: a 30s tick picks the most-overdue loop and runs it, serialized through a single global lock.
- **3 modes**: `suggest` (read-only) / `auto` (can write files, but money/order/ad/messaging actions are explicitly forbidden in the prompt, and Bash/Web/Task tools are excluded) / `full` (unrestricted — every tool and every MCP server — requires the user to acknowledge the risk in the UI before enabling).
- **Independent verification** (auto/full only): spawns a second, read-only CLI instance with the prompt "assume the result is WRONG, prove it," returning `{pass, reason}`.
- **Self-protection**: `fail_streak >= 3` (errors or failed verifications in a row) auto-pauses the loop and notifies via Telegram, without any human needing to intervene.

### 2.7 MCP integration — 3 layers

1. `mcp_store.py` — manages the list of MCP servers, generates a `.mcp_config.json` for `claude --mcp-config`. OAuth-authenticated servers are excluded from that config file (they're registered instead via `claude mcp add --scope user`, since the CLI can't do headless OAuth).
2. `mcp_client.py` — Javis implements its own MCP client (JSON-RPC 2.0 over Streamable HTTP) so API-based models (not routed through the CLI) can also use MCP tools — a hand-written tool-calling loop (`_cc_tool_loop`, capped at 8 rounds), with no framework like LangChain involved.
3. `meta_tools.py` — seeds a special "Javis Builder" skill that teaches Claude how to create agents/skills/workflows/loops on its own.

### 2.8 Other modules

- **Sessions** (`sessions.py`): plain SQLite, WAL + FTS5 (falls back to `LIKE`), distinguishes `conv_id` (managed by the dashboard) from `cli_session_id` (Claude's own `--resume` session) — letting a conversation switch providers mid-history without losing context.
- **Git brain** (`git_brain.py`): git as an undo layer for memory data (not code); `BrainLock`, a cross-platform file lock, serializes learn/curator/reflect/backup; GitHub backups go through a separate mirror directory plus a runtime-injected force-push token (never stored in git config).
- **Telegram** (`telegram_bot.py`): plain long-polling, one background task per turn (so `/stop` can cancel it), shares its provider-routing logic with the web chat path.
- **ChatGPT OAuth** (`openai_oauth.py`): an unofficial device-code flow (reverse-engineered from the Codex CLI's own source), with a docstring explicitly warning it "could break whenever OpenAI changes their API."
- **Tasks/Kanban** (`tasks.py`): a state machine (`todo→ready→running→(review|done)`), always runs in file-only mode, and any action that would reach outside the sandbox must stop at `review` for a human to approve.

### 2.9 API surface (grouped, ~150 endpoints total in `main.py`)

Auth, Chat (`WS /ws`), Provider/Model, MCP, Memory/Second-brain, Studio (Agents/Skills/Workflows), File manager, Loops, Learn engine, Kanban, Automations registry, Graph (`GET /graph`, `WS /ws/graph`), Upload/Ingest, Backup, Metrics, Telegram, TTS, Deploy/Update, Domain/HTTPS (`/tls-check`), Branding, Misc (`/health`, `/browse`, `/config`).

### 2.10 Deployment — comparing the compose variants

| File | Key characteristics |
|---|---|
| `docker-compose.yml` | Pulls from GHCR, includes `tunnel` (Cloudflare, profile) + `watchtower` (`update` profile, off by default) |
| `docker-compose.build.yml` | Builds from source, used when forking |
| `docker-compose.hostinger.yml` | Traefik labels built in (no `networks:`/`external`), `DOMAIN_NAME` |
| `docker-compose.https.yml` | Overlays Caddy On-Demand TLS, gated by `/tls-check` |

Shared volumes: `javis-data:/data` (state + secrets, not tracked in git), `javis-brains:/brains` (knowledge data — can be bind-mounted for self-managed git backups), `claude-auth:/home/javis/.claude`, `codex-auth:/home/javis/.codex`.

---

## PART 3 — TAKEAWAYS FOR BUILDING AGENTON

### 3.1 Patterns worth reusing

1. **"CLI-as-brain"** — shelling out to `claude`/`codex` instead of an SDK inherits MCP, skills, sessions, and OAuth subscriptions for free. Trade-off: coupled to the CLI's `stream-json` output format, and requires a mandatory idle-timeout watchdog.
2. **Read-only fork + trusted-code-writes-last**, used for every automation (learn/loop) — the AI only ever proposes via JSON; trusted code decides what gets written.
3. **MCP isolation via an empty config file + `--strict-mcp-config`, fail-closed if that file can't be created** — every background fork defaults to zero MCP access unless explicitly needed.
4. **Provenance tagging** (`user|source|assistant`) to stop the AI from re-learning its own hallucinations.
5. **Git as an undo layer for learned data** — narrow-scoped commits, secret/injection scanning before every write.
6. **Multi-loop self-pausing** after 3 consecutive failures, with no external cron job needed to watch over it.
7. **Separating `conv_id` from `cli_session_id`** — lets a conversation survive a provider switch mid-history.
8. **Atomic writes** (`.tmp` → fsync → `os.replace`), applied consistently to every JSON/Markdown state file.

### 3.2 Weaknesses / hacks to avoid when writing agenton

1. **Zero tests anywhere in the codebase** — a serious risk given how complex the rate-limiting/debounce/git-lock logic actually is.
2. **`--dangerously-skip-permissions` on by default for every single CLI call**, including plain chat — safety depends entirely on hand-written allowlists, not on the CLI's own approval mechanism.
3. **The graph builder has no cache** and rescans the entire filesystem on every request — fine at small scale, doesn't scale.
4. **Global mutable state** (module-level variables) instead of dependency injection — hard to test, and incompatible with running multiple workers.
5. **No schema validation (Pydantic) at the boundary** — most endpoints use `Form()` plus manual `json.loads`.
6. **The ChatGPT OAuth flow relies on an unofficial endpoint** — a real risk of breaking whenever OpenAI changes their API.
7. **No migration framework for JSON config** — migration functions are hand-written and scattered throughout the codebase.
8. **No frontend build step** — global variables (`window.Javis*`) are prone to namespace collisions as the codebase grows.
9. **Secret-redaction regexes are duplicated** across multiple files instead of living in one shared module.

### 3.3 Concrete recommendations for agenton

- **Keep**: the CLI-as-brain pattern, read-only-fork-then-trusted-write, atomic writes, git-as-undo-layer, provenance tagging.
- **Improve from day one**: write a real test suite (especially for rate-limit/debounce/git-lock logic), use Pydantic models for every request/response, clearly separate permission levels between "regular chat" and "background automation" (never share a single `--dangerously-skip-permissions` flag across both), and validate configuration at startup.
- **Consider**: a lightweight frontend build step (esbuild/Vite) if the UI is expected to grow more complex over time, and a cache with mtime-based invalidation for the graph builder if the vault gets large.

---

## PART 4 — REFERENCE FILES (absolute paths inside `_reference-javis-os/`)

**Product docs**: `README.md`, `QUICKSTART.md`, `DEPLOY.md`, `CLAUDE.md` (system prompt + agent conventions — the single most important file for understanding the orchestration logic), `CHANGELOG.md`, `docs/01`–`18` + `docs/README.md`, `.env.example`.

**Operational scripts**: `install.sh`, `setup.bat`, `migrate-brain.bat`, `reset-auth.bat`, `stop-javis.bat`, `start-javis.vbs`, `update.sh`, `javis.service`.

**Infrastructure**: `Dockerfile`, `docker-compose.yml`, `docker-compose.hostinger.yml`, `docker-compose.https.yml`, `docker-compose.build.yml`.

**Backend**: `server/main.py` (entrypoint, ~150 routes), `server/claude_cli.py` (subprocess wrapper), `server/engine.py` (HTTP streaming for API-based providers), `server/learn.py` (self-learning), `server/self_improve.py` (multi-loop), `server/git_brain.py` (undo/backup), `server/graph_builder.py`, `server/sessions.py` (SQLite), `server/tasks.py` (Kanban), `server/mcp_client.py`/`mcp_store.py`/`meta_tools.py`, `server/telegram_bot.py`, `server/openai_oauth.py`, `server/config.py`.

**Frontend**: `dashboard/app.js`, `console.js`, `graph3d.js`/`graph.js`, `studio.js`, `voice.js`, `brains-ui.js`, `sessions-ui.js`, `quick-settings.js`, `chat-zoom.js`, `branding.js`, `index.html`, `style.css`/`console.css`.
