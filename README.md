# QuantNest

QuantNest is software for researching, building, backtesting and running a
customer's own trading rules. The customer website and workspace share one React
frontend. Public subscriptions support simulation through Paper; personal Live
execution is retained in a separate personal Private instance; customer Live is not offered.

[Commercial operations](docs/commercial-operations.md) covers no-code plan limits,
availability, required database setup, billing/support and personal deployment actions and their
frontend-to-backend flows.

## Application workflow

1. Research instruments, screen stocks and review existing strategy/backtest evidence.
2. Build entry, full-position exit, time and position-sizing rules. Save strategy versions.
3. Preview a backtest workload, run the historical simulation and review its results.
4. Allocate simulated capital and deploy a saved version to Paper.
5. Use the independent manual Terminal for simulated orders and positions.
6. Review closes in Journal and compare aggregate results in Reports.
7. In Private, connect your own authorized broker account and deploy a saved strategy.

Automated execution currently supports active NSE stocks through Direct routing.
Index data is for analysis, not direct index orders. Futures/options remain
coming soon; they are not enabled for strategy orders.

## Repository structure

| Directory | Responsibility |
| --- | --- |
| `backend/` | Django API, execution domain, market-data pipeline and runtime processes |
| `frontend/` | React customer site, authentication and trading workspace |
| `research_service/` | Private FastAPI provider for bounded AI research |
| `functions/` | Cloudflare Pages gateway for Public API, WebSocket and administrator access |
| `infra/development/` | Local stack and environment examples |
| `infra/public/` | Hosted Paper stack and Cloudflare/Caddy configuration |
| `infra/private/` | Personal Paper/Live stack with Docker-built React/Caddy |
| `infra/shared/` | Shared images, Redis/PostgreSQL setup and deployment/recovery scripts |
| `docs/` | Operating guides, execution reference and current business specifications |

## Deployment modes

| Mode | Scope |
| --- | --- |
| Development | Local development; usage is recorded and commercial allowances are bypassed |
| Public | Explore/Build/Pro allowances; Terminal, research, backtests and Paper; Live execution blocked |
| Private | Personal production with shared registration/UI, no commercial quotas or billing; owned broker execution |

`QUANTNEST_DEPLOYMENT_MODE` is independent of `DEBUG`. Production requires
`DEBUG=False`, configured providers, published feature states and enabled execution scopes. See
[deployment boundaries](infra/README.md) and [allowances](docs/commercial-operations.md).

## Configure and run

For a beginner walkthrough from the current repository, start with
[Your deployment checklist](infra/START-HERE.md), then follow
[Development](infra/development/SETUP.md), [Public](infra/public/SETUP.md) or
[Personal Private](infra/private/SETUP.md). The guides include tools, external
accounts, callbacks, first launch, verification and ongoing operations.

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
uses shared incremental indicators with locked Numba/NumPy dependencies. TA-Lib supplies the advertised candle
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

The market-data service owns verified history and sequenced local observations.
Persistent execution workers share numerical features and evaluate each session/instrument independently. One financial owner per account handles reservations and fills. The controller commits financial transitions and performs broker I/O outside the tick path.

Backtesting, Paper, Live and Terminal use the shared evaluator/matcher/ledger where applicable. Live fills come from cumulative broker order reports; historical OHLC fills remain explicitly approximate.

| Process | Purpose |
| --- | --- |
| Django ASGI | API, authentication, administration and browser sockets |
| market-data | Source connection, history and shared market buffers |
| execution | Persistent evaluators and account owners for Paper, Live and Terminal |
| broker-events | Live broker observations, when enabled |
| Celery background / compute / Beat | Maintenance, history, backtests, research and scheduling |
| Research FastAPI | AI provider calls and research tool orchestration |

Run `python -m execution` from backend. The `python -m quantnest_runtime execution` alias starts the same service. Market-data and broker-events retain their quantnest_runtime commands. Separate orders, terminal and outbox services are removed. See [runtime operations](docs/paper-trading.md).

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
every deploy/diagnostics/backup/restore command. The scripts need Python 3.12,
Docker/Compose and age for encrypted backups; no OCI host environment or signed
Private installer is required. Financial recovery comes from PostgreSQL commands
and account checkpoints. General Redis DB 3 provides runtime coordination; the
separate research-cache Redis is disposable.

## Reference guides

Start with the [documentation index](docs/README.md) to choose the guide for your task.

- [Complete customer and operator workflows](docs/commercial-operations.md)
- [Backtesting: complete workflow](docs/backtesting.md)
- [Paper trading: execution and operations](docs/paper-trading.md)
- [Live trading: broker orders and recovery](docs/live-trading.md)
- [Trading Terminal: manual simulation](docs/trading-terminal.md)
- [Deployment boundaries](infra/README.md)
- [Strategy configuration](docs/strategy-configuration.md)
- [Future strategy builder plan](docs/strategy-builder-plan.md)
- [Authentication and session lifecycle](docs/authentication.md)
- [Customer website](docs/customer-site.md)
- [Research service configuration](research_service/README.md)
- [Integration setup](docs/third-party-setup.md)
- [Business plan](docs/business-plan.md)
- [Implementation specification](docs/implementation-plan.md)
