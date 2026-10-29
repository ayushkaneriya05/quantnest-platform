# Execution verification — 26 October 2026

This is a record of the code review, corrections and isolated verification for this checkout. The four [trading guides](../README.md#trading-and-execution-guides) remain the architecture and operating instructions. Passing these checks does not establish that every provider failure or production workload has been tested.

## Scope and result

The review followed strategy snapshots and user actions through data preparation, shared numerical evaluation, account ownership, simulated/broker fills, persistence and UI updates.

| Mode | Input and execution | Verification performed |
| --- | --- | --- |
| Backtest | Confirmed history → calendar aggregation → compiled rules → OHLC replay → matcher/ledger → saved reports | Real replay and task orchestration with supplied synthetic candles; completed-candle timing, final closure, charges, report rollback, cancellation and duplicate task delivery |
| Paper | Prepared history + shared-memory observations → session/instrument evaluators → Paper account owner → simulated fills | Rules, fills, costs, deployment/wallet admission, persistence/recovery, capital and version boundaries, stop/resume configuration |
| Live | Same prepared inputs/evaluator → broker-account owner → durable order → FYERS → cumulative reports → local ledger | Synthetic partial/full/repeated/older/late broker reports; timestamps, ownership correlation review, persistence, allocation checks, broker disconnect and asynchronous lifecycle races |
| Terminal | Ticket/control commands + observed prices → Terminal account owner → shared matcher/ledger → WebSocket snapshots | Buy/sell order matrix, stop activation, amendment/cancellation, protection, reversals, funds, charges and account/protection update events |

No real broker order was submitted. Application services were not stopped or restarted during this audit. Database integration fixtures were contained in one rolled-back transaction, and rollback was checked. Shared-memory checks used a temporary directory. Audit scripts were removed after execution to respect the repository's current no-test-files preference.

## Corrections made

### Market input and recovery

- Late observations that conflict with a completed candle request a background graph rebuild. They no longer reopen a completed candle or kill the worker with an unhandled duplicate-candle exception.
- All timeframe boundaries are checked before mutating their forming candles. A full observation batch is drained before advancing completion using wall-clock time.
- Recovery does not rewind a new feed generation using a sequence from an older generation. Crossing samples reset at that boundary.
- Market-history preparation abandons results if its connection/generation changes during the request.
- FYERS history/quote transport keeps bounded timeouts and distinguishes network failures from provider errors. Trading profile/funds/order-book reads now also use a bounded HTTP call. Order submission is never automatically retried after an uncertain transport outcome.

### Rules and financial transitions

- Corrected Parabolic SAR's initial state, reversal bounds and next-level calculation. The corrected series matched the installed TA-Lib reference to floating-point precision on the checked sample.
- Doji uses the ten preceding candle ranges, excluding its current candle, and the inclusive threshold.
- Ichimoku retains enough candles for a custom Tenkan period greater than the other periods.
- Zero-range/zero-flow indicators return defined zero values after warmup where appropriate, rather than remaining unavailable indefinitely.
- An expired or otherwise invalid automatic close produces a visible rejected order, without crashing the account worker. Repeated identical protective failures are suppressed for the same position revision.
- A simulated working order is validated at fill time as well as admission; a contract can expire while an order remains pending.
- Live fills are compared with order eligibility at whole-second precision because broker timestamps can omit fractions. Stored broker time is preserved. Simulated fills retain their precise eligibility boundary.
- A rejected broker observation no longer mutates broker metadata before validating its fill.
- Expired authorization detected before submission creates a definite rejection through the normal ledger; it no longer leaves an order UNKNOWN even though no broker request was made. A timeout after submission starts still remains ambiguous.

The indicator reference implementations inspected were [TA-Lib SAR](https://raw.githubusercontent.com/TA-Lib/ta-lib/main/src/ta_func/ta_SAR.c) and [TA-Lib Doji](https://raw.githubusercontent.com/TA-Lib/ta-lib/main/src/ta_func/ta_CDLDOJI.c). FYERS routes and authorization were cross-checked against the installed SDK and the [official endpoint catalog](https://github.com/FyersDev/fyers-skills/blob/master/skills/fyers-trading/references/endpoints.md).

### User actions while execution runs

- A normal version/configuration refresh no longer clears an outstanding stop-and-close request. Resuming clears the prior stop flag.
- Stopped sessions no longer compile/install active rule evaluators. Contract facts needed by account orders and positions remain available.
- A delayed failure is checked against the session's applied version; an old version cannot disable its already-applied replacement. Late stop completion cannot overwrite a resumed session. Deleted sessions are ignored by these delayed lifecycle messages.
- Missing resources and invalid asynchronous controls are rejected visibly instead of stopping the controller. Non-broker user-command failures use the existing notification system.
- Protecting a position that closed before the command arrived gives a clear rejection.
- Terminal protection edits publish `POSITION_UPDATE`; applied account settings publish `ACCOUNT_UPDATE`, which the frontend now consumes.
- Disconnect/reconfiguration uses one common idle-broker check. Running/stopping sessions, positions, unresolved orders or unapplied commands block removal of broker access. Resume/deploy and disconnect serialize on the credential row. Explicitly disconnected accounts are excluded from periodic reconciliation.
- Backtest cancellation/deletion rereads locked state. Completion saves results and status atomically; report failure leaves no partial result rows, and a later history failure cannot overwrite cancellation.

## Runtime action semantics

An HTTP success for a queued action means it was accepted. The account owner applies it in order with the account's other controls and financial transitions. The worker rechecks mutable financial state because a fill can arrive after API validation.

| Action | Required behaviour |
| --- | --- |
| Edit a strategy draft | Existing deployments keep their saved version until deploy-version is requested |
| Deploy another version | Retain instruments with open positions; reject outstanding incompatible work; check `applied_version`/`applied_at` for application |
| Reduce capital | Reject a reduction that would consume committed positions or pending-order funds |
| Increase Paper capital | Reserve/debit wallet funds once; apply the account delta; refund if application is rejected |
| Pause | Stop new entries when the owner applies the change; retain exit/protection/reconciliation responsibilities |
| Stop with close | Cancel remaining entries and request full exits; wait for eligible ticks or broker fills before STOPPED |
| Stop without close | Preserve exposure; STOPPING can remain while positions exist |
| Resume | Revalidate deployment inputs/access/capacity, clear the old close-on-stop flag and install current configuration |
| Cancel/amend a filled order | Leave the completed fill intact; cancellation is a no-op and amendment is rejected |
| Change Terminal margins | Reject changes with working orders; recalculate existing collateral and require sufficient balance |
| Disconnect broker | Wait for applied controls and settled exposure, then invalidate authorization |

Configuration refreshes reconcile current desired database settings; rapidly changing those settings can coalesce before installation. Check the applied version and final status rather than treating every click as a separately completed runtime transition.

## Checks run

**28 isolated scenario checks passed.** They cover:

- Buy/sell MARKET, LIMIT, STOP_MARKET and STOP_LIMIT behaviour; later-observation fills; stop-limit activation and limit bounds.
- Amendment timing, cancellation after completion, replacement of pending orders by protection, full automatic exits, manual reversal, invalid margin changes and expired contracts.
- Backtest/Paper/Terminal closing-cost and balance consistency; held funds until commit; insufficient capital after a price gap.
- Broker partial/repeated/older/cancelled/late fills; mismatched IDs/quantities; whole-second times; transport timeouts without retrying mutations.
- Crosses, pause/resume, entry cutoff, completed-candle lookahead prevention, arithmetic, position operands, checkpoint round trip, weekly anchors, indicator warmup/flat data and reference SAR/Doji values.
- Real temporary shared memory, generation recovery, atomic history conflicts, calendar aggregation, version changes and allocation rejection.
- Real replay with database cursor access deliberately blocked inside the numerical kernel.

**58 database integration assertions passed.** They cover:

- Paper wallet/deployment creation, saved fills/closes, duplicate persistence and restored account state.
- Stop/resume configuration, stopped evaluator removal, Terminal cash/charges and account/protection events.
- Live fills/closes and original broker timestamps; safe disconnect; pending-control blocking; deleted/stale/current-version lifecycle messages.
- Public request/inventory/Paper/period limits, exact boundaries, duplicate reservation and failure refund.
- Development recording and Private bypass of commercial reservations/limits.
- Real backtest task and report completion using supplied candles, duplicate delivery, atomic rollback and cancellation surviving a history error.

Additional checks passed: Django system checks, migration consistency (no migration required), frontend lint, frontend production build and parsing of changed Python files. The frontend build reports an outdated Browserslist dataset; it did not fail the build.

## Follow-up execution cleanup

- Account installation is the only startup checkpoint reader; the controller no longer decodes every account a second time. Recovered ambiguous broker orders remain excluded from submission.
- Each account refresh loads evaluator checkpoints in one query instead of one query per instrument. Version and position-revision matching still determine whether a checkpoint can be restored.
- Unit removal shares one cleanup path. Removing the last evaluator for a worker/symbol drops unused warmup results and retries; other evaluators sharing that symbol retain their work.
- Amend/protect commands no longer prepare unused contract and calendar objects. Their owner still validates changes against its loaded contract; new orders still prepare their calendar and holidays.
- Removed unused transient receipt/observation timestamps, redundant checkpoint-message account data, unused numeric constants and a duplicated working-order status set. Provider event timestamps, order sequencing and persisted account snapshots retain their existing meaning.
- Removed the unused controller-side validity payload; the broker adapter continues to submit its supported DAY order format.

**40 additional assertions passed** for the cleanup, including a measured single checkpoint query, version/revision isolation, empty deployments, shared warmup cancellation, startup recovery, submission deduplication, command conversion, all four simulated order types in both directions, real historical replay and research evaluation. Replay and research numerical checks ran with database cursor access blocked. Database fixtures were rolled back and the temporary verification script was removed. No broker requests or real orders were made by these checks.

## Boundaries of this verification

1. **Broker execution still needs a controlled live acceptance run.** Synthetic reports verify the local ledger, not exchange acceptance, actual partial fills, network latency or a complete trading day with your account.
2. **No browser interaction session was run.** Frontend event wiring was inspected, linted and built; database-side event publication was exercised. Visual/browser reconnect behaviour was not replayed in an actual browser during this audit.
3. **The scenarios are deterministic interleavings, not a load/chaos campaign.** No user-capacity or latency percentile is established by their execution time. Measure the deployed server before increasing users/workers.
4. **Backtest/Paper fills remain simulations.** OHLC replay cannot reconstruct real tick ordering; Paper/Terminal matching does not model exchange depth or queue position. Live receives authoritative cumulative broker fills.
5. **Actual Live charges remain outside the order ledger.** Live P&L is before broker fees, as already labelled. An order snapshot is not a contract-note charge statement. REST reconciliation uses observation time for a newly discovered fill when no broker execution-event timestamp is supplied.
6. **A real lost tick buffer still requires review/resume.** A recoverable disconnect/history correction rebuilds inputs; lost observations cannot be invented. The requested removal of fixed tick-age expiry remains in place, including the limitation that a silently frozen connection is not detected by price age.
7. **Persistence and process failures remain explicit stop/recovery conditions.** A database outage, full IPC queue or broken financial revision sequence should not be disguised as successful execution. Warmup/provider I/O and database writes stay outside numerical workers, but durability and broker submission add necessary end-to-end latency.
8. **Missed cross signals are not replayed through unknown gaps.** Rebuilt history restores indicator inputs; it does not establish that an unseen historical tick was tradable.

## Loading these fixes

No schema migration is needed. Existing processes keep their loaded Python code until restarted.

1. Let active compute work finish and avoid submitting new work during the restart.
2. Restart the API, the compute/background workers, market-data, execution and broker-events processes using the existing deployment instructions. Restart the execution controller and its children together; their internal message contract changed.
3. Start only one market-data writer and one execution group for the shared runtime directory. Backtests need the compute worker; they do not require the execution runtime.
4. Observe history preparation, a fresh observed price and applied session versions before exercising Paper/Terminal actions.
5. Check create/amend/cancel/protect, capital/version edits and stop/resume using simulation first. Confirm History, account values and notifications agree after a refresh.
6. For intentional Live use, verify authorization and funds, then perform an operator-approved minimal live acceptance run and compare local order IDs, cumulative fills and timestamps with the broker. Do not retry an ambiguous placement manually without first reconciling it.

See the [deployment walkthroughs](../../infra/START-HERE.md) for the commands specific to Development, Public and personal Private installations.
