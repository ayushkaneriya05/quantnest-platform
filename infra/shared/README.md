# Shared deployment components

These files support all three modes. Start with [the mode selector](../README.md). The [script runbook](scripts/README.md) gives commands, inputs, expected results and recovery instructions for every shared script.

## 1. Images

| File | Contents | Consumers |
| --- | --- | --- |
| docker/backend.Dockerfile | Python 3.12, hashed backend lock, Django source, UID 10001 | API, runtime services, Celery, Beat and one-shot commands |
| docker/research.Dockerfile | Python 3.12, hashed research lock, FastAPI on 8001, UID 10001 | Research provider |

The backend build stage installs dependencies; the final image has no compiler requirement. pandas-ta installs from PyPI with the locked Numba/NumPy and TA-Lib. Qualify a release on its advertised ARM64/x86_64 architectures.

Public build example, from the repository root:

```sh
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml build
```

Substitute the other mode paths to build those images. This does not migrate or start trading. The root .dockerignore excludes environments, local dependencies, media and logs. Frontend is separate from the backend image: Cloudflare builds Public; Caddy mounts Private's prebuilt frontend/dist.

## 2. Writable data

| Volume/path | Purpose | Recovery |
| --- | --- | --- |
| PostgreSQL /var/lib/postgresql/data | Financial authority, strategies, candles, billing, licences and outbox | Database dump |
| General Redis /data | Celery, Channels and cached coordination | Durable snapshot |
| Runtime Redis /data | Order streams, projections, leases and heartbeats | Durable snapshot |
| Analytical Redis | Bounded research cache | Rebuild |
| /var/lib/quantnest/runtime | One host's shared market buffers | Rebuild from source/history |
| /var/lib/quantnest/scheduler | One Beat schedule file | Rebuild |
| backend/media | Private user media | Media archive |
| backend/staticfiles | Collected admin assets | Recollect from release |
| Caddy data/config | Certificate/runtime data | Manage with configuration separately |

The image creates application-owned writable directories. New named volumes inherit those permissions; arbitrary root-owned bind mounts do not. Production logs go to Docker's bounded console logs. Development additionally rotates per-process files.

There is no Private-specific directory in the shared image. Private mounts only public verification keys under /etc/quantnest/license. Its activation token is protected environment configuration; the OCI private signing key stays centrally held.

## 3. PostgreSQL initializer

postgres/010-initialize.sh runs once on an **empty** database volume:

1. Connect as bootstrap administrator quantnest_admin.
2. Install TimescaleDB.
3. Create DB_USER with login and without superuser/create-role/create-database rights.
4. Give the application role database ownership and usage/creation in public schema.

Use different POSTGRES_ADMIN_PASSWORD and DB_PASSWORD values. File edits do not rotate existing role passwords; stop affected application services, rotate in PostgreSQL, update clients together, then recreate those services.

Django migrations use the application role. Candle hypertable/compression setup is a separate operator command after migration. See the mode guide for initial data setup.

setup_timescale is atomic; run it with application services stopped. A conversion/compression failure rolls back and exits nonzero; it does not silently drop schema dependencies or report a partial setup as successful.

Application connections use a five-second PostgreSQL connection timeout so unavailable dependencies fail promptly instead of tying up API/worker connection attempts indefinitely. ASGI keeps Django's default nonpersistent connection behavior; tune pooling only with measured connection pressure.

## 4. Redis policy

| Store | Data/container ceiling | Persistence and eviction |
| --- | --- | --- |
| General | 256 / 384 MiB | AOF; noeviction |
| Runtime | 320 / 768 MiB | AOF, appendfsync always; noeviction |
| Analytical | 128 / 192 MiB | No RDB/AOF; rebuildable; allkeys-lru |

runtime.conf is shared because financial handoff must not be evicted in any mode. Its extra container memory allows RDB/AOF rewrite and allocator overhead. Analytical cache eviction cannot remove financial state.

Compose supplies authenticated URLs. General Redis DB 0 serves Celery/results/Channels, DB 1 ordinary Django cache, DB 2 quotes. Analytical Redis DB 0 serves research cache. Runtime Redis DB 0 serves coordination/order streams. Production publishes no Redis/database ports.

REDIS_PASSWORD must be hexadecimal for unambiguous URL parsing. Rotate server and client credentials together. A ping is not a persistence check; Public monitoring also checks AOF/RDB status. Investigate noeviction write failures rather than enabling eviction.

## 5. Process separation

API handles requests/sockets. Feed handles data I/O. Execution owns actors and calculation children. Orders handles enabled-scope account operations. Terminal runs simulated matching. Outbox publishes committed changes. Broker events runs only in Private or intentional Development Live.

Celery background consumes default,paper,marketdata,notifications; Private/Development also has live reconciliation. Celery compute consumes compute for bounded backtests/research. One Beat schedules all periodic work. FastAPI research is private-network-only.

Docker supervises these processes. Do not run duplicate native runtime/Celery supervisors alongside Compose. Public systemd units supervise **host backup/monitoring**, not another application runtime. A runtime container includes supervised child processes; container count is not process count.

API health uses the lightweight quantnest_runtime.probe module to request the running API's /health/ endpoint, verify its mode and dependency status, and supply the trusted token internally. It does not start a second Django/numerical-library process every 30 seconds. Research health likewise uses a lightweight local HTTP request. Full Django checks remain deployment/operator diagnostics, while the minute monitor reuses container readiness and one metrics command.

## 6. Gateway boundaries

Development uses Vite. Public uses a Cloudflare Function and locked Caddy origin. Private Caddy serves React and injects the installation's ingress token. API joins the edge network; ingress does not join the database network.

Research tool paths are blocked at external ingress and require a shared service token internally. Browser builds contain no trusted ingress or AI secret. Public has no Live execution consumer; Private checkout is centrally managed.

Gateways overwrite X-QuantNest-Client-IP from the actual connection (Cloudflare's verified connecting address in Public). Django accepts it only with the correct ingress token, then normalizes REMOTE_ADDR for throttles, audit and session history. Browser-supplied forwarding chains cannot choose that address. Private's supplied Caddy is direct ingress; adding a customer load balancer requires an explicitly reviewed trusted-proxy/address configuration.

## 7. Daily operations

Follow [the script guide](scripts/README.md) for all three modes:

- first deployment and controlled upgrade;
- complete diagnostics and logs;
- age key generation and local/OCI encrypted backups;
- state-only isolated recovery without production ports/subnets;
- previous-release recovery and financial reconciliation;
- resource changes and topology rebuilding.

Retain release artifacts, protected environments, signing trust, credential encryption keys and offline recovery identities separately. A database backup does not replace these prerequisites.
