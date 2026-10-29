# Complex strategy evaluation latency — 29 October 2026

## Result and measurement boundary

On this laptop, the isolated production callback/worker path generated signals for
a warmed 20-rule, six-timeframe strategy in **10.09 ms median / 13.80 ms p95**.
With 1,000-candle windows and shifts, and ticks completing several timeframes,
the result was **10.80 ms median / 20.62 ms p95**. The largest observed delay in
that heavier case was 26.69 ms. These are measurements of the scenarios below,
not latency guarantees or measurements of broker fills.

The timed path was:

```text
FYERS SDK callback receives a decoded quote
  -> normalize price, timestamps and volume delta
  -> write observation to the private shared-memory buffer
  -> separate execution worker wakes and reads the observation
  -> update forming candles and any completed indicator values
  -> evaluate all applicable rules, combine results and construct Intent
```

The clock starts at entry to `FyersLiveFeedClient._on_message()`. It excludes
exchange-to-provider delivery, network transit and SDK processing before that
callback. It ends when the evaluation unit returns its signal, before account
acceptance, sizing, order persistence, matching, broker submission or UI updates.

This is a synthetic, isolated measurement using the actual callback, shared-memory
implementation, worker event processing, compiler, indicators and rule evaluator.
It is **not** a timing trace of the user's running strategy or a complete deployment
load test. No user orders were created and no live services were restarted.

## Environment and workload

- Source revision: `ba34f4f575879f30533ac22e1fcb0b60fb84b55a`.
- Windows laptop: Intel Core i5-13420H, 8 cores / 12 logical processors, approximately
  16 GB RAM. Other desktop/services remained running; available memory was about
  1 GiB at the initial check.
- One isolated producer and one execution worker process, one symbol and one
  session/instrument evaluation unit for the callback measurements.
- Timeframes: **1m, 5m, 15m, 30m, 1H and 1D**.
- All 15 or 20 rules belong to an active entry group. The number of actual
  `evaluate_rule()` calls was checked outside timing. They are not 20 configured
  rules of which only a smaller entry/exit subset runs.
- The group uses OR, with an LTP condition chosen to produce an Intent in every
  measured trial. The engine evaluates every rule before combining the group,
  so the matching first rule does not skip later calculations.
- Pending-order state is reset between independent signal-generation trials.
  This deliberately excludes the order lifecycle and its restrictions.
- Operand parameters were checked with the current serializer validation; all
  warmed operand values were confirmed finite before measurement.

### The 20-rule profile

The 15-rule profile uses the first 15 rows. `CLOSE` and indicator operands use
completed candles; `LTP` uses the injected observation.

| # | Left operand | Comparison | Right operand |
| --- | --- | --- | --- |
| 1 | LTP | Greater | EMA 200, 1D |
| 2 | EMA 50, 1m | Crosses above | EMA 200, 5m |
| 3 | RSI 50 of EMA 100, 5m | Greater | RSI 50, 15m |
| 4 | MACD histogram 50/100/30, 15m | Greater | MACD histogram 50/100/30, 1H |
| 5 | ADX 50, 15m | Greater | ADX 50, 1H |
| 6 | CLOSE, 5m, shift 100 | Greater | Bollinger upper band 200, 30m |
| 7 | HMA 144, 5m | Greater | WMA 200, 15m |
| 8 | ALMA 100, 15m | Greater | KAMA 100, 30m |
| 9 | TEMA 100, 5m | Crosses below | DEMA 100, 1H |
| 10 | CCI 100, 5m | Greater | CCI 100, 15m |
| 11 | Stochastic K 100/10/5, 15m | Greater | MFI 50, 1H |
| 12 | Supertrend 50, 15m | Greater | Ichimoku Senkou B 26/52/104, 1H |
| 13 | `(LTP - EMA(200,15m)) / ATR(50,1H)` | Greater | ROC 100, 1D |
| 14 | `(CLOSE(1m) + OPEN(5m)) / 2` | Greater | SMA 200, 15m |
| 15 | `100 * (CLOSE(5m) - CLOSE(1D,shift=100)) / CLOSE(1D,shift=100)` | Greater | ROC 100, 30m |
| 16 | `VOLUME(1m) / (SMA(100,VOLUME,5m) + 1)` | Greater | MFI 50, 15m |
| 17 | `EMA(200,5m) - 2 * ATR(100,1H)` | Greater | Donchian lower band 200, 30m |
| 18 | `(RSI(50,1m) + RSI(50,5m) + RSI(50,15m)) / 3` | Greater | Stochastic K 100/10/5, 1H |
| 19 | `(CLOSE(5m) - CLOSE(15m,shift=100)) / (ATR(100,1H) + 1)` | Greater | ROC 50, 1D |
| 20 | `.5*EMA(200,1m) + .3*EMA(100,15m) + .2*EMA(200,1D)` | Greater | Weekly VWAP, 5m |

The **heavy** profile increases the Bollinger, WMA, SMA and Donchian windows to
1,000 and the two intraday candle shifts to 1,000. The daily shift remains 100.
The expressions are a computational workload, not a recommended trading strategy.

### Prepared history

| Profile | Compiled feature nodes | Aggregated candles warmed | In-memory warmup |
| --- | ---: | ---: | ---: |
| 15 rules | 32 | 4,466 | 0.380 s |
| 20 rules | 45 | 5,216 | 0.518 s |
| 20 rules, heavy | 45 | 5,756 | 0.546 s |

The compiler requested **39,180 one-minute source candles and 1,003 daily source
candles** for these profiles. The aggregated counts above are across all six
timeframes and include ten extra warmup bars per timeframe. Source-candle counts
and aggregated-candle counts describe different stages; do not add them together
as a count of unique stored observations.

For the normal 20-rule profile the required aggregated counts were 1,001 each for
1m/5m/15m/1D, 651 for 1H and 501 for 30m. The heavy profile raises 5m/15m to 1,021
and 30m to 1,001. The hourly requirement still dominates the source-history plan.

The measured warmup uses already available synthetic candles. It excludes
database reads, missing-history downloads, resampling from raw source history,
and reconnect recovery; it is not an estimate of cold session startup time.

## Callback to generated signal

Each row has 400 measured observations after 20 warmup observations. All times
are milliseconds. **p95** means 95% of those measured trials were at or below
that value; the maximum is only the maximum observed in this sample.

| Scenario | Median | p95 | p99 | Maximum |
| --- | ---: | ---: | ---: | ---: |
| 15 rules, ordinary tick | 10.23 | 13.83 | 14.32 | 15.68 |
| 20 rules, ordinary tick | 10.09 | 13.80 | 14.45 | 15.22 |
| 20 rules, heavy, ordinary tick | 10.14 | 14.01 | 15.51 | 18.89 |
| 20 rules, multiple timeframe completions | 10.16 | 14.04 | 15.31 | 20.25 |
| 20 rules, heavy, multiple timeframe completions | 10.80 | 20.62 | 23.99 | 26.69 |

The producer calls the real decoded-quote callback and writes real memory-mapped
observations. The separate worker runs `Worker.step()`, `read_market()` and
`actor_turn()`. Its `send()` captures the signal timestamp instead of submitting
an order. Reporting over the diagnostic pipe occurs after that timestamp.

The producer waits for each result and varies its next injection by 1–9 ms.
Consequently this table measures a worker without an accumulated tick backlog.
It does not measure sustained high-rate traffic or many subscribed symbols.

For completion scenarios, synthetic tick time advances through hourly session
boundaries and subsequent weekdays. This exercises multiple intraday completions
and occasional daily completion, rather than a realistic replay of every trade.
The diagnostic worker clock follows that synthetic time, so an unrelated current
wall clock cannot close historical test buckets. These are tick-triggered
completion measurements; clock-only candle-close scheduling is a separate path.

### Where the time goes

| Stage, same separate-process trials | 20 rules ordinary: median / p95 | 20 heavy at completions: median / p95 |
| --- | ---: | ---: |
| Provider callback through observation publication | 0.161 / 0.286 ms | 0.157 / 0.304 ms |
| Worker read start through generated signal | 1.149 / 2.689 ms | 5.436 / 9.306 ms |
| Within that worker time: evaluator and Intent construction | 0.668 / 1.533 ms | 2.197 / 4.190 ms |

Do not add percentiles across columns or stages: they need not describe the same
observation. The evaluator is already included in worker time.

The worker requests `stop.wait(.002)` when idle. A separate 120-sample measurement
of that exact multiprocessing Event wait on this Windows machine returned
**15.864 ms median / 16.157 ms p95**, despite requesting 2 ms. This supports idle
wakeup/scheduling as a substantial part of callback-to-signal delay here. It is
not evidence of a 2 ms upper bound, nor a measurement of Linux scheduling.

## Active calculation cost without waiting for another process

Each row contains 1,000 measured iterations after 50 warmup iterations. This
isolates `observe()` plus `EvaluationUnit.evaluate()` in one process with hot
state. It includes Intent construction but excludes shared-memory access, polling
and OS wakeup between processes.

| Profile | Ordinary tick: median / p95 | 1m completion: median / p95 | Five intraday completions: median / p95 |
| --- | ---: | ---: | ---: |
| 15 rules | 0.194 / 0.282 ms | 0.204 / 0.303 ms | 0.703 / 0.936 ms |
| 20 rules | 0.237 / 0.408 ms | 0.266 / 0.426 ms | 0.938 / 1.270 ms |
| 20 rules, heavy | 0.342 / 0.469 ms | 0.369 / 0.548 ms | 1.591 / 2.578 ms |

For ordinary ticks, rules and Intent construction alone took 0.073 ms median
for 15 rules, 0.109 ms for 20 rules and 0.211 ms for the heavy profile.
Different cache/scheduling conditions mean these tight-loop numbers should not
replace the larger separate-process measurements above.

The isolated completion trials supply new forming candles outside the measured
interval and retain the indicator accumulators. Five intraday timeframes close
together; the daily feature values remain cached. This checks computation cost,
not chronological correctness of a complete market replay.

Database execution was guarded during the measured numerical paths and worker
loop: any SQL statement would fail the diagnostic. None occurred. The diagnostic
omits background checkpoint publication and real account actors; that result
does not establish that every part of the deployed application avoids SQL.

## Multiple sessions receiving the same symbol

A separate numerical fanout exercise used the normal 20-rule profile, one shared
feature graph, one tick and independent evaluation units. The table measures time
until the **last** unit generates its signal, not the latency of every unit.
There were 100 measured batches after 20 warmup batches.

| Independent units on one symbol | Median last signal | p95 last signal |
| ---: | ---: | ---: |
| 10 | 2.14 ms | 3.58 ms |
| 100 | 17.94 ms | 26.08 ms |
| 1,000 | 132.65 ms | 169.48 ms |

This is sequential in-memory evaluation without worker scheduling, shared-memory
reads, account work or persistence. It demonstrates that independent session
state still consumes CPU for each session. Shared indicators avoid repeating
identical calculations but do not make all decisions simultaneous. These figures
are not supported user counts or a measured multi-worker capacity.

Different instruments require separate feature updates. Different strategy
parameters add feature nodes. Both can be more expensive than this shared-symbol
case. Worker count and usable capacity need measurement with representative tick
rates, session distribution, account actors and concurrent backtest/research load
on the intended server.

## Why long histories do not imply seconds per tick

1. `compile_strategy()` resolves feature identities, history requirements and
   arithmetic ASTs during preparation; expressions are not reparsed each tick.
2. `FeatureGraph.register()` shares identical feature definitions for a symbol
   within the worker. Different shifts can read the same stored feature series.
3. Recursive indicators retain state; completed candles update that state once.
   Ordinary ticks do not rebuild the full historical dataset.
4. `Feature.at()` selects the value available at the observation time, including
   any requested shift. Large shifts currently scan stored history and cost more.
5. Several finite-window calculations still scan their windows. Increasing a
   WMA/Bollinger-style window to 1,000 can increase completion-time work; not every
   indicator has constant-time updates.
6. `evaluate_rule()` reads values before checking whether their input stamps
   advanced. Candle-only operands can therefore still incur read costs on ticks.

If later production measurements justify optimization, the concrete candidates
are indexed historical-value lookup, reuse of unchanged operand values with correct
crossing state, and rolling aggregates for costly window operations. None was
changed during this measurement task.

## Interpretation and limits

- This tested 20-rule workload needs milliseconds after the callback, not seconds,
  once history is ready and no backlog is present. It does not explain away a
  separate multi-second order placement/fill delay.
- Candle-only groups may generate their signal on the worker's candle-clock event
  without waiting for another provider quote. A simulated fill can still require
  a later eligible observation. Signal time and fill time must remain separate.
- A delayed or missing provider observation is outside the measured callback
  interval. So are history rebuilds after a connection or history revision.
- This is not exhaustive operand correctness testing, a worst-case limit for all
  possible expressions, an Oracle/Linux benchmark, or a proof of broker latency.
- Longer/more deeply composed expressions, more unique indicators, deep shifts,
  backlog, memory pressure and many instruments can raise the tail latency.
- No production code, settings or accounts were changed. Temporary diagnostic
  code and buffers were removed; no new test suite was retained.

## Source paths

| Responsibility | Current implementation |
| --- | --- |
| Normalize FYERS observations | [`FyersLiveFeedClient._on_message`](../../backend/marketdata/fyers.py) |
| Publish observations to shared memory | [`MarketObservationClient.ingest_observation`](../../backend/marketdata/live_feed.py), [`SharedMemoryManager`](../../backend/marketdata/shared_memory.py) |
| Read observations, schedule actors, idle wait | [`Worker`, `run_worker`](../../backend/execution/worker.py) |
| Form and complete timeframe candles | [`observe`, `complete`](../../backend/execution/market.py) |
| Compile rules and share features | [`compile_strategy`, `FeatureGraph`](../../backend/execution/compiler.py) |
| Incremental indicators and shifted reads | [`Feature`, `Window`](../../backend/execution/features.py) |
| Evaluate expressions, rules and signals | [`EvaluationUnit`, `arithmetic`](../../backend/execution/engine.py) |
