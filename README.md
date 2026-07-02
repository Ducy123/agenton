# AgentOn

AgentOn is a multi-tenant **Agent Rental Marketplace**: renters browse a
catalog of task-executing AI agents, pay to activate an instance, use it,
and the platform meters usage, handles billing, and manages the agent's
lifecycle end to end.

This repository implements the backend platform described in
[`_AgentOn Agent 租用功能说明.pdf`](<_AgentOn Agent 租用功能说明.pdf>) (the
original product spec). Its execution kernel borrows architectural patterns
from [javis-os](https://github.com/blogminhquy/javis-os) — see
[`ANALYSIS-javis-os.md`](ANALYSIS-javis-os.md) for the full writeup —
reshaped for multi-tenant SaaS instead of a single-user personal assistant.
See [`app/engine/README.md`](app/engine/README.md) for exactly what was
reused and why.

## Features

- **Marketplace** — browse/search rentable agent templates by category,
  view capabilities and pricing.
- **Rental & billing** — wallet-based credits, online recharge through a
  pluggable payment provider, pay-per-order, time-based (hour/day/month) or
  token/package metered pricing, auto-renewal, low-balance detection, and a
  full append-only consumption ledger.
- **Agent instance lifecycle** — Created → Running → Paused → Stopped →
  Expired → Released, matching the spec's state diagram exactly, enforced
  by an explicit state machine.
- **Pluggable execution engine** — every sellable task type (AI content
  generation, X/Twitter follow/like/retweet/post, Discord join, generic
  platform registration, web visits, ...) is a `TaskConnector` plugin.
  Adding a new task type never touches billing, marketplace, or instance
  code.
- **Self-protecting automation** — every task run gets an independent
  verification pass, and 3 consecutive failures auto-pause the instance —
  patterns adapted from javis-os's self-improvement loop.

## Architecture

```
app/
├── auth/          multi-tenant user accounts, JWT auth
├── marketplace/   agent template catalog: browse/search/publish
├── billing/       wallet, ledger, orders, pluggable payment providers
│   └── providers/ PaymentProvider interface + mock implementation
├── instances/     AgentInstance lifecycle state machine + scheduler
├── engine/        execution kernel (extracted javis-os patterns)
│   └── connectors/  one file per task type, registered in bootstrap.py
├── common/        shared errors, pagination, enums, atomic file writes
└── config.py, db.py, deps.py, main.py

tests/             pytest suite covering every module above
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full breakdown, request
flow diagrams, and — most importantly — **how to add a new sellable task
type or payment provider**.

## Getting started

### 1. Requirements

- Python 3.10+
- (optional) Docker + Docker Compose for a Postgres-backed deployment
- (optional) the `claude` CLI on `PATH` if you want the
  `ai_content_generation` connector to actually run (see
  [Claude Code](https://docs.claude.com/claude-code))

### 2. Local setup

```bash
cd agenton
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # edit as needed — SQLite works out of the box
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for interactive Swagger UI, or
http://localhost:8000/health to confirm the server is running.

### 3. Docker (Postgres-backed)

```bash
docker compose up --build
```

This starts the API on port 8000 backed by a Postgres container (see
`docker-compose.yml`).

### 4. Run tests

```bash
pytest
```

## Walkthrough: rent and run an agent

All examples assume the API is running at `http://localhost:8000`.

**1. Register and log in**

```bash
curl -X POST localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "a-strong-password"}'

TOKEN=$(curl -s -X POST localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "a-strong-password"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")
```

**2. Publish an agent template** (normally done by an operator, not a
renter — see the note in `marketplace/router.py` about adding a role check
before this goes live)

```bash
curl -X POST localhost:8000/marketplace/agents \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "slug": "web-visitor",
    "name": "Web Visitor Bot",
    "category": "growth",
    "task_type": "webvisit",
    "short_description": "Visits a URL for quest/referral tracking",
    "base_price_cents": 100,
    "pricing_unit": "token"
  }'
```

**3. Browse the marketplace**

```bash
curl localhost:8000/marketplace/agents
```

**4. Recharge your wallet** (uses the `mock` payment provider in dev — swap
in a real one before going live, see `app/billing/providers/`)

```bash
curl -X POST localhost:8000/billing/wallet/recharge \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"amount_cents": 5000}'
```

**5. Create and pay for an order**

```bash
ORDER=$(curl -s -X POST localhost:8000/billing/orders \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"template_id": "<id from step 3>", "quantity": 3}')
ORDER_ID=$(echo $ORDER | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")

curl -X POST localhost:8000/billing/orders/$ORDER_ID/pay -H "Authorization: Bearer $TOKEN"
```

**6. Create the agent instance and start it**

```bash
INSTANCE=$(curl -s -X POST localhost:8000/instances \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"order_id\": \"$ORDER_ID\", \"task_params\": {\"url\": \"https://example.com\"}}")
INSTANCE_ID=$(echo $INSTANCE | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")

curl -X POST localhost:8000/instances/$INSTANCE_ID/start -H "Authorization: Bearer $TOKEN"
```

**7. Run the agent's task**

```bash
curl -X POST localhost:8000/instances/$INSTANCE_ID/execute \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{}'
```

**8. Check your wallet and consumption history**

```bash
curl localhost:8000/billing/wallet -H "Authorization: Bearer $TOKEN"
curl localhost:8000/billing/transactions -H "Authorization: Bearer $TOKEN"
```

**9. Stop and release when done**

```bash
curl -X POST localhost:8000/instances/$INSTANCE_ID/stop -H "Authorization: Bearer $TOKEN"
curl -X POST localhost:8000/instances/$INSTANCE_ID/release -H "Authorization: Bearer $TOKEN"
```

## Going to production

This repo ships with **safe defaults that are not production-ready on their
own**:

- `PAYMENT_PROVIDER=mock` always "succeeds" — swap in a real Stripe/crypto
  adapter (`app/billing/providers/`) before accepting real money.
- The Twitter/Discord connectors expect an already-issued renter OAuth
  token (`user_access_token`) — the three-legged OAuth authorize/callback
  flow that produces that token isn't implemented here yet (see the
  docstrings in `app/engine/connectors/twitter.py` and `discord.py`).
- SQLite is fine for local development; use Postgres
  (`DATABASE_URL=postgresql+psycopg2://...`) for anything with concurrent
  writes or real money on the line.
- There's no role/permission system yet — any authenticated user can
  publish marketplace listings today (see the `TODO` note in
  `marketplace/router.py`).

## Further reading

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — module-by-module breakdown,
  request flow diagrams, and extension points.
- [`app/engine/README.md`](app/engine/README.md) — what was ported from
  javis-os and why.
- [`ANALYSIS-javis-os.md`](ANALYSIS-javis-os.md) — full feature and
  architecture analysis of javis-os, the reference codebase this project
  was built on top of.
- [`_AgentOn Agent 租用功能说明.pdf`](<_AgentOn Agent 租用功能说明.pdf>) —
  original product spec.
