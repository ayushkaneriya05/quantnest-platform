# Backend runtime operations

**Source review: 16 October 2026.** This is the process and recovery runbook.
Read the [execution technical reference](execution-technical-reference.md) for tick,
calculation, order, fill and backtest internals. Begin deployment with the selected
[mode guide](../infra/README.md); it owns exact installation commands and scripts.

## 1. Architecture in one view

```text
React → trusted same-origin gateway → Django API / Channels
                                      ↓
                           PostgreSQL financial/configuration records
                                      ↓ transactional outbox
data source → market-data → local mmap → execution owners / calculation children
                    ↓                       ↓ background publisher
               UI quote fanout         durable Redis order streams
                                            ↓
                                       orders gateway
                                     ↙              ↘
                              Paper ledger      broker → observations
                                                      → Live ledger

manual Terminal API → immediate market fill OR outbox command → Terminal book
backtest/research API → Celery compute → historical engine / private AI service
```

PostgreSQL is authoritative for financial records and saved configuration. Local
mmap carries bounded market observations; each actor keeps local execution state.
Runtime Redis supplies fenced ownership, requests, projections and control streams.

Funds/risk projection access goes directly through
`core/shared_state_store.py`; there are no separate cache read/write wrapper
services. This removes indirection while retaining the same storage keys, risk
locks and runtime synchronization.

The evaluation path uses prepared/local state. Database locks, provider calls,
commercial admission and durable publication happen in their owning services/
background paths. Financial recording necessarily uses database transactions.

## 2. What each process does

| Compose service | Launch target | Responsibility |
| --- | --- | --- |
| api | uvicorn backend.asgi:application | REST, Admin and authenticated WebSockets |
| feed | python -m quantnest_runtime market-data | Source subscription, normalization, mmap and UI publication; replica on nonzero nodes |
| execution | python -m quantnest_runtime execution | Actor ownership, bounded tick scans, protection and calculation scheduling |
| orders | python -m quantnest_runtime orders | Per-enabled-scope stream consumers and serialized account admission/submission |
| terminal | python -m quantnest_runtime terminal | Indexed conditional-order simulation |
| outbox | python -m quantnest_runtime outbox | Retryable database-to-runtime publication |
| broker-events | python -m quantnest_runtime broker-events | Qualified Live broker sockets and shared order observations |
| background | Celery background worker | Default, Paper, data, notifications and enabled Live maintenance |
| compute | Celery compute worker | Backtests and research starts |
| beat | Celery Beat | One scheduler for periodic jobs |
| research | Private FastAPI service | Authenticated model/tool loop; no direct browser access |
| postgres / redis services | Their container images | Persistent database, queues/projections and bounded analytical caching |

The service name is **feed**, although its CLI argument is **market-data**.
Use feed in Compose logs/start commands.

A runtime parent supervises execution/Terminal/order children and restarts failed
children with backoff. Five repeated crashes fail the service; a healthy minute
resets its crash count. Compose restarts failed services. Singleton leases prevent
two feed/outbox/broker-event owners from silently acting as one.

There are no shared systemd runtime/Celery units in the current deployment path.
Public systemd timers only operate host backups and monitoring. Django management
commands remain appropriate for finite setup, migration, health and maintenance work.

## 3. Deployment and scope controls

| Control | Responsibility |
| --- | --- |
| QUANTNEST_DEPLOYMENT_MODE | development/public/private commercial and deployment behavior |
| EXECUTION_ENABLED_SCOPES | paper/live execution availability |
| DEBUG | Boolean diagnostics/security configuration; not a deployment mode |
| BILLING_ENABLED | Hosted payment availability; not a Live trading switch |

Public rejects Live in settings and uses Paper. Development defaults to Paper and
can explicitly enable Live for intentional broker development. Private enables
the configured execution scopes. Private new work requires a current signed licence and has no numeric software
quotas; Live requires current broker qualification.

Development records usage without enforcing numeric plan limits. There are no
catalog feature-state or Private per-module permission gates.
Ownership, funds, input validation, scopes and runtime admission still apply.
Commercial checks are made on user-driven entry points; execution safety/funds/
identity checks remain at financial admission. Orders are not cancelled merely
because a subscription allowance runs out.

Navigation can show Broker/Live pages with a Private notice when unavailable.
Visibility in the sidebar is not evidence that execution is enabled.

## 4. Shared infrastructure requirements

1. Use Python 3.12 and the locked backend dependencies. Numerical libraries are
   configured for one native thread by the backend image/runtime launcher.
2. Use PostgreSQL/TimescaleDB. Row locking, date_bin and source aggregation queries
   are not portable to SQLite/MySQL/Oracle Database unchanged.
3. Keep Redis private. Celery/Channels/general caches, durable runtime work and
   evictable research caches have distinct roles.
4. Use the same runtime Redis/database/topology settings for all related services.
5. Feed, execution/calculation and Terminal need the same local mmap directory on
   a host. A network filesystem is not the cross-node observation transport.
6. Preserve encryption keys, signing verification keys and required durable volumes
   across upgrades/restores.
7. Ensure market history/calendar/token preparation before expecting entries.

The supplied stacks use separate Redis processes so analytical cache eviction
cannot discard financial runtime requests. Logical Redis database numbers alone
do not isolate eviction or memory pressure. Runtime Redis uses AOF, noeviction and
synchronous fsync; account for its disk latency and rewrite headroom.

Private stores accepted licence/revision state in PostgreSQL and mounts delivered
verification keys read-only. It has no separate licence-state volume. The shared
backend image does not create a Private-only licence directory.

## 5. Runtime settings

These are current source defaults, not measured capacity promises. Mode Compose
files inject connection addresses, notification targets, scope and runtime paths.
Do not copy every derived value into an environment file.

| Setting | Default | Meaning |
| --- | ---: | --- |
| EXECUTION_WORKERS | 1 | Owner children per execution service |
| CALCULATION_WORKERS | 1 | Numerical children per execution owner |
| EXECUTION_SHARDS | 64 | Stable actor partitions |
| EXECUTION_NODE_COUNT / EXECUTION_NODE_INDEX | 1 / 0 | Topology size and this node |
| EXECUTION_MAX_ACTORS | 8 | Actor admission per owner |
| EXECUTION_MAX_USER_ACTORS | 4 | Aggregate per-user actor admission |
| EXECUTION_ENABLED_SCOPES | paper | Nonempty paper/live scope set |
| EXECUTION_TICK_BATCH | 128 | Bounded observation processing |
| EXECUTION_SCAN_INTERVAL | 0.005 seconds | Fallback scan interval |
| EXECUTION_TASK_TIMEOUT | 10 seconds | Warm calculation deadline |
| EXECUTION_STARTUP_TASK_TIMEOUT | 60 seconds | Initial calculation deadline |
| CALCULATION_CACHE_MB | 32 | Each bounded calculation cache budget; not total process RSS |
| ORDER_PARTITIONS | 16 | Account request streams |
| ORDER_WORKERS | 1 | Children in each orders and Terminal service |
| ORDER_CONCURRENCY | 2 | Concurrent accounts per scope/gateway |
| ORDER_TASK_TIMEOUT | 30 seconds | Gateway task supervision deadline |
| TERMINAL_MATCH_BATCH | 64 | Eligible work per symbol visit |
| EXECUTION_NOTIFY_PORT | 19600 | Local UDP wakeup base port |
| MARKET_TICK_CAPACITY | 32768 | Tick-ring capacity for newly created/resized buffers |

MARKET_TICK_CAPACITY and QUANTNEST_RUNTIME_DIR are also read directly from process
environment by local market storage. Set them consistently in every relevant
native shell; Compose supplies the shared runtime path.

CACHE_URL defaults to REDIS_URL; RUNTIME_REDIS_URL also defaults there for native
configuration. The supplied Compose stacks deliberately assign their service URLs.
Research and market quote caches use RESEARCH_CACHE_URL and MARKET_CACHE_URL.

Total owners cannot exceed execution shards; total gateways cannot exceed order
partitions. Node index must be within node count; worker/batch/cache values must
be positive. A shorter timeout does not make broker execution faster.

## 6. Initial Oracle A1 profile

For the agreed **2 OCPU / 12 GB** Public VM, begin with the supplied conservative
Compose profile:

- One API process.
- One execution owner and one calculation child.
- One order gateway child with two concurrent account operations.
- One Terminal child.
- One background task and one compute task at a time.
- One Beat, one feed and one outbox relay.
- Numerical library threads fixed at one.

Compute is CPU-bounded by the supplied production profile. Container ceilings
leave host headroom but do not guarantee safe simultaneous peak use/builds.

The four-actor per-user admission is below Build/Pro's five/twenty Paper instruments.
Their checkout stays blocked until promised capacity is provisioned. Increasing a
commercial allowance or adding idle worker processes does not create hardware.

Measure CPU/RSS, tick backlog, calculation scheduling, gateway age, database locks,
Redis persistence and broker response time before raising concurrency.

## 7. Start the system

### Recommended mode-specific workflow

1. Follow [Development](../infra/development/README.md),
   [Public](../infra/public/README.md) or [Private](../infra/private/README.md).
2. Copy only that mode's example files and configure required inputs.
3. Run the documented deploy/migration/static initialization.
4. Enrol Admin, configure the Site and finish provider/data/licence preparation.
5. Check service status, runtime diagnostics and real end-user actions.

For an existing Public stack, from the repository root:

```sh
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml ps
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml logs --tail 100 feed execution orders terminal outbox
python infra/shared/scripts/diagnostics.py --root . --mode public
```

The shared scripts' requirements and exact arguments are documented in
[shared script instructions](../infra/shared/scripts/README.md). Do not substitute
another mode's env file.

### Native development

The Development guide owns PostgreSQL/Redis port mappings and complete native
environment setup. From backend/ with the project environment active:

```sh
python manage.py migrate
python -m uvicorn backend.asgi:application --host 127.0.0.1 --port 8000
```

Each long-running command below needs a separate shell:

```sh
python -m quantnest_runtime outbox
python -m quantnest_runtime market-data
python -m quantnest_runtime orders
python -m quantnest_runtime terminal
python -m quantnest_runtime execution
```

Only when Live scope is intentionally enabled:

```sh
python -m quantnest_runtime broker-events
```

Linux Celery uses prefork. Native Windows development uses solo:

```sh
python -m celery -A backend worker -Q default,notifications,marketdata,paper,live --pool=solo -c 1 -l info --hostname=background@%h
python -m celery -A backend worker -Q compute --pool=solo -c 1 -l info --hostname=compute@%h
python -m celery -A backend beat -l info
```

Use one Beat. A worker must consume every queue to which work is routed.

## 8. Background tasks

| Work | Queue / schedule |
| --- | --- |
| Backtests and research.start_research | compute |
| Other research, commercial, customer-support, installation, user/common work | default |
| Market history/instruments | marketdata |
| Paper / Live / notifications task families | paper / live / notifications |
| Commercial reconciliation and customer-content retention | Every 5 minutes |
| Private licence refresh | Every 6 hours, Private only |
| Risk auto-reenable | Every 5 minutes |
| Live account reconciliation | Every minute, Live scope only |
| Expire abandoned research | Every minute |
| Tracked subscriptions | Every 30 seconds |
| Recent official source candles | Every minute |
| Daily snapshots, rebalances, calendars, instruments and cleanup | Named schedules in settings |

Beat schedules tasks; it does not execute them. Backtests/research intentionally
share one heavy queue initially. Long I/O tasks can still delay other background
jobs; monitor queue age and separate queues only when measured load justifies it.

Accepted compute work is submitted directly to Celery after its database
transaction commits. There is no additional dispatch table or polling interval.
The shared `queue_compute_work` helper marks eligible unstarted work failed and
refunds its reservation if publication raises an error. If the API process stops
between commit and submission, inspect the saved job, cancel it through the
workspace and submit a new request. There is no automatic replay of that gap.
Payment webhooks verify the raw-body signature, fetch authoritative provider
state and apply it during the HTTP request. No payment-event inbox or event replay
task is used. Duplicate deliveries still use the same payment/refund/dispute
identifiers, so they cannot grant the same paid period twice. A provider failure
returns HTTP 503 rather than acknowledging an unapplied webhook. Checkout
reconciliation continues to inspect provider outcomes. Support emails,
newsletter updates and approved refunds use
ordinary Celery tasks with up to five retries after task failures.

Celery uses late acknowledgement, rejection on worker loss and prefetch one.
Individual services still need idempotent outcomes; queue delivery is not an
exactly-once financial guarantee.

## 9. Health, diagnosis and latency

GET /health/ checks database and runtime Redis. It does not prove source freshness,
all workers, broker connectivity or every unpublished outbox aggregate.

The container probe calls local health without booting a second Django process,
checks the expected mode and supplies trusted-ingress headers when needed.
Use deployment_health/deployment_metrics and the shared diagnostics for deeper
operational checks, with the commands described in the mode guides.

Runtime owner telemetry reports local protection, receipt-to-check and calculation
timing percentiles. An observed check can be a no-op. It does not measure complete
broker submission, exchange fill or financial convergence.

| Symptom | First checks |
| --- | --- |
| History chart works, no live prices | Source token/feed/subscriptions and Channels/gateway |
| Prices work, strategy never enters | Session/version, history readiness, assignments, freshness, risk, sizing and funds |
| Decisions pending | Publisher, Redis stream pending age, orders gateway and locked admission |
| Live order UNKNOWN | Account-scoped order identity, broker events and REST reconciliation |
| STOPPING never completes | Open quantity, unresolved orders and pending runtime requests |
| Terminal conditional order waits | Book command cursor, fresh in-session observation and committed order |
| Jobs remain queued | Correct Celery queue worker, not merely Beat |
| Errors after source changes | Restarted processes, consistent environment/dependencies and migration state |

Do not delete pending requests/UNKNOWN orders to clear an incident. Correlate
session, account, request and order IDs; keep credentials out of logs.

## 10. Safe restart, recovery and upgrades

A decision in the local publisher queue is not durable. Successful Redis publication
is the request durability boundary. Gateway reclaim and request IDs prevent
repeating an already recorded submission; ambiguous broker outcomes reconcile.

Actors reconstruct from recorded positions/orders and runtime projections. They
start near current observations, not a full replay of downtime. UI notifications
are best effort; REST and durable records recover the view.

For planned work:

1. Settle or explicitly manage exposure and renewal obligations.
2. Read the mode's deployment/backup procedure. Stop or pause sessions through
   their normal workspace controls before stopping the application services.
3. Back up and preserve secrets/keys before modifying containers or schema.
4. Use the documented deploy workflow; do not run competing owners or Beat.
5. Diagnose and explicitly review/resume eligible sessions afterward.

Backups and isolated restores are detailed in infra. Rebuilding execution
assignments is a controlled topology/recovery action; it is not required at each
normal startup.

Application stops/targets cannot run while execution services are stopped.
Independent broker access remains necessary for accepted Live operation.

## 11. Scaling and extension

Instrument/strategy actors have separate state and cursors, but share finite CPU,
owner scans, session risk and account locks. Fair scheduling is not equal latency.

Scale the identified bottleneck: numerical calculation, protective scans, financial
gateway, history, API fanout or outbox. Serialize shared account funds deliberately.

Multiple nodes share PostgreSQL/runtime Redis but keep local mmap. Node zero
relays observations; other feed processes replicate them. Node counts, index,
shards and partitions must agree. Changes require controlled stop/drain/rebuild;
there is no automatic rolling reshard protocol.

Market-data adapters normalize quote/history/live observations. Broker adapters
normalize submission/funds/order observations. Current FYERS/Indian instrument and
calendar assumptions still require work when adding another provider/market.
Only the implemented broker and NSE stock execution paths are available now.

Review [technical limitations](execution-technical-reference.md#20-current-limitations-and-verification-boundaries)
before claiming derivatives, universal adapters, exchange matching, guaranteed HFT
or exact backtest/Paper/Live execution equivalence.
