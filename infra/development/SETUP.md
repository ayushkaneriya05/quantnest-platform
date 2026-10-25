# Development: from this repository to a working local platform

This walkthrough is for **Windows + PowerShell**, using your current
`E:\QuantNest` repository and Docker Desktop's Linux engine. It creates a separate
local Docker database. It does not import or overwrite your existing native
PostgreSQL database or `backend/.env`.

Read [Start here](../START-HERE.md) first. Commands below run from the repository
root unless a step explicitly says otherwise.

## Step 1. Prepare your computer

You need:

| Tool | What to do | Why |
| --- | --- | --- |
| Docker Desktop | Install/open it and use Linux containers with its WSL 2 backend | Runs the application, database and Redis containers |
| Python 3.12 | Use the existing root `.venv` if it is already 3.12 | Runs deployment helpers on Windows |
| Git + your IDE | Keep your existing checkout | Review/save source changes |
| Browser + authenticator | Use your normal browser and an OTP authenticator | Website and staff Admin access |

For Docker installation/WSL requirements use
[Docker's Windows instructions](https://docs.docker.com/desktop/setup/install/windows-install/).
Reuse your current Python 3.12 `.venv`; do not replace it just to run these
standard-library scripts. On a new computer without that environment, one option
is [uv's Windows installation](https://docs.astral.sh/uv/getting-started/installation/#winget):

```powershell
winget install --id astral-sh.uv --exact
```

Reopen PowerShell after installation, then only if the root `.venv` does not exist:

```powershell
Set-Location E:\QuantNest
uv python install 3.12
uv venv --python 3.12 --seed .venv
```

This installs the selected Python and creates its environment, without installing
backend application packages on the host. See [uv Python setup](https://docs.astral.sh/uv/guides/install-python/).

In PowerShell:

```powershell
Set-Location E:\QuantNest
docker version
docker compose version
.\.venv\Scripts\python.exe --version
```

Expected: Docker shows Client and Server, Compose is available, and Python says
3.12.x. If Docker shows only Client or an engine connection error, open Docker
Desktop and wait for its Linux engine. You do not need host PostgreSQL/Redis or
Node for this Docker path; the frontend Node environment is a container too.

## Step 2. Stop the native instance that would conflict

Save your work. Stop the old native API, Celery/Beat, research, feed and execution
commands with Ctrl+C in their terminals before following this local Compose setup.
The new stack uses loopback 8000 and 5173, so an older API/Vite server can conflict.

Do not start a second native `python -m execution` alongside Compose execution.
Do not run the retired separate `orders`, `terminal`, `outbox` or calculation
services. The Docker execution supervisor owns the current combined flow.

This is a switch in how you run the code, not a command to delete your old data.
If you want to continue the native workflow instead, use the root README and do
not start this second local stack at the same time.

## Step 3. Create the three local configuration files

For the first setup only:

```powershell
Copy-Item .\infra\development\backend.env.example .\infra\development\backend.env
Copy-Item .\infra\development\frontend.env.example .\infra\development\frontend.env
Copy-Item .\infra\development\research.env.example .\infra\development\research.env
```

If these destination files already exist, **edit them instead of copying over
them**. The examples are tracked; the real files stay local.

For the first local start:

- Keep `EXECUTION_ENABLED_SCOPES=paper`.
- Keep console email so you do not need Brevo yet.
- Keep the local DB/Redis/encryption examples only on your private development
  machine. Do not reuse them for Public or Private production.
- Leave FYERS/Gemini keys blank while those profiles are disabled.
- Ensure `RESEARCH_SERVICE_TOKEN` is the same in backend and research files.
- The frontend example's `VITE_SITE_URL` is static build metadata; it does not
  change the local Vite address from `http://localhost:5173`.

All three files must exist even when the optional profiles are off. Compose needs
to resolve their file paths. You do not need to copy settings into `backend/.env`.

## Step 4. Build and start the basic platform

```powershell
.\.venv\Scripts\python.exe infra/shared/scripts/deploy.py --root . --mode development --build
```

The first build downloads images and installs the locked dependencies inside
them. It may take longer than later builds. Keep the terminal open and read any
error before retrying. Do not manually start extra processes while it builds.

The helper then starts data services, stops application services if they exist,
runs migrations/Timescale setup/Site configuration/static collection and starts
the selected stack. A migration failure leaves the applications stopped.

Check it:

```powershell
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml ps
.\.venv\Scripts\python.exe infra/shared/scripts/diagnostics.py --root . --mode development
Invoke-RestMethod http://localhost:8000/health/
```

The base stack has PostgreSQL, two Redis services, API, unified execution,
background, compute, Beat and frontend. It does not start the FYERS feed or
Gemini service yet. Diagnostics should report ready services/application/worker
checks. A passing check does not mean external data is already authorized.

Open:

- Website: `http://localhost:5173`
- Admin: `http://localhost:8000/admin/`

## Step 5. Create and secure the administrator

```powershell
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml exec api python manage.py createsuperuser
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml exec api python manage.py enrol_staff_otp --username YOUR_ADMIN_USERNAME
```

1. The first command asks for username/email/password. Password input is hidden.
2. Replace `YOUR_ADMIN_USERNAME` in the second command with that username.
3. It prints an `otpauth://` provisioning URI. Import it into your authenticator
   privately. If your app accepts a setup key rather than a URI, use the URI's
   `secret` value with time-based OTP and a descriptive account name.
4. Sign into `/admin/` using password and the current authenticator code.

The URI contains the OTP secret; do not post it in screenshots or support. Enrol
once, not on every restart. A confirmed device already existing is expected on a
repeat attempt. Keep a separate ordinary website account for feature acceptance.

## Step 6. Load instrument and calendar metadata

```powershell
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml exec api python manage.py sync_market_holidays
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml exec api python manage.py sync_instruments --source NSE_CM
```

The first command uses the current-year NSE holiday source. The second downloads
NSE cash instrument metadata; it does not place orders or download all history.
Both need outbound Internet access. Inspect their summaries for errors.

In Admin review Exchange Configurations and Market Holidays. Check the segment,
Asia/Kolkata timezone, hours and special-session overrides. Before backtesting
older years, sync the range you will use, for example:

```powershell
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml exec api python manage.py sync_market_holidays --start-year 2024 --end-year 2026
```

Adjust the years; future years are rejected. Historical coverage comes from the
installed NSE calendar library. See [initial data setup](../shared/INTEGRATIONS.md#11-initial-platform-data-and-ordinary-user-acceptance).

## Step 7. Add the market-data connection

1. Follow [FYERS data setup](../shared/INTEGRATIONS.md#6-fyers-shared-market-data-connection).
2. Put the data App ID/Secret in Development's `backend.env`.
3. Register `http://localhost:8000/api/v1/market/fyers/callback/` where FYERS
   accepts local callbacks; use an approved reachable HTTPS origin otherwise.
4. Start the profile:

   ```powershell
   .\.venv\Scripts\python.exe infra/shared/scripts/deploy.py --root . --mode development --build --profile market-data
   ```

5. Sign into Admin at localhost:8000 and open
   `http://localhost:8000/api/v1/market/fyers/login/` in the same browser.
6. Complete FYERS authorization. Keep using `localhost`, rather than switching
   between localhost and 127.0.0.1 during the callback flow.
7. In the website, search/add a stock and load its chart. Request older history.
   During its exchange session, check that live prices/candles update.

History is acquired on demand. An empty database cannot display an instrument's
history until an authorized provider fetch succeeds. If the market is closed,
do not expect new live ticks simply because the feed is connected.

## Step 8. Add AI research when ready

Follow [Gemini setup](../shared/INTEGRATIONS.md#5-gemini-ai-research): set the key,
an available supported model and matching internal tokens. Then:

```powershell
.\.venv\Scripts\python.exe infra/shared/scripts/deploy.py --root . --mode development --build --profile market-data --profile research
.\.venv\Scripts\python.exe infra/shared/scripts/diagnostics.py --root . --mode development --profile market-data --profile research
```

Pass every profile you want each time. Omitting a previous profile from the deploy
command disables that optional service. The supported research jobs use the
`compute` worker already in Compose; do not start a separate research Celery queue.

When upgrading an existing research installation, follow the
[AI Research rollout steps](../../docs/ai-research.md#deployment-and-verification).
The backend and research service must use the same release. Development records
actual token usage without enforcing the period credit allowance.

Google login can now be configured through
[its optional Admin setup](../shared/INTEGRATIONS.md#8-google-sign-in-optional-backend-client).
Brevo and Turnstile can remain deferred for local console-mail/DEBUG development.

## Step 9. Accept the ordinary user flow

Register at localhost:5173 and follow
[the platform checklist](../shared/INTEGRATIONS.md#11-initial-platform-data-and-ordinary-user-acceptance).
Complete at least:

- [ ] Load/search a tradable stock and its historical/live chart.
- [ ] Review the default QuantNest charge profile.
- [ ] Save a strategy with entry/full-exit/sizing/time rules and a version.
- [ ] Preview/run a small backtest and inspect recorded results/charges.
- [ ] Add simulated Paper wallet funds and deploy from the strategy list.
- [ ] Inspect session state, rule outcomes and an intentional simulated fill/exit.
- [ ] Use Terminal's separate account/watchlist/order/history flow.
- [ ] Try a screener and, if enabled, a completed AI response.
- [ ] Create a Support ticket and verify its Admin reply.

Development records usage but does not enforce Public plan ceilings. Therefore
this is not a substitute for checking Public allowances on a Public deployment.
If a strategy has no valid signal, a correctly running session can take no trade.

## Step 10. Optional intentional Live development

Leave this off while learning the simulation path. It can submit real orders.
When you deliberately want your own broker integration:

1. Set `EXECUTION_ENABLED_SCOPES=paper,live` in Development's backend file.
2. Follow [personal broker setup](../shared/INTEGRATIONS.md#9-personal-fyers-trading-private-or-intentional-live-development).
3. Include both the scope change and `live` profile:

   ```powershell
   .\.venv\Scripts\python.exe infra/shared/scripts/deploy.py --root . --mode development --build --profile market-data --profile research --profile live
   ```

The deploy script rejects a scope/profile mismatch. The data app is still needed;
the trading app entered in Broker Integration does not replace it. For leaving
Live development, first settle/review active work, return scopes to `paper`, and
deploy without `--profile live`.

## Step 11. Daily use and troubleshooting

```powershell
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml logs --tail=100 api
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml logs --tail=100 execution
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml --profile market-data logs --tail=100 feed
```

| Problem | First action |
| --- | --- |
| Docker engine unavailable | Open Docker Desktop and check Linux containers/WSL |
| Port 8000/5173 already used | Stop the old API/Vite terminal before retrying |
| Missing env file | Create all three mode-local files from examples |
| Research key/token error | Configure it, or omit `research` for now |
| Empty instrument search | Check metadata sync and selected filters |
| No historical candles | Check data login, symbol and provider error in logs |
| No live fills | Check market session, feed observations, saved rules, capital and execution logs |
| Email absent from inbox | Console email is intentional; inspect logs |
| Backend edit has no effect | Rebuild/recreate via deploy; backend source is baked into the image |
| React edit has no effect | Check Vite/frontend logs; React source is mounted for development |

To stop the entire local stack while retaining data:

```powershell
docker compose --env-file infra/development/backend.env -f infra/development/compose.yaml --profile "*" stop
```

Use the same reviewed deploy command/profiles to start it again. Do not add `-v`
to a `down` command unless deliberately destroying this local database.
For backups and upgrades, follow [the operations runbook](../shared/scripts/README.md).
For first-time backup key/copy setup, use [Recovery setup](../shared/RECOVERY-SETUP.md).
