# Private: customer-owned installation

Private runs on the customer's own Linux server: market feed, strategy rules, Paper/Live order path, broker observations, database and records stay in that installation. Its renewable subscription is a centrally signed QuantNest contract. Public plan checkout does not run locally.

The stack is portable across customer-owned Oracle, AWS, Azure, Google Cloud, other VPS providers and on-premises Linux hosts that meet the requirements below. The customer does not need an Oracle account: central licence refresh is HTTPS, verification uses public keys, and backups can stay with the customer's chosen storage. This Compose deployment needs persistent volumes, long-running worker processes, outbound broker/data connections and local shared runtime files; shared web hosting and request-only serverless functions cannot host the complete execution stack.

Start with [the architecture overview](../README.md) and [provider setup](../../docs/third-party-setup.md). The same React app serves customer pages and workspace; there is no separate customer-site deployment.

## 1. Decide the installation scope first

Agree on:

- server/domain owner, capacity, operator and backup responsibility;
- renewable or perpetual continuing-use rights and support/maintenance terms;
- required execution scopes: Paper, qualified Live or both, plus numeric workflow allowances;
- unlimited software usage while the installation licence is active;
- supported software release identifiers and qualified integrations;
- source/AI processing rights and, for Live, the actual permitted broker arrangement.

Current strategy execution supports NSE stocks via Direct routing. Futures/options are coming soon; a Private contract does not enable an unimplemented instrument/adapter.

Default resource ceilings total 9.875 GiB. Use at least 12 GB RAM with headroom and a measured workload profile. Start with one execution/calculation worker and one heavy compute job at a time. Contract allowances cannot exceed available operational admission.

## 2. Central QuantNest provisioning

These steps run on **QuantNest's central Public authority**, not on the customer server:

1. Configure the OCI licence key/version/endpoint and exported verification key.
2. Create the customer account and a Private contract in Operations Admin.
3. Fill every limit with a nonnegative integer. The contract form rejects incomplete approved limits; use the current catalog as the field list.
4. Set continuing-use rights, paid-through/maintenance dates, seats, broker accounts, deployment scope and supported releases.
5. Live additionally needs a current live-approved-until date, approval reference and qualified integration; do not approve it merely because a Live module exists.
6. Approve the contract after the actual agreed scope is accepted.
7. Provision an installation:

```sh
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py provision_installation --contract YOUR_CONTRACT_ID
```

It prints LICENSE_INSTALLATION_ID and an activation token **once**. Store them securely. Only the token hash is retained centrally. Deliver the installation ID/token, licence public-key mapping, signed release, release trust mapping and scope documentation to the customer through a trusted channel.

Release trust keys and licence verification keys are separate. Private receives only public PEM keys. OCI private signing keys never leave QuantNest.

## 3. Prepare the customer's Linux host

The supported installer is Linux with Docker Compose v2 and Python 3.12. Ubuntu 24.04 is a straightforward starting OS; ARM64/aarch64 or x86_64 must match the signed release's qualified architectures.

For a fresh Ubuntu 24.04 host:

```sh
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 python3-venv age
sudo systemctl enable --now docker
docker compose version
uname -m
```

Create a restricted operator and deployment directories:

```sh
sudo useradd --system --create-home --home-dir /opt/quantnest --shell /usr/sbin/nologin quantnest
sudo usermod -aG docker quantnest
sudo install -d -m 750 -o quantnest -g quantnest /opt/quantnest/releases /opt/quantnest/operations
sudo install -d -m 700 -o quantnest -g quantnest /etc/quantnest/private /etc/quantnest/trust /mnt/quantnest-data/backups
```

Skip user creation if that managed account already exists. Docker group access has host administrative power. Use sudo -u quantnest for operator commands.

Provision persistent disk space, monitor it, and configure Docker storage placement during an initial reviewed setup if the boot disk is too small. Public's bootstrap_host.sh and OCI Terraform are **Public-only**; do not use them to silently change the customer's infrastructure.

Point the customer's hostname to this server. Permit HTTPS 443 and HTTP 80 for Caddy certificate issuance/renewal; SSH is administrator-restricted. PostgreSQL, Redis, research and execution transports must remain unexposed.

## 4. Install the host tools

Obtain a reviewed bootstrap copy of the Private/shared scripts through the trusted QuantNest delivery channel. Do not execute an unverified installer from an arbitrary downloaded archive.

Place that reviewed bootstrap directory at an operator-readable location, preserving its infra/private and infra/shared structure:

```sh
sudo install -d -m 750 -o quantnest -g quantnest /opt/quantnest/bootstrap
sudo cp -a /secure-delivery/quantnest-bootstrap/. /opt/quantnest/bootstrap/
sudo chown -R quantnest:quantnest /opt/quantnest/bootstrap
cd /opt/quantnest/bootstrap
```

Use the actual trusted delivery directory. This avoids a service account being unable to read scripts inside another user's protected home directory.

From that reviewed source root:

```sh
sudo -u quantnest python3 -m venv /opt/quantnest/operations
sudo -u quantnest /opt/quantnest/operations/bin/pip install --require-hashes -r infra/private/requirements.lock
```

This small lock installs only host verification/installer dependencies. Application dependencies are installed in Docker images. The OCI SDK/signing private key is not required on the customer host.

Install the separately delivered release trust JSON at /etc/quantnest/trust/release-public-keys.json. It maps key-version IDs to P-256 PEM public keys. Confirm the trusted fingerprint/key identity through the delivery channel; a key supplied only inside an untrusted archive cannot establish trust.

## 5. Prepare protected customer configuration

```sh
sudo -u quantnest cp infra/private/backend.env.example /etc/quantnest/private/backend.env
sudo -u quantnest cp infra/private/research.env.example /etc/quantnest/private/research.env
sudo -u quantnest mkdir -p /etc/quantnest/private/license
sudo chmod 600 /etc/quantnest/private/backend.env /etc/quantnest/private/research.env
sudoedit /etc/quantnest/private/backend.env
sudoedit /etc/quantnest/private/research.env
```

Put the issued licence mapping at /etc/quantnest/private/license/public-keys.json. This public file may be readable but must not be group/world writable (644 is acceptable). Its directory is operator-protected.

Generate fresh values per installation:

```sh
/opt/quantnest/operations/bin/python -c "import secrets; print(secrets.token_urlsafe(64))"
/opt/quantnest/operations/bin/python -c "import secrets; print(secrets.token_hex(32))"
/opt/quantnest/operations/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Use different URL-safe values for Django, database/admin passwords, ingress and research tokens. Use the hex value for Redis. Preserve the Fernet key for all later upgrades/restores.

| Inputs | Customer configuration |
| --- | --- |
| QUANTNEST_RELEASE | Exact identifier of the signed software release and the contract's supported release list |
| SECRET_KEY / CREDENTIAL_ENCRYPTION_KEYS | Customer-specific signing/encryption keys |
| DB_NAME / DB_USER / passwords | Application role and separate bootstrap administrator credentials |
| REDIS_PASSWORD | Unique hexadecimal password |
| FRONTEND_URL / BACKEND_URL / PUBLIC_HOSTNAME | Same customer HTTPS website origin/hostname |
| ALLOWED_HOSTS | Customer hostname plus internal api/localhost health hosts |
| QUANTNEST_PROXY_TOKEN | Unique installation ingress token; Caddy injects it |
| EMAIL_HOST_USER / PASSWORD / DEFAULT_FROM_EMAIL | Customer-authorized Brevo SMTP login/key and verified sender |
| FYERS_CLIENT_ID / FYERS_SECRET | Data-source app; callback derives from BACKEND_URL + /api/v1/market/fyers/callback/ |
| BROKER_FYERS_CLIENT_ID / BROKER_FYERS_SECRET | Qualified execution app; callback derives from BACKEND_URL + /api/v1/brokers/credentials/fyers/callback/ |
| RESEARCH_SERVICE_TOKEN | Identical in backend.env and research.env |
| GEMINI_API_KEY / GEMINI_MODEL | Customer-authorized AI credentials/model in research.env |
| LICENSE_INSTALLATION_ID / ACTIVATION_TOKEN / SERVER_URL | Issued identity/token and central HTTPS licensing URL |
| Licence public key file | Mount infra/private/license/public-keys.json at /etc/quantnest/license/public-keys.json; this is the settings default, not an additional env input |
| Turnstile / optional integrations | Configure the customer-domain widget and the optional labelled features |
| Worker/admission settings | Starting resource profile; increase only with measured capacity |

Private Compose sets Private mode, DEBUG=False, Paper/Live runtime scopes and BILLING_ENABLED=False. New Private work is unlimited while its licence is valid; Live deploy/resume also requires current broker qualification. Already running sessions have no background commercial-expiry gate. No central Razorpay or OCI signing secret belongs in this environment.

Licence renewal reaches the central HTTPS website gateway; the customer does not need QuantNest's central ingress token. Its own QUANTNEST_PROXY_TOKEN is unrelated.

## 6. Install a signed release

First verify:

```sh
sudo -u quantnest /opt/quantnest/operations/bin/python infra/private/scripts/release.py verify --archive /secure-delivery/RELEASE.tar.gz --signature /secure-delivery/RELEASE.jws --trusted-keys /etc/quantnest/trust/release-public-keys.json
```

Then install:

```sh
sudo -u quantnest /opt/quantnest/operations/bin/python infra/private/scripts/install.py --archive /secure-delivery/RELEASE.tar.gz --signature /secure-delivery/RELEASE.jws --trusted-keys /etc/quantnest/trust/release-public-keys.json --releases /opt/quantnest/releases --configuration /etc/quantnest/private --current /opt/quantnest/current
```

Use the delivered filenames. Do not set COMPOSE_PROJECT_NAME to another deployment; installer uses quantnest-private consistently.

The installer verifies the signed archive/manifest and host architecture, extracts into a new release directory, validates/copies private config and public licence keys, builds images and calls the shared deployment sequence. The React build is already inside the signed release; the customer does not need Node to rebuild it. The current symlink changes only after startup succeeds.

If startup fails, read the failing step; the previous release pointer is retained, but shared database migration changes are not automatically undone. Use the recovery guide if schema recovery is necessary.

After correcting configuration or a transient build/startup failure, the installer can reuse that same release directory only if its complete signed source/static content still matches. It revalidates the manifest and checksums before copying configuration or retrying. Modified/unexpected source files are refused; an incompatible migrated schema still requires reviewed recovery.

[Every Private script and flag](scripts/README.md).

## 7. Direct source deployment alternative

For a reviewed complete source checkout rather than a delivered archive:

1. Copy the mode examples to infra/private/backend.env and research.env.
2. Install the public licence mapping at infra/private/license/public-keys.json.
3. Copy frontend.env.example to frontend/.env; set the customer's real HTTPS domain and public widget key. Configure legal name, support email and support hours only in backend.env; the frontend reads them from the installation's API.
4. Install Node 22 and build:

```sh
npm ci --prefix frontend
npm run build --prefix frontend
```

5. Deploy:

```sh
python3 infra/shared/scripts/deploy.py --root . --mode private --build
```

This alternative requires the full frontend source. A signed customer package contains frontend/dist, not the frontend source/dependency tree. Do not combine both installations on the same active volumes.

## 8. Create the customer administrator

From /opt/quantnest/current:

```sh
sudo -u quantnest docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py createsuperuser
sudo -u quantnest docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py enrol_staff_otp --username YOUR_ADMIN_USERNAME
```

Import the secret otpauth URI privately. Sign into https://<customer-host>/admin/ with username/password/current OTP. The configured Site is automatically set from FRONTEND_URL.

There is no software seat or broker-account-count quota while the licence is active. Configure Google SocialApp/Site only if customer Google sign-in is included; register the exact customer callback.

## 9. Refresh/import the licence before new work

The current licence format uses signed schema_version=3. During an
upgrade from quantity-limited licences, run migrations on the central service first;
the migration advances contract revisions automatically. Then update the customer
installation and refresh/import its new licence. No module list is needed, and no
usage or subscription records need manual insertion. Keep the central and customer
software releases aligned for this upgrade.

Run the initial refresh explicitly; do not wait for the six-hour schedule:

```sh
sudo -u quantnest docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py shell --no-imports -c "from installations.tasks import refresh_installation_licence_task; print(refresh_installation_licence_task())"
```

The response reports revision, not the activation token. Beat schedules subsequent refreshes every six hours. HTTPS to the configured authority, a valid activation token, correct public keys and supported release are required.

For an approved offline signed lease, the installation administrator can import it in **Billing and Usage → Private licence** using Verify and import. Clock/revision rollback is rejected. If rights expired and were renewed, use Enable new work after verifying the new lease. Running strategies are not paused by background expiry checks, and renewal does not restart stopped sessions.

Renewable rights stop **new exposure/work** when their accepted paid-through/lease deadline is exhausted. Existing financial obligations still need reconciliation and bounded reduction/exit flows. Expiry is not an automatic server shutdown or forced liquidation. Perpetual continuing-use rights behave according to their signed contract; support/maintenance is separate.

## 10. Source, history and qualified broker activation

1. Configure the installation's source and AI service under its agreed provider arrangements. Check the configured execution scopes; the signed licence supplies expiry and Live qualification, without resource quantities. No separate approval rows need insertion.
2. Authorize the data source through the customer's market login/callback in the same browser.
3. Sync supported instruments/calendar and bounded history:

```sh
sudo -u quantnest docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py sync_instruments --source NSE_CM
sudo -u quantnest docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py sync_market_holidays
sudo -u quantnest docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py ingest_historical --symbols NSE:SBIN-EQ --days 30 --timeframe 1m
```

4. Optional candle hypertable/compression setup: run setup_timescale after migrations with application services stopped and a current backup.
5. For Live, register the separate broker callback, connect the customer's broker through the workspace and verify broker session authorization.
6. Confirm broker-events observations and REST reconciliation with accepted broker test procedures, before deploying a qualified Live strategy.

Order ownership matches broker account plus broker order ID or verified local QN tag, retains the order's saved strategy session, and shares cumulative-fill accounting. Unmatched broker activity remains outside strategy P&L; account position totals do not overwrite strategy positions.

No central QuantNest server participates in this customer's order placement path. Central HTTPS is used for subscription/licence refresh, not broker execution.

## 11. Diagnose and configure backups

```sh
sudo -u quantnest /opt/quantnest/operations/bin/python infra/shared/scripts/diagnostics.py --root . --mode private
sudo -u quantnest docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml ps --all
sudo -u quantnest docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml logs --tail 100 api execution orders broker-events outbox background compute research ingress
```

Expected services are the Public-style core plus broker-events, with customer Caddy serving the local React build. Private does not use the Cloudflare Pages Function or central Oracle Terraform.

Follow [the shared backup guide](../shared/scripts/README.md) to generate an offline age identity, run backup.py --mode private, copy encrypted artifacts off-host, and restore into an isolated state-only project. Schedule backups using the customer's accepted cron/systemd/backup system; Public's OCI upload timers do not belong here.

Default capacity has one calculation child and compute job. Measure queue age, broker request limits, CPU/RSS, Redis persistence and financial reconciliation before increasing admission/contract capacity.

## 12. Upgrade and recovery

The same installer accepts a new signed release. Upgrades additionally require:

```sh
sudo -u quantnest /opt/quantnest/operations/bin/python infra/private/scripts/install.py --archive /secure-delivery/NEW_RELEASE.tar.gz --signature /secure-delivery/NEW_RELEASE.jws --trusted-keys /etc/quantnest/trust/release-public-keys.json --releases /opt/quantnest/releases --configuration /etc/quantnest/private --current /opt/quantnest/current --backup-directory /mnt/quantnest-data/backups --backup-recipient age1YOUR_PUBLIC_RECIPIENT
```

Update QUANTNEST_RELEASE in the protected configuration to the new signed identifier and approve that release in the central contract first. Preserve existing credential/signing keys. Stop or pause strategies and settle orders/positions through normal flows. The installer stops application services, backs up before migrations and preserves the previous release directory.

After startup run diagnostics, refresh/verify the licence and inspect session states. Resume/deploy through the workspace as needed; sessions left Running can recover after services restart. Never reverse migrations against active financial records. Recovery/rollback uses matching encrypted backups, isolated stores and broker reconciliation since the backup.

## 13. Acceptance before customer Live

Confirm HTTPS/cert renewal, account/OTP/avatar, signed licence and renewal/expiry behavior, unlimited software usage, source/history freshness, Paper/Terminal/backtests, AI/mail/support if included, broker ownership/cumulative fills/reconciliation, encrypted recovery and the customer's monitoring/incident responsibility.

Starting broker-events does not itself authorize or place a trade. Keep Live deployment disabled until actual qualification/activation is complete.
