# Architecture

This document goes one level deeper than the README: module boundaries,
request flow, and — most importantly — the extension points you'll actually
touch when growing the platform.

## Module dependency graph

```
auth  ◄─────────────┐
  ▲                    │
  │                    │
marketplace ◄── billing ◄── instances ──► engine
  ▲                                          ▲
  └───────────────────────────────────────┘
              (instances reads task_type
               from marketplace, executes
               it through engine)
```

Rules that keep this from turning into a ball of mud:

- **`engine` depends on nothing else in `app/`.** It receives a
  `TaskContext` (plain data) and returns a `TaskResult` (plain data). It has
  no idea what billing, marketplace, or instances even are. This is what
  makes it portable — you could lift `app/engine/` into its own package
  later without touching anything else.
- **`marketplace` depends on `engine`** only to validate that a template's
  `task_type` is a real, registered connector at publish time
  (`marketplace/service.py::create_template`).
- **`billing` depends on `marketplace`** only to snapshot a template's price
  when creating an `Order` (`billing/service.py::create_order`).
- **`instances` is the orchestrator** — it's the only module that touches
  `engine`, `billing`, and `marketplace` all at once, because "run this
  rented agent's task" is inherently a cross-cutting operation (look up the
  template → get the connector → run it → charge for it → update state).
- **Nothing depends on `instances`.** If you add a second orchestrator later
  (e.g. a batch scheduler that runs many instances' tasks on a timer
  outside the request path — see `instances/scheduler.py`, which already
  does this for expiry), it plugs in the same way `instances/service.py`
  does, without instances.py itself needing to change.

## Request flow: renting and running an agent

```
1. POST /marketplace/agents          (operator publishes a template)
     marketplace.service.create_template()
       -> engine.connectors.registry.is_registered(task_type)  [validate]
       -> INSERT AgentTemplate

2. POST /billing/orders               (renter picks a template + quantity)
     billing.service.create_order()
       -> marketplace.service.get_template()   [snapshot price]
       -> INSERT Order(status=pending)

3. POST /billing/orders/{id}/pay
     billing.service.pay_order()
       -> debit Wallet.balance_cents
       -> INSERT Transaction(kind=order_payment)
       -> Order.status = paid

4. POST /instances                    (renter activates the purchase)
     instances.service.create_instance_from_order()
       -> marketplace.service.get_template()
       -> compute expires_at from pricing_unit (hour/day/month only)
       -> INSERT AgentInstance(status=created)

5. POST /instances/{id}/start
     instances.service.start_instance()
       -> lifecycle.assert_transition_allowed(created -> running)

6. POST /instances/{id}/execute       (renter actually uses the agent)
     instances.service.execute_instance_task()
       -> marketplace.service.get_template()
       -> engine.connectors.registry.get_connector(task_type)
       -> engine.verify.execute_with_verification(connector, ctx)
            -> connector.run(ctx)      [does the real work]
            -> connector.verify(ctx, result)  [independent re-check]
       -> on success + token/package pricing: billing.service.meter_consumption()
       -> on 3rd consecutive failure: auto-pause the instance
```

Background, outside the request path (`instances/scheduler.py`, started
from `app/main.py`'s lifespan handler):

```
every INSTANCE_TICK_SECONDS:
  for each RUNNING instance whose expires_at has passed:
    if wallet.auto_renew_enabled and balance covers renewal:
      billing.service.charge_for_renewal()
      extend expires_at
    else:
      instance.status = expired
```

## Extension points

### Adding a new sellable task type

This is the extension point the spec explicitly calls out ("支持持续扩展新的
任务能力" — must support continuously extending new task capabilities), so
it's deliberately the cheapest thing to do in this codebase:

1. Create `app/engine/connectors/your_task.py`:

   ```python
   from app.engine.connectors.base import TaskConnector, TaskContext, TaskResult

   class YourTaskConnector(TaskConnector):
       task_type = "your_task"

       async def run(self, ctx: TaskContext) -> TaskResult:
           ...  # do the work, using ctx.params
           return TaskResult(success=True, message="done")

   connector = YourTaskConnector()
   ```

2. Register it in `app/engine/connectors/bootstrap.py`:

   ```python
   from app.engine.connectors import your_task
   register(your_task.connector)
   ```

3. Publish an `AgentTemplate` with `task_type: "your_task"` through
   `POST /marketplace/agents`. That's it — billing, instances, and the
   marketplace never needed to change.

Override `verify()` on your connector if completion can be independently
checked from a separate source of truth (see `twitter.py`'s
`TwitterFollowConnector.verify`, which re-queries the follow relationship
instead of trusting the write call's 2xx response).

### Adding a new payment provider

1. Implement `app/billing/providers/base.py::PaymentProvider` (one method:
   `charge(user_id, amount_cents) -> str`, raising `PaymentFailedError` on
   failure).
2. Register it in `app/billing/providers/__init__.py`'s `_PROVIDERS` dict.
3. Set `PAYMENT_PROVIDER=your_provider_key` in `.env`.

Nothing in `billing/service.py` needs to change — it only ever calls
`get_payment_provider().charge(...)`.

### Adding a new pricing unit

`PricingUnit` lives in `app/common/enums.py`. Time-based units
(hour/day/month) need an entry in `app/instances/pricing.py`'s
`TIME_BASED_DURATIONS` so the scheduler knows how to compute expiry and
renewal windows; usage-based units (token/package) are metered per
`execute` call instead — see the branch in
`instances/service.py::execute_instance_task`.

## Design decisions worth knowing about

- **Wallet-based billing, not direct card charges per order.** Renters
  recharge a wallet (an external payment call happens exactly once, at
  recharge time), then all rentals and metered usage are simple internal
  ledger debits. This keeps `Order`/`AgentInstance` completely decoupled
  from whichever payment processor is configured, and gives you `Wallet`,
  `Transaction`, and `Order` as one clean audit trail instead of scattering
  payment-provider calls through the rental and usage code paths.
- **Append-only `Transaction` ledger.** Rows are never mutated or deleted;
  corrections are new offsetting entries (`kind=refund`). This means
  `GET /billing/transactions` is always a faithful history, and any future
  balance-mismatch bug can be diagnosed by replaying the ledger instead of
  trusting a mutable `balance_cents` column in isolation (that column is
  still kept on `Wallet` as a cache for fast reads — it should always equal
  the sum of that wallet's transactions).
- **Orders snapshot pricing.** `Order.unit_price_cents` and `pricing_unit`
  are copied from the template at purchase time, so changing a template's
  price later never rewrites historical orders or the instances created
  from them.
- **Independent verification before anything is billed or marked done.**
  Ported directly from javis-os's self-improvement loop: a connector's own
  "it worked" response is never trusted by itself for anything billable —
  see `engine/verify.py` and the 3-strikes auto-pause in
  `instances/service.py::execute_instance_task`.
- **Real relational DB (SQLModel/SQLAlchemy) for everything billing-
  related**, unlike javis-os's file-based JSON/Markdown state. Money needs
  ACID transactions and constraints, not a file lock — this was one of the
  explicit "avoid" recommendations from the javis-os analysis
  (see [`ANALYSIS-javis-os.md`](ANALYSIS-javis-os.md), section 3.2).
- **The scheduler is a single `asyncio` background task, not a distributed
  queue.** Fine for one process; if AgentOn ever needs multiple API
  workers, `instances/scheduler.py::tick_once` is already a self-contained
  function that can be lifted into a separate worker process or a real
  queue (Celery/BullMQ) — deliberately not built now, per YAGNI, since
  there's no evidence yet that a single process can't keep up.
