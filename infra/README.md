# QuantNest deployment guide

Choose one mode, then follow its README from the beginning. Each mode is a separate deployment of the same Django/React application.

After deploying, follow [Commercial operations](../docs/commercial-operations.md)
to review the seeded catalog, change plan limits, configure actual
merchant mappings and Private contracts, and operate customer support workflows.

## 1. Choose a mode

| Mode | Intended use and rules | Deployment | Instructions |
| --- | --- | --- | --- |
| Development | Local development; usage recorded and commercial allowances bypassed. Paper by default; data, AI and real broker development are opt-in | Docker and local Vite | [Development](development/README.md) |
| Public | Explore/Build/Pro numeric limits and configured execution scopes. Simulation through Paper; Live blocked | Oracle A1 and Cloudflare Pages | [Public](public/README.md) |
| Private | Customer-owned installation; unlimited software usage until licence expiry and qualified broker access. Qualified Live requires an active licence | Customer Linux host and Caddy | [Private](private/README.md) |

Compose owns the mode. Production forces DEBUG=False and Redis-backed Channels. Public excludes Live queues/broker events; Private disables hosted checkout and obtains its subscription rights from QuantNest's central licensing service.

Automated execution currently supports NSE stocks through Direct routing. The manual simulated Terminal also supports enabled NSE indices. Futures/options are coming soon, including on paid/Private plans.

## 2. Understand what runs

The browser reaches Vite, Cloudflare's gateway or customer Caddy. The gateway serves/proxies one main React frontend and Django ASGI API. API handles authentication, user operations and workspace/chart WebSockets.

The market-data service normalizes source observations and writes local shared market buffers and quote/chart projections. Execution owners evaluate strategy/instrument actors, dispatch bounded calculations to separate child processes and emit durable order intents. The order gateway serializes financial operations per account, runs Paper simulation or calls a qualified Private broker adapter, and commits financial records plus outbox events to PostgreSQL.

Broker WebSocket observations and REST reconciliation share ownership and cumulative-fill accounting. Outbox publishes committed results. The simulated manual Terminal has a separate order book. Celery compute runs historical backtests and AI research; Celery background runs reconciliation/notifications/maintenance; exactly one Beat schedules periodic work.

Paper/Live/backtests share strategy configuration, rule evaluation, sizing and exits. Backtests have historical candle fill/timing limitations. This is a Python platform with measured workload limits, not an HFT latency guarantee.

The local runtime volume belongs to **one execution host**. Do not distribute these local buffers across unrelated hosts or start duplicate native runtime/Celery services beside Compose. More execution nodes require explicit ownership/topology configuration, not an extra Compose replica.

Detailed references: [runtime](../docs/backend-runtime.md), [execution lifecycle](../docs/execution-technical-reference.md), [availability and allowance rules](../docs/commercial-operations.md#1-the-three-independent-controls). The [documentation index](../docs/README.md) identifies each guide's responsibility.

## 3. Folder boundaries

| Folder | Responsibility |
| --- | --- |
| development/ | Local stack and examples |
| public/ | Hosted stack, Caddy API origin, production examples |
| public/oracle/ | Public OCI Terraform |
| public/scripts/ and public/systemd/ | Host bootstrap, monitoring and backup timers |
| private/ | Customer stack, activation examples and public verification keys |
| private/scripts/ | Signed packaging/verification/installation |
| shared/docker/ | Mode-neutral application images |
| shared/postgres/ | Empty-database extension/role initialization |
| shared/redis/ | Durable runtime Redis policy |
| shared/scripts/ | Explicit-mode deploy, diagnostics, backup and isolated restore/recovery |

Customer pages and workspace both use frontend/. No separate customer-site framework is deployed. The root functions/[[path]].js is required for the Public Cloudflare gateway.

## 4. Environment ownership

### Two settings with separate responsibilities

- `QUANTNEST_DEPLOYMENT_MODE` selects deployment policy: `development`, hosted `public`, or customer-owned `private`. It controls billing/licensing, production security and deployment operations. Its default is `public`; `DEBUG` never selects a mode.
- `EXECUTION_ENABLED_SCOPES` selects automated execution availability: `paper`, `live`, or `paper,live`. APIs, entry admission, workers and workspace controls use this setting. Manual Terminal simulation has no plan quota, scope gate or Private-licence gate. Historical records remain owned and readable independently of new-entry permission.

Compose supplies both settings consistently to every process. Development defaults to Paper and can explicitly enable Live. Public fixes Paper scope; requesting Live in Public is a configuration error. Private supplies Paper and Live; the signed licence and broker qualification still decide whether new live exposure is permitted. Never use a UI setting as execution authorization.

Worker counts, admission capacity, timeouts and transport addresses remain configurable where they affect real resource use or topology. Do not copy every setting into an environment file: ordinary installations use the source/Compose defaults. All modes use PostgreSQL and shared Redis; SQLite, local cache and in-memory Channels alternatives have been removed.

| File | Consumer | Contents |
| --- | --- | --- |
| infra/<mode>/backend.env | Compose, Django, runtime and Celery | Protected server configuration |
| infra/<mode>/research.env | Research FastAPI | AI key and shared service token |
| frontend/.env copied from the mode's frontend.env.example | Vite/build | Site URL, public widget key and optional local proxy target; never server secrets |
| /etc/quantnest/operations.env | Public host units | Oracle metadata and backup recipient |
| backend/.env and research_service/.env | Native development only | Not loaded by Compose containers |

Internal DB/Redis URLs, notification IP and runtime path are supplied by Compose. Mode examples contain only consumed operator inputs. Optional integration groups are labelled; leaving them empty keeps those integrations unavailable. Production replace-with-* values must be replaced. Celery and Channels use REDIS_URL directly; separate duplicate connection settings are unnecessary.

The startup provider set is Oracle (Public hosting, signing, backup and monitoring), Cloudflare (Public frontend/gateway and form protection), Brevo (mail), the existing market source, Gemini (AI), Razorpay (when checkout is enabled), and Google (when social login is enabled). There is no external analytics SDK, error SDK, heartbeat service or automated Vault environment bundle. Product usage and website visits are not tracked; errors use bounded application logs. Brevo's optional API fields have a concrete purpose: newsletter confirmation and inbound support replies.

### Operator inputs and their consumers

This is the complete input inventory for the supplied examples. Do not add container-generated addresses or derived values to those files.

| Inputs | Consumer and action |
| --- | --- |
| QUANTNEST_RELEASE | Django release identity and production image tags; use the reviewed release identifier, exactly matching a signed Private artifact |
| SECRET_KEY / CREDENTIAL_ENCRYPTION_KEYS | Django signing / encrypted credentials; generate separate values and retain them for recovery |
| DB_NAME / DB_USER / DB_PASSWORD | PostgreSQL initializer and Django; application database, non-superuser role and its password |
| POSTGRES_ADMIN_PASSWORD | PostgreSQL bootstrap administrator only; use a different password from DB_PASSWORD |
| REDIS_PASSWORD | Redis servers, health commands and generated client URLs; use hexadecimal |
| QUANTNEST_PROXY_TOKEN | Trusted HTTP/WebSocket gateway authentication; Public must match the Cloudflare Function, Private Caddy receives it from Compose |
| FRONTEND_URL / BACKEND_URL | Browser origin / externally reachable callback origin; keep the same HTTPS origin in production |
| ALLOWED_HOSTS | Django host validation; include the browser hostname, internal api and loopback health hosts |
| PUBLIC_HOSTNAME | Caddy's browser hostname, without scheme/path; this name is also used in Private and does not mean Public deployment mode |
| ORIGIN_HOSTNAME | Public Caddy TLS origin hostname only, without scheme/path |
| EMAIL_BACKEND | Development console email; production uses the SMTP settings default |
| EMAIL_HOST_USER / EMAIL_HOST_PASSWORD / DEFAULT_FROM_EMAIL | Brevo SMTP login/key and verified sender; required for production account mail |
| FYERS_CLIENT_ID / FYERS_SECRET | Market-source authorization; source app credentials, separate from execution credentials |
| BROKER_FYERS_CLIENT_ID / BROKER_FYERS_SECRET | Private or intentional Development Live broker authorization; register the separate execution callback |
| RESEARCH_SERVICE_TOKEN | Shared Django-to-research authentication; identical value in both mode files |
| GEMINI_API_KEY / GEMINI_MODEL | Research container only; choose a model actually enabled in that Gemini project |
| TURNSTILE_SECRET_KEY | Server-side form verification; match VITE_TURNSTILE_SITE_KEY. Required for production anonymous contact/newsletter submission |
| BILLING_ENABLED | Hosted checkout switch; keep False until merchant configuration, webhook acceptance and capacity are ready. Private forces False |
| RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET / RAZORPAY_WEBHOOK_SECRET | Public payments and verified webhook handling; configure only when enabling checkout |
| BILLING_TAX_BPS / BILLING_TAX_ID | Public invoice/checkout tax configuration; basis points, e.g. 100 = 1 percent; use the applicable verified tax treatment |
| BREVO_API_KEY / BREVO_NEWSLETTER_LIST_ID / BREVO_DOI_TEMPLATE_ID | Optional newsletter contact sync and double-opt-in confirmation; see the provider guide before enabling |
| BREVO_WEBHOOK_TOKEN / BREVO_INBOUND_DOMAIN | Optional authenticated Brevo delivery/inbound support processing; SMTP account mail does not require these |
| OCI_LICENSE_KEY_ID / OCI_LICENSE_KEY_VERSION / OCI_SIGNING_ENDPOINT | Central Public licence issuer only; dedicated Vault key, version and crypto endpoint |
| LICENSE_INSTALLATION_ID / LICENSE_ACTIVATION_TOKEN / LICENSE_SERVER_URL | Private activation/lease refresh; issued installation identity/token and central HTTPS authority |
| EXECUTION_ENABLED_SCOPES | Development example allows Paper or intentional Paper/Live; production Compose supplies the permitted scope set |
| EXECUTION_MAX_ACTORS / EXECUTION_MAX_USER_ACTORS | Shared runtime admission; initially 8 per owner and 4 per user, subject to host and commercial limits |
| VITE_SITE_URL | Public website URL for canonical links and build output; must use HTTPS for production builds |
| VITE_TURNSTILE_SITE_KEY | Public widget key; safe to expose. The secret counterpart stays on the backend |
| QUANTNEST_API_PROXY_TARGET | Native Vite server only; Development Compose supplies http://api:8000 instead |

Host-only operations.env inputs and Terraform inputs/outputs have their own exact tables in [Public scripts](public/scripts/README.md) and [Oracle provisioning](public/oracle/README.md). They are not Django settings. The Cloudflare Function additionally needs BACKEND_ORIGIN and QUANTNEST_PROXY_TOKEN in its platform settings; [Public deployment](public/README.md#5-builddeploy-the-main-react-frontend) shows where to set them.

Derived defaults are defined once in backend/backend/settings.py:

- FYERS_REDIRECT_URI is BACKEND_URL plus `/api/v1/market/fyers/callback/`.
- BROKER_FYERS_REDIRECT_URI is BACKEND_URL plus `/api/v1/brokers/credentials/fyers/callback/`.
- TURNSTILE_HOSTNAMES defaults to FRONTEND_URL's hostname.
- LICENSE_PUBLIC_KEYS_FILE defaults to `/etc/quantnest/license/public-keys.json`, matching Private's read-only mount. The `private/license/.gitkeep` only preserves that otherwise empty source directory; place the delivered public key mapping there.
- Execution/calculation/order workers default to 1/1/1, order concurrency to 2, and calculation cache to 32 MiB. Add those real settings to backend.env only when intentionally changing resources; API_WORKERS defaults to 1 in the production Compose command. Increase matching container memory/CPU budgets when required.
- The backend image fixes numerical library threads at one before importing libraries. Compose does not repeat these defaults. Django, Celery and runtime processes receive the same image/environment.

Override a derived setting only for a deliberate nonstandard callback/widget setup. For ordinary deployment, edit the canonical URLs once and register their resulting callback paths. In a shell that already exports Compose interpolation inputs, those exported values override --env-file; unset stale values before deploying another installation. Use `config --quiet` to validate without displaying resolved secrets.

Generate secrets locally, never with an online generator:

```sh
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Use a separate URL-safe output for Django, each database password, ingress token and research token. The hex output is for Redis. Generate the Fernet credential key with the exact command in each mode guide and preserve it across upgrades/restores.

The backend defaults to legal name QuantNest and contact ayushkaneriya05@gmail.com. To change them, add QUANTNEST_LEGAL_NAME, QUANTNEST_SUPPORT_EMAIL and optionally QUANTNEST_SUPPORT_HOURS to the mode's backend file, then restart the API. Both the customer site and workspace read these values from the public catalog; there are no separate frontend copies. quantnest.site is the planned domain, not an assertion that it is purchased.

## 5. Deployment sequence

1. Prepare your machine; production also needs domain, HTTPS and provider accounts.
2. Copy only the selected mode's examples and configure required credentials.
3. Build/deploy; migrations and static collection precede application startup.
4. Create your administrator, enrol its authenticator and configure the Django Site.
5. Diagnose services; authorize the source, sync instruments/calendar and initialize history.
6. Public: publish reviewed prices/limits and provision capacity before enabling checkout. Private: import/refresh the signed licence before new work.
7. Make an encrypted backup, verify isolated recovery, configure monitoring, then launch.
8. For upgrades stop or pause sessions, settle obligations, back up, deploy and inspect session states after diagnostics.

[All shared script instructions](shared/scripts/README.md). [Provider account/callback guide](../docs/third-party-setup.md).

## 6. Production capacity

Public's initial Oracle A1 profile is **2 OCPUs / 12 GB**. Its container memory ceilings total **9.5 GiB**; Private adds broker events and totals **9.875 GiB**. Ceilings are not idle usage. Reserve host/build/Redis rewrite headroom and run one production stack on that machine.

Start with one API worker, one execution worker and one calculation child, one order worker/two concurrent account operations, one compute job and one background job at a time, and one Beat. Compute is capped at 0.75 CPU; numeric library threads are one.

Per-user actor admission starts at four, below Build/Pro's Paper allowance. Checkout is withheld for plans exceeding that admission ceiling. Increase resources and validate larger admission before enabling those plans; changing plan names does not create capacity.

Monitor CPU, RSS, PostgreSQL locks/connections, Redis persistence/memory, disk, queue age and actual order latency before increasing workers. Runtime Redis uses durable AOF, noeviction and synchronous fsync; analytical cache is independently bounded and evictable.

Verify your tenancy's actual allowance before applying infrastructure. [Oracle's current Always Free documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) describes quotas and reclamation; free resources are not an uptime guarantee.

## 7. Real deployment acceptance

Local configuration/syntax checks do not prove email delivery, source entitlement, merchant approval, licence signing, broker reconciliation or recovery. Follow the selected mode's launch checklist on its actual host/accounts. Do not place real orders as a general health check.
