# QuantNest execution technical reference

**Source review date:** 12 October 2026, Asia/Kolkata.

This document describes the current repository implementation: how market observations travel through QuantNest, which processes consume them, how orders become positions and trades, and how to configure and operate those processes. It covers automated Paper and Live execution, the manual simulated Terminal, market charts, and Backtesting.

This is a source-based reference, not a new production validation or capacity benchmark. Examples use illustrative IDs and prices. Defaults are taken from source and may differ from a deployment's environment. Implemented behavior and remaining limitations are identified explicitly.

## Contents

1. [Architecture and terminology](#1-architecture-and-terminology)
2. [Processes, threads and responsibilities](#2-processes-threads-and-responsibilities)
3. [Configuration, versions and execution ownership](#3-configuration-versions-and-execution-ownership)
4. [Market data preparation and storage](#4-market-data-preparation-and-storage)
5. [A tick travelling through the system](#5-a-tick-travelling-through-the-system)
6. [The Paper and Live actor loop](#6-the-paper-and-live-actor-loop)
7. [Shared strategy evaluation](#7-shared-strategy-evaluation)
8. [Order requests and durable transport](#8-order-requests-and-durable-transport)
9. [Paper execution lifecycle](#9-paper-execution-lifecycle)
10. [Live execution lifecycle](#10-live-execution-lifecycle)
11. [Manual Terminal lifecycle](#11-manual-terminal-lifecycle)
12. [Chart and browser lifecycle](#12-chart-and-browser-lifecycle)
13. [Backtest lifecycle](#13-backtest-lifecycle)
14. [Risk, pause, stop, resume and version changes](#14-risk-pause-stop-resume-and-version-changes)
15. [Financial publication, state and recovery](#15-financial-publication-state-and-recovery)
16. [Configuration reference](#16-configuration-reference)
17. [Development and production startup](#17-development-and-production-startup)
18. [Scaling and extension boundaries](#18-scaling-and-extension-boundaries)
19. [Monitoring and troubleshooting](#19-monitoring-and-troubleshooting)
20. [Current limitations and verification boundaries](#20-current-limitations-and-verification-boundaries)
21. [Source navigation](#21-source-navigation)

## 1. Architecture and terminology

### 1.1 Overall flow

~~~mermaid
flowchart TD
    Browser[React browser] --> API[Django ASGI control APIs]
    API --> PG[(PostgreSQL)]
    PG --> Outbox[Committed outbox publications]
    Outbox --> Runtime[(Runtime Redis)]

    Provider[Market data provider] --> Feed[Market-data service]
    Feed --> Buffer[Local mmap candles and observed ticks]
    Feed --> Quotes[Coalesced quote cache and Channels]
    Quotes --> Browser
    Feed --> Replica[Optional observation replication]

    Buffer --> Actors[Paper and Live instrument actors]
    Actors --> CPU[Calculation process pool]
    CPU --> Actors
    Actors --> LocalQueue[Local publication queue]
    LocalQueue --> Streams[Paper and Live Redis order streams]
    Streams --> Paper[Paper simulated fills]
    Streams --> Live[Live broker submission]
    Live --> Broker[Broker]
    Broker --> Observations[WebSocket and REST observation handler]
    Paper --> PG
    Observations --> PG
    Runtime --> Actors

    Buffer --> Terminal[Terminal indexed matching]
    Terminal --> PG

    History[Stored and fetched historical candles] --> Backtest[Celery historical simulation]
    PG --> Backtest
    Backtest --> Results[Backtest trades, equity, metrics and diagnostics]
    Results --> PG
~~~

The browser configures execution, sends control requests and displays results. Trading workers continue without an open browser. Charts do not drive strategy decisions.

### 1.2 Core objects

| Object | Meaning |
| --- | --- |
| Strategy | Editable builder configuration owned by a user |
| StrategyVersion | Saved configuration snapshot with version number and notes |
| Allocation | Capital assignment and selected deployed strategy version |
| PaperTradingSession / TradingSession | Paper or Live deployment, status and lifecycle |
| Actor | Local execution state for one scope/session/instrument |
| OrderRequest | Strategy-generated instruction to the execution gateway |
| PaperOrder / LiveOrder | Recorded request and execution outcome |
| PaperPosition / LivePosition | Owned open exposure in that execution environment |
| PaperTrade / LiveTrade | Recorded closed exposure |
| Terminal Account / Order / Position | Separate manual simulated account and execution records |
| BacktestRun / BacktestContext | Saved experiment and its in-memory simulation state |
| RuntimeAssignment | Indexed assignment of an actor to an execution shard |
| RuntimeOutbox | Durable publication recorded with a financial or control mutation |

Actor identity is `(scope, session_id, instrument_id)`, not simply the strategy ID or symbol:

~~~text
paper : session 14 : instrument 101
paper : session 14 : instrument 102
live  : session 22 : instrument 101
~~~

These actors have separate trading state. They may share a symbol's market buffer.

### 1.3 Where state belongs

| State | Location and purpose |
| --- | --- |
| Strategies, versions, allocations, orders, positions, trades, balances | PostgreSQL: durable financial and configuration records |
| Current tick history and one-minute OHLCV ring | Local memory-mapped files: fast inter-process market reads |
| Actor trade state and refreshed capital/risk inputs | Worker memory: local evaluation |
| Ownership, pending requests, order streams, runtime projections | Runtime Redis: shared handoff and coordination |
| Latest browser quote | Market cache Redis: expiring, replaceable observation |
| Browser candles and chart series | React refs/state and chart library: presentation |
| Backtest positions and queued simulated fills | BacktestContext: one experiment's in-memory state |

There is no database write for every protective tick check. Actual financial fills still use database transactions. Redis projections can lag committed records; they are not a substitute for financial row locks.

## 2. Processes, threads and responsibilities

Source: [runtime CLI](../backend/quantnest_runtime/cli.py).

### 2.1 Service inventory

Run the runtime commands from `backend/` using the project virtual environment.

| Service | Command / entry point | Work performed |
| --- | --- | --- |
| Django HTTP/WebSocket API | `python -m uvicorn backend.asgi:application` | Authentication, permissions, configuration, lifecycle controls, chart history, results and browser WebSockets |
| Market data | `python -m quantnest_runtime market-data` | Provider socket, subscription reconciliation, warmup, local tick/candle publication and optional replication |
| Strategy execution | `python -m quantnest_runtime execution` | Actor ownership, protective checks, calculation admission and decision application |
| Order gateways | `python -m quantnest_runtime orders` | Separate Paper and Live stream consumers, account scheduling and recorded outcomes |
| Manual Terminal | `python -m quantnest_runtime terminal` | Conditional manual simulated orders matched against observations |
| Broker events | `python -m quantnest_runtime broker-events` | Broker-account order WebSockets and connection supervision |
| Outbox | `python -m quantnest_runtime outbox` | Retry committed runtime, cache, risk, Terminal and control publications |
| Celery workers | `python -m celery -A backend worker ...` | Bounded historical, reconciliation, research and maintenance jobs |
| Celery Beat | `python -m celery -A backend beat ...` | Publish scheduled jobs; it does not execute them itself |
| Private research service | `research_service.main:app` | AI model calls and allowlisted Django research tools; outside execution |

The market-data socket and the broker-order socket are different connections. A functioning price chart does not prove that broker order events are connected.

### 2.2 Execution process structure

The execution CLI is a supervisor. It spawns `EXECUTION_WORKERS` owner processes per node. Each owner contains:

- An owner loop that alone applies its actors' decisions.
- A background control/publication thread.
- A `ProcessPoolExecutor` with `CALCULATION_WORKERS` numerical processes.
- A localhost UDP notification socket.
- An inbox of at most 4,096 messages.
- A publication queue of at most 1,024 items.

CPU calculations run in child processes so a large indicator calculation does not execute inside the protective owner loop. Results cross a process boundary and incur serialization and scheduling costs.

### 2.3 Gateway process structure

The orders CLI spawns `ORDER_WORKERS` gateway processes per node. Each process currently starts **both** Paper and Live consumer threads. Each scope has its own bounded account thread pool with `ORDER_CONCURRENCY` workers.

The scope setting controls entry/deployment eligibility; it does not remove the Live consumer thread from this CLI implementation. On a public Paper deployment, leave broker-events stopped and do not configure/start Live sessions.

Gateway accounts are serial within their scope owner, while different accounts can run concurrently. If either scope consumer fails, its gateway process fails so the supervisor can recover it.

### 2.4 Terminal and singleton process structure

The Terminal CLI also spawns `ORDER_WORKERS` children. This setting controls two separately launched services; starting both services creates both sets of children.

Market-data runs one service per node. Node 0 connects to the source; other nodes replicate observations. Outbox and broker-events use deployment-wide singleton leases and should run on their chosen host.

The feed uses separate subscription/preparation and quote-publisher threads in addition to provider SDK callbacks. Multi-node publication adds an observation relay thread.

### 2.5 Worker counts

For `N` nodes, `E` execution owners per node and `C` calculation workers per owner:

~~~text
Execution owner children = N × E
Calculation children    = N × E × C
Gateway children        = N × ORDER_WORKERS
Terminal children       = N × ORDER_WORKERS
~~~

Supervisor processes, singleton services, ASGI workers, Celery parents/children, Redis and PostgreSQL are additional processes. Shards are ownership partitions, not operating-system processes.

### 2.6 Initialization and supervision

`initialize()` configures Django, sets numerical library thread defaults to one, and rejects an unsuitable runtime:

- The default database engine must be PostgreSQL.
- Django's default cache backend must be Redis.
- Worker counts and selected capacities must be positive.
- Node index must be inside the configured topology.
- Execution/gateway owners cannot exceed available partitions.
- Enabled scopes must be Paper and/or Live.

Process targets are importable from `cli.py`, supporting multiprocessing spawn on Windows and Linux. The thin `__main__.py` also handles directory/script invocation, but module invocation is preferred.

The parent polls child liveness, restarts failed children with bounded exponential delay, and exits after five repeated failures for an index. A child healthy for at least 60 seconds resets that counter. Shutdown interrupts backoff without starting another child. Production service supervision handles a failed parent.

## 3. Configuration, versions and execution ownership

Sources: [strategy snapshots](../backend/strategies/services.py), [assignments](../backend/core/assignments.py), [ownership](../backend/quantnest_runtime/ownership.py).

### 3.1 Strategy snapshot

The snapshot contains:

- Strategy identity and market metadata.
- Entry and exit configuration.
- Rule groups, rule operands, parameters, priorities and actions.
- Instruments and DIRECT execution routes.
- Position sizing.
- Time restrictions and event filters.
- Auto-disable rules.

Execution uses `allocation.deployed_version.config_snapshot`. It does not rebuild configuration from editable ORM rule rows on each tick. Saving a new builder version and selecting a deployed version are distinct operations.

Backtests use their saved version/snapshot with recursively merged run parameters. Normal creation takes an automatic snapshot; a confirmed research action can supply an approved snapshot.

### 3.2 Deployment

Paper deployment validates strategy status, Paper enablement, resource ownership, matching allocation/account and cost settings. It rejects redeployment while already running and changing deployment costs with open positions.

Live deployment validates strategy status, Live enablement and the allocation's strategy/user/broker-account relationship. Both paths record session controls and prepare funds/risk projections.

### 3.3 Assignment and capacity admission

Control publication synchronizes assignments inside the lifecycle transaction:

~~~text
shard = stable_hash("scope:session:instrument") % EXECUTION_SHARDS
global_owner = shard % (EXECUTION_WORKERS × EXECUTION_NODE_COUNT)
node_owner_index = node_index × EXECUTION_WORKERS + local_worker_index
~~~

Each owner acquires the shards mapped to its global index. A PostgreSQL advisory transaction lock serializes assignment admission, not tick processing.

New assignments must fit the user's total actor cap and the destination owner's actor cap. Capacity is hash-distributed; spare capacity on another owner does not automatically rebalance a full owner.

### 3.4 Leases

Execution and gateway leases normally expire after 15 seconds and renew approximately every three seconds. Singleton leases use 30 seconds and renew every five seconds.

The lease value is a unique owner token. Order publication and gateway validation verify it. Losing a lease stops the owner rather than allowing two owners to continue executing the same partition.

## 4. Market data preparation and storage

Sources: [provider selection](../backend/marketdata/providers.py), [data services](../backend/marketdata/services.py), [historical access](../backend/marketdata/access.py), [feed](../backend/marketdata/live_feed.py).

### 4.1 Three data paths

| Path | Consumers | Properties |
| --- | --- | --- |
| Accepted observed ticks in local rings | Paper/Live protection, Terminal matching | Independent reader cursors, bounded retention, source/receipt timestamps |
| Coalesced latest quotes | Browser, chart headers, cached execution reference/fill quotes | Latest value replaces earlier values; unsuitable as a complete tick replay |
| Stored/fetched provider candles | Warmup, backtests, chart history, research | Calendar/coverage checks, shared fetch coordination and database storage |

An observed tick is an accepted provider update. The current Fyers normalization does not establish that every exchange trade or exchange sequence number is available.

### 4.2 Subscription universe

`refresh_from_active_accounts()` includes:

- Instruments in the selected versions of sessions in RUNNING, PAUSED, STOPPING or ERROR.
- Manual Terminal positions and open orders.
- Browser subscription reference counts.

For an execution symbol, required history is the maximum lookback needed by its deployed strategies. Multiple strategies do not create multiple source subscriptions for the same symbol.

The feed's subscription thread reconciles approximately every 15 seconds. It resolves the active universe in one instrument query and reuses each version's lookback calculation. Beat also refreshes the registry every 30 seconds. Subscription admission and initial history preparation are not instantaneous.

### 4.3 History loading

Historical requests call `provider().history(...)`. Identical requests share a Redis lock and a short result cache. Returned candles are normalized and upserted in PostgreSQL.

Execution warmup checks expected market minutes, OHLC validity and coverage. Missing history is backfilled, then checked again. A symbol is not ready solely because some candles exist.

The local execution buffer is built from one-minute history. Historical backtests load one-minute source data for intraday frames and daily source data for daily/weekly frames, with coverage recorded per instrument/timeframe.

The running feed renews its preparation/readiness projection and can reconstruct a lost projection from locally prepared buffers. Removing a buffer clears its prepared-depth entry. Tick freshness, gap handling and completed-frame coverage checks still gate decisions.

### 4.4 Local mmap format

`SharedMemoryManager(symbol, "1m")` opens a file under `QUANTNEST_RUNTIME_DIR`. The filename contains a hash of symbol/timeframe and a format version.

| Region | Format |
| --- | --- |
| Header | 128 bytes; capacity and metadata |
| Candle ring | Six float64 values: open, high, low, close, volume, epoch |
| Tick ring | Five float64 values: local sequence, event epoch, receipt epoch, price, volume delta |

~~~text
File bytes = 128 + candle_capacity × 48 + tick_capacity × 40
~~~

With 10,000 candles and 32,768 ticks, this is about 1.71 MiB per symbol, before dataframe copies, caches and process overhead. History capacity is initially at least 10,000 or the required lookback plus 500, whichever is larger.

Metadata includes the current candle index, tick counter, last receipt time, candle revision, history revision, gap revision and optional upstream sequence/generation.

The feed is the intended local writer. Readers copy consistent slices under operating-system file locks. Linux uses shared/exclusive locks; Windows uses a short exclusive lock. This is memory-mapped storage, not lock-free execution.

Changing `MARKET_TICK_CAPACITY` does not resize existing files. Existing insufficient candle capacity requires controlled maintenance and resize.

### 4.5 Persisting recent official candles

The minute Beat task fetches recent provider candles for tracked symbols, upserts them and sends the latest completed one-minute candle as `candle.closed` to browser subscribers.

This is not a PostgreSQL write for every incoming tick, and the task does not itself replace every live execution mmap row. Local live aggregation and stored official candles can differ.

## 5. A tick travelling through the system

Sources: [ingestion](../backend/marketdata/live_feed.py), [buffer publication](../backend/marketdata/shared_memory.py), [wakeups](../backend/quantnest_runtime/signals.py), [UI publication](../backend/marketdata/streaming.py).

### 5.1 Provider callback

For a Fyers update:

1. Accept dictionary/list messages and ignore unusable symbols/prices.
2. Resolve the provider event timestamp, falling back to current time when absent.
3. Normalize quote fields: price, day OHLC, previous close, change, volume and last traded quantity.
4. Calculate volume delta from the previous daily cumulative volume.
5. On the first observation or a cumulative reset, use zero delta rather than assigning the whole day's volume to one minute.
6. Call `ingest_observation()` with event time and current receipt time.

The first observation's volume delta and coalesced quote volume are not a guarantee of exact trade-by-trade volume.

### 5.2 Local publication

For a prepared symbol, `update_current_candle()`:

1. Validates finite positive price, nonnegative volume and valid timestamps.
2. Checks upstream generation/sequence when supplied by replication.
3. Rejects an event older than the active minute.
4. Advances the candle ring on a minute change.
5. Creates or updates the minute's OHLCV.
6. Appends the accepted observation with a local sequence number.
7. Updates receipt metadata and the tick watermark.

If the symbol buffer is not prepared yet, that callback does not preserve an execution tick in a ring. The feed can still publish its UI quote. Strategy actors wait for readiness.

### 5.3 Wake the owner

The feed sends a small UDP packet to `127.0.0.1:EXECUTION_NOTIFY_PORT + worker_index` for each execution owner on that host.

UDP packets contain a wakeup, not the price or order. The owner reads the ring and its own sequence cursor. Lost wakeups are tolerated because the socket read times out at `EXECUTION_SCAN_INTERVAL`, and the owner scans watermarks again.

### 5.4 UI fanout

The feed separately replaces `_publications[symbol]` with the latest quote. Every approximately 50 milliseconds, the publisher:

- Updates `QuoteStore` in the market cache.
- Sends a Channels group message for the symbol.
- Periodically updates per-symbol feed receipt health.

This coalescing reduces browser traffic. Paper fills and Live freshness checks use the published quote cache, so the cached quote and the individual triggering observation are separate reference points.

### 5.5 Gap behavior

Each reader has its own sequence cursor. If a cursor falls behind the oldest retained tick, or source generation/sequence exposes a discontinuity, the actor records a gap.

For Paper/Live, new entries are blocked and a background operation pauses the affected session and notifies the user. Eligible OPEN-position protection can continue on subsequent available observations. Missing ticks are not reconstructed from candle highs/lows.

For Terminal, the worker logs the gap, moves its cursor to the current watermark and waits for fresh ticks.

## 6. The Paper and Live actor loop

Sources: [actor worker](../backend/quantnest_runtime/execution.py), [local context](../backend/strategy_engine/context.py), [decision application](../backend/strategy_engine/engine.py).

### 6.1 Background preparation and updates

The control thread normally refreshes sessions every three seconds, or sooner after an invalidation with a minimum snapshot spacing of about 250 milliseconds. It:

- Reads assignments and committed session status.
- Loads the allocation's selected version.
- Reconciles the union of assigned, positioned and pending-order instruments once on recovery, then restores risk state.
- Refreshes cached capital and risk inputs.
- Preloads calendars, holidays and instrument events.
- Reads runtime projection snapshots and lifecycle streams.
- Renews leases and publishes telemetry.
- Publishes queued order requests and guarded checkpoints.

A new actor waits for history and runtime readiness. Existing actors remain registered when readiness falls so eligible protection is still possible.

The readiness gate checks pending runtime outbox publications for the session; it is not a universal barrier for every cache or risk publication.

Each actor preloads its owner-side StrategyProgram once per deployed configuration. Event refreshes update that program. Snapshot application visits only that actor's instrument, and stale/duplicate state revisions do not invalidate a current calculation.

### 6.2 Per-cycle owner work

~~~text
Wait for wakeup or scan timeout
  → apply newer controls and runtime state
  → visit actors and read bounded tick batches
  → run eligible protective checks
  → admit changed-candle calculation work
  → process completed calculation results
  → submit bounded work, rotating between users
~~~

Each actor consumes at most `EXECUTION_TICK_BATCH` observations per visit. The owner checks candle work using `(market.revision, current_minute)`; it is not evaluating all indicators on every individual tick.

### 6.3 Protective checks

For an eligible OPEN position:

1. Update current price and peak price.
2. Compare observed price with the derived protected stop.
3. If no stop triggers, compare with the protected target.
4. Dispatch an opposite-side full exit when triggered.
5. Increment the actor generation to invalidate calculations using older state.

For BUY, stop triggers at or below its price; target triggers at or above. SELL comparisons reverse.

These price checks do not require ORM, Redis or broker calls in the owner. The resulting order publication is handed to its background thread.

The normal position reader requires phase OPEN. Pending and partially filled orders therefore suppress this normal protection path; see the limitations section.

### 6.4 Numerical calculation

Each task contains immutable configuration, symbol, preloaded calendar/events, copied instrument state/position, copied risk statistics and an `as_of` time.

The calculation process:

1. Reuses a StrategyProgram by configuration key.
2. Reads local one-minute history.
3. Builds complete, exchange-aligned required timeframes.
4. Reuses timeframe/indicator caches.
5. Evaluates exits if a position was supplied, otherwise entries.
6. Returns the decision, completed candle timestamp and diagnostic timing.

It cannot place an order. Program and indicator object counts are bounded; frame and indicator memory have separate cache budgets.

### 6.5 Result validity and entry admission

The owner discards results for removed actors or mismatched generations. A committed fill arriving during calculation changes generation and prompts another evaluation rather than using stale state.

Before entry, it requires RUNNING status, no gap, readiness, fresh ticks, positive capital, complete risk metrics, a permitted auto-disable policy, calendar/session/time/event/cooldown eligibility and a completed timestamp different from `last_entry_candle`.

Capital/risk inputs older than five seconds cause the context to return zero/empty values, blocking entries. Gateway financial admission checks again under locks.

### 6.6 Fairness and independence

Calculations rotate through per-user queues; outstanding jobs are bounded to twice the calculation-worker count. One actor has at most one calculation in flight.

Instrument trade/cooldown state is separate; risk and capital remain session/account concerns. Multiple actors can calculate in different processes, but protective visits on one owner are sequential. Accounts sharing one broker serialize gateway work and account financial changes.

A calculation deadline restarts its execution owner and therefore affects other actors owned by that process. This is bounded shared execution, not identical latency or complete fault isolation for every instrument.

### 6.7 Worked multi-strategy example

Assume two selected versions:

| Deployment | Instruments | Actor identities |
| --- | --- | --- |
| Strategy A, Paper session 14 | RELIANCE, TCS | paper:14:RELIANCE and paper:14:TCS |
| Strategy B, Paper session 15 | RELIANCE, INFY | paper:15:RELIANCE and paper:15:INFY |
| Strategy A, Live session 22 | RELIANCE, TCS | live:22:RELIANCE and live:22:TCS |
| Strategy B, Live session 23 | RELIANCE, INFY | live:23:RELIANCE and live:23:INFY |

This is eight actors over three market symbols. The same RELIANCE observation can be read independently by four actors. The feed does not subscribe four times, and one actor's read does not remove the observation for another.

An actor is not a dedicated OS process. These eight assignments map to the configured owners and numerical pool. If all deployments belong to one user, the Oracle starting cap of four user actors would reject admission of all eight until capacity is deliberately changed or deployments are reduced.

If both Live strategies use one broker account, their order requests enter that account's serial gateway scheduling and share broker funds reservations. Their strategy positions remain separated by allocation.

### 6.8 One signal through the full cycle

The following is illustrative behavior in a configured open trading session, not a measured timing result:

1. A five-minute entry candle covering 09:15–09:20 completes.
2. A new observed price updates the one-minute buffer and wakes the owner.
3. The owner checks any existing eligible position protection and schedules analytical work.
4. The calculation sees completed data through 09:20 and returns a BUY signal.
5. The owner verifies current state/gates, sizes ten units and records local ENTRY_PENDING.
6. The publisher persists the request; the gateway validates its lease, age, version and financial admission.
7. Paper fills ten units against its fresh published quote with modeled slippage. Live sends ten units to the broker and awaits confirmed observations.
8. Committed fill records and outbox publications eventually produce OPEN state with protection derived from each environment's actual fill price.
9. Later observed prices are checked against those levels. A triggered exit becomes a separate request with a new identity.
10. Exit fills reduce exposure, record realized results and update risk/cooldown state. A subsequent permitted entry uses that updated state.

In a backtest, the comparable five-minute signal queues a fill at the next available candle open. In the chart, quotes update the forming browser candle independently. Neither chart rendering nor backtest simulation executes the Live order.

## 7. Shared strategy evaluation

Sources: [StrategyProgram](../backend/trading_domain/strategy.py), [rule evaluator](../backend/rules_engine/evaluator.py), [indicators](../backend/rules_engine/indicators.py), [configuration](../backend/trading_domain/configuration.py), [exit actions](../backend/trading_domain/exit_actions.py).

### 7.1 Completed frames and timeframes

The data preprocessor aligns intraday candles to exchange session openings, daily candles to trading sessions, and weeks to Monday boundaries. Analytical indexes represent completion times. It excludes incomplete candles and checks expected source-minute counts.

Missing minutes in eligible completed candles can raise a calculation error. Missing data is not interpreted as a valid trading signal.

### 7.2 Entry and exit order

Entry evaluation checks time/event restrictions and instrument cooldowns, then active entry groups. Rules inside a group and groups themselves use configured combinations. Crossovers use the shared evaluator's crossing comparisons rather than a simple current greater-than comparison.

Configured exit evaluation checks:

1. STOP_LOSS groups.
2. TARGET groups.
3. EXIT groups.

For competing matched exit actions, full exit takes priority over partial exit, then move to breakeven. Already-applied partial and breakeven actions carry markers so they do not repeat indefinitely for that position.

Static protection is separately derived into price levels at fills. Complex rule-group combinations/actions need explicit parity checks against this fast derivation; sharing the evaluator does not prove that every derived protection configuration behaves identically.

### 7.3 Routing and sizing

Current strategy routing supports DIRECT: the signal instrument is the execution instrument. Unsupported route types are rejected.

Sizing uses the route override when supplied, otherwise strategy sizing. Fixed quantity and capital based sizing are supported; the removed risk based sizing is not part of this flow. Zero/invalid quantity prevents dispatch.

The execution context preloads lot metadata. Terminal performs explicit lot/tick admission checks. A Contract abstraction exists for quantity, tick size, currency and multiplier, but it is not universally applied to every strategy notional calculation.

Strategy entry/exit orders are MARKET. Terminal conditional orders are a separate feature.

## 8. Order requests and durable transport

Sources: [request/router](../backend/strategy_engine/router.py), [dispatcher](../backend/strategy_engine/dispatcher.py), [queue](../backend/strategy_engine/order_queue.py).

### 8.1 Request fields

| Field | Purpose |
| --- | --- |
| request_id | Unique retry/deduplication identity |
| scope | PAPER or LIVE; stream routing normalizes it |
| session_id / strategy_id / instrument_id | Exact execution ownership |
| strategy_version_id | Version against which the decision was made |
| account_key | `paper:<account-id>` or `broker:<credential-id>` |
| side / qty / order_type | Requested execution |
| intent | ENTRY or EXIT |
| target_price | Entry reference price; MARKET orders do not wait at this price |
| reason | Human-readable rule/exit cause |
| owner_key / owner_token | Execution lease fencing |
| expires_at | Entry deadline; currently five seconds from request construction |
| entry_time | Identifies the position an exit was calculated for |
| state_updates | Partial/breakeven-related state mutations |

### 8.2 Local handoff and Redis publication

The owner first marks local pending state and places the request in its in-process queue. This avoids synchronous Redis I/O in decision application.

The background publisher runs a Lua operation that:

1. Returns an existing pending request identity when present.
2. Checks the owner's current lease token.
3. Checks that EXIT still refers to the expected entry time.
4. Applies request state mutations and pending phase.
5. Appends the request to a scope/account-partitioned stream.
6. Stores the pending-request payload.

~~~text
stream partition = stable_hash(account_key) % ORDER_PARTITIONS
stream key       = quantnest:orders:<paper|live>:<partition>
pending key      = quantnest:pending-order:<scope>:<session>:<instrument>
~~~

The durable boundary is successful Redis publication. A request still inside the local queue can be lost if its process dies. Recovery does not claim to replay every unpersisted signal.

### 8.3 Gateway consumption and acknowledgement

Each partition has one leased gateway owner and a Redis consumer group named `execution`. Consumers read new entries and periodically reclaim unacknowledged messages idle for at least 30 seconds.

The gateway bounds its backlog, schedules different accounts concurrently and allows one in-flight task per account. It checks ownership and entry expiry, then invokes the scope-specific financial service.

After a recorded outcome, it clears only the matching pending request, reconciles runtime state, acknowledges and removes the stream item. Failure leaves it recoverable. An acknowledged Live submission may still be an unresolved broker order; stream acknowledgement does not mean FILLED.

Request-ID checks prevent a recovered request with an existing recorded order from being submitted again. Redis persistence, database transaction behavior and broker reconciliation remain essential; this is not a universal exactly-once guarantee.

## 9. Paper execution lifecycle

Source: [PaperExecutionService](../backend/paper_trading/services.py).

### 9.1 Start and entry

~~~text
Paper portfolio/allocation/account
  → select strategy version and costs
  → deploy session
  → register actors and prepare history
  → evaluate completed rules
  → enqueue Paper request
  → gateway financial admission
  → simulated fill
  → position/runtime publication
~~~

The consumer validates request ownership/deadline and current session status. Entry auto-disable checks also run in the execution service using the selected snapshot.

Inside a transaction, execution locks account, allocation and session separately. It verifies version/status, obtains a published quote no older than 15 seconds, applies session slippage, and checks required allocation capital and margin.

It records a REJECTED order when admission fails, or a FILLED order with the full simulated quantity and fill price. It creates/increases a PaperPosition, blocks notional margin and derives protection from the selected configuration.

There is no exchange queue, orderbook depth or probabilistic partial-fill model.

### 9.2 Exit and accounting

An opposite-side fill closes owned quantity. EXIT may not open exposure beyond the position quantity.

For a close:

~~~text
Gross P&L = price difference × closed quantity, adjusted for side
Net P&L   = gross P&L − configured charges
~~~

Execution records PaperTrade, releases proportional margin, updates current balance, reduces/deletes the position and records risk/runtime/cache outbox work. Session slippage and the saved charge profile determine modeled costs.

Partial closure publishes the remaining position. Full closure publishes CLOSED state and instrument cooldown timestamps.

### 9.3 User-visible updates

Paper order/position model signals schedule Channels messages after the transaction commits to `user_<id>_paper`, consumed through `/ws/paper/`.

Those browser notifications are best-effort post-commit delivery, distinct from retryable outbox projections. REST records remain available if a browser misses a notification.

## 10. Live execution lifecycle

Sources: [LiveExecutionService](../backend/live_trading/services.py), [broker adapters](../backend/brokers/services.py), [order observations](../backend/live_trading/order_processor.py), [fill reducer](../backend/trading_domain/orders.py).

### 10.1 Account preparation

The user connects an implemented broker, establishes a valid authentication session, selects a version and assigns capital through a Live allocation. Broker funds are refreshed outside the actor tick loop.

The calculation context uses the smaller of allocation availability and available broker funds. Authoritative admission checks account reservations again before sending an order.

### 10.2 Persist before broker submission

The Live gateway verifies session/version/ownership, entry freshness and risk. Under broker-account, allocation and session locks it:

- Requires valid reference price and an appropriately recent broker funds snapshot for entries.
- Subtracts outstanding entry notional reservations.
- Validates allocation and broker capital.
- Reserves EXIT quantity against owned positions and outstanding exits.
- Checks the request ID for an existing order.
- Records LiveOrder, its original session/allocation/version and an execution log.

For a valid submission, status is initially UNKNOWN before crossing the network boundary. Then BrokerService sends a MARKET order using `QN<local-order-id>` as its tag.

The broker's HTTP acknowledgement is merged against a locked current row. A WebSocket fill arriving first must not be overwritten by a later PLACED acknowledgement.

A transport error is ambiguous: the broker may already have accepted the request. The recorded UNKNOWN order remains reconcilable and is not blindly resubmitted.

### 10.3 Broker event ownership

The broker-events service creates processors for active, verified credentials. The implemented Fyers socket normalizes order/position events.

Both order WebSocket callbacks and REST reconciliation call `apply_order_observation()`. Matching is scoped to credential/user:

1. Match broker order ID.
2. Otherwise verify an exact `QN<local-order-id>` tag.
3. Reject identity conflicts in existing broker ID, symbol, side or quantity.
4. Retain the matched order's saved session/allocation/version.

Unmatched events are BrokerAccountObservation records. They do not create strategy positions, trades or P&L.

### 10.4 Cumulative fills

Account locking serializes concurrent REST/WebSocket observations. The reducer applies increased cumulative quantity only.

Illustrative example:

~~~text
Previous cumulative fill: 4 units, value 400
New cumulative fill:      7 units, value 715
Additional fill:          3 units at (715 − 400) / 3 = 105
~~~

Repeated/older observations have no new fill effect. Invalid fill quantities/prices are marked for reconciliation. A changed average at unchanged quantity is not silently applied to previously realized accounting.

Entry fills increase the allocation-owned LivePosition. Exit fills reduce it and create LiveTrade records. Remaining order quantity can stay active after a partial fill.

### 10.5 REST reconciliation

Beat schedules `live_trading.reconcile_all_active_accounts` every minute. Broker trade notifications can also request it, throttled per account.

The task includes active, paused, stopping or error sessions and sessions with open exposure or unresolved orders. It fetches orderbook/positions once per relevant credential, applies shared observations, refreshes funds and recomputes allocation health.

Signed broker position totals are compared with summed owned strategy positions by symbol/product. Differences are recorded and notified; account totals do not overwrite individual strategy positions.

### 10.6 Live accounting and browser state

Live order/position/session signals publish after commit to `user_<id>_live`, exposed through `/ws/live/`. Durable outbox publications update runtime/caches separately.

The current close writer sets realized P&L to gross price-difference P&L. It does not yet provide Paper's complete net-charge ledger. Slippage records compare cumulative actual fill prices with the signal reference.

Current implemented broker support is Fyers. The adapter factory rejects unfinished Zerodha/Angel paths. Serial account scheduling does not by itself implement every broker's rate-limit policy.

The former Execution Engine Defaults modal, settings API and OrderSettings model were removed because their stored timeout was never applied by submission. Gateway supervision uses ORDER_TASK_TIMEOUT; it does not mean an uncertain broker order can be cancelled or declared unfilled after that deadline.

## 11. Manual Terminal lifecycle

Sources: [Terminal services](../backend/trading/services.py), [matching books](../backend/trading_domain/matching.py), [Terminal worker](../backend/quantnest_runtime/terminal.py).

The current Terminal is a manual **simulated** environment with its own Account, Order, Position, TradeHistory and ClosedPositionLog records. It does not use PaperTradingSession actors and does not send these manual orders to the Live broker gateway.

### 11.1 Order admission

`POST /api/v1/trading/orders/` calls `TradingOrderService.create_order()`:

1. Validate supported type, positive quantity, required limit/trigger prices and instrument.
2. Lock the user's Terminal account.
3. Enforce the configured manual open-order limit.
4. Add the instrument to the tracked market universe.
5. Validate contract lot size and tick-size increments.
6. Reserve pending capital under the account lock.
7. Persist the order and publish a Terminal command through the outbox.

For an ordinary SELL, reservation distinguishes closing available long quantity from opening a short. Linked protective exits reserve no new capital. Outstanding orders are included in available-capital admission.

### 11.2 MARKET versus conditional orders

**MARKET:** admission resolves a fresh quote and immediately calls `execute_order()` in the API service. This does not wait for the Terminal worker's next price event. The default market-admission quote age is 30 seconds through a service setting; the worker's observed-tick freshness limit is 15 seconds.

**LIMIT, STOP and STOP_LIMIT:** the persisted OPEN order enters the worker's indexed book through `quantnest:terminal:commands`.

Terminal owners are partitioned by instrument:

~~~text
owner = stable_hash(instrument_id)
        % (ORDER_WORKERS × EXECUTION_NODE_COUNT)
~~~

This differs from strategy actor and gateway account partitioning.

### 11.3 Indexed matching

Each symbol book contains a market deque and heaps for buy/sell limits and buy/sell stops. Each order insertion/modification receives a revision. Old heap entries are ignored and periodically compacted.

| Order | Trigger against observed price |
| --- | --- |
| Buy limit | Price at or below limit |
| Sell limit | Price at or above limit |
| Buy stop | Price at or above trigger |
| Sell stop | Price at or below trigger |
| Stop-limit | Trigger activates a LIMIT order; limit eligibility still applies |

The worker handles commands, then reads one observation per symbol. It requires freshness, an exchange trading day and an in-session event timestamp. Eligible work is bounded by `TERMINAL_MATCH_BATCH`.

If eligible book work remains, it retains the same tick cursor until that work drains. The matching stage identifies candidates; the financial service rechecks the committed order before applying a fill.

This is indexed price-trigger simulation. It does not match one customer's buy against another customer's sell, model bid/ask depth, or reproduce exchange queue position.

### 11.4 Financial fill

`execute_order()` locks the account and order, refuses a non-OPEN order and validates linked exit quantity. It:

- Rechecks capital/margin against current positions and pending reservations.
- Updates signed position quantity and average price.
- Records realized closes for long sales or short covers.
- Updates account cash, realized P&L and short collateral.
- Sets the order COMPLETE and releases its reservation.
- Records TradeHistory.
- Cancels linked OCO alternatives when applicable.
- Publishes order/position changes.
- Synchronizes position-linked stop-loss and take-profit orders.

Buying reduces cash and selling increases cash. Short proceeds and collateral are represented in the used-margin calculation; a simulated short is not free capital for unrelated purchases.

### 11.5 Modification, cancellation and OCO

Committed modifications are republished to the book. The worker reads the current database row instead of trusting an old command payload, preventing a delayed command from reopening a cancelled order.

Cancellation releases reserved cash. Modifying a linked SL/TP updates its position setting; cancelling it clears the corresponding position protection. Position quantity changes adjust linked exit quantities.

Linked exits cannot reverse a flat position. OCO cancellation commits with the fill and publishes book changes.

### 11.6 Browser updates

Terminal order and position signals are delivered through the market-data WebSocket's user group. REST snapshot/history endpoints recover the view after missed messages.

Primary endpoints are `/api/v1/trading/terminal/`, `orders/`, `positions/`, `trades/` and `pnl-report/` under the trading prefix.

## 12. Chart and browser lifecycle

Sources: [chart endpoint](../backend/marketdata/views.py), [ChartDataService](../backend/marketdata/services.py), [consumer](../backend/marketdata/consumers.py), [browser socket](../frontend/src/shared/hooks/useWebSocket.js), [candle hook](../frontend/src/features/terminal/hooks/useRealtimeCandles.js), [ChartView](../frontend/src/features/terminal/components/ChartView.jsx).

### 12.1 Initial historical request

~~~text
ChartView selects symbol/timeframe
  → useRealtimeCandles
  → GET /api/v1/market/candles/
  → ChartDataService.chart_window
  → stored candles, optional source backfill
  → normalized chronological browser history
  → chart series setData
~~~

The frontend requests 300 candles per page. The server defaults to 240 and clamps requested limits to 50–1,000.

Query parameters:

~~~text
symbol=NSE:RELIANCE-EQ
interval=5m
limit=300
before=<optional Unix-seconds history boundary>
~~~

The server also accepts an instrument ID. Response fields include symbol, interval, candles, window, pagination and source/backfill information.

Each candle has `time` in Unix seconds plus open/high/low/close/volume. The older `ohlc/` endpoint returns millisecond timestamps; the active chart hook uses `candles/`.

### 12.2 Database/history behavior

The chart reads stored data first. Insufficient/stale windows can cause a coordinated provider fetch and database reread.

Intraday requests backfill one-minute source candles; daily/weekly requests backfill daily source candles. Requests exceeding the synchronous lookback threshold can schedule a background backfill and fetch a bounded recent portion.

`has_more` is inferred from the returned page length; it is not a precomputed guarantee that all older history exists.

### 12.3 Authenticated symbol subscription

The browser's shared WebSocket hook opens `/ws/marketdata/`. Django ASGI routes it through origin validation, JWT authentication middleware and the authenticated consumer.

~~~json
{"type":"subscribe","instrument":"NSE:RELIANCE-EQ"}
~~~

The consumer joins the normalized symbol group and increments the registry's client subscription count. It sends a subscription acknowledgement and immediately sends a cached quote, or a provider quote fallback when needed.

Multiple mounted chart/watchlist components share the browser socket and reference-count subscriptions. The last unsubscribe removes the backend subscription for that socket.

### 12.4 Live rendering

The feed's coalesced tick message has:

~~~json
{"type":"tick","symbol":"NSE:RELIANCE-EQ","data":{"price":2500,"timestamp":"<source time>","updated_at":"<receipt time>"}}
~~~

The hook normalizes the event, dispatches Redux quote updates at most about once per 200 milliseconds per symbol, and calls symbol callbacks for received events.

`useRealtimeCandles` updates the currently forming browser candle, preserves its open, extends high/low, changes close and accumulates volume. It batches chart rendering through `requestAnimationFrame`. ChartView updates candlestick, line/area and volume series and the quote header.

Source `candle.closed` events come from the scheduled recent-candle task. These provide a further candle update, not a complete correction/replay of every timeframe.

### 12.5 Older history and stale request handling

Scrolling near the left history boundary calls `loadOlder()`. It requests `next_before`, prepends/deduplicates results and preserves the visible logical range.

Symbol/timeframe changes abort obsolete HTTP requests. Request IDs prevent a late response from replacing newer initial history. Live data arriving during the initial fetch is merged into the current series.

### 12.6 Reconnect and time presentation

The socket sends ping about every 25 seconds and closes on a five-second pong timeout. Reconnect uses capped backoff, refreshes access credentials and resubscribes known symbols.

Reconnection is not a durable chart tick replay. The current candle hook does not explicitly refetch the entire missed history on every reconnect.

ChartView uses Asia/Kolkata formatting. Crosshair times include the year and IST for intraday bars; axis tick types show year/month/day/time as selected by the chart library. Daily/weekly series use IST business dates for presentation.

### 12.7 Chart accuracy boundary

The browser's live bucketing currently floors Unix time by fixed interval seconds. Backend strategy frames instead align to exchange session openings and Monday weekly boundaries. These are not the same aggregation for every timeframe.

UI quotes are coalesced, and frontend volume accumulation uses received updates/last traded quantities. Combining tick updates with completed-candle updates is not a proven exact volume-replacement algorithm.

Consequently, the browser's forming candle/volume is a presentation view, not the authoritative strategy evaluation frame. Do not use this chart pipeline as evidence of exact strategy/backtest data parity.

## 13. Backtest lifecycle

Sources: [creation/dispatch](../backend/backtesting/services.py), [task](../backend/backtesting/tasks.py), [engine](../backend/backtesting/engine.py), [historical adapter](../backend/backtesting/executor.py), [simulation context](../backend/backtesting/context.py), [fills](../backend/backtesting/execution_service.py).

### 13.1 Creation and queue dispatch

1. Validate ownership, snapshot instruments and active entry rules.
2. Save BacktestRun with selected dates, capital, slippage, charge profile and effective strategy configuration.
3. Transition a PENDING run into RUNNING for dispatch.
4. Queue `backtesting.run_backtest` after commit.
5. Revert dispatch state to PENDING with an error if queue submission fails.

The actual Celery queue is `backtesting`, not `backtest`. No live tick socket or execution actor is required to simulate a run.

### 13.2 Historical preparation

For each instrument the engine:

- Loads its calendar and holidays.
- Calculates indicator/timeframe warmup.
- Loads source candles and attempts missing-data backfill.
- Records coverage/warnings.
- Builds completed-time analytical indexes and indicator engines.
- Creates a BacktestStrategyExecutor inheriting StrategyProgram.
- Vectorizes active entry groups with the shared RuleEvaluator.
- Loads instrument event context.

Execution candles retain opening timestamps for fills. Analytical candles use completion timestamps so higher timeframe observations are not made available before their scheduled close.

Coverage failures are recorded; the backtest can continue on incomplete available datasets and skip instruments without data. This differs from strict real-time readiness gating.

### 13.3 Historical clock

One run forms the sorted union of all instrument candle timestamps. It processes that timeline sequentially in its Celery task.

At each timestamp:

| Step | Operation |
| --- | --- |
| 1 | Gather available instrument candles |
| 2 | Execute previous pending MARKET orders at this candle's open |
| 3 | Update position excursion/peak data and inspect OHLC protection |
| 4 | Apply immediate simulated stop/target closes; stop first if both are touched |
| 5 | Treat the candle as completed for rule evaluation |
| 6 | Evaluate configured exits and queue applicable next-open orders |
| 7 | Check entry signals, risk/time/event/cooldown restrictions, routes and sizing |
| 8 | Queue permitted entries for the next available candle open |
| 9 | Record current equity and drawdown |

If an instrument has no candle at that timestamp, its pending order waits. Available capital is shared within the run. Earlier exits in a pending batch can release capital before later entries. Actual slipped fill notional is checked again at fill.

Historical timestamps are the simulation clock; they are not wall-clock receipt times. An entry at a candle close is not filled at that same candle's opening price.

### 13.4 Shared and separate logic

Shared: rule evaluator, indicators, strategy group/exit semantics, cooldown/time/event logic, DIRECT routing, sizing evaluator, protection derivation, exit actions, risk policy and modeled cost calculator.

Separate: historical entry vectorization, sequential simulation state, OHLC stop/target policy, next-open fills and financial persistence. Paper/Live run actors; a backtest does not run the real-time actor scheduler or broker observation pipeline.

### 13.5 Accounting and result persistence

BacktestContext holds positions, pending orders, closed-trade accumulators, available capital, risk counters and diagnostics in memory. Realized partial exits accumulate into a trade record for their entry.

The engine writes trades/equity and calculates metrics including totals, win/loss statistics, charges, slippage, drawdown, instrument breakdown and periodic-equity-return measures. Undefined ratios such as profit factor without losses are stored unavailable.

Diagnostics include entry signals, existing positions, time/event restrictions, cooldown, sizing/capital/route rejection, queued entries, fills and auto-disable restrictions.

Progress and completion use `/ws/backtest/progress/` and per-user Channels groups. Cancellation is checked during simulation; exceptions persist FAILED state and error details.

### 13.6 End-of-run policy

`finalize_open_positions()` currently preserves realized partial exits and removes residual positions without a final market-price liquidation. The final equity point is set to realized current capital.

An untouched open position is therefore not represented as a forced closing trade or final unrealized equity. Results are not a complete final marked-to-market portfolio valuation under this policy.

OHLC cannot establish which level traded first inside a candle, exchange queue position, real partial fills or broker latency. The stop-first convention is a model assumption.

## 14. Risk, pause, stop, resume and version changes

Sources: [auto-disable](../backend/risk_management/auto_disable.py), [policy](../backend/risk_management/policy.py), [reenable task](../backend/risk_management/tasks.py), [finalization](../backend/core/lifecycle.py).

### 14.1 Risk configuration and metrics

Auto-disable rules are taken from the deployed snapshot, not individually queried rule models during tick evaluation.

The owner evaluates that configuration against refreshed local risk statistics before entry. Gateway entry services check again. Closed trades record risk outbox work; the relay updates deduplicated counters and evaluates whether to persist a PAUSED session.

Instrument cooldowns use that instrument's runtime entry/exit timestamps. Session risk counters can block all instruments of the session. Cached actor capital is an early gate; locked gateway reservations are the final financial gate.

### 14.2 Session transitions

~~~mermaid
stateDiagram-v2
    [*] --> RUNNING: deploy
    RUNNING --> PAUSED: user pause, risk restriction or recorded gap
    PAUSED --> RUNNING: eligible explicit resume or risk auto-reenable
    RUNNING --> STOPPING: stop
    PAUSED --> STOPPING: stop
    STOPPING --> STOPPED: no positions, active orders or queued requests
    STOPPED --> RUNNING: eligible deployment/resume
~~~

ERROR sessions are also loaded for monitoring/recovery. A session status is separate from an order status or instrument trade phase.

### 14.3 Pause and resume

Pause blocks new entries. Existing eligible OPEN-position exits remain evaluable. Queued entries are checked against committed session status at the gateway.

Resume refreshes lifecycle state and acknowledges recorded risk/gap controls. It does not bypass history, freshness, capital or version requirements.

The risk reenable task runs every five minutes. It resumes only recorded risk pauses whose cooldown and deployed-version rules permit automatic reenabling. Ordinary user pauses and data-gap pauses are not equivalent to those recorded risk pauses.

### 14.4 Stop

Paper's service defaults to closing positions. Live's service defaults to leaving exposure unless closure is requested by the caller.

Both enter STOPPING to block entries. Live commits this barrier before broker network I/O. Requested square-off submits opposite-side exits; the stop response is not a guarantee of immediate broker settlement.

Finalization locks account/session resources and requires:

- No owned positions with remaining quantity.
- No PENDING, PLACED, PARTIAL_FILL or UNKNOWN orders.
- No pending Redis order requests for assigned instruments.

Only then is STOPPED recorded with a stop control, releasing assignments. An unresolved broker outcome can keep STOPPING active.

### 14.5 Version changes

The selected deployed version is reloaded on the background path. A changed configuration identity replaces the actor/configuration. Orders carry the original decision version; financial admission rejects a changed allocation version.

Broker fills use the order's saved version rather than whichever version is currently latest in the builder. Risk pause acknowledgements are version-scoped.

Use the allocation deployment APIs and their validation. Directly modifying database version pointers bypasses lifecycle publication and is not an operational update method.

## 15. Financial publication, state and recovery

Sources: [outbox](../backend/core/outbox.py), [projection](../backend/core/runtime_projection.py), [runtime reconciliation](../backend/strategy_engine/runtime.py), [retention](../backend/core/retention.py).

### 15.1 Transactional outbox

A financial transaction records its database mutation and RuntimeOutbox work together. The outbox relay publishes later:

| Topic | Destination/effect |
| --- | --- |
| control | `execution_control` invalidation; assignment synchronization occurs when enqueued |
| runtime | Instrument runtime state plus per-session lifecycle stream |
| cache | Broker/session funds and risk projections |
| risk | Recorded close counters and auto-disable enforcement |
| terminal | `quantnest:terminal:commands` |

The relay selects independent aggregate heads. A failed publication blocks its successors in that topic/aggregate while unrelated aggregates can progress. Savepoints allow recording failures without poisoning the retry transaction.

Browser post-commit signals are separate best-effort notifications. They do not all have the same retry guarantee as outbox work.

Duplicate order/position cache lists were removed because no API or actor read them. Financial records remain in PostgreSQL, and active instrument state uses the dedicated runtime projection. The cleanup migration retires only the four obsolete cache publication methods; it does not delete financial records, queued order requests or runtime/risk/control events. Funds/risk caches do not generate unused generic version stamps; runtime revisions and the risk metric schema version remain active.

### 15.2 State keys and revision rules

| Key | Purpose |
| --- | --- |
| `quantnest:runtime:<scope>:<session>:<instrument>` | Current JSON instrument projection |
| `quantnest:lifecycle:<scope>:<session>` | Ordered projection updates |
| `quantnest:runtime-index:<scope>:<session>` | Instruments in a projection snapshot |
| `quantnest:pending-order:<scope>:<session>:<instrument>` | Request awaiting gateway outcome |
| `quantnest:orders:<scope>:<partition>` | Durable gateway work |
| `execution_control` | Session/configuration invalidations |
| `quantnest:terminal:commands` | Terminal book changes |
| `quantnest:market:observations` | Optional cross-node observations |
| `quantnest:lease:...` | Renewable process/partition fencing |

Runtime publication carries versions and committed outbox revisions. Old committed updates are rejected. Local application preserves protected-stop tightening and does not let an unrelated settled request clear a newer pending decision.

Hot peak/protection/action markers checkpoint about once per second with lease and entry-time guards. They are local/Redis state, not a database write on every tick.

Instrument state commonly contains side, quantity, average price, execution instrument ID, entry time, last entry/exit times, protected stop/target, current/peak price, pending/settled request identity, action markers and projection revisions.

| Trade phase | Meaning |
| --- | --- |
| Empty or CLOSED | No eligible open position; entry gates may admit new exposure |
| ENTRY_PENDING | Entry has been requested or an entry order remains active |
| OPEN | Recorded exposure is eligible for the normal position/protection reader |
| EXIT_PENDING | Full or ordinary exit work remains unresolved |
| PARTIAL_EXIT_PENDING | Partial exit work has unresolved remaining execution |

These phases are reconstructed from active recorded orders, pending Redis requests and positions. A rejected order can return the instrument to CLOSED or the remaining OPEN position. A partial broker fill can still leave an active pending phase. The phase, database position quantity and broker order status are different pieces of state and need not change simultaneously.

### 15.3 Recovery after an owner crash

1. Supervisor starts a replacement.
2. Acquire valid ownership after conflicting leases are released/expire.
3. Read assigned non-stopped sessions and selected versions.
4. Reconstruct financial state under account locks.
5. Include durable active orders and queued pending requests.
6. Restore instrument cooldowns from durable fills/closes.
7. Refresh funds/risk and take projection snapshots.
8. Replay lifecycle updates and resume eligible evaluations.

New actors initialize near the latest tick watermark, not at the beginning of all retained history. Recovery does not claim exact tick replay through downtime. Hot-only markers can have a checkpoint interval of exposure to loss.

### 15.4 Gateway and broker recovery

Unacknowledged Redis requests can be reclaimed. An existing request-ID order is not submitted again. Financial outcomes and runtime reconciliation allow the pending state to converge.

An existing UNKNOWN Live order remains a broker reconciliation problem, not a reason to retry the submission. If verified order/fill information is unavailable, manual resolution may be needed.

### 15.5 Retention

The nightly retention task:

- Deletes bounded batches of published outbox rows older than seven days.
- Removes stale stopped/nonexistent execution assignments.
- Trims snapshot-recoverable lifecycle/control streams to approximately two days.
- Trims Terminal commands only when all expected owners have current consumption cursors.

Pending financial publications are retained. Gateway requests are removed after acknowledgement, not by blanket stream expiry. Market replication retains approximately 120 seconds; mmap rings overwrite their oldest entries by capacity.

## 16. Configuration reference

Sources: [settings](../backend/backend/settings.py), [environment example](../backend/.env.example), [shared memory](../backend/marketdata/shared_memory.py), [Oracle overlay](../infra/oracle-a1-2cpu.env.example).

### 16.1 Environment loading and consistency

Django settings read the environment and project configuration through python-decouple. Systemd exports `/etc/quantnest/backend.env`; development normally uses the backend environment file. mmap directory/tick capacity also read process environment directly.

All producers/consumers must use matching database, runtime Redis, default cache, topology and partition settings. On one node, feed/Terminal/execution/calculation processes must use the same mmap directory. Restart affected services after settings changes.

Different deployment instances require deliberate isolation of database, Redis namespaces/databases, mmap directories and UDP ports; the current hardcoded key names do not provide an arbitrary deployment-ID namespace.

### 16.2 Connections

| Setting | Default / purpose |
| --- | --- |
| DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT | Existing PostgreSQL connection; required in production settings |
| REDIS_URL | `redis://127.0.0.1:6379/0`; default shared service URL |
| CACHE_URL | Defaults to REDIS_URL; Django default cache used by shared projections/registry |
| RUNTIME_REDIS_URL | Defaults to REDIS_URL; explicit runtime streams/leases client |
| CHANNEL_REDIS_URL | Defaults to REDIS_URL; browser event fanout |
| CELERY_BROKER_URL / CELERY_RESULT_BACKEND | Default to REDIS_URL |
| MARKET_CACHE_URL | Default localhost:6379/2; latest market quotes |
| RESEARCH_CACHE_URL | Default localhost:6379/3; analytical cache |
| QUANTNEST_RUNTIME_DIR | Default OS temp directory/quantnest-runtime; use stable writable local storage |
| USE_IN_MEMORY_CHANNEL_LAYER | Defaults to DEBUG; set false for separately running processes |
| USE_LOCMEM_CACHE | Runtime must not use this; runtime startup rejects a local default cache |

An in-memory Channels layer cannot deliver feed/Celery events across separate OS processes, even on a single development machine. A different logical Redis database does not isolate memory pressure or eviction from another database in the same Redis process.

Single-host separated-cache example:

~~~dotenv
REDIS_URL=redis://127.0.0.1:6379/0
CACHE_URL=redis://127.0.0.1:6379/0
RUNTIME_REDIS_URL=redis://127.0.0.1:6379/0
CHANNEL_REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
MARKET_CACHE_URL=redis://127.0.0.1:6380/1
RESEARCH_CACHE_URL=redis://127.0.0.1:6380/0
USE_IN_MEMORY_CHANNEL_LAYER=false
EXECUTION_NODE_COUNT=1
EXECUTION_NODE_INDEX=0
~~~

Runtime Redis uses the supplied [runtime.conf](../infra/redis/runtime.conf): AOF, `appendfsync always`, noeviction and private binding. Durable writes therefore include storage/fsync cost. The separate [cache configuration](../infra/redis/research-cache.conf) uses bounded memory and LRU eviction without persistence.

### 16.3 Execution and gateway settings

| Setting | Source default | Meaning |
| --- | --- | --- |
| EXECUTION_ENABLED_SCOPES | paper,live | Allowed deployment/entry scopes |
| EXECUTION_WORKERS | 2 | Owners per node |
| CALCULATION_WORKERS | 1 | Numerical children per owner |
| EXECUTION_SHARDS | 64 | Stable actor partitions |
| EXECUTION_NODE_COUNT | 1 | Coordinated execution nodes |
| EXECUTION_NODE_INDEX | 0 | This host's index |
| EXECUTION_MAX_ACTORS | 200 | Registered actors per owner |
| EXECUTION_MAX_USER_ACTORS | 64 | Registered actors per user across scopes |
| EXECUTION_TICK_BATCH | 128 | Tick observations per actor visit |
| EXECUTION_SCAN_INTERVAL | 0.005 seconds | UDP timeout/fallback scan interval |
| EXECUTION_NOTIFY_PORT | 19600 | Base localhost notification port |
| EXECUTION_TASK_TIMEOUT | 10 seconds | Calculation deadline after startup allowance |
| EXECUTION_STARTUP_TASK_TIMEOUT | 60 seconds | Deadline used during the initial owner startup period |
| CALCULATION_CACHE_MB | 128 | Separate frame and indicator cache budgets per numerical process |
| ORDER_PARTITIONS | 16 | Account stream partitions |
| ORDER_WORKERS | 2 | Children per separately launched orders and Terminal service |
| ORDER_CONCURRENCY | 4 | Concurrent account jobs per scope/gateway process |
| ORDER_TASK_TIMEOUT | 30 seconds | Gateway task deadline |
| TERMINAL_MATCH_BATCH | 64 | Eligible indexed work per symbol visit |
| TERMINAL_MAX_OPEN_ORDERS | 200 | Manual ordinary OPEN-order account limit |
| MARKET_TICK_CAPACITY | 32768 | Observations per newly created/resized symbol ring |

The limits are admission controls, not proven capacity guarantees. Reducing deadlines does not make an operation faster. CALCULATION_CACHE_MB is not a total RSS limit: frames, indicators, active calculations, mmap pages, queues and Django have additional memory.

### 16.4 Fixed timings in current source

| Mechanism | Approximate current timing |
| --- | --- |
| Actor funds/risk input validity | Five seconds |
| Execution tick freshness for new entries | 15 seconds |
| Paper published fill quote validity | 15 seconds |
| Live funds snapshot admission | Up to 90 seconds |
| Entry request expiry | Five seconds from construction |
| Feed subscription reconciliation | 15 seconds |
| UI quote publisher sleep | 50 milliseconds |
| Gateway blocking stream read | Up to 50 milliseconds |
| Gateway abandoned-item eligibility / scan | 30 seconds idle / scan every five seconds |
| Outbox idle wait | 50 milliseconds |
| Terminal command blocking read | Up to 50 milliseconds |
| Background execution snapshot | Three seconds normally; invalidations can refresh sooner |
| Guarded hot-state checkpoint | About one second |

These are scheduling/validity parameters, not tick-to-order latency measurements. Some are code constants, not environment options.

### 16.5 Market, broker and browser settings

- `MARKET_DATA_PROVIDER=fyers` selects the current provider; an importable implementation class can replace it.
- `FYERS_CLIENT_ID`, `FYERS_SECRET`, `FYERS_REDIRECT_URI` and the existing market-data token lifecycle configure the source.
- `BROKER_FYERS_*` settings configure the broker app connection separately, with defaults to corresponding source settings where defined.
- User BrokerCredential/BrokerSession records establish Live account authentication.
- `FRONTEND_URL`, `BACKEND_URL`, `ALLOWED_HOSTS`, CORS/origin and cookie settings must match deployment domains.
- `VITE_REACT_APP_API_URL` points React to the API, for example `https://api.example.com/api/v1`.
- The frontend derives `ws:` or `wss:` and root WebSocket paths from that URL.

A reverse proxy must support WebSocket upgrades and the current authentication/origin model. Configure Django's trusted proxy/HTTPS behavior for the actual host; copying localhost DEBUG settings is not a complete production configuration.

### 16.6 Celery and Beat

| Task name family | Queue |
| --- | --- |
| backtesting.* | backtesting |
| research.* | research |
| marketdata.*, instruments.* | marketdata |
| paper_trading.* | paper |
| live_trading.* | live |
| notifications.* | notifications |
| common.*, users.* and unmatched task families | default |

`risk_management.check_and_reenable_strategies` has no separate route and uses default. A queue needs a consuming worker; Beat alone is insufficient.

Defaults include prefork, concurrency selected at launch, prefetch multiplier one, late task acknowledgement and rejection on worker loss. Task-level idempotency is still required for retries.

Important scheduled work:

| Job | Current schedule |
| --- | --- |
| Refresh tracked subscriptions | Every 30 seconds |
| Fetch recent provider candles | Every minute |
| Reconcile Live accounts | Every minute |
| Check recorded risk auto-reenable | Every five minutes |
| Expire abandoned research runs | Every minute |
| Paper daily performance | 00:05 Asia/Kolkata |
| Market holiday sync | 00:05 |
| Paper allocation rebalance | 00:15 |
| Runtime retention | 02:15 |
| User session cleanup | 03:00 |
| Instrument master sync | 06:00 |
| Daily market-data repair | 23:55 |

Run exactly one Beat scheduler for a deployment.

## 17. Development and production startup

### 17.1 Required infrastructure

- Project Python environment and dependencies.
- PostgreSQL with the existing candle/TimescaleDB setup. Source SQL uses PostgreSQL date_bin and Timescale-style FIRST/LAST aggregation; runtime locking needs PostgreSQL.
- Redis supporting streams and XAUTOCLAIM, with persistent runtime configuration and appropriate private access.
- A stable writable mmap directory shared by the runtime processes on each node.
- Valid market-source credentials/token for observed ticks.
- Valid broker account sessions when using Live execution.
- Redis Channels for inter-process browser updates.

Oracle Database/MySQL is not a drop-in replacement for the current PostgreSQL queries. Cloudflare frontend hosting does not run these Python services; they run on the backend host.

### 17.2 Windows development

Activate the environment and use `E:/QuantNest/backend` as working directory. Set a shared process environment or consistent backend configuration, for example:

~~~powershell
$env:QUANTNEST_RUNTIME_DIR = 'E:/QuantNest/runtime/market'
$env:USE_IN_MEMORY_CHANNEL_LAYER = 'false'
~~~

Export QUANTNEST_RUNTIME_DIR consistently in every relevant shell; a variable set in one PowerShell window is not automatically exported to another.

After infrastructure/environment setup, apply migrations:

~~~powershell
python manage.py migrate
~~~

Start these in separate shells, one supervised runtime command per shell:

~~~powershell
python -m quantnest_runtime outbox
python -m quantnest_runtime market-data
python -m quantnest_runtime orders
python -m quantnest_runtime terminal
python -m quantnest_runtime execution
~~~

For a Live-enabled development deployment also run:

~~~powershell
python -m quantnest_runtime broker-events
~~~

Start the API separately:

~~~powershell
python -m uvicorn backend.asgi:application --host 127.0.0.1 --port 8000
~~~

Windows Celery development uses the solo pool; production Linux uses prefork. A small combined setup, from backend:

~~~powershell
python -m celery -A backend worker -Q default,notifications,marketdata,paper,live --pool=solo -c 1 -l info --hostname=control@%h
python -m celery -A backend worker -Q backtesting,research --pool=solo -c 1 -l info --hostname=heavy@%h
python -m celery -A backend beat -l info
~~~

Each command needs its own shell. A shared heavy queue intentionally runs one backtest or research job at a time. Use separate queue workers when resources permit and independent responsiveness is required.

From the repository root, the optional private research service starts with:

~~~powershell
.venv/Scripts/python.exe -m uvicorn research_service.main:app --host 127.0.0.1 --port 8001 --env-file research_service/.env
~~~

Start React from `frontend/` using its existing npm scripts. Frontend startup does not start backend runtime processes.

### 17.3 Oracle A1: 2 OCPUs / 12 GB

Use the existing [Oracle overlay](../infra/oracle-a1-2cpu.env.example) with the real deployment environment. This is a conservative starting profile for the specified host size, not a measured Oracle throughput or uptime guarantee:

~~~dotenv
EXECUTION_ENABLED_SCOPES=paper
EXECUTION_WORKERS=1
CALCULATION_WORKERS=1
ORDER_WORKERS=1
ORDER_CONCURRENCY=2
CALCULATION_CACHE_MB=32
EXECUTION_MAX_ACTORS=8
EXECUTION_MAX_USER_ACTORS=4
EXECUTION_SHARDS=64
ORDER_PARTITIONS=16
EXECUTION_NODE_COUNT=1
EXECUTION_NODE_INDEX=0
EXECUTION_SCAN_INTERVAL=0.005
EXECUTION_TICK_BATCH=128
EXECUTION_TASK_TIMEOUT=10
EXECUTION_STARTUP_TASK_TIMEOUT=60
ORDER_TASK_TIMEOUT=30
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
NUMBA_NUM_THREADS=1
~~~

Begin with one API worker, one execution owner and one numerical child, one gateway child, one Terminal child, one feed, one outbox, one control Celery child, one heavy Celery child and one Beat. Broker-events is optional for private Live; the source feed is still required for Paper.

For public Paper, consume `default,notifications,marketdata,paper` in the control worker. Add `live` for a separately configured Live deployment.

Do not start combined Celery workers and all per-queue worker instances unintentionally. Two CPUs are shared with PostgreSQL, Redis, API, warmup and analytical work. Increase actor admission only after measuring latency and backlog on the actual host.

### 17.4 Linux supervision

The supplied templates are:

- [quantnest-runtime@.service](../infra/systemd/quantnest-runtime@.service).
- [quantnest-celery@.service](../infra/systemd/quantnest-celery@.service).

They expect:

~~~text
Code:           /opt/quantnest
Virtualenv:     /opt/quantnest/.venv
Backend cwd:    /opt/quantnest/backend
Environment:    /etc/quantnest/backend.env
Runtime state:  /var/lib/quantnest/market
OS user/group:  quantnest
Writable logs:  /opt/quantnest/backend/logs
~~~

Install/adapt the units, prepare the account/directories and reload systemd. Start runtime instances according to enabled features:

~~~bash
sudo systemctl daemon-reload
sudo systemctl enable --now quantnest-runtime@outbox
sudo systemctl enable --now quantnest-runtime@market-data
sudo systemctl enable --now quantnest-runtime@orders
sudo systemctl enable --now quantnest-runtime@terminal
sudo systemctl enable --now quantnest-runtime@execution
~~~

For Live, start `quantnest-runtime@broker-events` too.

The runtime unit restarts on failure and kills the service control group on shutdown. It sets QUANTNEST_RUNTIME_DIR explicitly; configure the exported service environment and environment file together. Editing only backend/.env does not replace the environment already exported by the service.

The Celery template fixes concurrency one, bounded task reuse and memory policies, and lowers background CPU priority. A combined small-host worker can use a queue-list instance such as:

~~~bash
sudo systemctl enable --now quantnest-celery@default,notifications,marketdata,paper
sudo systemctl enable --now quantnest-celery@backtesting,research
~~~

API, Beat, reverse proxy and optional FastAPI need their own supervision; these two supplied templates do not install those services automatically. Bind private services to private interfaces and expose HTTP/WebSocket traffic through the configured proxy.

### 17.5 Startup and planned maintenance order

For a new deployment: infrastructure and migrations → outbox/feed → gateways and optional broker-events → Terminal/execution → API, background workers, Beat and optional research. Confirm history/funds/readiness before enabling sessions.

For an existing deployment/topology change:

1. Stop new starts/configuration mutations; pause new entries.
2. Reconcile broker obligations and decide how open exposure will be managed during downtime.
3. Drain requests where possible; retain unresolved outcomes.
4. Stop relevant owners/services before repartition/resize.
5. Apply migrations and consistent settings.

When upgrading through the 12 October cleanup, stop old API/fill producers and the outbox relay before applying `common.0010_retire_unused_order_position_projections` and `brokers.0008_remove_ordersettings`. Restart the matching new code afterward so old producers cannot recreate retired cache messages or query the removed settings table.
6. Rebuild assignments with execution stopped:

~~~bash
python manage.py rebuild_execution_assignments
~~~

7. Start feed/outbox and confirm preparation, then consumers/owners.
8. Restore API/background services and explicitly review/resume sessions.

The backend does not provide protective checks while its execution services are stopped. Closing the browser is different from stopping workers.

## 18. Scaling and extension boundaries

### 18.1 Scaling within one host

Increase actual CPU/memory resources before raising calculation concurrency or actor admission. Tune the measured bottleneck:

- Calculation backlog: numerical capacity/strategy complexity.
- Protective scan delay: owner count, admitted actors and tick batch.
- Gateway backlog: account threads, broker latency and database locks.
- Warmup/history pressure: marketdata queue and provider limits.
- Outbox lag: database/projection performance.
- Browser fanout: Channels, API and subscriber volume.

Increasing ORDER_CONCURRENCY cannot make requests on one broker account independent. Shared account capital and broker limits remain constraints.

### 18.2 Multiple execution nodes

Node 0 connects to the provider and relays accepted observations into `quantnest:market:observations`. Other nodes run a market-data replica which prepares local buffers and ingests sequence/generation-aware observations without another source socket.

Each node runs its execution, gateway and Terminal owners with a unique NODE_INDEX. PostgreSQL and runtime Redis are shared over a private network. mmap files are local to each host and are not a network filesystem transport.

Replication preserves original receipt timestamps. Approximately 120 seconds of stream retention and bounded relay queues limit replay. An overrun or sequence discontinuity is a gap, not proof of a complete replicated feed.

The current replica initializes its stream cursor near the tail. Multi-node startup/recovery and provider failure still require deployment testing.

### 18.3 Repartitioning and buffer changes

Changing owner/node counts changes shard ownership. Coordinate settings, stop old owners, rebuild assignments and restart. There is no automatic rolling reshard/handoff protocol.

Keep EXECUTION_SHARDS and ORDER_PARTITIONS stable where possible. Changing order partition count requires draining/migrating work in old streams; simply changing a number does not move existing requests.

To resize a symbol buffer, stop all local writers/readers and wait for leases to clear:

~~~bash
python manage.py resize_market_buffer NSE:SBIN-EQ --capacity 50000
~~~

Set MARKET_TICK_CAPACITY before the operation when changing tick retention too. Restart the feed before consumers. Replaced rings do not imply replay of missing observations.

Current multi-key Lua operations assume a compatible single Redis primary; Redis Cluster requires intentional key-slot changes.

### 18.4 Another data source

The provider boundary supports quote, history, live_client, name and capabilities. A replacement adapter should normalize source symbols/history into existing canonical IDs/keys and use the common ingestion function.

This is not universal plug-and-play: current instrument import fields, symbol normalization, market status and some timing assumptions still contain Indian/Fyers-specific behavior. Separate provider identity mappings and verified coverage semantics are needed for a general multi-market universe.

### 18.5 Another broker or instrument type

A broker needs authenticated submission/cancellation/funds, normalized orderbook/positions, reliable identity/tag handling, cumulative fill accounting, account limits and recovery through REST/WebSocket.

Future futures/options/crypto require contract selection, calendars, quantity multipliers, tick/lot validation throughout financial paths, margin, expiry/roll and settlement handling. The presence of Contract and MarketEvent types does not enable these products automatically.

### 18.6 Research isolation

Research uses Django/Celery/private FastAPI and existing data tools. It does not belong in the tick path. Heavy backtests/research can still compete for CPU on one VM; resource limits and admission policy are needed even though the processes are separate.

Business licensing/subscription enforcement is a separate implementation. EXECUTION_ENABLED_SCOPES is a deployment configuration gate, not a billing system or a statement of regulatory compliance.

## 19. Monitoring and troubleshooting

Sources: [health](../backend/quantnest_runtime/health.py), [telemetry](../backend/quantnest_runtime/telemetry.py), [runtime runbook](BACKEND_RUNTIME.md).

### 19.1 Health and latency meanings

`GET /health/` checks PostgreSQL connectivity and runtime Redis ping, returning 200 or 503. It does not check every source socket, actor, outbox aggregate or broker order.

Runtime keys:

- `quantnest:health:execution:<global-index>`: timestamp and rolling owner telemetry.
- `quantnest:health:terminal:<global-index>`: Terminal heartbeat.
- `quantnest:terminal:cursor:<global-index>`: command-consumption boundary.

Owner telemetry keeps up to 2,048 recent samples per stage and exports p50/p95/p99:

| Metric | Actual meaning |
| --- | --- |
| protection | Duration of one protective evaluation; may be a no-op |
| tick_to_decision | Receipt-to-protective-check processing time; not proof an order was generated |
| calculation_total | Admission-to-completion elapsed time including pool scheduling |

These metrics do not measure broker acknowledgement, execution or all gateway/database/outbox stages. Wall-clock-based receipt ages also depend on synchronized clocks.

### 19.2 Full latency decomposition

~~~text
Tick-to-broker-send =
  source transport/normalization
  + local publication and owner wait
  + protective decision OR completed-candle calculation
  + local publisher wait
  + Redis persistence/stream scheduling
  + gateway validation, locks and reservation
  + broker SDK submission

Tick-to-confirmed-position =
  the above
  + broker/exchange execution delay
  + broker observation delivery
  + database fill accounting
  + outbox/runtime convergence
~~~

For indicator entries, waiting for the configured candle to complete is a strategy condition, not a slow tick-processing bug.

The existing [instrument benchmark](benchmarks/INSTRUMENT_LATENCY.md) and [integrated order benchmark](benchmarks/ORDER_E2E_LATENCY.md) document measured local cases and limitations. The integrated broker is simulated; those results are not Oracle or actual exchange measurements.

### 19.3 Diagnostic commands

Use service logs and private authenticated operational access. Read-only Linux examples:

~~~bash
systemctl status quantnest-runtime@execution
journalctl -u quantnest-runtime@execution -n 100 --no-pager
systemctl status quantnest-runtime@orders
systemctl status quantnest-runtime@market-data
systemctl status quantnest-runtime@outbox
redis-cli --scan --pattern 'quantnest:health:*'
redis-cli XLEN execution_control
redis-cli XLEN quantnest:terminal:commands
~~~

For an identified scope/partition, inspect its consumer-group pending age through XPENDING and XINFO. Do not delete pending/UNKNOWN work as a troubleshooting shortcut.

### 19.4 Symptom-to-component map

| Symptom | Inspect first |
| --- | --- |
| Chart works but strategy does not enter | Assignment, selected version, history readiness, session status, tick/funds freshness, risk gates and sizing |
| Chart history works but prices do not update | Feed token/subscriptions, Channels Redis, ASGI socket/origin authentication, browser connection |
| Cross-process WebSocket events missing | USE_IN_MEMORY_CHANNEL_LAYER; default DEBUG can enable it |
| Paper says price unavailable | QuoteStore receipt age, feed publisher and MARKET_CACHE_URL |
| Decisions appear but no gateway outcome | Publication queue, stream pending age, ownership/expiry, orders service and DB admission |
| Live order UNKNOWN | Broker orderbook/tag matching, broker-events and REST reconciliation; do not resubmit blindly |
| Actor remains pending after fill | Pending request identity, recorded order status, outbox age, runtime revisions/reconciliation |
| Session remains STOPPING | Remaining positions, active/UNKNOWN orders and pending Redis requests |
| Conditional Terminal order does not fill | Terminal owner/book, committed order, fresh/in-session observations and command cursor |
| Strategy pauses on a gap | Ring overrun, source reconnect/generation, replica lag or missing source minutes |
| Backtest remains queued | Worker consumes backtesting queue; broker availability is unrelated |
| High calculation latency | CPU saturation, cold imports/indicator preparation, queued actors and cache memory |
| Memory/Redis pressure | Cache process separation, actor/universe caps, mmap capacity, RSS, AOF and noeviction errors |

### 19.5 Operational signals

Monitor CPU/RSS, source health, history failures, oldest gateway request, oldest unpublished outbox row, lease loss, worker crashes, unresolved broker observations, database lock waits, Redis persistence errors and chart socket reconnects.

Use session/account/request/order IDs and exception types for correlation. Keep credentials, tokens and raw authentication payloads out of logs.

## 20. Current limitations and verification boundaries

| Area | Implemented behavior / remaining boundary |
| --- | --- |
| Shared strategy logic | Common rules/sizing/exits, different live and historical drivers; complete execution equivalence is not established |
| Instrument independence | Separate state/cursors; shared owner scans, CPU queues, session risk and account locks |
| Equal latency/HFT | Neither identical per-instrument latency nor exchange-grade HFT is guaranteed |
| Order handoff | Durable after Redis publication; the initial local queue is not durable |
| Live partial-fill protection | Normal actor position/protection reads require OPEN; pending exposure needs further review |
| Application protection | Stops/targets trigger application MARKET exits; not native exchange protection |
| Complex protection rules | Fast static derivation and full group/action semantics need targeted parity validation |
| Paper fills | Immediate full simulated quantity against a fresh published quote with modeled costs |
| Live costs | Current closed-trade writer records gross P&L as realized P&L; complete net-charge accounting is unfinished |
| Broker cost corrections | Same-quantity cumulative cost changes are marked for reconciliation, not silently rewritten |
| Terminal matching | Indexed price simulation, not customer-to-customer exchange matching/depth |
| Chart aggregation | Frontend epoch buckets/coalesced volume are not backend session-aligned authoritative frames |
| Chart reconnect | Reconnect/resubscribe exists; complete missed history replay is not established |
| Backtest final exposure | Residual positions discarded; no automatic final liquidation or complete final unrealized valuation |
| Historical coverage | Coverage recorded; incomplete available backtests can continue with warnings |
| Multi-node operation | Sequenced replication exists; rolling repartition and comprehensive failure validation remain separate |
| Future markets/brokers | Adapter foundations exist; additional broker and contract lifecycle implementation is required |
| Browser notifications | Best-effort post-commit delivery; durable financial records/outbox projections remain separate |
| Startup/recovery | Financial reconstruction exists; full downtime tick replay is not claimed |

This document does not add or run tests, change runtime behavior, or validate a production deployment. Existing architecture/benchmark verification is described in [BACKEND_ARCHITECTURE_AUDIT.md](BACKEND_ARCHITECTURE_AUDIT.md), [BACKEND_RUNTIME.md](BACKEND_RUNTIME.md) and the benchmark reports.

## 21. Source navigation

| Concern | Primary files / functions |
| --- | --- |
| Service launch and supervision | [cli.py](../backend/quantnest_runtime/cli.py): initialize, main, run_child, singleton |
| Assignment/capacity | [assignments.py](../backend/core/assignments.py): synchronize; [ownership.py](../backend/quantnest_runtime/ownership.py): partition, Lease |
| Source adapter | [providers.py](../backend/marketdata/providers.py): provider, FyersProvider |
| Subscription and callback | [live_feed.py](../backend/marketdata/live_feed.py): refresh_from_active_accounts, sync_subscriptions, ingest_observation |
| Local market storage | [shared_memory.py](../backend/marketdata/shared_memory.py): update_current_candle, read_ticks, preload_historical_data |
| Replica transport | [replication.py](../backend/marketdata/replication.py): ObservationRelay, run_replica |
| Candle history and chart windows | [services.py](../backend/marketdata/services.py): MarketDataService, ChartDataService; [access.py](../backend/marketdata/access.py): StrategyMarketDataService |
| Official recent-candle jobs | [tasks.py](../backend/marketdata/tasks.py): fetch_live_candles_from_broker, backfill_missing_candles |
| Owner and calculations | [execution.py](../backend/quantnest_runtime/execution.py): Actor, _snapshot, run_worker; [calculation.py](../backend/quantnest_runtime/calculation.py): evaluate |
| Local context and decisions | [context.py](../backend/strategy_engine/context.py): SessionContext; [engine.py](../backend/strategy_engine/engine.py): evaluate_protection, apply_calculation |
| Completed MTF frames | [data_feed.py](../backend/strategy_engine/data_feed.py): completed_horizon, DataPreprocessor |
| Rules and indicators | [strategy.py](../backend/trading_domain/strategy.py): StrategyProgram; [evaluator.py](../backend/rules_engine/evaluator.py): RuleEvaluator; [indicators.py](../backend/rules_engine/indicators.py): IndicatorEngine |
| Requests and streams | [dispatcher.py](../backend/strategy_engine/dispatcher.py): OrderDispatcher; [router.py](../backend/strategy_engine/router.py): OrderRequest; [order_queue.py](../backend/strategy_engine/order_queue.py): publish_order, consume_orders |
| Protection and exit actions | [utils.py](../backend/rules_engine/utils.py): derive_protection_levels; [exit_actions.py](../backend/trading_domain/exit_actions.py): process_exit_action |
| Paper ledger | [services.py](../backend/paper_trading/services.py): PaperExecutionService |
| Live submission/ledger | [services.py](../backend/live_trading/services.py): LiveExecutionService |
| Broker normalization | [services.py](../backend/brokers/services.py): BrokerService, FyersAdapter; [factory.py](../backend/brokers/websocket/factory.py): BrokerWebSocketFactory |
| Live fill ownership | [order_processor.py](../backend/live_trading/order_processor.py): find_owned_order, apply_order_observation, observe_account_position |
| Cumulative reducer | [orders.py](../backend/trading_domain/orders.py): observe_order |
| Broker recovery | [websocket_processor.py](../backend/live_trading/websocket_processor.py); [reconciliation_service.py](../backend/live_trading/reconciliation_service.py); [tasks.py](../backend/live_trading/tasks.py) |
| Manual Terminal | [terminal.py](../backend/quantnest_runtime/terminal.py); [matching.py](../backend/trading_domain/matching.py): IndexedOrderBook; [services.py](../backend/trading/services.py): TradingOrderService |
| Browser market transport | [streaming.py](../backend/marketdata/streaming.py), [quote_store.py](../backend/marketdata/quote_store.py), [consumers.py](../backend/marketdata/consumers.py), [useWebSocket.js](../frontend/src/shared/hooks/useWebSocket.js) |
| Browser chart | [useRealtimeCandles.js](../frontend/src/features/terminal/hooks/useRealtimeCandles.js), [ChartView.jsx](../frontend/src/features/terminal/components/ChartView.jsx), [tradingTerminalApi.js](../frontend/src/features/terminal/services/tradingTerminalApi.js) |
| Backtest run | [services.py](../backend/backtesting/services.py), [tasks.py](../backend/backtesting/tasks.py), [engine.py](../backend/backtesting/engine.py), [executor.py](../backend/backtesting/executor.py), [context.py](../backend/backtesting/context.py), [execution_service.py](../backend/backtesting/execution_service.py) |
| Risk lifecycle | [auto_disable.py](../backend/risk_management/auto_disable.py), [policy.py](../backend/risk_management/policy.py), [tasks.py](../backend/risk_management/tasks.py) |
| Durable publication/recovery | [outbox.py](../backend/core/outbox.py), [runtime_projection.py](../backend/core/runtime_projection.py), [runtime.py](../backend/strategy_engine/runtime.py), [lifecycle.py](../backend/core/lifecycle.py), [retention.py](../backend/core/retention.py) |
| Runtime settings/operations | [settings.py](../backend/backend/settings.py), [backend env example](../backend/.env.example), [runtime guide](BACKEND_RUNTIME.md), [Oracle profile](../infra/oracle-a1-2cpu.env.example) |
