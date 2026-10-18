# QuantNest

QuantNest is software for researching, building, backtesting and running a
customer's own trading rules. The customer website and workspace share one React
frontend. Public subscriptions support simulation through Paper; qualified Live
execution runs in a separate customer-owned Private installation.

[Commercial operations](docs/commercial-operations.md) covers no-code plan limits,
availability, required database setup, billing/support/licensing actions and their
frontend-to-backend flows.

## Application workflow

1. Research instruments, screen stocks and review existing strategy/backtest evidence.
2. Build entry, exit, time, position-sizing and automatic-disable rules. Save strategy versions.
3. Preview a backtest workload, run the historical simulation and review its results.
4. Allocate simulated capital and deploy a saved version to Paper.
5. Use the independent manual Terminal for simulated orders and positions.
6. Review closes in Journal and compare aggregate results in Reports.
7. In Private, connect an approved broker account and deploy a qualified Live strategy.

Automated execution currently supports active NSE stocks through Direct routing.
The manual Terminal also supports enabled NSE indices. Futures/options remain
coming soon; they are not enabled for strategy orders.

## Repository structure

| Directory | Responsibility |
| --- | --- |
| `backend/` | Django API, execution domain, market-data pipeline and runtime processes |
| `frontend/` | React customer site, authentication and trading workspace |
| `research_service/` | Private FastAPI provider for bounded AI research |
| `functions/` | Cloudflare Pages gateway for Public API, WebSocket and administrator access |
| `infra/development/` | Local stack and environment examples |
| `infra/public/` | Hosted Paper stack, Oracle provisioning, monitoring and backups |
| `infra/private/` | Customer-owned execution stack and signed release/install tools |
| `infra/shared/` | Shared images, Redis/PostgreSQL setup and deployment/recovery scripts |
| `docs/` | Operating guides, execution reference and current business specifications |

## Deployment modes

| Mode | Scope |
| --- | --- |
| Development | Local development; usage is recorded and commercial allowances are bypassed |
| Public | Explore/Build/Pro allowances; Terminal, research, backtests and Paper; Live execution blocked |
| Private | Signed contract capabilities and allowances; qualified broker execution on customer infrastructure |

`QUANTNEST_DEPLOYMENT_MODE` is independent of `DEBUG`. Production requires
`DEBUG=False`, configured providers, published feature states and the applicable licence. See
[deployment boundaries](infra/README.md) and [allowances](docs/commercial-operations.md).

## Configure and run

Use the [infrastructure guide](infra/README.md) to select one mode. Its Compose
stack is the deployment entry point and supervises the required services. Follow
the matching mode README for environment files, secrets and startup commands:

- [Development](infra/development/README.md)
- [Public](infra/public/README.md)
- [Private](infra/private/README.md)

For provider accounts, callbacks and integration configuration, follow the
[third-party setup guide](docs/third-party-setup.md). The current stack uses
PostgreSQL/TimescaleDB, Redis, the existing FYERS data integration, Brevo email and
Cloudflare for the Public React frontend. Public host provisioning uses Oracle.

Local frontend setup:

```sh
cd frontend
npm ci
npm run dev
```

The browser uses same-origin `/api/v1/` and `/ws/` routes. Vite forwards these to
`QUANTNEST_API_PROXY_TARGET`; its proxy token stays on the server. Public
production traffic goes through the Cloudflare gateway. Do not expose the trusted
token as a `VITE_*` browser variable.

Use Python **3.12** for local development, matching Docker and CI. The backend
installs `pandas-ta==0.4.71b0` directly from PyPI, with compatible Numba/NumPy
versions in the hashed dependency lock. TA-Lib supplies the advertised candle
patterns. No vendored package or legacy NumPy compatibility patch is required.

From the repository root, create the environment with Python 3.12 and install the
locked dependencies:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r backend/requirements.lock -r research_service/requirements.lock
```

On Windows with `uv`:

```powershell
uv python install 3.12
uv venv --python 3.12 --seed .venv
uv pip install --python .venv/Scripts/python.exe --require-hashes -r backend/requirements.lock -r research_service/requirements.lock
```

Stop API, Celery, research and runtime processes before replacing an existing
Python 3.11 environment, then select the new interpreter in the IDE and restart
those processes. Dependency resolution supports Python 3.12–3.13; Python 3.14 is
outside the current Numba compatibility range.

Regenerate the backend lock after changing dependency constraints:

```sh
uv pip compile backend/requirements.txt --constraint backend/constraints.txt --python-version 3.12 --universal --generate-hashes --output-file backend/requirements.lock
uv pip compile research_service/requirements.txt --constraint research_service/constraints.txt --constraint backend/requirements.lock --python-version 3.12 --universal --generate-hashes --output-file research_service/requirements.lock
```

### FYERS market-data sign-in

Start a fresh authorization at `/api/v1/market/fyers/login/`. It uses the origin
configured in `FYERS_REDIRECT_URI` and requires an active staff account. For the
default local configuration, use:

```text
http://localhost:8000/api/v1/market/fyers/login/
```

The login redirects from `127.0.0.1` to the configured hostname before creating
the verification cookie. Sign in on that hostname if prompted. Finish the FYERS
flow in the same browser within ten minutes. Authorization links cannot be
replayed; expired access tokens require a new sign-in.

Public mode requires the canonical gateway address for login, callback and admin
access. Register the exact callback URL with FYERS. Market-data authorization and
customer broker execution credentials are separate.

## Execution architecture

The market-data service normalizes observations, publishes shared local market
buffers and updates quote/chart projections. Execution owners evaluate active
strategy/instrument actors and send bounded calculation work to separate
processes. The tick decision path keeps ORM, broker and Redis I/O outside rule
evaluation. Account-partitioned order gateways perform durable admission and
financial changes; the transactional outbox publishes committed results.

Paper and Live use common strategy configuration, rules, sizing and exit actions.
Backtests use the same domain with historical candle simulation limitations.
Terminal matching has its own simulated order book. Broker WebSocket observations
and REST reconciliation share order ownership and cumulative fill accounting.

| Process | Purpose |
| --- | --- |
| Django ASGI | API, authentication, administration and workspace WebSockets |
| `market-data` | Source connection, observation normalization and shared market buffers |
| `execution` | Strategy/instrument ownership, protection and bounded calculation dispatch |
| `orders` | Enabled Paper/Live gateway streams and account-serialized order work |
| `terminal` | Manual simulated order matching |
| `outbox` | Committed event publication and recovery |
| `broker-events` | Broker execution observations; Private/Development Live only |
| Celery background | Reconciliation, notifications and maintenance |
| Celery compute | Bounded backtests and research work |
| Celery Beat | Exactly one task scheduler per deployment |
| Research FastAPI | AI provider calls and validated research tool orchestration |

Runtime targets run as `python -m quantnest_runtime <service>` from `backend`.
Compose supplies the deployment supervision; one-shot Django commands remain for
migrations, market history/calendar maintenance and diagnostics.

## Build and configuration checks

With the intended backend environment configured:

```sh
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
```

Frontend:

```sh
cd frontend
npm run lint
npm run build
```

CI checks configuration, migration consistency, frontend
lint/build, images and the three Compose definitions. Production capacity and
provider acceptance must be checked on the configured deployment.

Compose deployment also runs `python manage.py configure_site` after migrations
to configure Django's selected Site for email/social sign-in. Run it explicitly
for native setup or after changing the website origin. The mode READMEs cover
administrator OTP enrolment and first source authorization.

The [infrastructure operations runbook](infra/shared/scripts/README.md) explains
every deploy/diagnostics/backup/restore command, including earlier-release recovery in isolated
recovery and session review after updates. Public host tools and Private signed
installers have their own small hashed dependency locks; application dependencies
stay in the shared Docker images.

## Reference guides

Start with the [documentation index](docs/README.md) to choose the guide for your task.

- [Complete customer and operator workflows](docs/commercial-operations.md)
- [Runtime services and configuration](docs/backend-runtime.md)
- [Complete tick and execution lifecycle](docs/execution-technical-reference.md)
- [Deployment boundaries](infra/README.md)
- [Strategy configuration](docs/strategy-configuration.md)
- [Future strategy builder plan](docs/strategy-builder-plan.md)
- [Journal and execution review](docs/execution-review.md)
- [Authentication and session lifecycle](docs/authentication.md)
- [Customer website](docs/customer-site.md)
- [Research service configuration](research_service/README.md)
- [Integration setup](docs/third-party-setup.md)
- [Business plan](docs/business-plan.md)
- [Implementation specification](docs/implementation-plan.md)
