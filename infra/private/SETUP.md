# QuantNest Private: managed deployment walkthrough

Use this as the QuantNest operator to run **one customer's managed Private
instance**, or your own personal instance, on a separate Ubuntu server. It uses
the shared website, registration and workspace, with Paper and Live scopes.
There is no customer licensing server, automated expiry, public-plan quota or
Private checkout to activate. Agreed costs, service periods and renewals are
managed directly, outside public subscription billing.

The Oracle server instructions were reviewed on 18 November 2026; the managed
offering was restored on 22 November 2026. Read
[Live release checks](../../docs/live-trading.md#release-checks-and-unsupported-behavior) for technical
acceptance boundaries before onboarding a real broker workflow.

## Customer agreement and isolation

1. Record the quotation, supported broker/products, intended sessions/instruments,
   capacity, users, service period, hosting/provider costs and support arrangement.
2. Agree backup retention, updates, recovery, any uptime commitment and offboarding.
3. Use a separate host/hostname/database/volumes and new secrets per customer.
   The fixed `quantnest-private` Compose project belongs to that host; this initial
   deployment flow does not put several customer stacks on one host.
4. Keep root/SSH, Docker, repository access and staff Admin with QuantNest. Give
   the customer an ordinary application account; do not send source or env files.
5. Ask the customer to complete their own trading authorization in Broker
   Integration. Never collect app secrets or one-time codes through Support.
6. Agree any public-to-Private record transfer explicitly. There is no automatic
   account, subscription, credential or financial-record migration.
7. Verify the selected workflow and restore procedure. No unattended real order
   is part of these setup commands.

Your own personal instance can use the same steps without a customer agreement.

## Step 1. Complete local simulation and prepare this separate instance

Start with [Development](../development/SETUP.md) so you understand the ordinary
strategy/backtest/Paper/Terminal flow before connecting a real broker account.
Read [Start here](../START-HERE.md) for how to publish the reviewed current source.

Prepare:

- [ ] A separate Ubuntu server/database for this instance, not the Public stack.
- [ ] A dedicated hostname, such as `private.example.com`.
- [ ] A reserved public server IP, including the required broker IP configuration.
- [ ] FYERS market-data app and the account owner's separate trading app.
- [ ] Gemini key/model and matching internal research tokens.
- [ ] Outgoing SMTP sender/login/key and production Turnstile widget.
- [ ] Your reviewed source release and a safe plan for any existing data.

Public user accounts, strategies and payments are not automatically copied here.
Use instance-local accounts and credentials. Private still has the
ordinary registration page; it does not introduce a separate sign-in interface.

## Step 2. Prepare the host and DNS

Complete [Server setup](../shared/SERVER-SETUP.md). Use Ubuntu 24.04 with Docker,
Compose, Python 3.12 and age. SSH into the dedicated server and enter the clone:

```sh
cd ~/QuantNest
git log -1 --oneline
docker version
docker compose version
python3 --version
```

These and subsequent shell commands run **on the Ubuntu server**. Public and
Private production defaults both publish 80/443, so do not start both on the same
host using these files unchanged.
On Oracle, follow that guide's public-subnet/Internet-Gateway, reserved-IP, NSG
and guest-firewall steps. Each separate Private host has its own resource needs;
the tenancy's free A1 CPU/RAM is shared with any Public host. On A1, build the
Private backend, research and frontend images natively for ARM64.

Create a DNS A record for `private.example.com` pointing at this server's
reserved IP. If using Cloudflare DNS, use **DNS-only** for this direct-ingress
configuration. No Cloudflare Pages project or Public origin hostname is needed.
Allow inbound 80/443 and your restricted SSH access. Do not publish database,
Redis, API or research ports.

```sh
dig +short private.example.com
```

Confirm it returns your server address. Use AAAA only if the IPv6 route/firewall
also works. The trading app's approved IP must match the actual outbound server
address, not this hostname, a Docker address or a Cloudflare edge address.

## Step 3. Create protected mode-local settings

For first setup only:

```sh
umask 077
cp infra/private/backend.env.example infra/private/backend.env
cp infra/private/research.env.example infra/private/research.env
chmod 600 infra/private/backend.env infra/private/research.env
nano infra/private/backend.env
```

If real destination files already exist, edit them instead of copying examples
over them. In nano use Ctrl+O, Enter to save and Ctrl+X to exit.

Generate independent secrets:

```sh
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Run the first separately for Django `SECRET_KEY`, PostgreSQL administrator
password, application DB password, `QUANTNEST_PROXY_TOKEN` and
`RESEARCH_SERVICE_TOKEN`. Use the hexadecimal output for `REDIS_PASSWORD`.
Keep each value in your password manager; do not reuse Public's values.

Set these domain/process values in `backend.env`:

```dotenv
QUANTNEST_RELEASE=YOUR_REVIEWED_RELEASE_LABEL
FRONTEND_URL=https://private.example.com
BACKEND_URL=https://private.example.com
PUBLIC_HOSTNAME=private.example.com
ALLOWED_HOSTS=private.example.com,api,localhost,127.0.0.1
API_WORKERS=1
EXECUTION_WORKERS=1
```

Replace the release label/domain. The variable named `PUBLIC_HOSTNAME` means the
browser hostname; it does not change this instance into Public mode. Compose
sets mode `private`, DEBUG false, scopes `paper,live`, and billing false.
Do not add registration switches, licence files or customer activation settings.

Use [Integration setup](../shared/INTEGRATIONS.md) to enter:

- Brevo SMTP login/key and your verified `DEFAULT_FROM_EMAIL`.
- FYERS **data** App ID/Secret in backend `FYERS_CLIENT_ID/FYERS_SECRET`.
- Shared `RESEARCH_SERVICE_TOKEN`, copied exactly into research.env too.
- `TURNSTILE_SECRET_KEY` and matching public `VITE_TURNSTILE_SITE_KEY`.
- Optional actual contact/name/hours overrides for the shared site.

Edit `research.env` with its Gemini key, accessible supported model and the shared
token. Production includes research and preflight requires its real key.
Google login is optional and configured later in Admin. Razorpay is not needed.

## Step 4. Build everything and create the encryption key

```sh
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml build
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml run --rm --no-deps api python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

The build creates backend/research images and a frontend image that builds React
and embeds it in Caddy. You do not need host Node, `frontend/dist`, a Private
frontend.env, or a manually copied TLS certificate.

Save the printed Fernet key as `CREDENTIAL_ENCRYPTION_KEYS`, preserving any
trailing `=`. This key protects stored provider credentials. Keep it with your
recovery material and retain it across normal upgrades; replacing it with a new
key does not decrypt existing credentials.

Frontend settings are build inputs: `FRONTEND_URL` supplies the public site URL,
and `VITE_TURNSTILE_SITE_KEY` supplies the widget key. Their changes need a rebuild.
Backend/broker/Gemini secrets are not browser build arguments.

## Step 5. Deploy and confirm HTTPS/readiness

```sh
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml config --quiet
python3 infra/shared/scripts/deploy.py --root . --mode private --build
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml ps
python3 infra/shared/scripts/diagnostics.py --root . --mode private
curl -i https://private.example.com/health/
```

Deploy stops application writers for migrations, sets up Timescale/Site/static
assets, then starts services. Caddy obtains/renews HTTPS for the domain. Expected
health response is HTTP 200 JSON with mode `private` and database/runtime true.
Diagnostics also checks execution worker readiness.

The stack includes feed, unified execution and `broker-events`; it does not start
a second Terminal/orders engine. A running broker-events container without a
saved active broker connection does not mean a trading account is authorized.
Before initial data consent, the feed stays running in a waiting state. It checks
the saved source authorization every five seconds without calling FYERS. Saving
a valid token starts its socket; daily reauthorization replaces that socket
automatically. A healthy API/container is not proof that live data is connected.

If TLS fails, inspect DNS, inbound 80/443, server clock and Caddy logs:

```sh
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml logs --tail=100 ingress
```

Open the normal website at the Private domain. Use it for all user/provider
callbacks rather than raw API/container addresses.

## Step 6. Create the administrator and initial metadata

```sh
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py createsuperuser
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py enrol_staff_otp --username YOUR_ADMIN_USERNAME
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py sync_market_holidays
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py sync_instruments --source NSE_CM
```

Replace the administrator username. Import the printed OTP URI into an
authenticator privately, then log into `https://private.example.com/admin/`.
Do not repeat OTP enrolment every restart or share its secret.

Review exchange/segment calendars, timezone/hours, holidays and special sessions.
Sync historical years before older backtests, adjusting this example range:

```sh
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py sync_market_holidays --start-year 2024 --end-year 2026
```

Instrument sync imports metadata, not every historical candle. Charts/backtests
request missing history through the common data layer when needed.

## Step 7. Authorize data and finish account integrations

Follow [FYERS data setup](../shared/INTEGRATIONS.md#6-fyers-shared-market-data-connection):

1. Register `https://private.example.com/api/v1/market/fyers/callback/` in the data app.
2. Sign into Admin on this same hostname.
3. Open `https://private.example.com/api/v1/market/fyers/login/` in the same browser.
4. Complete FYERS consent and inspect its staff token status/feed logs.
5. Request a stock chart and deeper history; check live updates during its session.

Keep `feed` running during consent. After the token is saved, allow up to five
seconds for the local authorization check, then wait for the FYERS authentication
acknowledgement and the required subscriptions/history. This interval is unrelated
to per-tick rule evaluation. Daily source sign-in is still your responsibility.

Then confirm account/password/support email, Turnstile anonymous enquiries and
Gemini research. If desired, add [Google login](../shared/INTEGRATIONS.md#8-google-sign-in-optional-backend-client)
to this database's configured Site. It is separate from Public's Google client.

## Step 8. Prove the simulated flow with an ordinary account owner

Create a normal account through `/register`; do not use Admin as your everyday
trading identity. Follow [the platform checklist](../shared/INTEGRATIONS.md#11-initial-platform-data-and-ordinary-user-acceptance):

- [ ] Configure your default charge assumptions and Terminal account.
- [ ] Create a small stock strategy with explicit full-exit/sizing/time rules.
- [ ] Save a version, run a bounded backtest and inspect its results.
- [ ] Add simulated Paper wallet funds and deploy from the strategy list.
- [ ] Inspect live observations, rule outcomes, session state and deliberate Paper fills/exits.
- [ ] Exercise Terminal's separate simulated order/position/history flow.
- [ ] Finish a screener/research run and Support reply/email.

Private has no plan allowance ceilings, but normal correctness rules still apply:
valid data/rules/instruments, market session, simulated capital, owned resources
and broker access/margin where applicable. No quotas does not mean unlimited
hardware or that every strategy has an entry signal.

## Step 9. Connect your own broker app separately

Read [Personal FYERS trading](../shared/INTEGRATIONS.md#9-personal-fyers-trading-private-or-intentional-live-development).
Then complete these steps deliberately:

1. In FYERS, use your individual trading app with order permissions and the
   server IP approved where required.
2. Register `https://private.example.com/api/v1/brokers/credentials/fyers/callback/`.
   This is **not** the data callback configured in Step 7.
3. In your ordinary QuantNest user account open Broker Integration -> FYERS.
4. Save the trading App ID/Secret there and complete its browser login/consent.
5. Verify account identity, active session, funds and broker order updates.
6. Keep the broker's own application available to inspect real state independently.

Do not put the trading app into backend `FYERS_CLIENT_ID/FYERS_SECRET`; those
settings are for shared market data. Private already starts broker-events and
allows Live scope, but this connection step does not deploy a strategy.

## Step 10. Accept Live only when you choose to trade

From the strategy list, deploy the saved version to **Live**, choose your broker
account and a fixed allocation, then manage it from Live Deployments. Check:

- Correct strategy/version and instruments were deployed.
- The allocation and broker margin can cover its intended order.
- Exchange/segment session is open and current observations are being received.
- Rules evaluate as expected; a false rule legitimately creates no order.
- For an intentional real trade, acknowledgement/fill/cancellation/exit agree with
  the broker's order records and QuantNest's session-owned state.
- Order updates/reconciliation continue and reconnect works when required.

One strategy can use different broker accounts, but cannot be duplicated on the
same account. Paper can have multiple saved-version deployments subject to its
own supported uniqueness rules. Live is never activated by merely checking a
health endpoint or funding the simulated Paper wallet.

After an expiry, reconnect in Broker Integration and review the session before
continuing. Do not replace app credentials while active orders/positions depend
on them. See [Live operations](../../docs/live-trading.md) for the order lifecycle.

## Step 11. Set up backup and recovery

First follow [Recovery setup](../shared/RECOVERY-SETUP.md) for Windows age tools,
key generation and exact SCP copy commands, then
[the encrypted backup runbook](../shared/scripts/README.md#4-encrypted-local-backup).
Generate an age recovery identity on your operator computer using
[the official age tools](https://github.com/FiloSottile/age), keep the private key
off this server, and use its public `age1...` recipient here.

Settle/review active work first. Stopping containers does not close broker positions.
Then:

```sh
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml stop api feed execution broker-events background compute beat research ingress
python3 infra/shared/scripts/backup.py --root . --mode private --output "$HOME/quantnest-backups" --recipient age1YOUR_PUBLIC_RECIPIENT
python3 infra/shared/scripts/deploy.py --root . --mode private
```

Copy the encrypted archive/checksum off-host over SSH/SCP. Preserve the original
credential-encryption key, protected environments and matching code release
separately. Practice restore on a clean instance with no application running.
The restore helper refuses to overwrite existing tables and does not start trading.

A restored database is not a snapshot of the broker's external orders. Review
recovered commands/checkpoints and reconcile real broker state before enabling
Live. Use [the restore procedure](../shared/scripts/README.md#5-restore-into-an-empty-deployment).

## Step 12. Daily operation and updates

For the AI Research upgrade, follow the
[research rollout steps](../../docs/ai-research.md#deployment-and-verification).
Update backend and research together. Private retains per-answer provider usage
but does not create commercial reservations or enforce period credits.

```sh
python3 infra/shared/scripts/diagnostics.py --root . --mode private
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml logs --tail=100 execution
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml logs --tail=100 feed
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml logs --tail=100 broker-events
docker stats --no-stream
df -h
```

Before a market session, check broker/data authorization, intended session
statuses, observations and available capital/margin. Reauthorize expired sessions
through their proper data or Broker Integration flow.

For an upgrade: settle/review trading, back up, select the reviewed source,
update `QUANTNEST_RELEASE`, run deploy with `--build`, then run diagnostics and
repeat affected feature checks. A normal restart can use deploy without `--build`
when the exact images already exist and configuration is unchanged.

Keep one execution supervisor and one Beat. Increase `EXECUTION_WORKERS` only
with measured CPU/memory headroom on this shared-buffer host; do not scale the
execution container count. Do not use `down -v` for upgrades and do not run
native runtime commands against these same containers/volumes.

## Service periods, renewal and offboarding

There is no automatic Private payment, licence or expiry task. Keep the agreed
period and renewal in your external operating records, contact the customer
before it ends and confirm payment/renewal directly. The application does not
enforce a date or automatically stop sessions at expiry.

For offboarding, coordinate with the customer: review pending orders and real
broker exposure, use the existing explicit session controls, confirm broker
outcomes, provide agreed records, then handle account access, service shutdown
and backup retention. A stopped process does not itself cancel broker orders.
Do not use account deactivation or server shutdown as an unreviewed liquidation
mechanism. Follow the written agreement for refunds, support and retained data.

Reference: [Private configuration](README.md),
[shared options](../shared/README.md), [operations](../shared/scripts/README.md).
