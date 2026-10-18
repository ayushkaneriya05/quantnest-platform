# Public: QuantNest hosted deployment

This guide deploys the hosted customer product on your Oracle A1 **2 OCPUs / 12 GB** VM, with the main React site/workspace on Cloudflare Pages. Public offers approved research, backtests, Terminal and Paper simulation. Live execution is blocked, including if someone changes a browser plan label.

Read [the infrastructure overview](../README.md) first. Provider console details are in [THIRD_PARTY_SETUP](../../docs/third-party-setup.md).

## 1. Prepare accounts and the release

You need:

- an OCI tenancy/home region with accepted capacity and free allowance;
- Ubuntu 24.04 ARM64, SSH key access and a verified data-volume mount;
- a reviewed copy of this repository/release;
- your owned domain, Cloudflare DNS/Pages and origin certificate;
- Brevo SMTP sender/login/key for account email;
- permitted source access with a registered FYERS data app;
- Gemini key/model for the included research provider;
- an offline age recovery identity and its public recipient.

The planned domain is quantnest.site. Until you own it, substitute an actual owned domain consistently; example domain text does not create DNS or certificates.

Use [the Oracle guide](oracle/README.md) to provision/import infrastructure. It creates a 2/12 host, 50 GB boot volume and 150 GB data volume; verify actual quota and resource costs before applying. It does not deploy software or format the attached disk.

On the VM compare the attachment output with `lsblk -f`. Mount the verified data filesystem at /mnt/quantnest-data, persist its UUID in /etc/fstab and verify:

```sh
uname -m
python3 --version
mountpoint /mnt/quantnest-data
df -h /mnt/quantnest-data
```

Expected: aarch64, Python 3.12 and a mounted data filesystem. Do not format an unverified device.

Put a reviewed release at /opt/quantnest/releases/YOUR_RELEASE, and create /opt/quantnest/current as a symlink to it **for the first installation**. Use your repository URL and actual release identifier:

```sh
sudo mkdir -p /opt/quantnest/releases
sudo apt-get update
sudo apt-get install -y git
sudo git clone YOUR_REPOSITORY_URL /opt/quantnest/releases/YOUR_RELEASE
sudo ln -s /opt/quantnest/releases/YOUR_RELEASE /opt/quantnest/current
cd /opt/quantnest/current
```

If current already exists, follow the upgrade section; do not replace it during an active deployment.

## 2. Bootstrap the host once

From the release root:

```sh
sudo bash infra/public/scripts/bootstrap_host.sh /mnt/quantnest-data /opt/quantnest/current
sudo chown -R quantnest:quantnest /opt/quantnest/releases/YOUR_RELEASE
```

The script requires Ubuntu 24.04 and a fresh Docker host. It installs Docker/Compose, age and a locked Python operations environment at /opt/quantnest/operations; sets Docker's data root to the mounted volume; creates the quantnest operator; and installs host timer/service definitions. It does not migrate an existing Docker directory or start application/backup/monitor timers.

The quantnest user is a non-login service account. Use sudo -u quantnest for operator commands. Docker group access has root-level host power; limit this account's access accordingly.

See [host script details](scripts/README.md). The operations interpreter is for host scripts; application dependencies stay inside Docker images.

## 3. Configure protected environment files

```sh
sudo -u quantnest cp infra/public/backend.env.example infra/public/backend.env
sudo -u quantnest cp infra/public/research.env.example infra/public/research.env
sudo chmod 600 infra/public/backend.env infra/public/research.env
sudoedit infra/public/backend.env
sudoedit infra/public/research.env
```

Use an editor to replace all required values. Do not echo a real file into a terminal/log.

Generate independent URL-safe values locally with Python's secrets module. For the Fernet key use the operations interpreter:

```sh
/opt/quantnest/operations/bin/python -c "import secrets; print(secrets.token_urlsafe(64))"
/opt/quantnest/operations/bin/python -c "import secrets; print(secrets.token_hex(32))"
/opt/quantnest/operations/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Treat the printed values as secrets and copy them privately. Generate different values for separate purposes.

| Group | Required inputs and meaning |
| --- | --- |
| Release and protection | QUANTNEST_RELEASE identifies the deployed reviewed release; SECRET_KEY is 50+ random characters; CREDENTIAL_ENCRYPTION_KEYS contains the Fernet key |
| Database | DB_NAME/DB_USER are your application database/role; DB_PASSWORD differs from POSTGRES_ADMIN_PASSWORD |
| Redis | REDIS_PASSWORD is the generated hex value, with no redis:// prefix |
| Website | FRONTEND_URL and BACKEND_URL are the browser HTTPS origin; PUBLIC_HOSTNAME is its hostname; ORIGIN_HOSTNAME is origin.<your-domain>; ALLOWED_HOSTS includes browser/origin/internal api host |
| Trusted gateway | QUANTNEST_PROXY_TOKEN is 32+ random characters and must match the Cloudflare Function secret |
| Email | EMAIL_HOST_USER is the Brevo SMTP login; EMAIL_HOST_PASSWORD is the SMTP key; DEFAULT_FROM_EMAIL is a verified sender. Defaults are smtp-relay.brevo.com:587 with STARTTLS |
| Source | FYERS_CLIENT_ID/SECRET are the data app; the callback defaults to BACKEND_URL + /api/v1/market/fyers/callback/ |
| Research | RESEARCH_SERVICE_TOKEN matches research.env; research.env also needs GEMINI_API_KEY and a project-supported GEMINI_MODEL |
| Public forms | TURNSTILE_SECRET_KEY matches VITE_TURNSTILE_SITE_KEY; the allowed hostname derives from FRONTEND_URL |
| Checkout | BILLING_ENABLED stays False until merchant approval/capacity. Razorpay keys/webhook verification and correct tax fields are required when enabling it |
| Private issuance | OCI_LICENSE_KEY_ID, OCI_LICENSE_KEY_VERSION and OCI_SIGNING_ENDPOINT only when this central host issues Private contracts; separate release-signing values go in operations.env |
| Optional integrations | Brevo API/DOI fields enable newsletter confirmation; inbound fields enable email replies. SMTP alone covers account and workspace support mail |
| Resource inputs | API/execution/calculation/order worker counts and actor admission; keep conservative defaults initially |

Legal name/support address/hours and 90-day customer-content retention have application defaults. Add their documented settings only to override them. The example omits internal DB/Redis URLs, mode/debug/scope, numeric library threads and default topology because Compose/application owns them.

Keep backend.env and research.env readable only by the deployment operator (mode 600). OCI Vault is used for licence/release signing; application environment files are managed directly.

## 4. Configure DNS and origin TLS

1. Add the Public website as the Cloudflare Pages custom domain.
2. Create a **proxied** Cloudflare A record for origin.<your-domain> pointing to the reserved Oracle IP. The Function fetches this hostname; a Cloudflare Origin CA certificate is not a general browser-trusted certificate.
3. Use Cloudflare SSL/TLS Full (strict).
4. Create an origin certificate covering the exact origin hostname.
5. Place the certificate and key at infra/public/tls/origin.pem and origin-key.pem:

```sh
sudo -u quantnest mkdir -p infra/public/tls
sudo chmod 700 infra/public/tls
sudoedit infra/public/tls/origin.pem
sudoedit infra/public/tls/origin-key.pem
sudo chown quantnest:quantnest infra/public/tls/origin.pem infra/public/tls/origin-key.pem
sudo chmod 600 infra/public/tls/origin.pem infra/public/tls/origin-key.pem
```

Paste the real certificate/key into the respective protected files with the editor, or transfer them through your accepted secret channel. Keep the directory and files owned by the deployment operator so preflight can inspect their existence. Caddy's container starts as root and can read the bind mount; other host users cannot read the key. The operator's Docker access already has host administrative power.

6. OCI security rules allow 443 only from the reviewed Cloudflare IPv4 ranges and 22 from your administrator CIDR. Check the Linux firewall consistently. PostgreSQL/Redis/research have no published production ports.
7. Do not configure the main website's Pages Function on the origin hostname; otherwise the origin request could recurse through the same gateway.

Caddy here is an API origin, not the static frontend host. It preserves the verified ingress token and forwards browser protocol/host metadata. /api/v1/research/tools remains blocked at external ingress.

## 5. Build/deploy the main React frontend

In Cloudflare Pages connect the repository with:

| Setting | Value |
| --- | --- |
| Root directory | Repository root, not frontend/ |
| Build command | npm ci --prefix frontend && npm run build --prefix frontend |
| Output directory | frontend/dist |
| Node version | 22.14.0 or the qualified Node 22 version |
| Public build values | The VITE_ values in frontend.env.example, with your actual domain/site key |
| Function secrets | BACKEND_ORIGIN=https://origin.<your-domain> and matching QUANTNEST_PROXY_TOKEN |

Keeping the root at repository level makes functions/ available. Cloudflare's scoped Function handles backend paths; generated _routes.json keeps static assets outside it. The build also generates route rewrites, CSP headers, sitemap and fonts/assets. Plans and support labels load from the backend at runtime; no metadata export or backend connection is needed to build.

Do not put BACKEND_ORIGIN or the proxy token into VITE_ variables. Never put Razorpay secret, SMTP/Gemini keys or licence activation tokens into a frontend build.

A preview deployment must use isolated backend/configuration if you want to sign in there. The production application accepts its configured origin/callbacks; it is not an unrestricted API for every *.pages.dev URL.

For local inspection you can copy frontend.env.example to frontend/.env and build with Node; deploy production through Pages with the root Function included. Do not upload dist with a mechanism that omits Functions.

## 6. Deploy backend services

From /opt/quantnest/current:

```sh
sudo -u quantnest docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml config --quiet
sudo -u quantnest /opt/quantnest/operations/bin/python infra/shared/scripts/deploy.py --root . --mode public --build
sudo -u quantnest /opt/quantnest/operations/bin/python infra/shared/scripts/diagnostics.py --root . --mode public
```

Deployment performs mode checks, stops application services, runs migrations, configures the Site and collects static assets before startup. A failure leaves you with the reported state; do not repeatedly run upgrades without reading the failure. Read [the shared script sequence](../shared/scripts/README.md).

Expected services: postgres, redis, redis-runtime, redis-cache, api, feed, execution, orders, terminal, outbox, background, compute, beat, research and ingress. Public has **no broker-events service or Live queue**.

## 7. Create Operations Admin

```sh
sudo -u quantnest docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py createsuperuser
sudo -u quantnest docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py enrol_staff_otp --username YOUR_ADMIN_USERNAME
```

Import the printed secret otpauth URI into your authenticator privately. Sign in at https://<your-domain>/admin/ with username/password and its current six-digit OTP. Do not use the origin IP/hostname for browser login: Public requires the trusted gateway.

The configured Django Site is automatically created from FRONTEND_URL. Associate the Google Social application with this Site after registering the exact browser callback; see the provider guide.

## 8. Feature availability and source/history initialization

Publish reviewed prices and numeric plan limits in Commercial → Catalog revisions. Zero prevents new consumption of that allowance; saved results remain available. Keep EXECUTION_ENABLED_SCOPES=paper. Configure the source and AI service for the workflows you open; keep BILLING_ENABLED=False until merchant setup and capacity are ready. Maintain provider agreements in your operating records. No purpose-specific approval rows need insertion.

Authorize the source at:
https://<your-domain>/api/v1/market/fyers/login/

The registered callback is:
https://<your-domain>/api/v1/market/fyers/callback/

Use an active staff account on that browser origin. Complete the fresh flow in the same browser within ten minutes. Source access tokens are encrypted and need a new authorization after expiry; no FYERS refresh-token flow is deployed.

Then initialize supported data:

```sh
sudo -u quantnest docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py sync_instruments --source NSE_CM
sudo -u quantnest docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py sync_market_holidays
sudo -u quantnest docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py ingest_historical --symbols NSE:SBIN-EQ --days 30 --timeframe 1m
```

Choose the required symbol/timeframe/history including warmup; do not request all exchanges as a first ingestion. Market-hour and source-freshness requirements remain.

Optional hypertable/compression setup uses `python manage.py setup_timescale` after migrations; run with application services stopped and a backup if candle data exists. It is not required to make the initial application database usable.

## 9. Capacity and commercial launch

| Input | Starting value |
| --- | ---: |
| API_WORKERS / EXECUTION_WORKERS / CALCULATION_WORKERS | 1 / 1 / 1 |
| ORDER_WORKERS / ORDER_CONCURRENCY | 1 / 2 |
| CALCULATION_CACHE_MB | 32 |
| EXECUTION_MAX_ACTORS / EXECUTION_MAX_USER_ACTORS | 8 / 4 |
| Default node count/index | 1 / 0 |
| Default execution shards/order partitions | 64 / 16 |

One compute worker handles one heavy job at a time and is capped at 0.75 CPU. One background worker and Beat handle periodic work. Numerical library threads are one. Memory ceilings total 9.5 GiB, leaving 2.5 GiB on the 12 GB profile for host/build/Redis overhead.

Four actors per user is below Build's five and Pro's twenty Paper instruments. Checkout for a plan exceeding admission is withheld by the backend. Keep BILLING_ENABLED=False until resources, merchant setup, webhook acceptance and pricing/tax mappings are ready. Do not raise actor limits without measuring the host.

Enter provider price mappings and provider webhook settings through the existing billing/Operations flows in THIRD_PARTY_SETUP. Validate a real provider test transaction before enabling production payments. The workspace's usage meter does not itself charge a card.

## 10. Configure backup and monitoring

Follow [the host script guide](scripts/README.md):

1. Generate an age identity offline and put only its public recipient in operations.env.
2. Configure OCI instance/compartment/Object Storage metadata.
3. Copy operations.env to /etc/quantnest/operations.env, owner quantnest, mode 600.
4. Run the first backup service and verify its archive/checksum/uploaded marker.
5. Run monitoring once and confirm accepted metrics and notification subscription.
6. Enable the backup and monitor timers.

```sh
sudo systemctl start quantnest-backup.service
sudo systemctl start quantnest-monitor.service
sudo systemctl enable --now quantnest-backup.timer quantnest-monitor.timer
sudo systemctl list-timers --all
```

Restore a backup into the [isolated state-only recovery flow](../shared/scripts/README.md#6-restore-without-touching-the-active-installation) before relying on it. An upload is not proof of recoverability.

## 11. Updates and incidents

For an upgrade:

1. Prepare a reviewed new release and matching frontend deployment; preserve existing secret/encryption keys.
2. Stop or pause strategies and close/cancel unsettled obligations through normal flows.
3. Make an encrypted backup and record the previous release.
4. Run `python3 infra/shared/scripts/deploy.py --root . --mode public --build`.
5. Diagnose API/workers, gateway, assets and selected integrations.
6. Inspect saved session states and resume/deploy through the workspace as needed. Sessions left Running can recover after services restart; do not recreate them by manually writing model states.

Env edits require recreation, not simply restart. Keep one Beat and one runtime topology. Do not start legacy host runtime services beside Docker.

Useful incident commands:

```sh
sudo -u quantnest docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml ps --all
sudo -u quantnest docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml logs --tail 100 api execution orders outbox background compute research ingress
sudo journalctl -u quantnest-monitor.service -u quantnest-backup.service -n 100 --no-pager
```

403 on direct origin/API access is expected. 403 through the website requires checking Function/backend token equality, canonical domain and the specific returned policy error. Missing charts require feed authorization/data checks; a container ping cannot prove live ticks.

## 12. Launch checklist

Confirm account signup/password reset/OTP/avatar; API/chart sockets through Pages; bounded history/backtest; Paper and Terminal; usage enforcement; support/Turnstile/mail; selected Gemini workflow; payment test/webhooks if enabled; backup download/restore; OCI monitoring and notifications; and the Public Live denial.

Keep unsupported/externally unconfigured integrations unavailable until their acceptance steps pass. Container startup is only the first stage of a production launch.
