# Private: personal production deployment

For the full beginner procedure, follow [Personal Private setup](SETUP.md),
including host/tools, data authorization and your separate trading connection.

This mode runs the QuantNest operator's own isolated production instance. It uses
the same frontend, signup/login, CRUD, data layer and execution engine as Public.
Paper and Live access follows enabled scopes; Terminal remains simulated. There
are no commercial quotas, licence activation, renewal or checkout in this mode.
Customer Private hosting is not currently offered.

One Linux host runs Caddy, API, the market-data feed, unified execution, broker
events, Celery/Beat, research and data services. This is not a separate execution
implementation. See [shared components](../shared/README.md) for every Compose
field/command and [the runbook](../shared/scripts/README.md) for maintenance.

## 1. Host and files

Install Docker/Compose v2, Python 3.12 and age. Use your own domain, stable host
address, persistent storage and independently generated secrets. Configure the
broker account's applicable app/static-IP access for this host. Keep SSH restricted
and allow 80/443 for HTTPS. Database, Redis and research ports stay private.

```sh
cp infra/private/backend.env.example infra/private/backend.env
cp infra/private/research.env.example infra/private/research.env
chmod 600 infra/private/backend.env infra/private/research.env
```

Each copy creates this deployment's protected settings. Replace every placeholder;
do not copy Public's database credentials or encryption keys into a personal host.

### Each group of settings

| Input | Meaning and action |
| --- | --- |
| `QUANTNEST_RELEASE` | Reviewed tag for backend, research and frontend images. |
| `SECRET_KEY` | Unique Django signing key. |
| `CREDENTIAL_ENCRYPTION_KEYS` | Unique Fernet credential key; retain for encrypted broker-data recovery. |
| `POSTGRES_ADMIN_PASSWORD` | Bootstrap administrator password. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Personal application database and restricted role. |
| `REDIS_PASSWORD` | Hexadecimal Redis password used in generated internal URLs. |
| `QUANTNEST_PROXY_TOKEN` | Random token Caddy injects when forwarding API/WebSocket requests. |
| `FRONTEND_URL`, `BACKEND_URL` | Same HTTPS browser origin, e.g. `https://personal.example.com`. |
| `PUBLIC_HOSTNAME` | That hostname without scheme/path; selects Caddy's HTTPS site. |
| `ALLOWED_HOSTS` | Personal host plus `api`, `localhost`, `127.0.0.1`. |
| SMTP login/key/sender | Outgoing account and support emails. Host/port/TLS use backend defaults. |
| `FYERS_CLIENT_ID`, `FYERS_SECRET` | Market-data app, separate from each user's trading app. |
| `RESEARCH_SERVICE_TOKEN` | Match the value in research.env. |
| `TURNSTILE_SECRET_KEY` | Anonymous enquiry verification secret. |
| `VITE_TURNSTILE_SITE_KEY` | Matching public widget key, passed only to the frontend image build. |
| `API_WORKERS=1` | Initial API process count. |
| `EXECUTION_WORKERS=1` | Initial persistent execution CPU worker count. |
| research.env token/key/model | Shared authentication and Gemini credentials, consumed by the internal research service. |

Compose owns `QUANTNEST_DEPLOYMENT_MODE=private`, `DEBUG=False`, scopes `paper,live`,
disabled billing, container URLs and the shared runtime path. The frontend's
canonical URL comes from `FRONTEND_URL`; there is no separate Private frontend.env
or host `frontend/dist` deployment step.

## 2. Build and generate the credential key

```sh
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml build
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml run --rm --no-deps api python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

The build creates backend, research and React/Caddy images. The one-shot command
prints a Fernet key without starting API/execution; put it in backend.env and retain
it securely. Other secrets can be generated with the commands in [the root guide](../README.md).

## 3. DNS and deployment

Point the personal hostname's A/AAAA record directly at this host and allow ports
80/443. The supplied Caddy configuration assumes direct browser ingress; use a
DNS-only record if managing DNS through Cloudflare. Adding another proxy requires
reviewing trusted client-IP handling rather than trusting arbitrary headers.

```sh
python3 infra/shared/scripts/deploy.py --root . --mode private --build
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py createsuperuser
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py enrol_staff_otp --username YOUR_ADMIN_USERNAME
python3 infra/shared/scripts/diagnostics.py --root . --mode private
```

Deploy performs stopped-service migrations, Timescale/Site/static setup, then
startup. Caddy obtains and renews HTTPS certificates, persisted in its volumes.
Create Admin and enrol its authenticator. Use a normal non-staff account for routine
trading via `/register`; no local account provisioning or licence token is required.

### Private ingress configuration, line by line

| Directive | What it does and why |
| --- | --- |
| `{$PUBLIC_HOSTNAME}` | Personal domain listener and HTTPS certificate identity. |
| `import /srv/site/security.caddy` | CSP generated from this exact frontend build/public origin. |
| `import /srv/site/routes.caddy` | Known React routes used for direct links and page refreshes. |
| `encode zstd gzip` | Compresses suitable responses. |
| `request_body max_size 12MB` | Bounds incoming request size. |
| `@internal` + `respond ... 404` | Hides internal research-tool routes from the browser Internet path. |
| `@backend path ...` | Routes API, WebSocket, admin/static and health URLs to Django. |
| `reverse_proxy api:8000` | Forwards those requests and WebSocket upgrades to the ASGI server. |
| `X-QuantNest-Proxy-Token` | Authenticates this gateway's client-IP/protocol headers. |
| `X-QuantNest-Client-IP {http.request.remote.host}` | Supplies the actual directly connected browser address. |
| `X-Forwarded-Proto https`, `X-Forwarded-Host` | Provides the browser scheme/host for Django and OAuth. |
| `handle @frontend` + `rewrite /index.html` | Serves the React shell for recognized application routes. |
| Final `handle` + `file_server` | Serves built assets directly. |
| `handle_errors 404` | Serves the generated 404 shell while preserving missing-path handling. |
| Security headers | Prevent MIME guessing and limit referrer information. |

The final frontend image contains only Caddy/assets. Docker receives only the two
public frontend build arguments; Django, broker and Gemini secrets are runtime
settings for their respective server containers.

## 4. Prepare data and personal broker access

```sh
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py sync_market_holidays
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py sync_instruments
```

Review the exchange/segment calendars in Admin. Authorize the shared market-data
source through `/api/v1/market/fyers/login/`. Its registered callback is
`https://personal.example.com/api/v1/market/fyers/callback/`.

Enter the user's individual trading App ID/Secret through Broker Integration. Its
separate callback is
`https://personal.example.com/api/v1/brokers/credentials/fyers/callback/`.
Broker credentials are encrypted in this instance's database. Broker-events ingests
order updates; the unified execution controller performs broker I/O and financial
persistence outside tick evaluation.

Configure charge assumptions, create/save a strategy version, check backtests and
Paper before intentional Live use. Deployment and diagnostics do not place real
orders. Initial history is acquired through the common data layer as needed.

## 5. Operate and update

Keep one execution launcher and one Beat per deployment. The account/session and
instrument workers share the same runtime directory. Increase `EXECUTION_WORKERS`
only after checking CPU, memory and actual evaluation/persistence latency; no
application container count change is needed.

Use the [shared backup/restore instructions](../shared/scripts/README.md). They
work for Private with `--mode private`, without signed customer artifacts, central
licensing, OCI keys or a special installer. Stop applications including broker-events
before backup/upgrade. After recovery review actual broker orders before enabling
trading, because a database backup is not a snapshot of the broker's external state.

For an older licensing-era database, complete its retirement migration on the
previous release before using this one. Preserve database/media volumes, environments
and encryption keys across ordinary upgrades. Never use `down -v` for an update.
