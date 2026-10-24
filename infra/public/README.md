# Public deployment

For the full beginner procedure, follow [Public setup](SETUP.md), including
server preparation, Pages configuration and first-user acceptance.

Public runs customer research, strategy CRUD, backtests, Paper and simulated
Terminal with plan allowances. Live execution is disabled. The shared site,
registration and Support pages remain available. Custom-development enquiries are
support messages; project agreements/payments are handled outside this platform.

Architecture: Cloudflare Pages serves React, the root `functions/[[path]].js`
proxies backend paths, Caddy terminates HTTPS at the origin, and Django handles
API/WebSocket requests. All database/data/execution/Celery services run on one Linux
host. Use [shared configuration](../shared/README.md) for every service option and
[the script runbook](../shared/scripts/README.md) for operations.

## 1. Prepare the Linux host

Install Docker Engine, Compose v2, Python 3.12 and age. Keep the database on reliable
persistent disk with enough free space for database growth, image builds and backup
temporary files. Begin with the conservative concurrency values in the example;
the supplied production caps assume approximately 12 GiB RAM.

Give the host a stable address and restrict SSH to your administration access.
Expose HTTP/HTTPS (80/443) for Caddy's certificate issuance and the origin connection.
Database/Redis/AI ports remain internal. The Function token is checked by Django
even though the origin hostname is externally reachable.

Cloud resource provisioning is an operator step. Terraform, OCI-specific IAM/Vault,
metric alarms and systemd jobs are not required by these application files.

## 2. Create protected configuration

```sh
cp infra/public/backend.env.example infra/public/backend.env
cp infra/public/research.env.example infra/public/research.env
cp infra/public/frontend.env.example frontend/.env
chmod 600 infra/public/backend.env infra/public/research.env frontend/.env
```

Each copy creates the real local configuration from its tracked example. `chmod`
restricts server files to the operator. Replace every `replace-with-*` value.
The [root input table](../README.md#configuration-files) explains every key.

| Public-specific input | Configuration and reason |
| --- | --- |
| `QUANTNEST_RELEASE` | Use your reviewed tag, for example `2026-10-first-release`; backend/research images use it. |
| `FRONTEND_URL`, `BACKEND_URL` | Same browser HTTPS origin, e.g. `https://app.example.com`. Email/provider callbacks go through the gateway. |
| `PUBLIC_HOSTNAME` | `app.example.com`, without scheme. Forwarded host for the API. |
| `ORIGIN_HOSTNAME` | `origin.example.com`, separate from the Pages domain. Caddy serves this origin hostname. |
| `ALLOWED_HOSTS` | Include both hostnames, `api`, `localhost`, `127.0.0.1`. |
| `QUANTNEST_PROXY_TOKEN` | Strong server-only value shared with Cloudflare's Function. Never prefix it with `VITE_`. |
| `API_WORKERS=1`, `EXECUTION_WORKERS=1` | Initial API/execution process counts. Increase only after measuring. |
| `BILLING_ENABLED=False` | Start without payment collection. Change only after merchant settings, prices/limits and resources are reviewed. |
| Razorpay/tax fields | Configure when activating Public checkout; signed webhooks remain required for payment application. |

The ordinary database/signing/Redis/SMTP/data/AI values are also required as
explained in the root table. Generate independent random secrets. To generate the
Fernet credential key without installing backend packages on the host:

```sh
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml build
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml run --rm --no-deps api python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

The first command builds images; the second prints a newly generated key without
starting the API. Put it in `CREDENTIAL_ENCRYPTION_KEYS` and save it for recovery.

## 3. Configure DNS and HTTPS

1. Set the browser domain as your Cloudflare Pages custom domain.
2. Add a **DNS-only** A/AAAA record for `ORIGIN_HOSTNAME` pointing directly at the
   Docker host. Do not attach the Pages Function to that origin hostname.
3. Allow inbound 80/443 to the origin host. Caddy obtains and renews its normal
   publicly trusted certificate. Its named volumes preserve certificate state.
4. Point the Pages Function at `https://origin.example.com` using `BACKEND_ORIGIN`.

No manually copied Origin CA certificate, `tls/` mount or release signing key is
needed. A DNS-only origin is protected at the application boundary by the gateway
token; exposing its hostname does not bypass that token.

### Public Caddyfile, line by line

| Directive | Why |
| --- | --- |
| `{$ORIGIN_HOSTNAME} { ... }` | Hostname listener and automatic HTTPS identity. |
| `encode zstd gzip` | Compresses appropriate HTTP responses. |
| `request_body { max_size 12MB }` | Bounds incoming request bodies before the API. |
| `@internal path ...research/tools...` | Matches the AI tool route that must remain internal. |
| `respond @internal "Not found" 404` | Blocks that internal route externally. |
| `reverse_proxy api:8000` | Proxies API, admin/static and WebSocket traffic to Django; Caddy handles WebSocket upgrades. |
| `header_up X-Forwarded-Proto https` | Tells Django the browser/gateway connection uses HTTPS. |
| `header_up X-Forwarded-Host {$PUBLIC_HOSTNAME}` | Gives source OAuth the canonical browser host. |
| Security response headers | Prevents MIME guessing and limits referrer information. |

The Pages Function supplies/overwrites the proxy token and client IP before
reaching Caddy. Caddy does not invent an authenticated token for direct origin
requests. Django's middleware verifies it before trusting the client IP.

## 4. Build/deploy React on Cloudflare Pages

Use the repository root as the Pages root so `functions/[[path]].js` is included.

| Pages setting | Value and purpose |
| --- | --- |
| Build command | `npm ci --prefix frontend && npm run build --prefix frontend` installs/builds the lockfile-defined React app. |
| Build output | `frontend/dist`, containing assets, redirects, headers and route metadata. |
| Node version | 22.14+; match the reviewed frontend runtime. |
| `VITE_SITE_URL` | Browser HTTPS origin; used for canonical links/CSP/sitemap. |
| `VITE_TURNSTILE_SITE_KEY` | Public widget key matching the backend secret. |
| `BACKEND_ORIGIN` | HTTPS origin hostname, no credentials/path/query. Read by the Function only. |
| `QUANTNEST_PROXY_TOKEN` | Same strong value as backend.env, stored as a server-side Function secret. |

For a local build, the copied `frontend/.env` supplies the public values; run
`npm ci --prefix frontend` and then `npm run build --prefix frontend`. Never put
database, Django, broker, AI or merchant secrets in VITE variables.

## 5. Start and initialize the backend

```sh
python3 infra/shared/scripts/deploy.py --root . --mode public --build
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py createsuperuser
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py enrol_staff_otp --username YOUR_ADMIN_USERNAME
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py sync_market_holidays
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py sync_instruments
python3 infra/shared/scripts/diagnostics.py --root . --mode public
```

Deploy builds/checks/migrates/configures and starts the services. The next two
commands create and secure Admin. The data commands populate exchange holidays
and instruments. Diagnostics checks the running stack. Current labels, subscriptions
and limits are managed through existing catalog/Admin functionality, not env quotas.

Sign in at the website; staff data authorization starts at
`https://app.example.com/api/v1/market/fyers/login/`. Register its exact callback
`https://app.example.com/api/v1/market/fyers/callback/` with your data app.
Review the provider's connection, instrument/calendar data and chart history before
starting Paper strategies. Live cannot be enabled in Public mode.

## 6. Topology differences and routine operations

Public forces `DEBUG=False` and `EXECUTION_ENABLED_SCOPES=paper`. It has no
broker-events container and no Live Celery queue. API/ingress share `edge`; ingress
does not join the database network. Only ingress publishes 80/443. General Redis
DBs 0/1/2/3 serve broker/cache/quotes/coordination, while research data uses the
separate cache Redis. All execution containers share one host's market buffers.

Use Docker `ps`, bounded `logs` and the shared diagnostics helper. Stop application
services for encrypted backups; copy archives off-host and verify recovery in an
empty deployment. [The runbook](../shared/scripts/README.md) gives exact commands
and describes every flag. No external monitor/OCI upload/timer is installed.

Before launch check HTTPS, normal signup/email verification, password recovery,
Support replies/email notifications, authorized market data, chart history,
backtest completion and a Paper session. Keep billing off until its real provider
test and purchased plan limits/capacity are accepted.
