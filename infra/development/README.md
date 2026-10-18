# Development: complete local setup

This is the recommended way to learn the application. It runs Django, PostgreSQL/TimescaleDB, three Redis stores, runtime/Celery services and the main React site locally. Commercial usage is recorded but subscription allowances are bypassed. Paper is enabled by default; data/AI/Live services are deliberate opt-ins.

## 1. Install the prerequisites

1. Install Git and obtain this repository.
2. On Windows install Docker Desktop with its WSL2/Linux-container backend. Start Docker Desktop; the CLI alone is insufficient. On Linux install Docker Engine and Compose v2.
3. Install Python 3.12 for the host deployment scripts. If using uv: `uv python install 3.12`.
4. Node 22.14 or later in the supported 22 line is needed only for native frontend/build work; Compose supplies Node for its Vite service.
5. Reserve enough memory for the development stack and image builds. It is not intended for a 2 GB laptop allocation.

Check tools from the repository root:

```powershell
Set-Location E:\QuantNest
docker version
docker compose version
python --version
```

Docker must report a server as well as a client. Python must be 3.12 or a supported 3.13 interpreter. The images and CI use 3.12 because pandas-ta requires Python 3.12+.

## 2. Copy local configuration

From E:\QuantNest, run once:

```powershell
Copy-Item infra/development/backend.env.example infra/development/backend.env
Copy-Item infra/development/research.env.example infra/development/research.env
Copy-Item infra/development/frontend.env.example frontend/.env
```

On Linux use `cp` instead of `Copy-Item`. Do not overwrite an existing configured frontend/.env; merge the needed values instead.

The backend example has working **local-only** Django/database/Redis/encryption values and console email. Compose supplies database/Redis hostnames, development mode, DEBUG=True and shared Channels. Do not copy this file into Public or Private.

| Input | What to do |
| --- | --- |
| Local keys/passwords | Existing values work locally; replace them if other people share this environment |
| FRONTEND_URL | Keep http://localhost:5173 for the supplied stack |
| BACKEND_URL | Keep http://localhost:8000 for direct development callbacks |
| FYERS_CLIENT_ID / FYERS_SECRET | Fill only when connecting the optional data service |
| RESEARCH_SERVICE_TOKEN | Must be identical in backend.env and research.env |
| GEMINI_API_KEY / GEMINI_MODEL in research.env | Fill only for AI; choose a model actually enabled in your project |
| EXECUTION_ENABLED_SCOPES | Keep paper unless intentionally connecting a real broker |
| BROKER_FYERS_* | Only for intentional Development Live; separate execution app from source authorization |

EMAIL_BACKEND is console: password-reset/verification mail is printed in API/worker logs, not delivered. DEFAULT_FROM_EMAIL is a local sender. For real delivery, configure the Brevo SMTP inputs described in the Public guide and change EMAIL_BACKEND to django.core.mail.backends.smtp.EmailBackend.

VITE_ settings are public browser values. QUANTNEST_API_PROXY_TARGET is Vite-server-only: Compose supplies http://api:8000. Do not set it to localhost inside the frontend container; that would address the frontend container itself.

## 3. Initialize and start the core stack

The simplest complete startup uses the shared script:

```powershell
python infra/shared/scripts/deploy.py --root . --mode development --build
```

It builds images, starts state stores, stops application services, migrates, configures the Django Site, collects admin assets and starts the core services. No source/AI account is needed for this initial startup. Updates use the same sequence without an application maintenance switch.

If an image build fails, inspect the dependency/network error. Do not switch Python back to 3.11 or install unpinned packages over the lock.

Open:

- Main customer site and workspace: http://localhost:5173
- Admin through Vite: http://localhost:5173/admin/
- Direct API diagnostics: http://localhost:8000
- PostgreSQL from a local client: localhost:54329

Customer pages and workspace are the same React app. The Vite gateway forwards API, WebSocket, admin and static paths. The database port is loopback-only; Redis remains container-only.

## 4. Create the administrator and OTP

Choose a username, then run:

```powershell
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml exec api python manage.py createsuperuser
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml exec api python manage.py enrol_staff_otp --username YOUR_ADMIN_USERNAME
```

The first command asks for account details/password. The second prints a secret otpauth URI. Import it privately into an authenticator such as Google Authenticator or Authy; its current six-digit code is the admin OTP Token. Keep the URI out of screenshots/log sharing.

Sign in with the username, password and current OTP. If a device already exists the enrolment command refuses to replace it. Use the documented recovery process rather than repeatedly creating devices.

The deployment script configures the selected Django Site automatically. For native development, or after changing the website origin, run `python manage.py configure_site` with the intended backend environment.

For Google sign-in, register the exact callback from [the provider guide](../../docs/third-party-setup.md), create a Google Social application in Admin and associate it with the configured Django Site. Google client credentials are stored in Admin, not additional unused env variables.

## 5. Add market data when ready

1. Set the data app credentials and register this exact callback with FYERS:
   http://localhost:8000/api/v1/market/fyers/callback/
2. Start a fresh authorization at http://localhost:8000/api/v1/market/fyers/login/.
3. Sign into the canonical localhost admin origin if requested, then complete the source sign-in in the same browser within ten minutes. Starting at 127.0.0.1 redirects to localhost before creating the verification cookie.
4. Source tokens are encrypted in the database. Expired access requires a new sign-in; there is no discontinued FYERS refresh-token flow.
5. Start the optional feed:

```powershell
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml --profile market-data up -d --build feed
```

Initialize supported instruments and the market calendar:

```powershell
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml exec api python manage.py sync_instruments --source NSE_CM
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml exec api python manage.py sync_market_holidays
```

For historical data start with one symbol and a bounded interval:

```powershell
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml exec api python manage.py ingest_historical --symbols NSE:SBIN-EQ --days 30 --timeframe 1m
```

Use the actual symbols/timeframes required by your strategy. Data availability/provider limits still apply in development. The optional `setup_timescale` command converts the candle table to a hypertable and enables compression; run it after migrations with application services stopped and a backup if the table contains data. PostgreSQL storage remains usable before this conversion.

Backtests require history plus indicator warmup; Paper and charts need a healthy feed and valid data. Starting containers does not fabricate prices or histories.

## 6. Add AI research

1. Put the Gemini key and a supported model in research.env.
2. Verify the shared service token matches backend.env.
3. Start the provider:

```powershell
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml --profile research up -d --build research
```

The provider is private; Django/Celery compute handles user research runs. Gemini availability/quota/billing is separate from the local software. See [research configuration](../../research_service/README.md).

For subsequent deployments preserve the selected profiles:

```powershell
python infra/shared/scripts/deploy.py --root . --mode development --build --profile market-data --profile research
```

## 7. Intentional real broker development

This is optional and sends **real** broker orders. Use your permitted development/sandbox account if available.

1. Set EXECUTION_ENABLED_SCOPES=paper,live in backend.env.
2. Configure BROKER_FYERS_CLIENT_ID and BROKER_FYERS_SECRET. Register BACKEND_URL + /api/v1/brokers/credentials/fyers/callback/ as the separate broker callback.
3. Recreate the API/runtime/background services with the reviewed deploy script and `--profile live`; add data/research profiles if used.
4. Connect the broker through the workspace and verify observations/reconciliation before deploying a strategy.

The live profile starts broker-events. Background consumes live reconciliation. Merely using this profile does not authorize a trade; customer-owned credentials/session deployment are still needed. Public mode never gains Live via this profile.

## 8. Inspect, stop and restart

```powershell
python infra/shared/scripts/diagnostics.py --root . --mode development
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml ps --all
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml logs --tail 100 api execution orders outbox compute
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml down
```

Pass matching --profile flags to diagnostics when you depend on optional services. Wait for image builds/worker warmup before interpreting initial health. Down stops/removes containers and keeps named volumes. **Down -v deletes local data**; use it only for an intentional disposable reset.

Backend/research source is baked into images, so changes require --build. Frontend source is mounted and Vite updates it. Plans, support labels and builder metadata are fetched from the backend, with no shared JSON files to regenerate. Env edits require container recreation, not just restart. Before an update stop or pause sessions in the workspace; afterward run diagnostics and inspect their saved states as explained in [the script guide](../shared/scripts/README.md).

## 9. Native development and public-mode checks

Native processes use backend/.env and research_service/.env, not Docker mode files. Follow [Python setup](../../README.md) and [runtime commands](../../docs/backend-runtime.md). Configure reachable PostgreSQL and the three Redis stores, share one local runtime directory and use Redis-backed Channels across processes. Do not run native and Compose application producers against the same execution state.

For local Public policy checks with native API/Vite, set backend/.env:

```dotenv
DEBUG=True
QUANTNEST_DEPLOYMENT_MODE=public
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:5173
ALLOWED_HOSTS=localhost,127.0.0.1
QUANTNEST_PROXY_TOKEN=YOUR_GENERATED_TOKEN_AT_LEAST_32_CHARACTERS
```

Vite reads the token server-side from backend/.env. Restart Vite/API/workers after changes. Open localhost:5173, including /admin/. Direct port 8000 is intentionally rejected in Public. Register source/Google callbacks for the gateway origin in this setup.

Public checks still enforce catalog availability, limits and Private-only Live. This does not enable real payments or grant source permission. The supplied Development Compose file stays Development.

## 10. Backups and common problems

Use the [shared script runbook](../shared/scripts/README.md) for local encrypted backups, isolated restore and previous-release recovery; use --mode development.

| Symptom | Check |
| --- | --- |
| Docker CLI works but startup cannot connect | Docker Desktop/server is running and Linux containers are selected |
| Webpage shows Network Error | API state/logs and Vite proxy target; use the same localhost origin |
| Invalid DEBUG value | Boolean True/False, not a release name |
| Empty charts/no Paper fills | Feed profile, fresh source token, symbols, market hours and data freshness |
| Backtest never starts | Compute worker and compute queue, history and warmup |
| Research unavailable | Research profile, Gemini key/model/quota and identical service token |
| Admin asks for OTP | Use the authenticator enrolled for that staff account |
| Application services remain stopped after an update failure | Read the failed migration/startup output, correct its cause and rerun the deployment |

Complete core startup, a bounded backtest, a Paper session, a Terminal order, account/OTP and selected provider workflows on your own environment before using it as a production template.
