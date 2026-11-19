# Development deployment

For the beginner Windows procedure, follow [Development setup](SETUP.md).
This README explains the configuration behind those steps.

This mode runs the same API, data layer and execution engine locally. It records
usage without enforcing Public plan quotas. It defaults to Paper/simulated Terminal.
Provider feed, AI research and real broker events are optional profiles.

From the repository root on Windows, the normal command is:

```powershell
.\.venv\Scripts\python.exe infra/development/dev.py
```

It creates missing `backend.env`, `research.env` and `frontend.env`, reuses local
FYERS/Gemini settings, builds images, initializes the database and starts the
configured services. Existing env files are preserved. A populated local native
database is **not** imported automatically. The Docker database has separate
credentials and volumes. No real order or provider sign-in is performed by setup.

API/AI Python changes reload automatically; React uses Vite hot updates. Feed,
execution and Celery processes need a restart after their Python code changes:
rerun the command with `--no-build`. Changes to either dependency lockfile need
the default command, which rebuilds the images.

```powershell
.\.venv\Scripts\python.exe infra/development/dev.py status
.\.venv\Scripts\python.exe infra/development/dev.py logs
.\.venv\Scripts\python.exe infra/development/dev.py stop
```

Stop retains the database and all named volumes. The helper resolves the repo
root from its own location. No host backend/Node packages are needed.

This is a local environment. Oracle-hosted production uses
[Public](../public/SETUP.md) or [Private](../private/SETUP.md) after
[Oracle server preparation](../shared/SERVER-SETUP.md), with separate data and
native images for that server's architecture.

Read [shared components](../shared/README.md) for the meaning of every Compose field,
service command, Redis database, volume and memory policy. Read
[the script runbook](../shared/scripts/README.md) for deploy/backup/restore flags.

## 1. Create the files

The launcher creates these files if absent. To prepare them without Docker:

```sh
python3 infra/development/dev.py --prepare-only
```

It copies configured FYERS and SMTP inputs from `backend/.env` and AI inputs from
`research_service/.env`, while keeping console email and Paper execution as
defaults. SMTP credentials are available for an intentional email-backend change.
It preserves the native credential-encryption key (including Development's
SECRET_KEY-derived key), so a separately imported database remains decryptable.
It does not copy native database/Redis addresses, production mode, or Live scopes.
After first setup, edit the mode-local files; native env changes are not silently
copied over your Docker settings on every launch.

For explicit manual configuration instead, from the repository root:

```sh
cp infra/development/backend.env.example infra/development/backend.env
cp infra/development/research.env.example infra/development/research.env
cp infra/development/frontend.env.example infra/development/frontend.env
```

In PowerShell, use `Copy-Item` instead of `cp` if desired and use `python` instead
of `python3` for subsequent host script commands. Start Docker Desktop's Linux
engine first. These three files must exist even when the AI profile is off because
Compose reads service env-file paths while resolving the project.

### Each backend.env input

| Line/key | Meaning and action |
| --- | --- |
| `SECRET_KEY` | Generated for Docker so its login/signing identity is separate from the native app. The example value is not for production. |
| `CREDENTIAL_ENCRYPTION_KEYS` | The launcher preserves the local encryption identity; the example contains only a sample key. Retain the real key with any copied data. |
| `POSTGRES_ADMIN_PASSWORD` | Generated local bootstrap database password. |
| `DB_NAME` | Separate Development database name. |
| `DB_USER`, `DB_PASSWORD` | Restricted local Django database role, created by the initializer. |
| `REDIS_PASSWORD` | Hexadecimal local Redis password, used for both Redis services. |
| `FRONTEND_URL=http://localhost:5173` | Browser origin for CORS, emails and Vite. |
| `BACKEND_URL=http://localhost:8000` | Direct local callback origin. The API's loopback port is published for this development setup. |
| `ALLOWED_HOSTS` | Allows browser, loopback and internal API hostname. |
| `EMAIL_BACKEND` | Prints account/support email to service logs rather than sending it. |
| `DEFAULT_FROM_EMAIL` | Sender shown in those local messages. |
| `RESEARCH_SERVICE_TOKEN` | Must match research.env when AI is enabled. |
| `FYERS_CLIENT_ID`, `FYERS_SECRET` | Leave empty until enabling the market-data profile; then enter the data app credentials. |
| `EXECUTION_ENABLED_SCOPES=paper` | Default simulated scopes. Use `paper,live` only for intentional personal broker integration development. |
| `EXECUTION_WORKERS=1` | Initial persistent evaluation-worker count. |
| `BILLING_ENABLED=False` | Checkout stays off until deliberately configured. |

`research.env` contains the matching token, `GEMINI_API_KEY` and `RESEARCH_MODEL`.
Leave the API key blank while AI is disabled. `frontend.env` contains
`QUANTNEST_API_PROXY_TARGET`, `VITE_SITE_URL` and `VITE_TURNSTILE_SITE_KEY`.
Compose overrides the proxy target to `http://api:8000`, and Vite reads that
process environment. `VITE_SITE_URL` is an HTTPS canonical URL for static build
metadata, not the local development server address. The widget key may stay empty
for local development because the backend bypasses anonymous-form verification in
Development with DEBUG true.

Vite forwards WebSocket upgrades and HTTP rejection responses, so expired sessions
and denied origins fail promptly. WebSocket transport is installed in the backend
image; after dependency changes, run `dev.py` without `--no-build`.

## 2. Start the base stack

```sh
python3 infra/shared/scripts/deploy.py --root . --mode development --build
python3 infra/shared/scripts/diagnostics.py --root . --mode development
```

The first command builds images, waits for data services, stops application
services, migrates, configures Timescale/Site/static assets and starts the stack.
The second checks effective configuration, running services, execution workers
and both Celery workers' actual queue subscriptions.
Open `http://localhost:5173` for React. `http://localhost:8000/admin/` is the local
backend Admin. PostgreSQL is available only on `127.0.0.1:54329` for host tooling.
Neither Redis nor research has a host port.

Base services are PostgreSQL, general Redis, research-cache Redis, API, execution,
background, compute, Beat and Vite. The launcher additionally enables `market-data`
when both FYERS settings are present, and `research` when its Gemini key is present.
These services do not issue an AI request or perform FYERS sign-in at startup.
Charts/execution still require authorized data and the appropriate market session.

## 3. Create the administrator and prepare data

```sh
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml exec api python manage.py createsuperuser
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml exec api python manage.py enrol_staff_otp --username YOUR_ADMIN_USERNAME
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml exec api python manage.py sync_market_holidays
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml exec api python manage.py sync_instruments
```

`createsuperuser` creates a staff login; `enrol_staff_otp` provides its authenticator
setup. Keep that provisioning URI private. Holiday synchronization uses the current
NSE API and the configured exchange/segment calendars. Instrument sync loads the
provider master. Initial history is acquired on demand by charts/backtests/research;
execution prepares the history its saved strategy requires.

## 4. Enable live market data or AI

```sh
python3 infra/shared/scripts/deploy.py --root . --mode development --build --profile market-data
```

After entering FYERS data credentials, use the staff data login flow at
`http://localhost:8000/api/v1/market/fyers/login/`. Register the exact callback
`http://localhost:8000/api/v1/market/fyers/callback/` with that data app. The feed
then subscribes only to current browser/execution demand.

To add AI, configure the Gemini key/model and matching research token, then run:

```sh
python3 infra/shared/scripts/deploy.py --root . --mode development --build --profile market-data --profile research
python3 infra/shared/scripts/diagnostics.py --root . --mode development --profile market-data --profile research
```

These shared `deploy.py` commands select profiles explicitly. The simpler
`dev.py` launcher selects them from your local settings each time. Both stop
services from previously enabled profiles that the new configuration omits.

## 5. Intentional Live development

Set `EXECUTION_ENABLED_SCOPES=paper,live`, then:

```sh
python3 infra/shared/scripts/deploy.py --root . --mode development --build --profile market-data --profile live
```

This starts broker-events and permits real broker access. Enter the user's trading
app credentials in Broker Integration, separately from the shared market-data app.
Register `http://localhost:8000/api/v1/brokers/credentials/fyers/callback/` for that
local trading app where the broker permits it. No test order is placed by deployment.

## 6. Understand the Development additions

| Compose addition | Why |
| --- | --- |
| `profiles: [market-data]` / `[research]` / `[live]` | Allows coding and migration work before external providers are configured. |
| API loopback 8000, Vite loopback 5173 | Local-only browser/API access. |
| PostgreSQL loopback 54329 | Host DB tools without publishing a database to the LAN. |
| Development-only `database-tools` bridge | Makes the loopback port reachable on Docker Desktop. The internal-only network did not expose the configured host port in verification; production databases keep only their internal network. |
| `frontend-node-modules` | Linux dependency cache separate from host node_modules. |
| `../../frontend:/workspace` | React edits are visible to Vite immediately; polling supports Windows/WSL bind mounts. |
| `../../backend:/opt/quantnest/backend` | Python source is available to every backend process without rebuilding. |
| Empty `container.env.example` mounted over the native `.env` | Prevents fallback to native settings. Real settings arrive through Compose's env_file; the private host file need not be readable by the container user. |
| `logs` named volume | Keeps rotated development logs writable by the container user, including on Linux hosts. |
| API and research `--reload` | Reload those HTTP processes after Python edits. |
| Frontend healthcheck | Deployment waits for Vite and its initial dependency install instead of reporting ready while it is still booting. |
| `npm ci && npm run dev -- --host 0.0.0.0` | Installs the lockfile and listens inside the container; only the loopback host port is exposed. |
| Background queues `default,live,marketdata` | Handles optional Live reconciliation without an extra Celery service. |

Dependency packages are baked into images; backend/research source is mounted.
Reload does not restart feed, execution or Celery workers automatically. Use
`dev.py --no-build` to restart them cleanly, or the normal command after dependency
changes. Do not also run native feed/execution against the same database and
buffer directory. For a native workflow, use the
root [README](../../README.md) instead of starting this Compose execution service.

For backup/restore, use the shared runbook with `--mode development`. Stop selected
application profiles first and preserve volumes. Real provider access and email
delivery are separate from a successful local health check.
