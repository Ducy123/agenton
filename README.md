# AgentOn

AgentOn is the solution being built to meet the AgentOn Agent Rental
requirements: a multi-tenant marketplace where renters browse
task-executing AI agents, pay to activate an instance, use it, and the
platform meters usage, handles billing, and manages the agent's lifecycle
end to end.

**→ [REQUIREMENTS.md](REQUIREMENTS.md) is the appendix that matters most
here**: it quotes every requirement from
[`_AgentOn Agent 租用功能说明.pdf`](<_AgentOn Agent 租用功能说明.pdf>) (the
original product spec) one by one and maps each to the concrete solution
implemented for it — which API, which module, which connector, and an
honest status (done, needs real credentials, or still planned). Read that
file to see the full pipeline: what was asked for, and exactly how this
codebase answers it.

The execution kernel borrows architectural patterns from
[javis-os](https://github.com/blogminhquy/javis-os) — see
[`ANALYSIS-javis-os.md`](ANALYSIS-javis-os.md) for the full writeup —
reshaped for multi-tenant SaaS instead of a single-user personal assistant.
See [`app/engine/README.md`](app/engine/README.md) for exactly what was
reused and why.

## Features

- **Marketplace** — browse/search rentable agent templates by category,
  view capabilities and pricing.
- **Rental & billing** — wallet-based credits, online recharge (immediate
  mock provider for dev, or a Stripe-hosted checkout + webhook flow for
  real payments), pay-per-order, time-based (hour/day/month) or
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
- **OAuth-connected social actions** — renters connect their X/Discord
  account once (PKCE / OAuth2), and every X/Discord task on any of their
  instances automatically uses that stored, encrypted token — no manual
  token-passing per call.
- **Self-protecting automation** — every task run gets an independent
  verification pass, and 3 consecutive failures auto-pause the instance —
  patterns adapted from javis-os's self-improvement loop.

## Architecture

```
app/
├── auth/          multi-tenant user accounts, JWT auth
├── marketplace/   agent template catalog: browse/search/publish
├── billing/       wallet, ledger, orders, pluggable payment providers
│   └── providers/ PaymentProvider/CheckoutProvider interfaces, mock + Stripe
├── instances/     AgentInstance lifecycle state machine + scheduler
├── platforms/     renter OAuth connections (X, Discord) — encrypted token storage
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
- (optional) an X (Twitter) developer app and/or Discord application if you
  want the social connectors to run against real accounts
- (optional) a Stripe account if you want real hosted-checkout recharges

### 2. Local setup

```bash
cd agenton
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # edit as needed — SQLite + mock payments work out of the box
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

**4. Fund your wallet** — pick one:

```bash
# (a) Immediate mock recharge — for local dev/testing, always "succeeds"
curl -X POST localhost:8000/billing/wallet/recharge \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"amount_cents": 5000}'

# (b) Real hosted checkout (requires PAYMENT_PROVIDER=stripe + Stripe keys in .env)
curl -X POST localhost:8000/billing/wallet/recharge/checkout \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"amount_cents": 5000, "success_url": "https://your-app/success", "cancel_url": "https://your-app/cancel"}'
# -> redirect the renter's browser to the returned checkout_url; the wallet
#    is credited once Stripe calls POST /billing/webhooks/stripe
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

**9. Turn on auto-renewal (optional, for time-based rentals)**

```bash
curl -X PATCH localhost:8000/billing/wallet/settings \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"auto_renew_enabled": true}'
```

**10. Stop and release when done**

```bash
curl -X POST localhost:8000/instances/$INSTANCE_ID/stop -H "Authorization: Bearer $TOKEN"
curl -X POST localhost:8000/instances/$INSTANCE_ID/release -H "Authorization: Bearer $TOKEN"
```

## Walkthrough: connect X/Discord before renting a social-action agent

Twitter and Discord task types (`twitter_follow`, `twitter_post`,
`discord_join`, ...) act on the **renter's own account**, so they connect
it once via OAuth — every instance execution afterwards picks the stored
token up automatically.

```bash
# 1. Get the authorize URL and send the renter's browser there
curl localhost:8000/platforms/twitter/authorize -H "Authorization: Bearer $TOKEN"
# -> {"authorize_url": "https://twitter.com/i/oauth2/authorize?...", "state": "..."}

# 2. Twitter redirects back to TWITTER_REDIRECT_URI with ?code=...&state=...
#    (your frontend forwards that to the backend, or the backend's own
#    redirect_uri handles it directly)
curl "localhost:8000/platforms/twitter/callback?code=<code>&state=<state>"

# 3. Confirm the connection
curl localhost:8000/platforms -H "Authorization: Bearer $TOKEN"

# From here, twitter_follow/like/retweet/post tasks on any of this renter's
# instances no longer need user_access_token / twitter_user_id in
# task_params — instances.service fills them in from the stored connection.

# Disconnect any time:
curl -X DELETE localhost:8000/platforms/twitter -H "Authorization: Bearer $TOKEN"
```

The same flow applies to `/platforms/discord/authorize` and
`/platforms/discord/callback`.

## Going to production

This repo ships with **safe defaults that are not production-ready on
their own** — see [REQUIREMENTS.md § "What 'Done\*' means in practice"](REQUIREMENTS.md#what-done-means-in-practice)
for the exact credentials each integration needs. In short:

- `PAYMENT_PROVIDER=mock` always "succeeds" — set `PAYMENT_PROVIDER=stripe`
  plus `STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET` before accepting real
  money (`app/billing/providers/stripe_provider.py`).
- The X/Discord OAuth flows are fully implemented (`app/platforms/`) but
  need real `TWITTER_CLIENT_ID`/`TWITTER_CLIENT_SECRET` and
  `DISCORD_CLIENT_ID`/`DISCORD_CLIENT_SECRET` registered with each
  platform to actually authorize renters.
- SQLite is fine for local development; use Postgres
  (`DATABASE_URL=postgresql+psycopg2://...`) for anything with concurrent
  writes or real money on the line.
- There's no role/permission system yet — any authenticated user can
  publish marketplace listings today (see the `TODO` note in
  `marketplace/router.py`).

## Further reading

- [`REQUIREMENTS.md`](REQUIREMENTS.md) — the PDF-requirement-to-
  implementation traceability appendix.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — module-by-module breakdown,
  request flow diagrams, and extension points.
- [`app/engine/README.md`](app/engine/README.md) — what was ported from
  javis-os and why.
- [`ANALYSIS-javis-os.md`](ANALYSIS-javis-os.md) — full feature and
  architecture analysis of javis-os, the reference codebase this project
  was built on top of.
- [`_AgentOn Agent 租用功能说明.pdf`](<_AgentOn Agent 租用功能说明.pdf>) —
  original product spec.
