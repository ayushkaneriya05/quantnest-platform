# Paper candle-close latency review — 29 October 2026

This review separates candle evaluation, order placement, simulated fill time and
UI display. Diagnosis used existing database records and retained WIPRO
observations. No diagnostic orders were placed or account state changed.

## Recorded evidence

All times below are IST, 29 October 2026. Placement is the persisted Paper order's
`placed_at`; fill time is the simulated price observation's `executed_at`.

| Paper order | Placed | Filled | Fill persisted |
| --- | --- | --- | --- |
| 840, entry | 14:18:09.431 | 14:18:10 | 14:18:11.520 |
| 841, exit | 14:20:00.040 | 14:20:01 | 14:20:02.686 |
| 842, entry | 14:24:00.040 | 14:24:05 | 14:24:06.142 |

The 14:24 entry was already saved about 40 milliseconds after the boundary. The
five-second time shown in the screenshot was its fill time, not its placement
time. The 14:18 entry was genuinely placed later and must not be explained away
as a display issue.

Retained observations around 14:24 contained changed prices with repeated
`last_traded_time = 14:23:59`. Callbacks carrying that timestamp arrived at
14:24:00.105, 01.299, 02.801 and 05.496. The first observation with a trade time
after the boundary had time 14:24:05 and arrived at 14:24:06.115. The fill was
persisted about 27 milliseconds after that callback.

The same pattern appeared around 14:18: quote updates received several seconds
after the boundary still carried the previous minute's last-trade timestamp.

## Causes

1. **Wrong clock for quote observations.** The FYERS adapter used
   `last_traded_time` to date every stock quote. A quote update can change price
   while that field remains unchanged. After a candle closes, assigning a new
   quote to its old minute can trigger the legitimate history-rebuild path and
   prevent fills until a later eligible event appears. This explains a mechanism
   for delayed evaluation as well as delayed fills; no per-event preparation
   trace was retained to attribute every millisecond of order 840's delay.
2. **Default subscription channel.** The SDK defaults to channel 11. FYERS support
   describes channel 15 for the cached-time/price-update issue. A short separate
   read-only channel-15 sample confirmed that `exch_feed_time` advanced with quote
   updates while `last_traded_time` could remain older.
3. **Precision mismatch.** The candle clock used the worker's polling instant as
   signal time. Order 841's eligibility was 14:20:00.012639. Quotes timestamped
   14:20:00 were therefore rejected as earlier, despite having a later observed
   sequence. The provider uses whole-second timestamps.
4. **Ambiguous UI.** The Paper table labelled a value “Time” but selected
   `executed_at` whenever it existed. It hid placement time after a fill.

The worker's idle wait is approximately two milliseconds, not five seconds.
Periodic checkpoint/history-maintenance intervals are not normal rule-evaluation
intervals. More CPU workers would not correct these timestamp problems.

## Changes

- `marketdata/fyers.py` subscribes and unsubscribes on channel 15 and dates stock
  and index observations using `exch_feed_time`. Local receipt time remains
  separately recorded. It does not relabel receipt time as exchange time.
- `execution/worker.py` stamps a candle-clock event with the actual completed
  candle boundary. Sequence ordering still prevents filling from the observation
  that produced the signal or from an earlier observation.
- The Paper Order Book shows placement and fill times separately.

History-conflict recovery, duplicate prevention, market sessions and order
eligibility checks remain in place. No tick-age rejection threshold was added.

## Verification

Temporary isolated checks exercised the actual worker candle-completion path,
compiled strategy evaluation and simulated account matching. They verified an
exact boundary timestamp, first eligible quote fill, rejection of earlier
observations, no duplicate candle/intent/fill, and zero database queries in the
numerical path. FYERS checks covered exchange timestamps, volume deltas,
out-of-order updates, index observations and matching subscription channels.

Django system checks and targeted frontend lint passed. Temporary diagnostic
scripts were removed after use; no new repository test suite was introduced.

After the user restarted market-data and execution, the feed reported connected,
WIPRO history ready and the Paper session RUNNING without an error. A sample at
14:39:56–14:40:10 showed advancing exchange-feed timestamps; their difference
from local receipt time ranged approximately 0.33–1.14 seconds. Because provider
timestamps are whole seconds, this difference includes timestamp granularity and
must not be reported as a precise network-latency measurement.

The follow-up at 14:42:50 confirmed evaluation checkpoints consuming the 14:42
completed candle. Across the latest 60 observations, the feed-timestamp/receipt
difference was about 839 ms median and 1,151 ms at the 95th percentile. No new
strategy order had occurred since the restart at that point; the subsequent
live Paper verification is recorded below.

These fixes remove the identified avoidable delays. They cannot guarantee a fill
at every candle boundary: Paper matching still needs an eligible subsequent
observed quote. Provider delivery and quiet symbols can introduce additional
waiting. No new strategy condition was forced to obtain a verification trade.

## Subsequent strategy orders verified

The next two naturally occurring orders were inspected against retained market
observations and the persisted account checkpoint. Both used feed generation 21
after the restart. All timestamps below are IST on 29 October 2026.

| Order | Decision event | Order placed | Eligible fill quote received | Fill saved | Quote receipt to fill save |
| --- | --- | --- | --- | --- | --- |
| 843, SELL target exit | 14:53:00 exact candle boundary | 14:53:00.046813 | Approximately 14:53:00.750 | 14:53:00.785052 | 35.08 ms |
| 844, BUY new entry | 14:53:01 exchange-feed event | 14:53:01.444922 | Approximately 14:53:02.859 | 14:53:02.912859 | 53.59 ms |

The exit was placed about 47 ms after candle close and filled from the first
subsequent eligible observed quote, at price 190.29. Its execution sequence was
9157; the fill quote sequence was 9158. Its recorded exchange fill time is
14:53:00, while actual receipt/persistence occurred later within that second.

After the exit, the next quote had event time 14:53:01 and was received at about
14:53:01.416. The new entry was placed about 29 ms later. It used sequence 9160
and filled at price 190.29 from the following observation, sequence 9162. That
quote's exchange time was 14:53:02. The strategy did not fill using the same
observation that generated its entry.

These were distinct target-exit and entry decisions, not duplicate submissions.
`EvaluationUnit.update_position()` resets rule samples after the position
revision changes. With the account flat, the next observation can satisfy the
entry rule using the latest completed candle. Current behaviour therefore permits
re-entry during the same minute; there is no wait-for-another-candle policy.
This verification did not change that strategy behaviour.

The feed remained connected and the session RUNNING without an error. The
observed local processing was tens of milliseconds; the earlier 5–10 second
placement/fill pattern was not present in these two orders. This is evidence for
these events, not a general latency guarantee for all workloads or provider
delivery conditions.

## Regular candle-close evaluation and scaling measurements

Further checks on 29 October used the current checkout on the development laptop:
Intel Core i5-13420H, 8 physical cores / 12 logical processors, approximately
16 GB RAM, Windows 11, Python 3.12.14. The running execution configuration had
`EXECUTION_WORKERS=1`. Other platform and desktop processes remained running;
available memory was approximately 1–1.5 GB during the initial measurements.
This is a workstation measurement, not a benchmark of an Oracle ARM VM or a
dedicated production server.

### Distinguish the four intervals

1. **Boundary to evaluation:** the worker notices a completed candle, updates
   features, and evaluates the session/instrument. This includes scheduling and
   any work already ahead of that actor.
2. **Evaluation to intent:** arithmetic, comparisons, crossing state and creation
   of the immutable signal. This is numerical work without database/provider I/O.
3. **Intent to order placement:** routing to the account owner, capital/order
   checks, controller queueing and database persistence.
4. **Placement to fill:** Paper waits for an eligible subsequent observed quote;
   Live submits to the broker, which determines execution and reports the fill.

An order's `eligible_at` records its market decision time; it does not record the
wall-clock instant when the Python evaluator finished. Consequently, persisted
order timestamps cannot isolate pure evaluation latency. The benchmark and
read-only shadow measurements below do that separately.

### Read-only live shadow observation

A temporary observer used the production `Worker.step()`, `read_market()` and
`EvaluationUnit.evaluate()` over WIPRO's existing shared-memory data and the
session's compiled configuration. It had no account owner or persistence/broker
sink; any generated intent would be discarded. It did not change the existing
session, add provider demand or place orders.

| Candle close, IST | Boundary to evaluation completion | Evaluator call duration |
| --- | ---: | ---: |
| 15:17:00 | 6.011 ms | 0.0747 ms |
| 15:18:00 | 15.323 ms | 0.1474 ms |
| 15:19:00 | 8.222 ms | 0.0828 ms |

These are three observations in a separate read-only process, not tracing inside
the production worker and not a statistically established latency guarantee.
The strategy entry window ended at 15:14, so these calls evaluated conditions but
did not produce an entry intent. The synthetic experiment below explicitly
asserted that signal generation occurred.

The runtime asks for `stop.wait(.002)` when idle. A separate 300-sample check of
`threading.Event.wait(.002)` measured **15.93 ms median, 16.20 ms p95** on this
machine. This demonstrates local Windows scheduling granularity; it is not a
measurement of the exact multiprocessing wait implementation or a promise about
Linux. A two-millisecond argument must not be described as a guaranteed
two-millisecond wake-up.

### Five complex rules used for the numerical benchmark

The compiled entry group contained these five comparisons:

1. One-minute `(CLOSE + OPEN) / 2 > EMA(20)`.
2. One-minute `RSI(14, source=EMA(10)) > 50` (nested indicator).
3. Five-minute MACD histogram `(12, 26, 9) > 0`.
4. Five-minute `ADX(14) > 20`.
5. Fifteen-minute `CLOSE > upper Bollinger band(20, 2)`.

The group used OR so the synthetic rising history could produce an intent on
every measured candle. The production evaluator still executes **all five**
comparisons before combining them; this does not short-circuit after the first
true comparison. There were nine registered feature nodes, including the nested
EMA. Warmup requirements were 121 one-minute, 176 five-minute and 21 fifteen-minute
bars. Compilation and history warmup were excluded from timed evaluation.

Every sample completed all three timeframes together, representing a common
fifteen-minute boundary. An ordinary minute where only the one-minute timeframe
closes does less feature-update work. Each numerical run recorded 1,950 samples
after 50 warmup samples and checked that all operand values were finite, history
was ready and an intent actually resulted.

| Numerical operation | Initial run median | Repeat median | Repeat p95 |
| --- | ---: | ---: | ---: |
| Incremental feature updates | 0.146 ms | 0.045 ms | 0.057 ms |
| Five rules plus intent construction | 0.139 ms | 0.037 ms | 0.050 ms |
| Combined | 0.295 ms | 0.082 ms | 0.109 ms |

The initial combined p95 was 0.791 ms and maximum 5.379 ms; the repeat maximum
was 1.104 ms. The wide variation between runs is a reason to report distributions
and machine load, not to promise a single microsecond figure. A database execution
guard around the repeat numerical and worker benchmarks observed zero SQL calls.

### One-worker simultaneous candle-close batches

One evaluation unit means **one session × one instrument**. The benchmark used
the actual worker scheduler, feature graph, calendar, evaluator, account actor
iteration and partition function. Shared-memory reads were replaced with
in-memory observation arrays. Order intents were captured at dispatch; financial
acceptance, inter-process message serialization, order persistence and broker
calls were intentionally not exercised. Simulated accounts had no open positions
or working orders. Idle waits and periodic checkpoint queue writes were outside
these timed batches.

Each case measured 12 rounds after three warmup rounds. All units were due at
the same synthetic candle boundary. The numbers are the time to the **last
generated signal in the batch**, not the latency of every individual unit, and
exclude waiting before the worker began that batch.

| Sessions × instruments each | Evaluation units | Unique symbols shared across sessions | Initial median | Repeat median | Largest measured batch across both runs |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 × 1 | 1 | 1 | 0.59 ms | 0.11 ms | 1.32 ms |
| 10 × 10 | 100 | 10 | 12.38 ms | 4.64 ms | 15.23 ms |
| 100 × 10 | 1,000 | 20 | 116.13 ms | 44.70 ms | 209.21 ms |
| 1,000 × 2 | 2,000 | 20 | 333.79 ms | 95.44 ms | 766.35 ms |
| 1,000 × 2 | 2,000 | 200 | 411.91 ms | 152.61 ms | 569.30 ms |

Additional initial-run cases:

- 100 sessions sharing one symbol: 18.65 ms median to the last signal.
- 1,000 sessions sharing one symbol: 156.88 ms median.
- One session with 100 distinct instruments: 35.65 ms median.
- 100 sessions × 10 instruments across 20 symbols, with ten different parameter
  variants: 142.90 ms median. Distinct feature parameters require additional
  nodes; identical indicators on the same symbol/timeframe share a node within
  that worker. The benchmark registered the union of all ten variants per symbol.

These are short experiments on synthetic prices, not sustained production load
tests. Do not turn these batch times into a claimed supported user count.

### Multiple workers

An isolated multiprocessing check partitioned the same 1,000 sessions × two
instruments, sharing 20 distinct symbols, using the production hash. Each worker
process ran its own scheduler and graphs. Workers synchronized before each round;
group completion was measured from the earliest process start to the latest
signal across processes. No production worker settings were changed.

| Worker processes | Units per worker | Median group completion | Largest measured group completion |
| --- | --- | ---: | ---: |
| 1, repeat above | 2,000 | 95.44 ms | 125.16 ms |
| 2 | 955 / 1,045 | 78.58 ms | 89.81 ms |
| 4 | 493 / 525 / 462 / 520 | 59.70 ms | 78.13 ms |

The one-, two- and four-process runs were not simultaneous and machine contention
varied. These numbers demonstrate parallel execution, not a controlled linear
speedup ratio. Actual cross-worker intent delivery and shared-memory lock
contention were not included. Indicators for a symbol used on multiple workers
are maintained separately on those workers.

### Important limits and simple improvements

Current numerical work is fast enough that four or five ordinary complex rules
do not themselves explain a recurring three-to-five-second delay. For one warm
symbol, the observed wall-clock boundary latency was dominated by wake-up and
scheduling rather than indicator arithmetic. Larger deployments need attention
to the following specific costs:

1. **Unchanged candle rules are still resolved on ordinary ticks.**
   `EvaluationUnit.evaluate_rule()` calculates values before checking their
   sample stamps. This preserves correct crossing state but spends CPU when
   closed-candle inputs have not changed. A future targeted optimization should
   reuse values/results for unchanged inputs, while preserving live-price,
   position-revision, exit and crossing semantics. Simply skipping every tick
   would break those semantics.
2. **Cursor scanning grows with both symbols and actors.** `Worker.step()`
   scans the full cursor mapping for every symbol to find its minimum consumed
   sequence. With 2,000 units and 200 symbols, an otherwise idle scan measured
   35.82 ms median in the repeat (94.52 ms initially), even using fake buffer
   reads. Indexing subscribers by symbol would remove this repeated global scan.
3. **All symbols are read before actor evaluation starts.** Feature updates and
   buffer scans for other symbols delay the first signal in a batch. The
   2,000-unit/200-symbol repeat took 50.17 ms median to its first signal and
   152.61 ms to the last. Small bounded read/evaluation turns could improve this,
   provided sequence ordering and candle-history consistency remain intact.
4. **Checkpoints and persistence are separate capacity costs.** Checkpoint
   construction alone sometimes showed tens of milliseconds of wall-clock
   time. Actual snapshot serialization and output queue backpressure add work.
   `Controller.receive()` currently persists transitions synchronously before
   acknowledgement/broker submission. A fast evaluator is not proof that
   thousands of simultaneous order writes can be completed equally fast.
5. **Quote frequency matters in addition to candle frequency.** For 2,000 units
   across 20 symbols, a round with one ordinary tick per symbol took 83.88 ms
   median in the repeat and 261.16 ms initially. Five such rounds per second
   would consume approximately 0.42–1.31 seconds of measured worker wall time
   before other overhead. This is a workload illustration, not a sustained
   throughput measurement. Large tick bursts can create backlog even when
   candles close only once a minute.
6. **Preparation is not the steady state.** A history correction, connection
   generation change or late observation can trigger background graph rebuilding
   and temporarily defer that symbol's evaluators. Those delays are excluded from
   the warmed numerical measurements.

For an initial deployment, keep the compiled, shared-feature, independent-unit
architecture. First optimize unchanged-rule work and per-symbol subscriber
lookups, then measure on the intended server with realistic tick frequency,
positions, order persistence and concurrent API/background load. Add worker
processes according to available physical CPU and memory; do not assume this
laptop's results apply to a small shared VM. Account ownership remains serialized
to avoid conflicting capital/position updates even when signal units run in
parallel.

No execution configuration, trading policy or application code was changed for
these measurements. Temporary benchmark/observer scripts and raw scratch output
were removed after recording results here.

## Why the later order still filled three seconds after the candle

Paper exit **846** provides a useful direct comparison with the numerical timing.
Its persisted decision eligibility is exactly 15:09:00, generation 21, execution
sequence 10603.

| Event | IST, 29 October 2026 |
| --- | --- |
| Last pre-boundary quote received (execution sequence 10602) | 15:08:58.651530 |
| Candle/decision boundary | 15:09:00.000000 |
| Order placed in the database | 15:09:00.251340 |
| Next observed quote received (execution sequence 10604) | 15:09:03.741245 |
| Fill persisted | 15:09:03.777011 |

The next quote carried exchange-feed time 15:09:03 and price 190.00. The retained
observation ring contains no intervening observation. Placement took 251 ms from
the boundary; the first subsequent quote arrived 3.741 seconds after it, and the
fill was persisted **35.766 ms after quote receipt**. The placement-to-quote wait
was approximately 3.490 seconds.

`match_order()` requires an observation with a suitable event time and a sequence
after the signal. The 15:08:58 quote cannot fill a new 15:09:00 decision under this
model. There is no fixed three- or five-second sleep in matching. The retained
data proves a gap in observations available to the simulator, but cannot by
itself distinguish provider publication, SDK/transport scheduling or messages
filtered before ingestion; it is not proof of exchange inactivity.

Live broker submission does not wait for this simulator's next-quote fill:
`Controller.receive()` persists the accepted order and schedules the broker call.
Live execution time and confirmation then depend on the broker/exchange and
the order-report path. Changing Paper to fill immediately from the last known
price would change its simulation assumptions, not accelerate receipt of a new
market observation. This review did not make that change.

The final read-only check found the existing session RUNNING without an error and
the market feed connected. No diagnostic orders were created.

## FYERS references

- [SymbolUpdate contract](https://fyers.in/api-docs/v3/api/websockets/data-socket/data-socket-symbol-update/).
- [Index update and exchange-feed timestamp](https://fyers.in/api-docs/v3/api/websockets/data-socket/data-socket-indices-update).
- [FYERS support: unchanged trade timestamps and channel 15](https://fyers.in/community/t/last-traded-time-not-getting-updated-in-websocket-but-ltp-changes/19820).
- [FYERS support: trade time versus feed time for candles](https://fyers.in/community/t/websocket-to-candlesticks/13579).
