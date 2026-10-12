# Oracle A1: 2 OCPUs / 12 GB worker starting profile

The user confirmed `VM.Standard.A1.Flex`, **2 OCPUs / 12 GB RAM**. These recommendations are engineering starting points for that host, not measured Oracle results or a concurrent-user capacity guarantee. Reproduce [the end-to-end test](ORDER_E2E_LATENCY.md) on the target VM before increasing admission limits.

Oracle's [current Always Free documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), checked 10 October 2026, lists 1,500 A1 OCPU-hours and 9,000 GB-hours per month, equivalent to 2 OCPUs / 12 GB for Always Free tenancies. Check the actual tenancy quotas in the Console. Do not size this deployment using older 4 OCPU / 24 GB examples.

## Runtime settings

Use [infra/oracle-a1-2cpu.env.example](../../infra/oracle-a1-2cpu.env.example) as an overlay to the existing deployment environment. It contains no credentials and does not replace the backend environment file.

| Setting | Start with | Reason |
| --- | --- | --- |
| `EXECUTION_WORKERS` | 1 | One lightweight protective owner, leaving CPU for calculations, database and API |
| `CALCULATION_WORKERS` | 1 | One CPU calculation child; total children are execution workers times calculation workers |
| `ORDER_WORKERS` | 1 | One gateway process and one Terminal process; this setting controls both service counts |
| `ORDER_CONCURRENCY` | 2 | Bounded concurrent accounts per enabled gateway scope; one account remains serial |
| `CALCULATION_CACHE_MB` | 32 | Separate 32 MB frame and indicator budgets; this does not bound total RSS |
| `EXECUTION_MAX_ACTORS` | 8 | Initial admission cap, not proof that eight complex actors meet a latency objective |
| `EXECUTION_MAX_USER_ACTORS` | 4 | Initial per-user admission cap; an actor is one scope/session/instrument |
| `EXECUTION_SCAN_INTERVAL` | 0.005 | Keep the observed-tick scan responsive; monitor CPU at real symbol rates |
| `EXECUTION_TICK_BATCH` | 128 | Existing bounded per-actor batch |
| `EXECUTION_SHARDS` / `ORDER_PARTITIONS` | 64 / 16 | Keep partition counts stable; partitions do not each create a process |
| Node count / index | 1 / 0 | Single-host deployment |
| Native numerical threads | 1 each | Prevent NumPy/BLAS/Numba from creating competing CPU pools |

Keep the existing calculation/startup/order deadlines. Reducing a deadline does not make execution faster. Do not set two execution workers and two calculation workers on this host: that creates four calculation children before the other services are counted.

For the public Paper product, use `EXECUTION_ENABLED_SCOPES=paper` and leave the broker-order `broker-events` service stopped. The market-data service is still required. A separately configured private Live deployment may enable `paper,live` and run `broker-events`; do not treat that as extra available CPU.

## Process and queue counts

| Service | Starting count |
| --- | --- |
| Django ASGI | 1 worker |
| Market-data | 1 supervised service |
| Outbox | 1 supervised service |
| Execution | 1 owner plus its 1 calculation child |
| Orders | 1 supervised service; bounded account threads |
| Terminal | 1 supervised service |
| Broker order events | 0 for public Paper, 1 for a private Live deployment |
| Celery control jobs | 1 worker, concurrency 1, combined low-volume queues |
| Celery backtests/research | 1 worker, concurrency 1, consuming both heavy queues |
| Celery Beat | Exactly 1 scheduler |
| Private FastAPI research service | 1 ASGI worker |

The two Celery workers are separate from execution. For the small host, combining `backtesting,research` deliberately allows only one of those jobs at a time; a long backtest can delay research. Larger deployments can use separately limited workers for each queue.

Examples from the backend directory:

```bash
celery -A backend worker -Q default,notifications,marketdata,paper -c 1 --prefetch-multiplier=1 --max-tasks-per-child=100 --max-memory-per-child=750000 --hostname=control@%h
celery -A backend worker -Q backtesting,research -c 1 --prefetch-multiplier=1 --max-tasks-per-child=100 --max-memory-per-child=750000 --hostname=heavy@%h
uvicorn backend.asgi:application --host 127.0.0.1 --port 8000 --workers 1
```

Add the `live` queue to the control worker in a private Live deployment. Preserve the existing per-task routes; `backtesting` is the actual queue name. Do not simultaneously start the seven per-queue Celery instances and these combined workers. Run these commands under the existing systemd supervision, not interactive production shells.

Keep the existing Celery template's low CPU weight and `Nice=10`. For a service consuming the two heavy queues, an initial systemd override of `CPUQuota=50%` limits that whole service, including its child processes, to half of one CPU, following the [systemd CPU quota definition](https://github.com/systemd/systemd/blob/main/man/systemd.resource-control.xml). This reduces its competition with execution at the cost of longer jobs. Raise or remove the quota off market hours only after measuring. Use [Celery's prefetch limit guidance](https://docs.celeryq.dev/en/stable/userguide/optimizing.html) to keep reservation bounded; multiplier one is not a universal guarantee of zero reserved work. Put limits on backtest history/instrument sizes as well; killing an oversized job with an RSS limit is not admission control.

Do not enable a generic extra worker per CPU on every service. RAM is adequate for a small deployment, but **two CPU cores are the main constraint**, especially for concurrent backtests, research dataframe tools, cold indicator compilation and historical warmup.

## Database, Redis and operating limits

- Keep PostgreSQL with the current TimescaleDB setup. Oracle's free Oracle/MySQL databases are not replacements for the PostgreSQL-specific financial queries and candle functions.
- Keep runtime Redis persistent with AOF and `noeviction`. Put UI quote/research caches in a separate bounded Redis process as described in [BACKEND_RUNTIME.md](../BACKEND_RUNTIME.md). Separate logical databases in one process do not isolate eviction.
- Keep market buffers on local storage shared by runtime processes. Size retained candle/tick depth to the actual enabled universe; RAM includes mmap pages and warmup, not just cache budgets.
- Monitor p95/p99 from normalized receipt to order request, broker send/ack, queue age, unpublished outbox age, cold recovery, process RSS, CPU saturation and database connections. Set an acceptable latency objective before admitting more actors.
- Warm only the active universe, rate-limit repair jobs, and run large backtests/data imports outside market hours. Upgrade CPU or isolate heavy jobs when queue age or latency exceeds that objective.

Always Free is suitable for an MVP and measurement. Oracle states that [Free Tier has no SLA](https://www.oracle.com/cloud/free/faq/), and its Always Free documentation describes idle-instance reclamation. A single VM also has no host redundancy. Keep tested backups and recovery procedures; this deployment does not establish dependable HFT or an uptime guarantee for Live trading.
