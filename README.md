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

## Try it now — live public demo

The dashboard is running publicly right now via a Cloudflare quick tunnel, so
anyone can click around without installing anything:

**→ https://arranged-inspired-fragrances-specifications.trycloudflare.com/app/**

Log in with the shared demo account (already loaded with a huge test
balance so you never have to think about recharging):

```
Email:    demo@agenton.dev
Password: AgentOnDemo2026!
```

A few things to know about this specific link:

- **It's a free quick tunnel, not a real deployment.** Quick tunnels have no
  uptime guarantee and the URL changes every time the tunnel is restarted —
  treat it as a temporary demo link, not a stable product URL. See
  ["Going to production"](#going-to-production) below for how to get a
  permanent domain instead.
- **Everyone who logs in shares the same demo account** — same wallet,
  same instances, same connected social accounts. That's intentional (see
  the FAQ entry ["Do I need my own Twitter/Discord developer
  account?"](#do-i-need-my-own-twitterdiscord-developer-account-to-test-this)
  below for why), but it also means don't treat anything typed into this
  demo as private, and expect the wallet balance/instance list to be
  whatever the last visitor left it as.
- `PAYMENT_PROVIDER=mock` on this instance, so "recharging" is always fake
  money — no real card is ever asked for.

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
- **Customer-facing dashboard** — a no-build vanilla-JS single-page app
  (`web/`) for the actual rental flow: sign up, browse the marketplace,
  rent and run agents, manage the wallet, and connect X/Discord — served
  directly by the backend, no separate frontend deployment.

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

web/               customer dashboard — vanilla JS SPA, no build step
├── index.html
├── styles/        design tokens, base layout, components
└── js/            api client, hash router, one file per view

tests/             pytest suite covering every backend module above
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

Open **http://localhost:8000/app/** for the customer-facing dashboard
(register, browse the marketplace, rent agents, manage your wallet), or
http://localhost:8000/docs for the interactive Swagger UI (developer-facing
API explorer), or http://localhost:8000/health to confirm the server is
running.

The dashboard (`web/`) is a plain HTML/CSS/vanilla-JS single-page app with
no build step — it's served directly by FastAPI's `StaticFiles`, so there's
no separate frontend server or Node toolchain to run. See
[`web/`](web/) if you want to restyle it or add screens.

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

### 5. Try it with sample agents already loaded

A fresh database has an empty marketplace. Run this once to load 8 ready-to-rent
sample agents (one per task type, so there's something to click on immediately):

```bash
python scripts/seed_demo_data.py
```

Safe to re-run any time — it skips agents that already exist.

## FAQ — what do I need before I start?

Short version: **some agents work the instant you rent them, with nothing to
prepare. Others need one small setup step first.** This section walks
through it like you've never done any of this before.

Two different people read this section:

- 🛠 **"I run the AgentOn server"** — a few steps below are done **once**,
  by you, in the server's `.env` file. After that, every renter benefits —
  they never see or touch these steps.
- 🙋 **"I just rent agents on a running AgentOn site"** — you only ever
  click buttons inside the dashboard. You never edit a config file or
  install anything.

### These agents need *nothing* — rent and run them right now

- **Web Visitor Bot**
- **Platform Signup Bot**

They don't touch any outside account. Register, recharge your wallet with
the free **Recharge (dev)** button on the Wallet page, and rent either of
these to see the whole flow work end to end in under a minute.

### "AI Content Writer" (writes text for you)

This is a **one-time setup for the server operator only** — renters never
need their own account for this one.

1. Go to **[claude.ai](https://claude.ai)** and create an account.
2. Subscribe to a paid plan — **Claude Pro** or **Claude Max** (this is a
   monthly subscription, like Netflix, and is what actually pays for the AI
   to write things).
3. On the computer/server running AgentOn, install the **Claude Code** CLI
   tool by following **[docs.claude.com/claude-code](https://docs.claude.com/claude-code)**.
4. Run `claude` once in a terminal and log in with the account from step 1.

That's it. From now on, anyone who rents "AI Content Writer" on your
AgentOn site gets real AI-written text — they don't need a Claude account
of their own.

### Do I need my own Twitter/Discord developer account to test this?

Short answer: **only the server operator needs one — real testers don't,
as long as the operator sets it up this way.**

There are two separate things that look similar but aren't:

1. **The "pool" (Client ID/Secret / Bot Token) — set up once by the
   operator in `.env`.** This just tells Twitter/Discord "this AgentOn
   server is allowed to ask people to log in." It doesn't perform any
   actions by itself.
2. **A connected account — set up per dashboard login, via Connected
   Accounts.** This is *whose* X/Discord account actually gets followed
   from / posted from / joined-into-servers-as. Someone has to log in with
   a real X/Discord account for this step to exist at all — there's no way
   around that, because that's what makes the action happen *as* a real
   account instead of a fake one.

For a **public demo where random visitors shouldn't need their own X or
Discord account**, the trick is: the operator does step 2 **once**, logged
in as the *shared demo account* (`demo@agenton.dev` from the [public demo
link above](#try-it-now--live-public-demo)), using any spare/throwaway X
or Discord account they're comfortable with automating. From then on,
every visitor who logs into that same shared demo account inherits that
already-connected account — nobody else ever sees an OAuth screen. This is
exactly the "I rent the API, testers just use my resources" model — it's
just implemented as "one shared login" rather than a special code path.

If instead every renter needs their *own* X/Discord identity behind their
actions (the correct model for a real multi-tenant product, not just a
demo), skip this trick — give each renter their own dashboard account and
let Part B below run per-renter, the normal way.

One honest caveat: X (Twitter) now requires a **paid API tier** (currently
starting at the "Basic" plan) to do write actions like follow/like/retweet/
post — the free tier is read-only. Budget for that before promising these
agents work for real. Discord's bot API remains free.

### "X Auto-Follow / Auto-Like / Auto-Retweet / Auto-Post" (Twitter agents)

**Part A — done once by the server operator:**

1. Go to **[developer.x.com](https://developer.x.com)** and sign in with
   any X account.
2. Click **Create a project**, then **Create an app** inside it.
3. X will show you two secret codes: a **Client ID** and a **Client
   Secret**. Copy both somewhere safe.
4. Open the server's `.env` file and paste them in:
   ```
   TWITTER_CLIENT_ID=<paste your Client ID here>
   TWITTER_CLIENT_SECRET=<paste your Client Secret here>
   ```
5. Restart the AgentOn server so it picks up the new values.

**Part B — done by each renter, inside the dashboard, no typing required:**

1. Open the dashboard → **Connected Accounts**.
2. Click **Connect X (Twitter)**.
3. Log in with your own X account — exactly like clicking "Sign in with X"
   on any other website.

From then on, every X agent that renter rents automatically uses their own
connected account.

### "Discord Community Joiner"

**Part A — done once by the server operator:**

1. Go to **[discord.com/developers/applications](https://discord.com/developers/applications)**.
2. Click **New Application**, give it any name.
3. Open the **Bot** tab → click **Add Bot** → copy the **Bot Token**.
4. Open the **OAuth2** tab → copy the **Client ID** and **Client Secret**.
5. Paste all three into `.env`:
   ```
   DISCORD_BOT_TOKEN=<paste bot token here>
   DISCORD_CLIENT_ID=<paste client id here>
   DISCORD_CLIENT_SECRET=<paste client secret here>
   ```
6. Invite that bot into any Discord server you want renters to be able to
   join, with permission to manage members.
7. Restart the server.

**Part B — done by each renter:**

1. Dashboard → **Connected Accounts** → **Connect Discord** → log in with
   your Discord account.

### Accepting real credit card payments (instead of test money)

Done once by the server operator:

1. Go to **[stripe.com](https://stripe.com)** and create a free account.
2. In the Stripe dashboard, go to **Developers → API keys** and copy your
   **Secret key**.
3. Add to `.env`:
   ```
   PAYMENT_PROVIDER=stripe
   STRIPE_SECRET_KEY=<paste secret key here>
   ```
4. In Stripe, set up a webhook pointing to
   `https://your-domain.com/billing/webhooks/stripe`, then copy the
   **Signing secret** it gives you into `.env` as `STRIPE_WEBHOOK_SECRET`.
5. Restart the server.

Until this is done, the **Recharge (dev)** button on the Wallet page always
"succeeds" instantly with fake money — perfect for testing, but it must
not be shown to real paying customers.

### I don't want to set any of this up yet — can I still try the product?

Yes. Register on the dashboard, click **Recharge (dev)** to get free test
funds, and rent **Web Visitor Bot** or **Platform Signup Bot** — both work
immediately with zero setup, so you can test the entire browse → rent →
run → pay flow today.

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
- The [public demo link above](#try-it-now--live-public-demo) is a free
  Cloudflare quick tunnel — fine for letting people click around, not a
  real deployment. For a permanent domain, deploy the same Docker image
  (see [Docker (Postgres-backed)](#3-docker-postgres-backed)) to a host
  that gives you a stable public URL — Render, Fly.io, and Railway all have
  a free/low-cost tier that can run a Docker container plus a managed
  Postgres database with no server to maintain.

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
