# Instrument latency and fairness test

Measured on 10 October 2026 against the current local execution code. The JSON report records source hashes so later changes can be distinguished from this result.

## Result

**The requirement that another instrument never delays an instrument is not met.** Every submitted observation completed in this benchmark, but instruments share a sequential protective scan and a bounded calculation pool. The scheduler provides service to all tested actors; it does not provide equal latency.

The final run validated **101,904 ticks and 384 completed strategy calculations** across 12 cases. No measured tick was lost, duplicated, or reordered, and no measured calculation wave was lost or duplicated. There were no worker errors or broker orders. Eight accounting tests and the existing 17 execution-domain tests also passed.

## Tick response

Each batch makes ticks available to all instruments at the same scan boundary. The table shows the p95 of the difference between the fastest and slowest instrument's **first protective decision in the same batch**. Each case includes 80 measured batches and 10 warmup batches. These are local response times after publication, not broker execution times.

| Workload on one execution owner | p95 latency spread | Median last-minus-first scan delay |
| --- | ---: | ---: |
| 10 instruments, one tick each | 1.82 ms | 1.09 ms |
| 50 instruments, one tick each | 5.40 ms | 1.88 ms |
| 100 instruments, one tick each | 10.55 ms | 3.92 ms |
| 200 instruments, one tick each | 12.86 ms | 8.20 ms |
| 100 instruments, reversed scan order | 9.24 ms | 4.05 ms |
| 100 instruments, first actor gets 128 ticks | 11.60 ms | 6.48 ms |
| 100 instruments, last actor gets 128 ticks | 9.10 ms | 4.15 ms |
| 100 instruments, first actor gets 256 ticks | 9.00 ms | 5.47 ms |

Reversing the actors moves the early/late advantage to different instrument identities. The difference is caused by scan placement, rather than a particular symbol or paper/live context. The first actor's 128-tick burst increases the median delay to the last actor relative to the equal-load case. The 256-tick case drains across multiple scans and verifies the bounded tick batch without dropping observations. Variations between case tails also include operating-system scheduling; these are separate runs, not controlled estimates of a precise burst penalty.

The per-instrument distributions, including total tick receipt age, are in [the JSON report](instrument-latency-2026-10-10.json). For example, individual instrument p95 ready-to-decision times in the 100-instrument equal-load case range from **0.83 to 11.22 ms**. The same-batch spread and the range of individual p95 values are different statistics.

## Candle calculation response

These cases use 12 instruments with real completed-candle construction, indicator computation, strategy evaluation, process-pool submission, and owner-thread application. There are eight measured history updates and two warmups per case. Each update invalidates the history cache. The small sample makes these exploratory results: the reported p95 is the maximum of eight observations for each instrument.

| Workload | CPU calculation processes | Range of instrument p95 ready-to-applied times |
| --- | ---: | ---: |
| Same EMA strategy | 1 | 92–925 ms |
| One strategy with 12 EMA/RSI rules, others with one EMA rule | 1 | 152–1,130 ms |
| Same EMA strategy | 2 | 77–403 ms |
| One strategy with 12 EMA/RSI rules, others with one EMA rule | 2 | 77–452 ms |

In the equal workload with one process, median computation time per instrument is about 49–59 ms. The largest instrument p95 admission wait is **770 ms**, and its separate pool wait can also add delay. In the mixed workload, the heavy strategy's median calculation takes **114 ms**, while the other strategies take about 58–64 ms. More calculation processes reduce completion time here but do not make it equal.

These measurements include frame rebuilding and cache accounting. They do not establish how much each internal function contributes; a CPU profile is needed before attributing the calculation cost to one function.

## Method and limits

- Host: Windows 11 build 26200, Intel Core i5-13420H, eight physical / twelve logical CPU cores, Python 3.11.9. This is a development machine without dedicated cores or controlled background load.
- The harness calls the actual `quantnest_runtime.execution.run_worker`, actual mmap buffers, actual paper/live session contexts, `evaluate_protection`, `calculation.evaluate`, and `apply_calculation`.
- Each strategy has up to five independent instrument actors. The cases include paper and live scopes and multiple tenant queues.
- One execution owner is tested per case. Calculation processes are set to one or two as shown. Normal settings are recorded separately in the report; deployment partitioning across owners/nodes is not exercised.
- The normal five-millisecond socket polling interval, 128-tick scan batch, and cache budgets are used. UDP uses a private ephemeral loopback port, so it cannot wake an existing execution service.
- Market data, cold session discovery, leases, Redis control, and persistence are fixtures. Database connections, runtime Redis access outside the fake control path, broker adapter creation, and order publication fail if attempted. Exit conditions deliberately remain false. No real market or broker feed is contacted.
- A test barrier holds the owner at a scan boundary while publishing each batch. The report includes publication time separately; `ready_ms` starts after all fixtures have been written, and `receipt_ms` includes their publication age. This makes the comparison simultaneous while excluding live feed arrival and ingestion skew.
- Measurement has overhead. The observer is notified once per whole tick batch to reduce observer/owner contention. Recorder operations still add time between actors, so these numbers are evidence of ordering and queueing, not an uninstrumented production SLA.
- Startup/import/JIT and initial history warmup are excluded. This is a finite batch benchmark, not a sustained-rate throughput, crash-recovery, multi-node, exchange latency, or HFT certification.
- Oracle Linux/ARM deployment, slow broker responses, triggered order submission, and persistent financial processing require separate measurements.

## Reproduce

From the `backend` directory:

```powershell
..\.venv\Scripts\python.exe -m quantnest_runtime.latency_benchmark --waves 80 --warmup 10 --output ..\docs\benchmarks\instrument-latency-2026-10-10.json
..\.venv\Scripts\python.exe -m unittest quantnest_runtime.test_latency_benchmark
```

Use `--quick --waves 3 --warmup 2` with a separate output path for a small smoke run. The benchmark always selects isolated SQLite/cache settings and a temporary market-data directory. It starts no trading services and does not use a production database.

## Next improvements supported by this result

1. Rotate the first instrument in each protective scan to remove a permanent scan-position advantage. Rotation distributes waiting; it does not remove waiting.
2. Admit protective ticks in smaller rounds across ready actors, preserving each instrument's tick sequence, so a busy instrument contributes less delay to its siblings.
3. Size execution partitions and calculation capacity against measured actor demand; define a latency budget and reserve sufficient capacity instead of promising equality on shared finite CPUs.
4. Profile completed-candle calculations and reuse already-built frames/indicators before raising process counts. Verify results still match backtesting and candle-coverage rules.
5. Measure on the deployment VM with continuous traffic, per-instrument queue age, and actual order handoff latency. Test mixed strategy cost, multiple owners, backlogs, and worker recovery under that load.

The current benchmark implements verification and reporting. A scheduler redesign needs its own correctness and performance acceptance criteria.
