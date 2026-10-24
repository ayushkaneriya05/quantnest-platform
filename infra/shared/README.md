# Shared infrastructure: configuration reference

For hands-on preparation, use [Server setup](SERVER-SETUP.md) and
[Integration setup](INTEGRATIONS.md) alongside your mode's `SETUP.md`.
[Recovery setup](RECOVERY-SETUP.md) covers the first operator key and off-host copy.

These definitions are used by [Development](../development/README.md),
[Public](../public/README.md) and [Private](../private/README.md). The
[script runbook](scripts/README.md) explains deployment, diagnostics and recovery.

## Files

| File | Responsibility |
| --- | --- |
| `docker/backend.Dockerfile` | Shared Python image for API, feed, execution, Celery, Beat and management commands. |
| `docker/research.Dockerfile` | Internal FastAPI/Gemini service image. |
| `docker/frontend.Dockerfile` | Builds Private React assets, then puts them into a Caddy image. |
| `postgres/010-initialize.sh` | Initial Timescale extension and application database role. Runs only on an empty PostgreSQL volume. |
| `scripts/compose_config.py` | Common mode/profile selection and private reading of effective Compose configuration. |
| `scripts/deploy.py` | Build, stopped-service migrations, Timescale setup, Site/static setup and startup. |
| `scripts/diagnostics.py` | Container, configuration, dependency and execution-worker checks. |
| `scripts/backup.py` | PostgreSQL/media encrypted archive; no cloud SDK or Redis snapshot. |
| `scripts/restore.py` | Restore only into an empty database with application services stopped. |

## Every Compose field: what it means

The mode files repeat their complete topology deliberately: you can read or run
one mode without merging several YAML files. Common service options are defined
once per file under `x-backend`. This reference covers the repeated fields; each
mode README lists its additions and exact commands.

| YAML line/key | Meaning and reason |
| --- | --- |
| `name: quantnest-<mode>` | Stable project identity. Docker volume/network names include it, keeping modes separate. |
| `x-backend: &backend` | YAML extension/anchor containing common backend container options. It does not start a container. |
| `<<: *backend` | Inherits that common backend definition into an application service. A service's own `volumes`/`networks` replaces the inherited list. |
| `build.context: ../..` | Repository root is the image build context; paths are relative to the mode directory. |
| `build.dockerfile` | Selects the backend, research or frontend Dockerfile under `shared/docker`. |
| `build.args` | Private frontend's public site URL/widget key only. Application secrets are never build arguments. |
| `image` | Container image/tag. Fixed infrastructure versions are kept consistent across modes. `QUANTNEST_RELEASE` identifies application builds. |
| `env_file: [backend.env]` | Passes this mode's protected server values into backend containers. |
| `env_file: [research.env]` | Gives the AI key only to the research service. |
| `env_file: [frontend.env]` | Development-only public Vite inputs. |
| `environment` | Values Compose owns, overriding `env_file` values. Internal addresses always use service DNS names. |
| `${VALUE:?message}` | Required Compose interpolation input; configuration fails when missing/empty. |
| `${VALUE:-default}` | Optional input with an explicit default. |
| `$$VALUE` | Keeps `$VALUE` for the container shell instead of substituting it on the host. Used by PostgreSQL health checks. |
| `volumes` | Named persistent volume or host bind mount. `:ro` makes a configuration mount read-only. |
| `networks` | Selects which service networks a container can reach. |
| `depends_on: ... service_healthy` | Waits for PostgreSQL/Redis readiness before launching backend services. |
| `depends_on: [api]` | Ensures an API container exists before starting the gateway/frontend; HTTP availability is checked separately. |
| `command` | Overrides the image's default command with one process role. |
| `ports` | Publishes a container port on the host. No production database, Redis or research ports are published. |
| `profiles` | Development only: opt-in feed, research or broker events. Default API/Paper/Terminal can start without those provider credentials. |
| `restart: unless-stopped` | Docker restarts an exited service, except after an explicit operator stop. It does not restart a merely unhealthy container. |
| `init: true` | Small PID 1 forwards signals and reaps child processes; needed for execution/Celery groups. |
| `stop_grace_period: 90s` | Allows workers/controllers time to stop and commit before Docker forces termination. |
| `logging.driver: json-file` | Docker captures console output. |
| `logging.options.max-size: 10m`, `max-file: "3"` | Bounds each container's logs instead of growing indefinitely. |
| `mem_limit` | Maximum container memory, not reserved idle usage. Leave host/build headroom. |
| `cpus: 0.75` | Caps compute container CPU usage so backtests/research cannot consume all host CPU; not a dedicated execution reservation. |
| `healthcheck.test: [CMD, ...]` | Executes the command directly. |
| `healthcheck.test: [CMD-SHELL, ...]` | Runs through a shell when environment expansion is required. |
| `interval`, `timeout`, `retries` | Probe frequency, per-probe deadline and failure threshold. |
| `start_period` | Startup grace period before health failures count. |
| `private: {internal: true}` | Database/service network without Internet egress. |
| `edge: {internal: true}` | Production gateway-to-API network; ingress does not join the database network. |
| `outbound: {}` | Provides Internet egress for providers/SMTP/AI and service connections that need it. |
| Top-level `volumes: {name: {}}` | Asks Docker to create/manage named data volumes. Plain `down` keeps them; `down -v` destroys them. |

### Backend environment block

| Entry | Exact role |
| --- | --- |
| `QUANTNEST_DEPLOYMENT_MODE` | Selects Development/Public/Private security and allowance policy. |
| `DEBUG` | Django Boolean debug setting, independent from mode. Production is false. |
| `EXECUTION_ENABLED_SCOPES` | `paper` or `paper,live`; determines server admission and UI execution access. Terminal is simulated. |
| `BILLING_ENABLED: "False"` | Private has no checkout; production Public reads its configured switch. |
| `DB_HOST: postgres`, `DB_PORT: "5432"` | Container-to-container database destination. |
| `REDIS_URL: .../0` | Celery broker and Channels. |
| `CACHE_URL: .../1` | Default Django cache. |
| `MARKET_CACHE_URL: .../2` | Shared display quotes and quote fallback cache. |
| `RUNTIME_REDIS_URL: .../3` | Subscription demand, provider ownership, history revisions and worker readiness. It is not the financial execution ledger. |
| `RESEARCH_CACHE_URL: ...redis-cache.../0` | Larger disposable research frames/evaluations use a separate evictable process. |
| `RESEARCH_SERVICE_URL: http://research:8001` | Internal AI provider endpoint. |
| `RESEARCH_INTERNAL_API_URL: http://api:8000/api/v1/research/tools/` | Research service's authenticated Django tool callback; blocked at public ingress. |
| `QUANTNEST_RUNTIME_DIR: /var/lib/quantnest/runtime` | Shared file-backed market buffers and execution ownership lock. Same path/volume for feed, API and execution. |

Logical Redis databases separate key namespaces; they share one process's memory
and availability. General Redis does not evict. Research cache pressure cannot
evict queues from the general process because it is a separate Redis service.

## Services and each command option

### PostgreSQL

`timescale/timescaledb:2.30.2-pg16` uses the pinned digest shown in Compose. It includes
PostgreSQL 16 and TimescaleDB. The `postgres` volume keeps all durable application data.

| Setting/command | Why |
| --- | --- |
| `POSTGRES_DB` | Initial application database. |
| `POSTGRES_USER: quantnest_admin` | Bootstrap/admin account, distinct from the Django application role. |
| `POSTGRES_PASSWORD` | Bootstrap password. |
| `DB_USER`, `DB_PASSWORD` | Inputs read by the initializer, not built-in image user variables. |
| `TIMESCALEDB_TELEMETRY: "off"` | Disables extension telemetry. |
| `TS_TUNE_MEMORY: 1536MB`, `TS_TUNE_NUM_CPUS: "2"` | Production tuning budget matching the starter memory cap and assumed CPU count; review when changing host/container capacity. |
| `pg_isready -U ... -d ...` | Confirms database readiness without a Django startup. |
| Development `127.0.0.1:54329:5432` | Optional host database tools can connect locally; production has no published database port. |

`postgres/010-initialize.sh` line meanings:

1. `#!/bin/sh`, `set -eu`: use the container shell and fail on unset inputs/errors.
2. `psql --username ... --dbname ...`: connects as the bootstrap account.
3. `--set=app_user/app_password/database`: sends values as psql variables.
4. `ON_ERROR_STOP=1` and the quoted heredoc: stop on SQL errors and avoid shell expansion in SQL.
5. `CREATE EXTENSION ... timescaledb`: installs the extension with administrator rights.
6. `format(... %I ... %L ...)` and `\gexec`: safely quote identifiers/passwords and execute generated SQL.
7. `CREATE ROLE ... NOSUPERUSER NOCREATEDB NOCREATEROLE`: Django gets a restricted login.
8. `ALTER DATABASE ... OWNER`: permits normal application schema migrations.
9. `GRANT USAGE, CREATE ON SCHEMA public`: permits table/index creation in the application schema.

The initializer runs only for a fresh database volume. Editing an env password
does not rotate an existing PostgreSQL role. `deploy.py` runs `setup_timescale`
after migrations to convert candle storage and set its compression policy.

### Redis

| Service option | Purpose |
| --- | --- |
| `redis:7.4.6-bookworm` | Same version in every mode. |
| `REDISCLI_AUTH` | Authenticates the health command without putting a password in its arguments. |
| `--requirepass` | Authenticates application clients. The resolved Compose config contains secrets; use `config --quiet`, not printed `config`. |
| General `--appendonly yes --appendfsync everysec` | Persists broker/coordination data with periodic fsync; database checkpoints remain the financial authority. |
| General `--maxmemory 512mb --maxmemory-policy noeviction` | Fails writes at its limit instead of evicting queued work. Container ceiling is 768 MiB for process/persistence overhead. |
| Research `--save "" --appendonly no` | No persistence needed for reproducible cached frames. |
| Research `--maxmemory 128mb --maxmemory-policy allkeys-lru` | Evicts cache entries when necessary; container ceiling is 192 MiB. |
| `redis-cli ping` | Small authenticated readiness probe. |

### Application processes

| Service | Command and explanation |
| --- | --- |
| `api` | `uvicorn backend.asgi:application --host 0.0.0.0 --port 8000`: serves HTTP and WebSockets on the container network. `--workers` selects API processes in production. `--no-proxy-headers` leaves trusted client/protocol handling to Django's explicit gateway middleware. Production also hides the server header and disables access logging; application errors still go to console. |
| `feed` | `python -m quantnest_runtime market-data`: provider connection, subscription demand, history warmup, shared observations and browser quote/chart publication. |
| `execution` | `python -m execution`: sole supervisor for the controller and persistent Paper/Live/Terminal workers. Never scale the container count; adjust `EXECUTION_WORKERS`. |
| `broker-events` | `python -m quantnest_runtime broker-events`: ingests personal Live order updates. Private includes it; Development uses the `live` profile; Public omits it. |
| `background` | `celery -A backend worker --queues=...`: consumes default/support/maintenance, marketdata and permitted Live reconciliation jobs. `--concurrency=2` provides two slots; `--max-tasks-per-child=100` periodically releases process resources; `--hostname` distinguishes it from compute. |
| `compute` | Consumes only `compute` for backtests/research. `--concurrency=1` bounds CPU/RAM use; `--max-tasks-per-child=25` and `--max-memory-per-child` recycle a child after work. The memory threshold is KiB and does not terminate an active job at that threshold; the container cap still applies. |
| `beat` | `celery -A backend beat --schedule=/var/lib/quantnest/scheduler/celerybeat`: one scheduler, persisted in its own volume. Its explicit `volumes` replaces the backend list because Beat does not need market buffers/media. |
| `research` | Internal FastAPI service on 8001. A single Uvicorn worker owns the provider client; Django tools require the shared token. |
| `frontend` | Development Node container runs `npm ci` then Vite with `--host 0.0.0.0`; the port is exposed only on host loopback. |
| `ingress` | Production Caddy. Public proxies to API behind Cloudflare. Private serves built React and proxies API/WebSockets. |

The API healthcheck uses Python's standard HTTP client to call `/health/` on the
already running server. `ProxyHandler({})` bypasses inherited host HTTP proxy
variables for this local request; trusted protocol/token headers let it pass the
same gateway policy. HTTP 200 means database/runtime Redis dependencies answered.
`deployment_health --workers` additionally checks the controller's reported worker
count. Neither check proves provider authorization or successful live order placement.

## Volumes

| Volume | Contents | Backup/rebuild policy |
| --- | --- | --- |
| `postgres` | Strategies, candles, users, financial records, commands/checkpoints, billing/support | Encrypted database dump. |
| `media` | User-uploaded private media | Media archive in the same backup. |
| `redis` | Broker queues, Channels, quotes, subscription coordination | Persistent locally; not restored as financial state. PostgreSQL remains the authority. |
| `runtime` | Market buffers and local execution lock | Rebuild after restart/recovery; do not copy buffers between hosts. |
| `scheduler` | Beat schedule file | Rebuildable; one active Beat instance per deployment. |
| `staticfiles` | Collected Django admin assets | Recreated by `collectstatic`. |
| `caddy`, `caddy-config` | TLS certificates and Caddy state | Preserve during ordinary upgrades; Caddy can reissue certificates if required. |
| `frontend-node-modules` | Development Linux Node dependencies | Recreate with `npm ci`; avoids mixing Windows node_modules into the container. |

All modes use named volumes. `down` preserves them; `down -v` deletes them. The
new image creates writable directories owned by UID 10001. New Docker volumes
inherit these permissions; root-owned host directory mounts may not.

## Dockerfiles, line by line

### Backend image

| Instruction | Reason |
| --- | --- |
| `FROM python:3.12-slim-bookworm AS builder` | Python ABI matches locks; Debian builder can compile dependencies. |
| First `RUN apt-get ... build-essential libpq-dev` | Build tools/database headers stay in the build stage. Package indexes are removed afterward. |
| `COPY backend/requirements.lock` | Dependency layer changes only when the lock changes. |
| `pip install --prefix=/install --require-hashes` | Installs locked dependencies into a directory copied to the runtime image. |
| Second `FROM python:3.12-slim-bookworm` | Small runtime stage without the compiler toolchain. |
| `ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1` | Avoids bytecode writes and makes console logs immediate. |
| Numerical `*_NUM_THREADS=1` | Prevents one worker's numerical libraries from spawning extra CPU pools. |
| `WORKDIR /opt/quantnest` | Stable application root. |
| Runtime `RUN apt-get ... libpq5` | Runtime PostgreSQL client library. |
| `COPY --from=builder /install /usr/local` | Copies installed Python packages/executables. |
| `COPY backend/ ...` | Copies application source; `.dockerignore` excludes environments, private keys, logs and local data. |
| `RUN useradd ... mkdir ... chown ...` | Creates fixed UID 10001 and application-owned runtime/media/static/log paths. |
| `USER quantnest` | Application processes run without root privileges. |
| Final `WORKDIR .../backend` | Makes Django module/management command imports resolve normally. |
| `CMD [uvicorn, ...]` | API default; Compose overrides it for each process role. |

### Research image

Its Python base, unbuffered/no-bytecode environment and fixed UID follow the
backend pattern. It copies only `research_service/requirements.lock`, installs
with `--require-hashes`, copies the research source, switches to `quantnest`, and
starts `research_service.main:app` on port 8001 with one Uvicorn process.
There is no compiler stage because the locked dependencies use available wheels.

### Private frontend image

| Instruction | Reason |
| --- | --- |
| `FROM node:22.14.0-bookworm-slim AS builder` | Matches the supported frontend build runtime. |
| `WORKDIR /site` | Build directory. |
| `COPY package.json package-lock.json` and `RUN npm ci` | Reproducible dependency install with a reusable Docker layer. |
| `COPY frontend/ ./` | Adds React source and public assets. |
| `ARG VITE_SITE_URL`, `ARG VITE_TURNSTILE_SITE_KEY` | Public build values only; the widget site key is intentionally public. |
| `RUN npm run build` | Produces assets, known-route matcher, CSP, sitemap and robots files. |
| `FROM caddy:2.10.2` | Runtime has Caddy/static assets, not Node/node_modules. |
| `COPY --from=builder ... /srv/site` | Embeds the exact built frontend in the release image. |
| `COPY infra/private/Caddyfile ...` | Installs the personal HTTPS/static/proxy configuration. |

## Keep changes understandable

Mode-specific environment files contain operator choices. Compose contains service
topology and derived container addresses. Backend settings contain application
defaults. Do not copy every internal default into all three environment files.
When increasing worker count, adjust container memory/CPU after measurement; when
changing domain, rebuild the frontend and register the resulting provider callbacks.
