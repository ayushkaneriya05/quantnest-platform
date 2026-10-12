# Backend architecture verification — 10 October 2026

## Follow-up review and simplification — 12 October 2026

### Assessment

The service boundaries, PostgreSQL financial transactions, account-scoped cumulative fill writer, Redis ownership/handoff, local tick buffers and bounded calculation processes are appropriate foundations for a bounded retail trading platform. They do not establish a fully validated production Live system, identical instrument latency, exchange-grade HFT or effortless support for arbitrary markets.

Scaling owner/calculation/gateway counts is possible through configuration and coordinated assignment rebuilds. It remains a planned maintenance operation, with shared database/Redis/source dependencies and account-level serialization.

### Cleanup implemented

| Finding | Change | Practical effect |
| --- | --- | --- |
| Order/position cache lists were written but had no API/actor readers | Removed the duplicate projections and their producers; retained financial records and dedicated runtime state | Removes list copying, Redis rewrites/locks and additional outbox rows per fill |
| Funds/risk cache versions and update stamps had no readers | Removed generic stamps/counters; retained runtime revisions and the risk schema version | Eliminates unused counter operations and metadata |
| Cache helpers exposed unused quotes, instruments, session versions and synthetic cache statistics | Removed dead interfaces and eager package exports | Smaller API surface and fewer import side effects |
| Paper and Live duplicated capital/risk getters and unused configuration queries | Consolidated local readers; removed unused configuration getters/constants | One implementation of stale-input entry blocking |
| Startup reconciled positions, pending orders and configured instruments in multiple overlapping passes | One recovery pass over their union; recovery errors abort initialization | Less database/outbox work and no ready state after hidden recovery errors |
| Each actor reapplied every instrument in its session snapshot | Apply only the actor's own instrument | Linear snapshot application; every affected actor gets its generation invalidation |
| Older/duplicate lifecycle messages still invalidated calculations | State application reports whether its revision was actually newer | Avoids discarding valid calculations for duplicate state |
| Owner entry application reconstructed StrategyProgram repeatedly | Preload the owner program by actor configuration and refresh its event context | Removes repeated rule/warmup setup from entry application |
| Warmup requirements were recalculated on each background refresh | Cache requirements with versioned instrument metadata | Less repeated configuration analysis |
| Subscription refresh queried instruments separately for every session | Resolve the active universe in one instrument query and reuse version lookbacks | Removes subscription N+1 instrument queries |
| Prepared readiness could expire after six hours although the feed remained active | Renew/recover the preparation projection; clear depth metadata for removed buffers | Avoids artificial readiness loss and stale preparation tracking |
| Broker normalization delegates were defined twice | Keep one definition of each | Removes shadowed code |
| Execution Engine Defaults persisted a broker timeout that submission never used | Removed the model, API, UI, helper, argument and submission lookup | No inactive setting advertised; removes an unnecessary order-path query |
| A Live entry fill created an extra inner atomic savepoint inside an already atomic fill method | Removed the redundant inner savepoint | Removes unnecessary database savepoint work |
| Paper accepted and forwarded an unused price fallback | Remove unused parameters/call arguments; retain fresh-quote enforcement | No misleading stale-price fallback path |
| Supervisor accumulated old failures indefinitely and could spawn after interrupted backoff | Reset failures after 60 healthy seconds; stop before respawning | More predictable process recovery |
| Unused event-day LRU queries, cache getters, service recovery wrappers and mmap index accessor | Removed after reference checks | Less unsupported/unused surface |

Existing fixture contracts were adjusted for the preloaded actor program and the retained session-cleanup cache operation. No new tests were added or executed during this review.

### Upgrade requirement

Stop old API/fill producers and the outbox relay, then apply `common.0010_retire_unused_order_position_projections` before restarting matching new code. The migration removes only cache events for update_order, update_position, remove_order and remove_position. It does not remove financial records, order streams, or runtime/risk/control events.

Also apply `brokers.0008_remove_ordersettings`, which removes only the inactive settings table. Broker credentials, sessions, charge profiles and trading records remain. The gateway still uses ORDER_TASK_TIMEOUT. The broker page no longer has the inactive modal; its reload callback is stable and does not make an extra initial fetch for an OAuth status notification.

Previously stored duplicate Redis lists become unused; this migration is database-only and does not automatically reclaim those old Redis keys. Avoid blanket runtime Redis flushes.

### Remaining production gates

1. **Partial-fill protection:** the normal actor position reader requires OPEN. Unsettled filled exposure needs a deliberate protection/cancellation policy, including UNKNOWN broker outcomes.
2. **Publisher/control isolation:** one execution background thread still combines database snapshots, recovery, lease refresh, checkpoints and order publication. Long control work can delay publication; reduce or separate this work after measured load/recovery traces.
3. **Risk convergence:** runtime readiness checks pending runtime publications, not every risk/funds publication. Validate rapid close/reentry against delayed risk delivery before claiming strict synchronous limits.
4. **Broker costs and observations:** complete the Live net-charge ledger and verified cost-correction handling. Account serialization alone is not a broker rate limiter.
5. **Browser subscription bookkeeping:** reference counts still use cache read/modify/write and a TTL. Concurrent ASGI subscribers and lost disconnects require atomic, expiring per-connection ownership for larger deployments.
6. **Replay and multi-node failure:** validate owner/gateway crashes, Redis durability/recovery, replica gaps and coordinated resharding on real supervised services.
7. **Market support:** provider identity, calendars, fractional quantities, contract multipliers, expiry/settlement and another broker still need implementation and validation.
8. **Simulation boundaries:** Terminal remains an observed-price simulator; charts use different live bucketing; Backtest residual exposure is discarded at completion.

Retain ownership fences, request IDs, account locks, pending outcomes, generation checks, coverage checks and outbox retries. Their correctness purpose is independent of whether they improve latency.

### Checks for this review

- All backend Python sources compiled from source without syntax errors.
- Changed active runtime sources passed Pyflakes.
- Django system checks and migration consistency checks passed with `research.test_settings`.
- The migration graph/plan loads; cleanup migrations have not been applied to the development database in this review.
- The edited broker frontend passed targeted ESLint and the production Vite build.
- Behavioral tests, the latency benchmarks, real broker calls and production services were not run. Earlier benchmark/test results below predate these edits.

## Conclusion

The current runtime provides a shared strategy core, durable financial ledgers, separate Terminal/Paper/Live flows and bounded execution workers. The checks below establish specific behavior for the current Indian stock/Fyers implementation. They do not establish universal market support, equal latency under arbitrary load, production failover or exchange-grade HFT performance.

The subsequent [instrument latency benchmark](benchmarks/INSTRUMENT_LATENCY.md) processed 101,904 synthetic ticks and 384 calculations without missing or duplicate observations. It demonstrates scan-order bias and calculation queueing: instrument latency is unequal even under equal workloads. Those local measurements exclude broker execution and do not replace the production load/recovery gates below.

## Requirement assessment

| Requirement | Current evidence | Remaining work or limit |
| --- | --- | --- |
| Common rule evaluation | `trading_domain/strategy.py`, shared evaluator/indicators, historical adapter in `backtesting/executor.py` | Candle simulation and actual broker fills have different timing, liquidity and costs. Expand deterministic replay parity coverage. |
| Shared sizing, risk and actions | Fixed/capital sizing, configuration-based auto-disable and shared partial-exit/breakeven decisions | Risk totals are session-wide by design. Live realized P&L currently lacks a verified broker-fee ledger. |
| Common data structure | Instrument IDs, OHLC frames, runtime state and contract definitions are reused | Separate financial models remain appropriate. `MarketEvent` is not enforced end to end; dictionaries and tick arrays remain. |
| Independent strategies and instruments | Actors keyed by scope/session/instrument; stable shards; ownership leases; bounded process pools; rotating user queues | Finite CPU causes queuing. Protective scans share an owner thread. A data gap or calculation error currently pauses the affected session's entries, including its other instruments. A calculation timeout restarts the owner and affects its other actors. Account admission/fills serialize to protect capital. |
| Low-latency decision path | Local market buffers and preseeded state; entry/protection tests prohibit ORM access and fail on Redis reads | Gateway submission, durable accounting and broker acknowledgement include DB/network latency. Actual p95/p99 must be measured. |
| Market-data source replacement | Configurable provider factory; history/quote/live transport adapter | Fyers-specific instrument fields/importers, NSE symbol fallback and Fyers market status remain. Add external identifier mappings and enforce normalized ingestion contracts. |
| New broker adapters | Broker adapter registry, normalized observation handler and separate WebSocket factory | Only Fyers is implemented. Add authentication, statuses, fills, identity mapping, recovery, rate limits and adapter contract tests per broker. Unknown/unfinished brokers now fail explicitly. |
| Crypto/new exchanges | Contract metadata and exchange timezone configuration provide starting points | Calendar assumes weekdays and one daytime session. Add 24/7, overnight, split-session and auction behavior. Integer quantities and price precision need instrument-specific treatment. |
| Indian futures/options | Contract tick/lot/multiplier metadata exists | Execution remains direct stock routing. Add contract selection, expiry/roll, derivatives margin, settlement, multiplier-aware sizing/accounting and broker capabilities before enabling. |
| Professional Terminal simulation | Indexed price/stop queues, bounded match batches, account reservations, short collateral and OCO checks | It uses observed prices; it has no exchange depth, counterparties or queue-position model. Its Redis command read and sequential DB fills can delay other symbols on the same worker. |
| Capacity expansion | Configurable owner/calculation/gateway counts, node indexes, stable shards and persisted admission limits | Topology changes require coordinated draining/rebuild. There is no automatic rolling rebalance or unlimited actor capacity. |
| CPU and database efficiency | Bounded pools/caches, preloaded configuration, batched retention, asynchronous outbox | Limit-only aggregated candle queries can scan long histories. Profile query plans, use bounded source windows/materialized aggregates, and avoid repeated global Terminal bootstrap scans. Outbox retry backoff and aggregate indexing need load validation. |
| Recovery and ownership | Durable requests, cumulative fill cursors, account locks, pending/unknown outcomes, lease/deadline checks and state revisions | Service crash timing, Redis persistence loss, provider reconnects, delayed replicas and broker outages require fault-injection testing. |
| Research isolation | Separate Celery queue/private FastAPI service; bounded calls, cancellation, evidence and action tests | Resource isolation depends on deployment limits. Queue separation alone does not reserve CPU/RAM on one small VM. |
| Public Paper/private Live | Execution scope configuration permits separate deployments; accounts/ledgers remain separate | Subscription licensing and business website implementation are separate work. Architecture settings do not establish regulatory compliance. |
| Professional service operation | Supervised `quantnest_runtime` entry points and systemd templates | One-shot Django management commands remain useful for administrative work. PostgreSQL, runtime Redis and the source node remain failure dependencies without a tested HA deployment. |

## Defects corrected during verification

1. Paper market-order execution referenced `PaperTradingSession` without importing it.
2. Backtests applied the first instrument's special-event restriction to every instrument.
3. Outbox batches could be filled by blocked successors from one failed aggregate, starving unrelated publications.
4. Backtest exit evaluation discarded partial-exit/breakeven markers and could prevent later exit rules from running.
5. Historical base and higher-timeframe analytical frames used different availability timestamps.
6. Backtest capital admission omitted entry slippage and failed to reuse capital released by earlier exits in the same batch.
7. Paper/Live cooldowns used session risk timestamps instead of the instrument's own state; historical entry/exit cooldown tracking was incomplete.
8. Contract price normalization mixed `Decimal` and float tick sizes.
9. Terminal full short covers recalculated margin before deleting the flat position, leaving collateral blocked.
10. Unknown broker names silently selected Fyers, and unfinished adapters could expose placeholder connection behavior.
11. Long rule names and combined partial/final exit explanations exceeded a 50-character database field. Exit reasons now use text fields in Backtest, Paper and Live, with schema migrations. Tests require the backtest to complete and persist its explanations.

Existing test fixtures were updated for pinned strategy versions and transactional outbox behavior. The research WebSocket routing test now preserves its PostgreSQL TestCase transaction during Channels connection cleanup. The private provider mock supplies the token-count API now used by the provider.

## Verified behavior

The retained `quantnest_runtime/tests.py` suite covers:

- Increased cumulative fills with correct incremental prices; duplicate/out-of-order snapshots; missing-price and cost-correction cases.
- Verified order tags retaining saved session/version ownership; foreign account activity remaining outside strategy positions; aggregate position differences not overwriting owned positions.
- Unknown submission outcomes being persisted and not resubmitted for the same request.
- Paper entry, partial exit, final exit, request deduplication, released margin and realized P&L.
- Live partial/final exits and duplicate snapshot P&L accounting.
- Independent event filters and instrument cooldowns; shared entry-rule results; consistent historical candle completion times and retained exit markers.
- Local hot entry handoff/protective checks; configuration-only auto-disable; expired entry/lost-owner rejection.
- Tick ring ordering, overflow gaps and receipt-time freshness.
- Indexed limit/stop/stop-limit matching, modifications and bounded matching batches.
- Terminal pending capital, short collateral, cover accounting and protective OCO behavior.
- Transaction rollback, retryable outbox database errors, aggregate order and unrelated aggregate progress.
- STOPPING sessions retaining unresolved UNKNOWN obligations.
- PostgreSQL races: Live capital admission, duplicate WebSocket/REST fills, Paper overspending and duplicate Terminal fills.

The full targeted suite includes the existing research, backtest, Paper account and market calendar tests. Broker transports are mocked. Disposable databases are created/dropped; no trading runtime is started and no real broker order is placed.

Static checks include Python compilation, Django system checks, migration consistency and diff whitespace checks. The three exit-reason migrations extend field capacity without changing saved trade values.

Results recorded on 10 October, before the 12 October cleanup: 110 backend tests passed on disposable PostgreSQL; the same SQLite suite passed with four PostgreSQL-only tests skipped; two private research-service tests passed. Compilation, system checks, migration consistency and migration application checks passed. The three exit-reason migrations were applied to the development database. Broker timeouts, invalid requests and failed publications deliberately exercised by tests produce expected error logs; the successful backtest assertions additionally verify saved trades and completed status.

## Next acceptance gates

1. Replay the same recorded observations through Paper and mocked Live, comparing decisions, sizing, actions and resulting ownership. Compare historical decisions only at matching completed-candle times, with simulation limitations recorded.
2. Run crash/recovery tests at durable handoff, broker timeout, partial fill, outbox delivery, lease expiry and process restart boundaries.
3. Load test with realistic instruments, strategies, users and database history. Record queue age, p50/p95/p99 protection, calculation, decision-to-submit and broker acknowledgement latency, plus CPU/RSS and DB lock time.
4. Finish provider identity/calendar/capability boundaries before advertising arbitrary data sources or markets.
5. Implement and validate one additional real broker adapter through the shared observation contract before describing broker addition as plug-and-play.
6. Measure and address Terminal worker blocking, candle aggregation cost, broker account quotas and outbox retry behavior. For strict instrument isolation, persist an instrument-level readiness/pause state and expose recovery controls; avoid pausing every instrument for one instrument's data or calculation failure while retaining session-wide risk restrictions.
7. Validate the public and private deployment configurations, backups, monitoring and recovery procedure on the actual deployment hardware.

Successful unit and PostgreSQL concurrency tests are a useful acceptance layer. Live sandbox execution, multi-node failover and sustained production capacity remain unverified.
