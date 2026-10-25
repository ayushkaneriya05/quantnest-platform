# Public: beginner deployment walkthrough

This installs the customer research/backtest/Paper/simulated-Terminal platform.
Live execution is disabled in Public. Begin with free Explore and checkout off.
The source and external setup references were reviewed on 24 October 2026.

There are two places to configure: **one Ubuntu Docker server** for the backend
and **Cloudflare Pages** for the browser application/gateway. You do not build
the Public frontend on the server.

## Step 1. Finish the preparation checklist

Read [Start here](../START-HERE.md). Complete these before running deployment:

- [ ] The intended current repository changes are reviewed, committed and pushed.
- [ ] You know the release branch/commit to use on both server and Pages.
- [ ] You own/control the browser domain and a separate backend origin hostname.
- [ ] You have the required FYERS data-use permissions and data app credentials.
- [ ] You have Gemini key/model access and Brevo SMTP credentials/verified sender.
- [ ] You have created a Turnstile widget for the browser hostname.
- [ ] You have a recovery plan for an existing database, or are using new empty volumes.

For provider accounts and exact key destinations, follow
[the integration guide](../shared/INTEGRATIONS.md). Google login and Razorpay can
be added after the main setup. The supplied full Public deploy requires research
credentials now; leaving its example Gemini key unchanged makes preflight fail.

## Step 2. Prepare the server

Complete [Server setup](../shared/SERVER-SETUP.md): Ubuntu 24.04, SSH, cloud
network rules, Docker/Compose, Python 3.12, age and the reviewed repository.
Keep the database/Redis/research ports private. Inbound 80/443 must reach Caddy.

Open SSH and enter the repository:

```sh
cd ~/QuantNest
git log -1 --oneline
docker version
docker compose version
python3 --version
```

Run the following shell commands on this server, not in local PowerShell.
Use the directory you actually cloned if it differs from `~/QuantNest`.

## Step 3. Choose consistent domains

This walkthrough uses:

| Name | Example | Goes to |
| --- | --- | --- |
| Browser site | `app.example.com` | Cloudflare Pages |
| Backend origin | `origin.example.com` | Your Docker server IP |

Replace every example with your own names. In Cloudflare DNS create a
**DNS-only** A record for the origin pointing at the server. Do not enable the
orange proxy cloud on this origin record. Do not point the browser-domain A
record directly at the server; Pages will provide its browser-domain setup.

Check from the server:

```sh
dig +short origin.example.com
```

It should resolve to your actual server. Add AAAA only when your server's IPv6
networking is working. DNS alone does not create a Pages project or HTTPS site.

## Step 4. Create the server environment files

For a new installation:

```sh
umask 077
cp infra/public/backend.env.example infra/public/backend.env
cp infra/public/research.env.example infra/public/research.env
chmod 600 infra/public/backend.env infra/public/research.env
nano infra/public/backend.env
```

Skip the copy if the destination already contains real settings. In nano, save
with Ctrl+O, Enter, and exit with Ctrl+X. The protected files are not committed.
`backend.env` supplies both Compose interpolation and backend runtime values.

Generate secrets one at a time:

```sh
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Run the first command separately for `SECRET_KEY`, PostgreSQL administrator
password, application DB password, `QUANTNEST_PROXY_TOKEN` and
`RESEARCH_SERVICE_TOKEN`. Use a fresh output for each. The second produces a
64-character hexadecimal `REDIS_PASSWORD` safe in the generated Redis URLs.
Save the values in your password manager, not a public deployment note.

Set the following in `backend.env`:

```dotenv
QUANTNEST_RELEASE=YOUR_REVIEWED_RELEASE_LABEL
FRONTEND_URL=https://app.example.com
BACKEND_URL=https://app.example.com
PUBLIC_HOSTNAME=app.example.com
ORIGIN_HOSTNAME=origin.example.com
ALLOWED_HOSTS=app.example.com,origin.example.com,api,localhost,127.0.0.1
BILLING_ENABLED=False
API_WORKERS=1
EXECUTION_WORKERS=1
```

The release label is a local image tag for the checked-out source, not a command
that fetches a Git release. Set the actual DB name/user/password values from the
example and keep bootstrap/application passwords different. Enter Brevo SMTP,
FYERS data credentials, Turnstile secret and the shared research token.

You may append `QUANTNEST_LEGAL_NAME`, `QUANTNEST_SUPPORT_EMAIL` and
`QUANTNEST_SUPPORT_HOURS` for your actual contact details. Read the name/email
defaults before exposing the site. Keep all Razorpay values blank and billing off
until [its separate acceptance procedure](../shared/INTEGRATIONS.md#10-razorpay-optional-public-checkout-activation).

Edit the research file:

```sh
nano infra/public/research.env
```

Enter the actual Gemini key, an available supported Interactions model, and the
same `RESEARCH_SERVICE_TOKEN` as backend.env. Confirm that the model in the
example is usable by your Google project; do not assume it is granted.

## Step 5. Build images and create the credential-encryption key

```sh
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml build
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml run --rm --no-deps api python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Build installs locked dependencies into the backend/research images. The second
command prints one Fernet key without starting API/execution or creating tables.
Paste the key into `CREDENTIAL_ENCRYPTION_KEYS` in backend.env, replacing the
placeholder. Keep its trailing `=` if present. Store it for recovery.

Keep this original key during ordinary upgrades. A new random key cannot decrypt
provider credentials already stored under the old key. Use the dedicated rotation
procedure if rotation is later required.

## Step 6. Start the backend and finish its automatic setup

```sh
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml config --quiet
python3 infra/shared/scripts/deploy.py --root . --mode public --build
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml ps
python3 infra/shared/scripts/diagnostics.py --root . --mode public
```

`config --quiet` validates without printing resolved secrets. Deployment runs
preflight, stopped-service migrations, Timescale setup, Site configuration and
static collection, then starts the full stack. It may reuse the images just
built. Do not bypass a failed migration or start old native runtimes alongside it.

Caddy requests its HTTPS certificate for the origin hostname. Inspect its log:

```sh
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml logs --tail=100 ingress
curl -i https://origin.example.com/health/
```

For the second command, **403 `untrusted_ingress` is expected** once HTTPS works:
you have contacted the origin directly without its gateway token. Do not remove
that check. The public browser URL should return healthy through Pages later.
A certificate error instead points to DNS, ports, time, or Caddy issuance.

## Step 7. Create Cloudflare Pages and its Function configuration

In Cloudflare **Workers & Pages**, create a **Pages** project connected to the
repository, using the reviewed production branch. Choose a custom/None build
preset if needed so you can enter the following values:

| Build setting | Value |
| --- | --- |
| Root directory | Repository root; leave empty or use the dashboard's root selection |
| Build command | `npm ci --prefix frontend && npm run build --prefix frontend` |
| Output directory | `frontend/dist` |
| `NODE_VERSION` | `22.14.0`, matching the reviewed frontend build |
| `VITE_SITE_URL` | `https://app.example.com` |
| `VITE_TURNSTILE_SITE_KEY` | Public key from this site's Turnstile widget |

Keep repository root as the project root so `functions/[[path]].js` is included.
Choosing `frontend` as the root hides that gateway. This is a Pages + Functions
deployment, not just a drag-and-drop copy of static frontend assets.

In the project's **Settings -> Variables and Secrets**, for Production add:

| Function value | Type | Value |
| --- | --- | --- |
| `BACKEND_ORIGIN` | Server environment variable | `https://origin.example.com` with no API path |
| `QUANTNEST_PROXY_TOKEN` | Encrypted secret | Exactly the value saved in Public backend.env |

Never call the token `VITE_QUANTNEST_PROXY_TOKEN`. It is not a browser setting.
Do not copy DB, FYERS, SMTP, Gemini or Razorpay secrets into the Pages frontend.
Redeploy after setting variables/secrets so the running deployment receives them.

Attach `app.example.com` under the Pages project's **Custom domains** and follow
its DNS instructions. Wait for its domain/certificate status to become active.
Use this canonical domain for normal user login and provider callbacks, not the
temporary `pages.dev` preview hostname. Keep preview environments isolated from
production secrets/backends if you enable them.

Where available under **Settings -> Runtime -> Fail open / closed**, choose
**Fail closed**. Backend routes depend on the Function; exhausting its allowance
should not fall back to a static HTML page for an API request.

References: [Functions project location](https://developers.cloudflare.com/pages/functions/get-started/),
[build configuration](https://developers.cloudflare.com/pages/configuration/build-configuration/),
[Function secrets](https://developers.cloudflare.com/pages/functions/bindings/#secrets),
[custom domains](https://developers.cloudflare.com/pages/configuration/custom-domains/),
and [fail-closed behavior](https://developers.cloudflare.com/pages/functions/routing/#fail-open--closed).

## Step 8. Check the complete browser/gateway path

```sh
curl -i https://app.example.com/health/
curl -i https://app.example.com/api/v1/public/catalog/
```

Expected: health is HTTP 200 JSON with mode `public` and database/runtime checks
true. Catalog is JSON with Paper scope and checkout unavailable while billing is
off. If API URLs return HTML, check Pages root/Function deployment and generated
route output rather than changing API URLs in React.

Open the website and Admin at `https://app.example.com/admin/`. Both frontend and
API use this browser origin; you do not need a browser-facing API URL variable.
API/WebSocket/admin/static requests go through the existing Function.

## Step 9. Create the operator account and configure platform integrations

On the server:

```sh
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py createsuperuser
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py enrol_staff_otp --username YOUR_ADMIN_USERNAME
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py sync_market_holidays
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml exec api python manage.py sync_instruments --source NSE_CM
```

Enrol the printed OTP URI privately in your authenticator, then log into Admin.
The enrolment command is for first setup, not every restart. Use the shared
integration guide to:

1. Review exchange/segment calendars and historical holiday years.
2. Sign into FYERS market data at the canonical browser URL. Register the exact
   data callback on `app.example.com`, not the origin hostname.
3. Review the seeded active catalog and customer contact details.
4. Configure the optional Google SocialApp for the Site created by deploy.
5. Verify Brevo account/support email, Gemini research and anonymous Turnstile
   enquiries. A green container health status does not verify these providers.

Paid catalog changes use the existing Admin clone/edit/publish process; do not
edit Python constants just to change customer prices/allowances.

## Step 10. Accept the free Public workflow

Use a new **ordinary user** through the public website. Follow
[the full platform checklist](../shared/INTEGRATIONS.md#11-initial-platform-data-and-ordinary-user-acceptance).

- [ ] Signup, sign-in, refresh, logout and password recovery work.
- [ ] Data history loads and live updates arrive during the allowed market session.
- [ ] A stock strategy/version saves and a bounded backtest finishes.
- [ ] Screener and Gemini research complete for allowed input sizes.
- [ ] Paper Wallet funding and strategy-list deployment create the right session.
- [ ] Paper session controls, observations, intentional fills/exits and results work.
- [ ] Terminal watchlist, chart, simulated order/position/history flow works.
- [ ] Support tickets/Admin replies and outgoing emails work.
- [ ] Billing and Usage reflects the actual Public inventory/period/request limits.
- [ ] New over-limit actions are rejected with the expected allowance message.
- [ ] Public has no Live execution scope; paid plans do not enable Live.

Use disposable acceptance data within the free plan's allowances. Development
bypasses ceilings, so success on your laptop did not prove Public enforcement.
Do not count a valid no-signal result as a failed execution test; inspect the
saved rules and their actual observations. When you want paid checkout, perform
[the separate Razorpay procedure](../shared/INTEGRATIONS.md#10-razorpay-optional-public-checkout-activation)
before accepting real sales.

## Step 11. Finish recovery preparation before relying on the server

First follow [Recovery setup](../shared/RECOVERY-SETUP.md) for Windows age tools,
key generation and exact SCP copy commands. Then use
[the backup/restore runbook](../shared/scripts/README.md#4-encrypted-local-backup).
Create the age recovery identity on your operator computer using the official
[age release/instructions](https://github.com/FiloSottile/age). The server needs
only its public `age1...` recipient for encryption. Keep the private identity off-host.

After settling/reviewing work, stop application writers, leaving data services up:

```sh
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml stop api feed execution background compute beat research ingress
python3 infra/shared/scripts/backup.py --root . --mode public --output "$HOME/quantnest-backups" --recipient age1YOUR_PUBLIC_RECIPIENT
python3 infra/shared/scripts/deploy.py --root . --mode public
```

Substitute the public recipient. This creates an encrypted archive/checksum, then
restarts the configured stack. Copy the archive/checksum off the host over SSH/SCP.
Retain env/encryption keys and the matching release separately. Practice restore
on a separate empty instance; never restore over the active production database.

## Step 12. Everyday operation and updates

For the AI Research credit upgrade, follow the
[research rollout steps](../../docs/ai-research.md#deployment-and-verification)
before restarting services. Update backend and research together; the migration
publishes the new credit catalog while preserving historical conversations and usage.

```sh
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml ps
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml logs --tail=100 execution
docker compose --env-file infra/public/backend.env -f infra/public/compose.yaml logs --tail=100 feed
docker stats --no-stream
df -h
```

| Situation | What to do |
| --- | --- |
| New backend code | Settle work, back up, fetch/select the reviewed release, deploy with `--build`, run diagnostics |
| New frontend code/public key | Redeploy Pages from that same reviewed release |
| New backend/research credentials | Edit mode-local env files, deploy to recreate services, verify the affected integration |
| Expired data authorization | Repeat the staff FYERS data login; inspect token status/feed |
| Changed hostname | Update DNS, backend origins/hosts, Pages domain/build variables and provider callbacks; redeploy |
| More load | Measure CPU/RAM/queue delay/storage first; increase workers only with available capacity |
| Payment uncertainty | Inspect verified payment/attempt records and reconciliation; do not invent a paid period |

Keep one execution supervisor and one Beat for this instance. Review logs rather
than starting duplicate processes after a health failure. Avoid `down -v` and
volume-prune commands during maintenance. See [the reference README](README.md)
for configuration details and [the runbook](../shared/scripts/README.md) for recovery.
