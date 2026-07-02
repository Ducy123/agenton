# Phân tích Javis OS — tài liệu tham khảo cho việc xây dựng agenton

> Nguồn: https://github.com/blogminhquy/javis-os (clone tại `_reference-javis-os/`, gitignored)
> Ngày phân tích: 2026-07-02

---

## PHẦN 1 — SẢN PHẨM & TÍNH NĂNG

### 1.1 Khái niệm sản phẩm

Javis OS không phải chatbot — nó là một **"lớp điều hành AI"** chạy trên máy/VPS cá nhân. Điểm khác biệt cốt lõi: **không gọi thẳng Anthropic/OpenAI API**, mà "cưỡi lên" **Claude Code CLI** hoặc **Codex CLI** đã cài sẵn, tận dụng subscription Pro/Max người dùng đã trả tiền (không tốn thêm phí API), đồng thời kế thừa luôn quyền đọc/ghi file, MCP tools, skills, session của chính CLI đó.

Xung quanh "bộ não" CLI, sản phẩm đóng gói: dashboard có đồ thị tri thức 3D, điều khiển giọng nói tiếng Việt, "Second Brain" tích luỹ kiến thức bền vững (Sources → Wiki), và vòng lặp tự cải thiện chạy nền.

Triết lý lặp lại nhiều lần: *"biên dịch tri thức thô → Wiki 1 lần, rồi duy trì nó sống cùng mỗi nguồn mới"* — tri thức tích luỹ, không tái phát hiện mỗi lần hỏi.

### 1.2 Danh sách tính năng đầy đủ (15 nhóm)

| Nhóm | Tính năng chính |
|---|---|
| **Chat & Voice** | Push-to-talk (giữ Space), chế độ rảnh tay (auto VAD ~1.5s), Edge TTS 2 giọng Việt, đính kèm file/ảnh (mặc định chỉ đọc, phải nói rõ mới lưu), Esc dừng đọc |
| **Đồ thị tri thức 3D** | Mỗi `.md` = node, mỗi `[[wikilink]]` = cạnh, phản ứng theo giọng nói/suy nghĩ, tự tạm dừng khi ẩn tab (tiết kiệm tài nguyên), real-time node mới |
| **Sessions** | SQLite + full-text search, đổi tên/xoá, tự đặt tên theo câu hỏi đầu, gắn theo brain |
| **File Manager** | Duyệt/sửa/tải lên-xuống trong phạm vi brain, path-traversal guard, giới hạn 2MB cho sửa trực tiếp |
| **Skills** | `.claude/skills/<slug>/SKILL.md`, tắt = move vào `.disabled/`, chỉ chạy khi engine = Claude Code CLI |
| **Agents/Workflows (Studio)** | Multi-step, verification agent tự sửa tối đa N lần, model per-agent, nhưng chạy nền luôn ép về Claude Code (an toàn) |
| **Self-improvement Loop** | Multi-loop, 3 mức quyền suggest/auto/full, tự tạm dừng sau 3 lỗi liên tiếp, LINT Wiki (chỉ đọc) |
| **MCP & Metrics** | Multi-shop cùng URL khác token, tool denylist → readonly, Data Cache cho kỳ đã đóng (tiết kiệm phí) |
| **Model/Engine** | 5 provider (Claude CLI, Codex CLI, OpenRouter, Anthropic API, OpenAI API), Main + Auxiliary + reasoning level riêng |
| **Telegram Bot** | Long-polling, whitelist Chat ID, lệnh `/cli /or /model /stop`, cảnh báo rõ "gửi test OK ≠ bot đang nhận tin thật" |
| **Automation/Scheduling** | Phần lớn chỉ là registry (không tự chạy) — cái thực sự tự chạy là Loop nội bộ + routine cloud sync |
| **Second Brain** | `sources/` → `wiki/` + `memory/`, đa-brain, memory facts có provenance, học tự động sau mỗi 6 lượt |
| **Security** | PBKDF2-HMAC-SHA256 120k vòng, fail-closed (host ≠ loopback → bắt buộc login), rate-limit 8 lần sai/5 phút |
| **Branding/Domain** | Caddy On-Demand TLS (VPS thường) vs Traefik (Hostinger) — 2 cơ chế khác hẳn nhau |
| **GitHub Backup** | Force-push mirror toàn bộ `brains/`, mirror sạch (bỏ log/lock/`.git` con) trước khi đẩy |

### 1.3 Bảng cách cài đặt/triển khai (7 đường)

| # | Cách | File | Đặc điểm |
|---|---|---|---|
| 1 | Hostinger Docker Manager | `docker-compose.hostinger.yml` | Traefik labels sẵn, `DOMAIN_NAME` cho HTTPS free, update = Redeploy |
| 2 | Docker VPS bất kỳ (pull) | `docker-compose.yml` | GHCR image, healthcheck, Watchtower (profile `update`, tắt mặc định), Cloudflare Tunnel (profile `tunnel`) |
| 3 | Docker build từ source | `docker-compose.build.yml` | `--build`, dùng khi fork sửa code |
| 4 | HTTPS tự động Caddy | `docker-compose.https.yml` | On-Demand TLS, domain nhập trong app UI, gate qua `/tls-check` |
| 5 | Native Linux/macOS | `install.sh` | Tự cài Python/Node22/Claude CLI, tạo systemd, fallback nohup |
| 6 | Windows | `setup.bat`/`start-javis.vbs`/`stop-javis.bat` | Foreground vs ẩn nền, tự kill port 7777 cũ |
| 7 | systemd trực tiếp | `javis.service` | Template cần `sed` thay placeholder |

### 1.4 20 chi tiết "ngóc ngách" quan trọng nhất

1. **MÃ THIẾT LẬP** (setup token) — sinh 1 lần khi public + chưa có admin, đọc qua log hoặc file `.setup_token`, tự huỷ sau khi dùng.
2. **Voice bắt buộc HTTPS** — Web Speech API không cấp quyền mic qua IP trần, cần domain/tunnel.
3. **Lỗi 409 Telegram** — cùng token chạy 2 nơi; "gửi test OK" không chứng minh bot nhận tin thật.
4. **Model Codex tự "coerce"** — nếu trỏ model API thường khi chạy qua Codex subscription, tự đổi sang model Codex hợp lệ.
5. **Agent an toàn khi chạy nền** — Studio cho chọn Codex/GPT, nhưng dispatcher nền luôn ép về Claude Code.
6. **3 mức quyền Loop** — loop tạo qua chat luôn mặc định `suggest` + tắt; `full` chỉ khi user yêu cầu rõ ràng.
7. **Cấm ký tự em dash (—)** trong mọi output — TTS đọc bị khựng, quy tắc cứng trong system prompt.
8. **Data Cache cho kỳ đã đóng** — chỉ gọi lại MCP cho kỳ hiện tại.
9. **Chuẩn hoá brain an toàn** — chỉ move khi đích chưa tồn tại, chạy lại vô hại.
10. **Reset đăng nhập** — xoá khối `"auth"` trong `settings.json`, `reset-auth.bat` tự động hoá trên Windows.
11. **Backup GitHub = force-push mirror** — chỉ nên 1 nguồn đẩy 1 repo.
12. **Fail-closed security** — host ≠ loopback → tự bật login bắt buộc, không cần cấu hình.
13. **Cookie Secure gây kẹt vòng login** khi chạy qua HTTP proxy — lỗi phổ biến được cảnh báo riêng.
14. **Rate-limit kép** — khoá 5 phút sau 8 lần sai + mỗi lần sai chậm thêm 0.5s.
15. **Watchtower = profile riêng** (tắt mặc định) vì cần Docker socket, Hostinger hay chặn.
16. **Quick tunnel vs Named tunnel** (Cloudflare) — quick đổi URL mỗi restart, named cần `TUNNEL_TOKEN` cố định.
17. **Traefik trên Hostinger: KHÔNG khai báo `networks:`/`external`** — từng gây lỗi "network not found".
18. **On-Demand TLS có gatekeeper `/tls-check`** — chống lạm dụng rate-limit Let's Encrypt.
19. **`automations.json` chứa dữ liệu cá nhân** (chat ID, trigger ID) — cẩn thận khi share brain.
20. **Migrate 1 lần tự động** — `loop_config.json` cũ tự sinh `Javis/loops/vong-lap-goc.md`, giữ JSON cũ làm backup.

### 1.5 Glossary thuật ngữ Việt → kỹ thuật

| Việt | Kỹ thuật |
|---|---|
| Bộ não | CLI engine (Claude Code/Codex) làm AI backend |
| Second Brain | External KB — vault Markdown (Sources+Wiki+Memory) |
| Wikilink | `[[Tên ghi chú]]` kiểu Obsidian → cạnh trong graph |
| INGEST | Pipeline biến file thô → note → chưng cất lên Wiki |
| Vòng lặp tự cải thiện | Self-improvement loop — scheduled agentic background task |
| Tự học/rewire | Memory consolidation từ log hội thoại |
| Đề xuất / Tự làm+kiểm chứng / Toàn quyền | suggest / auto / full mode |
| MÃ THIẾT LẬP | Setup token dùng 1 lần |
| Chặn tool → Chỉ đọc | Tool denylist → readonly mode cho MCP server |
| Brain | 1 second-brain vault độc lập (đa-brain = multi-vault) |
| Kiểm chứng viên | Verifier agent phản biện độc lập |
| LINT Wiki | Health check, chỉ đọc, không tự sửa |

---

## PHẦN 2 — KIẾN TRÚC KỸ THUẬT

### 2.1 Tech stack

**Backend**: FastAPI + Uvicorn (ASGI, single-process), httpx (async, mọi gọi ngoài), tự viết auth (PBKDF2-HMAC-SHA256 120k vòng), `edge-tts` cho TTS, PyYAML cho frontmatter. **Không ORM, không vector DB, không Redis.**

**Lưu trữ — hoàn toàn filesystem + git**:
- SQLite (duy nhất nơi dùng DB thật) — sessions, WAL mode + FTS5
- Markdown + YAML frontmatter — nguồn sự thật cho memory/wiki/agents/workflows/loops/skills
- JSON — mọi config (settings, mcp_servers, loop_config, kanban, automations)
- Git (qua subprocess, không GitPython) — versioning/undo cho memory, KHÔNG dùng cho code
- Knowledge graph — không DB, build lại from-scratch mỗi request bằng regex quét `.md`

**Frontend**: Vanilla JS (ES6 class + IIFE), KHÔNG build step, KHÔNG SPA framework. Alpine.js 3.14 (chỉ cho Console nav), Three.js + 3d-force-graph (3D graph), CSS thuần, Web Speech API. Mỗi file `.js` là 1 `<script>` tag riêng, cache-bust bằng `?v=N`.

**Deploy**: Docker multi-stage (node:22-slim → python:3.12-slim), copy Node sang stage Python để cài Claude Code CLI + Codex CLI qua npm, `tini` làm PID1 để reap subprocess node.

### 2.2 Nguyên tắc kiến trúc trung tâm

> *"Javis KHÔNG gọi Anthropic API trực tiếp. Mọi reasoning + tool calling đi qua `claude` CLI đã cài trên máy."* (docstring `main.py`)

Server **shell ra binary `claude`** làm subprocess thay vì dùng Anthropic SDK — đây là quyết định chi phối toàn bộ thiết kế.

### 2.3 Sơ đồ luồng dữ liệu

```
Browser ─ WS /ws ─► main.py:websocket_endpoint()
                      ├─ route theo provider (settings.model.main):
                      │   anthropic-cli → claude_cli.ClaudeCLI (subprocess `claude`)
                      │   openai-oauth  → claude_cli.CodexCLI (subprocess `codex`)
                      │   openrouter/openai/anthropic-api → engine.py (httpx trực tiếp)
                      ├─ build_system_prompt(brain) = CLAUDE.md + MEMORY.md
                      ├─ sessions.SessionStore (SQLite)
                      ├─ log_conversation() → memory/conversations/*.md (redact secret)
                      └─ learn_feature.enqueue() — non-blocking

Background scheduler (asyncio tick 30s):
  1. loop_feature.tick()   → self_improve.py: chọn loop quá hạn nhất, chạy
  2. learn_feature.tick()  → learn.py: debounce, chạy batch học
  3. tasks_feature.tick()  → tasks.py: dispatch 1 Kanban task
  4. backup tick           → git_brain.backup_brains() lên GitHub
```

### 2.4 Luồng 1 tin nhắn chat (chi tiết)

1. Browser gửi `{message, brain, session_id}` qua WS.
2. `main.py` đọc `settings.json` → xác định provider hiệu lực.
3. Provider mặc định `anthropic-cli`: dựng `ClaudeCLI(system_prompt=..., cwd=CLAUDE_CWD)`, gọi `.query(message)`.
4. `ClaudeCLI.query()` spawn subprocess:
   ```
   claude -p "<msg>" --output-format stream-json --verbose --dangerously-skip-permissions
     [--model] [--allowedTools] [--disallowedTools]
     [--mcp-config <path>] [--strict-mcp-config]
     [--append-system-prompt "<CLAUDE.md+MEMORY.md>"] [--resume <session_id>]
   ```
5. Đọc stdout theo dòng trong thread riêng (tương thích Windows), đẩy qua `asyncio.Queue`, parse JSON event → chuẩn hoá `{type: text|tool_call|tool_result|final|error}`.
6. Forward real-time qua WS, frontend render + TTS.
7. Lưu SQLite + log `.md` (redact secret) + `enqueue()` học nền không block.

### 2.5 Luồng tự học nền (learn.py)

1. `enqueue()` sau mỗi lượt → tăng bộ đếm pending (phân loại nhanh bằng regex, không tốn API).
2. Tick 30s → debounce (K lượt HOẶC idle timeout HOẶC "urgent" nếu nói "ghi nhớ") → `run_once()`.
3. `run_once()`: build prompt yêu cầu **1 JSON manifest** — chạy dưới **fork READ-ONLY cô lập tuyệt đối**: `allowed_tools=[Read,Glob,Grep,LS]`, MCP rỗng + `--strict-mcp-config`, `disallowed_tools=[Bash,WebFetch,WebSearch,Task]`, `max_wall_s=240`.
4. Output JSON → **Python tin cậy** (không phải AI) là bên duy nhất ghi file: quét secret, quét prompt-injection, kiểm confidence/density, dedupe.
5. Nếu brain là git repo: `git add` đúng path + commit `learn: +N fact...` → undo 1 chạm (`git revert`).
6. Rate limit cứng: `min_interval_s`, `fork_day`, `token_day`.

**Pattern quan trọng**: AI chỉ đề xuất qua JSON, code tin cậy quyết định ghi gì — triệt tiêu rủi ro model tự ý ghi đè file.

### 2.6 Self-improvement loop (tính năng đặc trưng nhất)

Multi-loop, mỗi loop = file `Javis/loops/<slug>.md` (frontmatter: `enabled/goal/mode/interval_min/workspace/tools_profile/quiet_hours/max_runs_per_day`), state runtime tách riêng `Javis/loop-state.json`.

- **Trigger**: tick 30s, chọn loop quá hạn lâu nhất, chạy tuần tự qua 1 lock toàn cục.
- **3 mode**: `suggest` (chỉ đọc) / `auto` (ghi file được nhưng cấm hành động tiền/đơn/quảng cáo/gửi tin, không Bash/Web/Task) / `full` (toàn quyền, mọi tool+MCP, cần user xác nhận rủi ro).
- **Kiểm chứng độc lập** (auto/full): spawn CLI thứ 2 readonly, prompt "giả định SAI, chứng minh", trả `{pass, reason}`.
- **Tự bảo vệ**: `fail_streak >= 3` → tự pause + báo Telegram, không cần người can thiệp.

### 2.7 MCP integration — 3 lớp

1. `mcp_store.py` — quản lý danh sách server, sinh `.mcp_config.json` cho `claude --mcp-config`. OAuth server không vào config file (đăng ký qua `claude mcp add --scope user`).
2. `mcp_client.py` — Javis tự làm MCP client (JSON-RPC 2.0, Streamable HTTP) cho model API-based không qua CLI — tool-calling loop viết tay (`_cc_tool_loop`, tối đa 8 vòng), không dùng LangChain/framework nào.
3. `meta_tools.py` — seed skill "Javis Builder" dạy Claude tự tạo agent/skill/workflow/loop.

### 2.8 Các module khác

- **Sessions** (`sessions.py`): SQLite thuần, WAL + FTS5 (fallback LIKE), phân biệt `conv_id` (dashboard-managed) vs `cli_session_id` (Claude `--resume`) — cho phép đổi provider giữa các lượt mà giữ lịch sử.
- **Git brain** (`git_brain.py`): git làm undo layer cho memory (không phải code); `BrainLock` file-lock cross-platform serialize learn/curator/reflect/backup; backup GitHub qua mirror dir riêng + force-push token runtime (không lưu git config).
- **Telegram** (`telegram_bot.py`): long-polling thuần, 1 lượt = 1 background task (`/stop` cancel được), share logic routing với web chat.
- **OAuth ChatGPT** (`openai_oauth.py`): device-code flow không chính thức (pin theo Codex CLI source), tự ghi rủi ro "có thể vỡ khi OpenAI đổi API".
- **Tasks/Kanban** (`tasks.py`): state machine `todo→ready→running→(review|done)`, luôn chạy file-only, hành động ra ngoài phải dừng ở `review` cho người duyệt.

### 2.9 API surface (tóm tắt nhóm, ~150 endpoints trong `main.py`)

Auth, Chat (WS `/ws`), Provider/Model, MCP, Memory/Second-brain, Studio (Agents/Skills/Workflows), File manager, Loops, Learn engine, Kanban, Automations registry, Graph (`GET /graph`, `WS /ws/graph`), Upload/Ingest, Backup, Metrics, Telegram, TTS, Deploy/Update, Domain/HTTPS (`/tls-check`), Branding, Misc (`/health`, `/browse`, `/config`).

### 2.10 Deployment — so sánh compose variants

| File | Đặc điểm chính |
|---|---|
| `docker-compose.yml` | GHCR pull, `tunnel` (Cloudflare, profile) + `watchtower` (profile `update`, tắt mặc định) |
| `docker-compose.build.yml` | Build từ source, dùng khi fork |
| `docker-compose.hostinger.yml` | Traefik labels sẵn (KHÔNG `networks:`/`external`), `DOMAIN_NAME` |
| `docker-compose.https.yml` | Overlay Caddy On-Demand TLS, gate `/tls-check` |

Volume chung: `javis-data:/data` (state+secret, không git), `javis-brains:/brains` (tri thức, bind-mount được để tự backup git), `claude-auth:/home/javis/.claude`, `codex-auth:/home/javis/.codex`.

---

## PHẦN 3 — ĐÁNH GIÁ CHO VIỆC XÂY DỰNG AGENTON

### 3.1 Pattern đáng học/tái sử dụng

1. **"CLI-as-brain"** — shell ra `claude`/`codex` CLI thay vì SDK → kế thừa miễn phí MCP, skills, session, OAuth subscription. Tradeoff: phụ thuộc format `stream-json` của CLI, cần watchdog/idle-timeout bắt buộc.
2. **Fork read-only + Python-ghi-cuối-cùng** cho mọi automation (learn/loop) — AI chỉ đề xuất JSON, code tin cậy quyết định ghi gì.
3. **Cô lập MCP bằng file rỗng + `--strict-mcp-config`, fail-closed nếu không tạo được file** — mọi fork nền mặc định 0-MCP trừ khi cần tường minh.
4. **Provenance tagging** (`user|source|assistant`) chống AI tự học lại ảo giác của chính nó.
5. **Git làm undo layer cho dữ liệu học** — commit theo scope hẹp, secret/injection-scan trước khi ghi.
6. **Multi-loop tự pause** sau 3 lỗi liên tiếp, không cần cron ngoài giám sát.
7. **Tách `conv_id` vs `cli_session_id`** — resume hội thoại xuyên suốt dù đổi provider.
8. **Atomic write** (`.tmp` → fsync → `os.replace`) áp dụng nhất quán cho mọi file JSON/Markdown state.

### 3.2 Điểm yếu / hacky cần tránh khi viết agenton

1. **Không có test nào** trong toàn bộ codebase — rủi ro lớn với logic phức tạp (rate-limit, debounce, git lock).
2. **`--dangerously-skip-permissions` mặc định trên MỌI lệnh**, kể cả chat thường — an toàn phụ thuộc hoàn toàn vào allowlist tự viết, không phải cơ chế native CLI.
3. **Graph builder không cache**, quét lại toàn filesystem mỗi request — không scale (dù chấp nhận được ở quy mô nhỏ).
4. **Global mutable state** (module-level variables) thay vì DI — khó test, không chịu được multi-worker.
5. **Không schema validation (Pydantic) ở boundary** — hầu hết endpoint dùng `Form()` + `json.loads` tay.
6. **OAuth ChatGPT dựa endpoint không chính thức** — rủi ro vỡ khi OpenAI đổi API.
7. **Không có migration framework** cho JSON config — migrate function viết tay rải rác.
8. **Frontend không build step** — biến global (`window.Javis*`) dễ xung đột namespace khi lớn thêm.
9. **Secret redaction regex duplicate** ở nhiều file thay vì 1 module dùng chung.

### 3.3 Khuyến nghị cụ thể cho agenton

- **Giữ**: CLI-as-brain pattern, read-only-fork-then-trusted-write, atomic write, git-as-undo-layer, provenance tagging.
- **Cải thiện ngay từ đầu**: viết test suite (đặc biệt rate-limit/debounce/git-lock logic), dùng Pydantic models cho request/response, tách rõ cấp độ permission giữa "chat thường" và "automation nền" (không dùng chung 1 cờ `--dangerously-skip-permissions`), validate config ở startup.
- **Cân nhắc**: build step nhẹ cho frontend (esbuild/Vite) nếu dự kiến UI phức tạp hơn theo thời gian, cache có invalidation cho graph builder nếu vault lớn.

---

## PHẦN 4 — FILE THAM CHIẾU (đường dẫn tuyệt đối trong `_reference-javis-os/`)

**Docs sản phẩm**: `README.md`, `QUICKSTART.md`, `DEPLOY.md`, `CLAUDE.md` (system prompt + quy ước agent — quan trọng nhất để hiểu logic điều phối), `CHANGELOG.md`, `docs/01`–`18` + `docs/README.md`, `.env.example`.

**Scripts vận hành**: `install.sh`, `setup.bat`, `migrate-brain.bat`, `reset-auth.bat`, `stop-javis.bat`, `start-javis.vbs`, `update.sh`, `javis.service`.

**Hạ tầng**: `Dockerfile`, `docker-compose.yml`, `docker-compose.hostinger.yml`, `docker-compose.https.yml`, `docker-compose.build.yml`.

**Backend**: `server/main.py` (entrypoint, ~150 routes), `server/claude_cli.py` (subprocess wrapper), `server/engine.py` (HTTP streaming cho API-based providers), `server/learn.py` (tự học), `server/self_improve.py` (multi-loop), `server/git_brain.py` (undo/backup), `server/graph_builder.py`, `server/sessions.py` (SQLite), `server/tasks.py` (Kanban), `server/mcp_client.py`/`mcp_store.py`/`meta_tools.py`, `server/telegram_bot.py`, `server/openai_oauth.py`, `server/config.py`.

**Frontend**: `dashboard/app.js`, `console.js`, `graph3d.js`/`graph.js`, `studio.js`, `voice.js`, `brains-ui.js`, `sessions-ui.js`, `quick-settings.js`, `chat-zoom.js`, `branding.js`, `index.html`, `style.css`/`console.css`.
