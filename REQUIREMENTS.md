# Requirements → Implementation Mapping

This is the appendix the [README](README.md) points to instead of a vague
"implements what's in the PDF." Every requirement from
[`_AgentOn Agent 租用功能说明.pdf`](<_AgentOn Agent 租用功能说明.pdf>) (the
original product spec) is quoted below, translated, and mapped to the
concrete solution built for it — the API/module/connector that satisfies
it, and an honest status. Read this top to bottom and you have the full
pipeline: what the spec asked for, and exactly how this codebase answers
it.

Status legend: **Done** (implemented and tested) · **Done\*** (implemented,
but needs real third-party credentials to actually go live) · **Partial**
(the mechanism exists but a specific case is out of scope) · **Planned**
(not built yet, extension point identified).

---

## 1. Agent capabilities (task types)

> *PDF §一 "Agent 作用": Agent 用于帮助用户自动完成 AgentOn 平台上的各类任务 —
> the Agent automates tasks on the AgentOn platform. Listed task types:*

| PDF requirement | Solution | Status | Reference |
|---|---|---|---|
| X (Twitter) — follow an account | `TwitterFollowConnector` calls X API v2 `POST /2/users/{id}/following` using the **renter's own** OAuth2 token (never a platform-wide credential), obtained once via the `/platforms/twitter/authorize` → `/platforms/twitter/callback` PKCE flow. Independently re-verified afterwards by re-querying `GET /2/users/{id}/following` before the task is marked done. | Done\* | `app/engine/connectors/twitter.py`, `app/platforms/oauth_twitter.py` |
| X (Twitter) — like, retweet | `TwitterLikeConnector` / `TwitterRetweetConnector`, same OAuth pipeline, X API v2 `/2/users/{id}/likes` and `/2/users/{id}/retweets`. | Done\* | `app/engine/connectors/twitter.py` |
| Post X (Twitter) content | `TwitterPostConnector`, X API v2 `POST /2/tweets`. | Done\* | `app/engine/connectors/twitter.py` |
| Join a Discord community | `DiscordJoinConnector` uses Discord's documented "add guild member" flow: AgentOn's own bot token plus the renter's `guilds.join`-scoped OAuth token (from `/platforms/discord/authorize`) to add them to a guild. Re-verified via `GET /guilds/{guild}/members/{user}`. | Done\* | `app/engine/connectors/discord.py`, `app/platforms/oauth_discord.py` |
| Register on a specified platform/app | `PlatformRegisterConnector` — generic HTTP POST to any signup endpoint that accepts a JSON payload (waitlist/referral/quest-platform signups). | Done for plain-POST signup APIs · **Partial** for platforms that require a real multi-step UI or CAPTCHA (deliberately out of scope — see the connector's docstring on why fragile browser automation wasn't built instead) | `app/engine/connectors/platform_register.py` |
| Visit a specified webpage | `WebVisitConnector` — plain HTTP GET with redirect following, for referral/quest tracking links. | Done | `app/engine/connectors/webvisit.py` |
| AI content generation — text | `AiContentConnector` generates text via the CLI-as-brain runner (shells out to the `claude` CLI, javis-os pattern). | Done\* (needs the `claude` CLI installed + authenticated on the host) | `app/engine/connectors/ai_content.py`, `app/engine/cli_runner.py` |
| AI content generation — image, video | Not implemented — image/video generation needs different provider APIs and async job polling, which is a distinct connector, not a variant of the text one. | Planned | TODO noted in `AiContentConnector`'s docstring |
| Other automatable Web3/internet tasks (continuously expanding) | The `TaskConnector` plugin architecture itself: a new task type is one file implementing `run()`/`verify()` plus one line in `bootstrap.py`. This is the mechanism that satisfies "continuously expanding" — see ARCHITECTURE.md's "Adding a new sellable task type." | Done (the extensibility mechanism) · specific Web3 connectors are Planned (none built yet beyond the pattern) | `app/engine/connectors/registry.py`, `app/engine/connectors/bootstrap.py`, `ARCHITECTURE.md` |

---

## 2. Feature goals

> *PDF §二 "功能目标": provide complete Agent Rental capability so users can
> conveniently rent, manage, and use Agents.*

| PDF requirement | Solution | Status | Reference |
|---|---|---|---|
| Browse rentable Agents | `GET /marketplace/agents` (paginated, filterable by category), `GET /marketplace/categories` | Done | `app/marketplace/router.py` |
| View an Agent's capabilities, price, and introduction | `GET /marketplace/agents/{id}` returns `capabilities`, `short_description`, `long_description`, `pricing_unit`, `base_price_cents` | Done | `app/marketplace/schemas.py::AgentTemplateRead` |
| Rent an Agent online | `POST /billing/orders` (create) → `POST /billing/orders/{id}/pay` (wallet debit) or `POST /billing/wallet/recharge/checkout` (Stripe hosted checkout) to fund the wallet first | Done\* (Stripe checkout needs a real Stripe account; wallet-pay path works end to end today) | `app/billing/router.py` |
| Use an Agent online | `POST /instances/{id}/execute` | Done | `app/instances/router.py` |
| Manage rented Agents | `GET /instances` (list mine), `GET /instances/{id}` (detail) | Done | `app/instances/router.py` |
| View an Agent's running status | `AgentInstance.status` + `last_run_at`/`last_result_success`/`last_result_message`/`fail_streak` on the detail response | Done | `app/instances/schemas.py::InstanceRead` |
| View an Agent's usage fees | `GET /billing/transactions`, filterable to a specific instance via the `reference` field on consumption entries | Done | `app/billing/router.py` |
| Support renewal, stop, and release of Agent instances | Auto-renewal via the background scheduler when `wallet.auto_renew_enabled` and balance covers it; `POST /instances/{id}/stop`; `POST /instances/{id}/release` | Done | `app/instances/scheduler.py`, `app/instances/router.py` |

---

## 3. Business flow

> *PDF §三 "业务流程": enter Marketplace → browse & select → view details &
> price → pay rental fee → create Agent Instance → instance created →
> start using → ongoing Token/compute consumption → low-balance reminder →
> (recharge / renew) → stop → release.*

This flow is implemented exactly as sequenced, step for step — see
[ARCHITECTURE.md § "Request flow: renting and running an agent"](ARCHITECTURE.md#request-flow-renting-and-running-an-agent)
for the full call chain through every module, rather than duplicating it
here. Status: **Done**.

---

## 4. Functional modules

> *PDF §四 "功能模块": 4.1 Agent Marketplace, 4.2 Agent Rental, 4.3 Agent
> Console, 4.4 Billing.*

| PDF module | PDF sub-requirements | Solution | Status |
|---|---|---|---|
| **4.1 Agent Marketplace** | Agent list, category browsing, search, Agent details, capability intro, price display | `app/marketplace/` — `list_templates()` supports category filter + free-text search over name/description; `list_categories()`; detail endpoint returns full capability/price info | Done |
| **4.2 Agent Rental** | View price, select rental package (quantity), create order, online payment, create Agent Instance, view rental status | `app/billing/` (`Order` model snapshots price at purchase time) + `app/instances/` (`create_instance_from_order`) | Done\* (payment: wallet path Done, Stripe checkout Done\*) |
| **4.3 Agent Console** | View running status, start/stop/delete Agent, view rental info, view cost/consumption, view remaining duration/balance | `app/instances/router.py` (start/pause/stop/release/execute) + `GET /instances/{id}` (rental info, `expires_at` = remaining duration for time-based rentals) + `GET /billing/wallet` (remaining balance) | Done |
| **4.4 Billing** | Time-based (hour/day/month), token/compute-based, auto-renewal (optional), low-balance reminder, online recharge, consumption record query | See § 6 below — all sub-items mapped individually | Done |

---

## 5. Agent lifecycle

> *PDF §五: Created → Running → Paused (optional) → Stopped → Expired →
> Released/Deleted.*

Implemented as an explicit, enforced state machine — this is a 1:1 match,
not an approximation:

```python
# app/instances/lifecycle.py
CREATED  -> {RUNNING, RELEASED}
RUNNING  -> {PAUSED, STOPPED, EXPIRED}
PAUSED   -> {RUNNING, STOPPED, EXPIRED}
STOPPED  -> {RELEASED}
EXPIRED  -> {RELEASED}
RELEASED -> {}   # terminal
```

Every transition goes through `assert_transition_allowed()`, so an invalid
jump (e.g. `CREATED → STOPPED`, skipping `RUNNING`) is rejected with a 409
rather than silently accepted. Status: **Done**. Reference:
`app/common/enums.py::InstanceStatus`, `app/instances/lifecycle.py`.

---

## 6. Billing modes

> *PDF §六 "计费模式": time-based, token-consumption-based, package-based,
> auto-renewal, online recharge, consumption records, low-balance
> reminder.*

| PDF requirement | Solution | Status | Reference |
|---|---|---|---|
| Time-based (hour/day/month) | `PricingUnit.HOUR/DAY/MONTH` + `TIME_BASED_DURATIONS` compute `expires_at` at instance creation; the scheduler expires or auto-renews on schedule | Done | `app/instances/pricing.py`, `app/instances/scheduler.py` |
| Token/compute-consumption-based | `PricingUnit.TOKEN` meters `unit_price_cents` per `/instances/{id}/execute` call via `billing.service.meter_consumption` | Done | `app/instances/service.py::execute_instance_task` |
| Package-based | `PricingUnit.PACKAGE` — interpreted as a usage bundle (metered per call like TOKEN, not a time window), a documented design decision since the spec doesn't define exactly what a "package" bounds | Done (interpretation documented) | `ARCHITECTURE.md` § Design decisions |
| Auto-renewal (optional) | `Wallet.auto_renew_enabled` toggle via `PATCH /billing/wallet/settings`; the scheduler charges `charge_for_renewal()` and extends `expires_at` when enabled and balance covers it, otherwise the instance expires | Done | `app/billing/router.py`, `app/instances/scheduler.py` |
| Online recharge | Two paths: immediate (`POST /billing/wallet/recharge`, mock provider for dev/testing) and hosted checkout (`POST /billing/wallet/recharge/checkout` → Stripe-hosted page → `POST /billing/webhooks/stripe` credits the wallet once payment is confirmed, idempotently) | Done\* (Stripe path needs real Stripe API keys; mock path works today) | `app/billing/providers/`, `app/billing/service.py` |
| Consumption record query | `GET /billing/transactions` — full append-only ledger, newest first, paginated | Done | `app/billing/router.py` |
| Low-balance reminder | `WalletRead.is_low_balance` computed against `LOW_BALANCE_THRESHOLD_CENTS`, returned on every `GET /billing/wallet` call | Done as a queryable flag · **Partial** — no push/webhook alert channel yet (the spec says "提醒"/reminder, which a frontend can already implement by polling this field; a push notification pipeline is a future enhancement, not a blocker) | `app/billing/schemas.py::WalletRead` |

---

## What "Done\*" means in practice

Every "Done\*" item above is fully implemented and covered by tests, but
depends on a third party that only exists once you register real
credentials:

1. **X (Twitter) connectors** — register a developer app at
   [developer.x.com](https://developer.x.com), set `TWITTER_CLIENT_ID` /
   `TWITTER_CLIENT_SECRET` / `TWITTER_REDIRECT_URI`.
2. **Discord connector** — create a Discord Application, set
   `DISCORD_BOT_TOKEN` (bot, for the join action itself) and
   `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET` (OAuth2 app, for the
   connect flow).
3. **AI content generation** — install and authenticate the `claude` CLI
   on the host running AgentOn (`CLAUDE_CLI_PATH`).
4. **Stripe checkout** — set `PAYMENT_PROVIDER=stripe`, `STRIPE_SECRET_KEY`,
   `STRIPE_WEBHOOK_SECRET`, and register the webhook endpoint
   (`/billing/webhooks/stripe`) in the Stripe dashboard.

None of these are architectural gaps — the code path is complete end to
end (see the tests in `tests/test_platforms.py` and
`tests/test_stripe_billing.py`, which exercise the full logic against
mocked provider responses). They're operational setup steps, the same as
any SaaS wiring in its own payment/social credentials before launch.
