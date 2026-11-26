# Your deployment checklist: start here

**Repository flow and Oracle server setup checked: 18 November 2026.** Other
provider-dashboard instructions retain their individual review dates; confirm
labels, permissions and entitlements in your own accounts.

These guides explain the actions you, the operator, need to take. They start from
the current repository and finish with a configured platform. You do not need to
install PostgreSQL, Redis, Celery or Python application packages manually when
following the Docker procedure.

## 1. Choose the guide

| What you want to do | Follow this walkthrough | Where you run it |
| --- | --- | --- |
| Learn and develop on your Windows computer | [Development setup](development/SETUP.md) | PowerShell, from `E:\QuantNest` |
| Run the customer website with research, backtests and Paper | [Public setup](public/SETUP.md) | Ubuntu server plus Cloudflare dashboard |
| Run a managed customer or personal Paper/Live instance | [Private setup](private/SETUP.md) | A separate Ubuntu server and your browser |

Do Development first. Then choose Public, Private, or both on separate servers.
For local development, start/unpause Docker Desktop, then run
`.\.venv\Scripts\python.exe infra/development/dev.py` from the repository root.
It prepares missing env files and starts the configured stack; native data is not
imported automatically. See the Development guide for account/data authorization.

Public and Private use different databases, credentials and users. Logging into
one does not create an account or copy strategies in the other. Both use the same
site, registration and workspace interface; execution scopes control access.

For Oracle, start with the shared [server guide](shared/SERVER-SETUP.md), which
now covers Console provisioning, current A1 allowance, reserved IPs, NSG/security
lists, the Oracle Ubuntu firewall and native ARM builds. One tenancy's free
allocation is shared: it does not automatically cover two full production hosts.

The walkthroughs refer to three shared procedures:

- [Server setup](shared/SERVER-SETUP.md): VM, SSH, network, Docker and repository.
- [Integration setup](shared/INTEGRATIONS.md): FYERS data, Brevo, Gemini, Google
  login, Turnstile, personal broker access, and optional Public billing.
- [Recovery setup](shared/RECOVERY-SETUP.md): install age on Windows, create
  recovery keys, copy backups off-host and practice an empty-instance restore.

Existing `README.md` files remain the technical configuration reference. The new
`SETUP.md` files are the ordered, beginner procedure. You do not have to read
every reference before starting.

## 2. Understand what exists at this stage

The repository contains Compose definitions, locked application dependencies,
Dockerfiles, migration history, environment examples and operator scripts.
It cannot create your external accounts, buy a domain, grant provider permissions,
approve a merchant, or choose your real secret keys.

| Item | Already provided | Your action |
| --- | --- | --- |
| API, database, queues and execution | Docker/Compose configuration | Install Docker and supply settings |
| Database schema and initial records | Django migrations | Let `deploy.py` apply them; do not invent SQL tables |
| Execution processes | One controller/worker supervisor | Start the Compose `execution` service; choose worker count |
| Historical/live market data | FYERS integration and local storage | Configure the data app and authorize it as staff |
| AI research | Internal research service | Supply a working Gemini key and supported model |
| Account/support email | Outgoing SMTP integration | Configure a verified sender and SMTP credentials |
| Public frontend gateway | Cloudflare Pages Function | Create the Pages project, custom domain and two gateway values |
| Private frontend | React/Caddy Dockerfile | Supply its HTTPS domain; Docker builds it |
| Google sign-in | Backend authorization-code flow | Add the Google client in Django Admin if you want this button to work |
| Anonymous enquiry verification | Turnstile widget/server validation | Supply matching widget site/secret keys in production |
| Public payments | Razorpay checkout/webhooks | Keep off initially; configure and accept separately |
| Backup/restore | Encrypted local archive scripts | Create a recovery key and copy backups off the server |

Production `deploy.py` currently includes the research service and requires its
Gemini key/token to be configured. Development can leave research disabled.
Google login and paid checkout can be deferred. Production anonymous enquiries
need Turnstile; authenticated Support replies use their existing signed-in flow.

## 3. Prepare the current code before copying it elsewhere

1. Keep your existing `E:\QuantNest` checkout. Do not clone another repository on
   top of it, delete its migrations, or reset it to discard local work.
2. In the IDE's Source Control view, review the current changes. A server clone
   and a Cloudflare Git build receive only code committed and pushed to the chosen
   remote branch. They cannot see uncommitted files on your computer.
3. Commit and push the reviewed code and documentation you intend to release.
   Exclude populated env files, credentials, backups, media, logs and local data.
4. Record the release branch/commit. Public frontend and backend must use the
   same reviewed release. Read the existing CI results before deploying it.
5. If retaining an existing database, make a backup with the tool matching its
   current release before upgrading. For databases from the retired licensing
   version, follow [the migration note](README.md#upgrading-the-former-infrastructure-layout)
   rather than deleting migrations or faking them.

The easiest first deployment is a **new empty Docker database**. Your native
Windows database is not automatically migrated into Docker. The Compose helpers
also do not read `backend/.env` as their operator configuration: each mode has its
own `infra/<mode>/backend.env`.

## 4. Values to decide before production

Write these in a private deployment record/password manager:

| Decision | Example only |
| --- | --- |
| Customer browser domain | `app.example.com` |
| Public backend origin domain | `origin.example.com` |
| Personal browser domain | `personal.example.com` |
| Public server address | Your server's reserved public IP |
| Private server address | This instance's separate server and reserved public IP |
| Oracle region/compartment/shape | Record the actual tenancy allocation and host architecture |
| OCI storage/recovery | Boot volume identity, remaining shared allowance and off-host backup location |
| Reviewed source release | Your pushed commit/tag |
| Support mailbox | An address you can receive and reply to |
| Verified sending address | `no-reply@example.com` |
| Database/credential/recovery secrets | Generated independently for each instance |

`example.com`, `YOUR_*`, `replace-with-*` and sample addresses in these documents
are placeholders. Substitute your actual values. Do not type angle brackets from
a prose placeholder into a command.

## 5. A few words used throughout the guides

| Word | Plain meaning |
| --- | --- |
| Host / VM | The computer running Docker; your laptop or rented server |
| SSH | Encrypted terminal connection from your computer to the server |
| Image | A built copy of application code and its dependencies |
| Container / service | A process running from an image, such as API or execution |
| Compose | Tool that starts the configured group of containers |
| Named volume | Persistent storage outside a container, such as the database |
| Environment file | Local text file of deployment settings and secrets |
| DNS / hostname | Maps a readable domain name to a service/address |
| Origin | The backend server that the Public gateway contacts |
| Callback / redirect URI | Exact URL a provider returns the browser to after login |
| Webhook | Provider-to-server event, for example a captured payment notification |
| Migration | Versioned database schema/data update supplied by the application |
| Scope | Whether this instance permits Paper or personal Live execution |
| Health check | Dependency/process readiness; it does not prove a strategy should trade |

## 6. Keep these operating rules in mind

- Run each command in the location and shell shown by its guide. Production
  examples use the Ubuntu terminal; Development examples use PowerShell.
- Configure all examples before the first deploy. Do not replace real env files
  with examples during an upgrade.
- Start with `API_WORKERS=1` and `EXECUTION_WORKERS=1`. More users need measured
  CPU/memory capacity, not just larger plan limits.
- Docker runs the application processes. Do not also start native execution,
  feed, Terminal, orders or Celery commands against the same deployment.
- Container startup is not provider acceptance. Follow the feature checklist at
  the end of your mode guide.
- `docker compose down` preserves named volumes. Adding `-v` deletes them; it is
  not an upgrade or ordinary restart command.
- Keep PostgreSQL data and the original credential-encryption key together for
  recovery. Replacing the key does not make old encrypted broker tokens readable.

When your selected walkthrough is complete, use the
[operations runbook](shared/scripts/README.md) for upgrades, backups and restores.

## 7. Acceptance and release checklist

Use this checklist for the exact release you intend to deploy. Record the commit,
mode, host, date, fixture/account and outcome for each run. A successful build,
type check or container health check does not prove provider authorization,
strategy correctness, real broker execution or production capacity.

### Development restart and readiness

1. Start or unpause Docker Desktop. Finish any running trading test before a
   planned restart; stopping application processes does not close broker exposure.
2. From `E:\QuantNest`, run
   `.\.venv\Scripts\python.exe infra/development/dev.py --no-build` when only
   source changed. Omit `--no-build` after dependency or image changes. This is the
   normal migration/restart flow, not just a health probe.
3. Run `.\.venv\Scripts\python.exe infra/development/dev.py status`. Require all
   readiness flags to pass and inspect failed services before continuing. Do not
   also start native feed/execution/Celery processes against this deployment.
4. Check which profiles were selected. A configured Live scope also enables
   broker-events; use isolated simulated fixtures for broad acceptance and arrange
   real-account broker verification deliberately.

### Ordinary-user journey

Use two disposable ordinary users, not a staff account with elevated permissions.
Complete the first user's workflow and verify that the second user cannot read,
change, attach, export or act on the first user's private resources.

| Area | Required acceptance evidence |
| --- | --- |
| Authentication | Registration, verification, login, refresh, reset, 2FA/backup code, logout and session revocation; optional Google callback on its configured domain |
| Data | Fresh and stored symbols, older chart history, all supported chart timeframes, correct session/holiday boundaries, reconnect and unavailable-history messages |
| Studio | Save/reopen/validate a version; price/indicator inputs, multi-timeframe rules, formulas, rolling windows, position inputs, capture/confirmation, sizing and entry schedule |
| Backtest | Preview workload, run/cancel, inspect known entries/exits, costs, metrics, pagination and Monte Carlo; distinguish synthetic OHLC observations from actual tick history |
| Paper | Fund wallet, deploy from Strategies, inspect signal/order/fill/P&L, pause/resume, stop and close owned positions, update capital/version and recover after restart |
| Terminal | Named watchlists, all supported order types on both sides, lots/units, modify/cancel, protection, reduce/reverse/close and separate gross/charges/net results |
| Derivatives | Fixed future/option, CE/PE ATM/ITM/OTM grid selection, expiry policy, pinned owned contract, expired history and clearly recorded historical-term assumptions |
| Research | Real configured-provider answer and streaming, calculated/grounded evidence, named watchlist reading, validated draft, strategy-version preview, backtest confirmation, cancellation and token-credit settlement |
| Screener | Compare known conditions with completed-candle calculations; save/reopen screens and verify filtering and server pagination |
| Reports | Journal ownership, review save, realized totals, fee basis and realtime open valuation agree with the underlying records |
| Support | Public enquiry verification, signed-in ticket, staff reply, owned notification and actual production SMTP delivery |
| Commercial | All three allowance categories, failure refunds, original-period charging and provider test-mode payment/webhook/renewal/refund flows |

### Mode and execution checks

Test the actual mode configuration; Development deliberately does not prove
Public quota rejection. Public must enforce inventory, period and per-request
allowances and deny Live admission. Development records usage without enforcing
commercial quotas. Private has no public-plan quotas or public checkout and uses
its enabled execution scopes. Authentication and ownership apply in every mode.

During execution, test simultaneous inputs, duplicate/late broker reports,
partial fills, uncertain submission, reconnect, warmup/history correction and
ordered capital/version/stop commands. Repeated reports must not duplicate fills,
fees or trades. A failed deployment must not stop unrelated accounts. Record
which scenarios used deterministic fixtures and which used real provider data.

For Live, verify broker acknowledgement, actual cumulative fills, rejection,
cancellation, exit, reconnect and order reconciliation with a controlled account.
Local simulations and stubbed broker reports cannot complete that acceptance.
Live results currently exclude actual broker fees and do not provide complete
delivery/assignment settlement. Atomic multi-leg orders and automatic rollover
are not current features. See [Live boundaries](../docs/live-trading.md#release-checks-and-unsupported-behavior).

### Capacity, recovery and beta

1. Measure tick receipt to evaluation, signal, admission, durable write and UI
   delivery separately; record broker transport/fill latency separately. Include
   p50/p95/p99, CPU, memory, instruments, sessions, rule count and warmup size.
   Numerical microbenchmarks alone do not establish concurrent customer capacity.
2. Exercise encrypted backup and restore on a separate empty deployment. Verify
   database rows, media, ownership and credential decryption. Keep execution and
   broker services off on the recovery drill. Never restore over the source.
3. Review the exact feature/market catalog, plan allowances, contact details,
   email/domain/callback settings and customer-facing limitations.
4. Commit the reviewed release and run CI. Publish/deploy only when the chosen
   host, accounts and acceptance gates are ready; retain its matching backup,
   environment keys and image/release identifier.
5. Begin with a small simulation/research beta. Expand users after observing
   measured resource headroom and resolving reproduced failures. Keep a separate
   acceptance record for each managed Private broker deployment.

Private service periods are managed by the operator. Record the agreed start,
renewal date, quotation, capacity and contact owner per instance. Before the end
date, obtain the renewal decision and agree how active positions and pending
orders will be handled. Suspension must follow that procedure; stopping a server
does not close trades. There is no automatic subscription/licence expiry service
in Private.

## 8. Local verification record: 23 November 2026

This record covers the uncommitted working tree based on `51328ef`. It is local
acceptance evidence, not a production release certificate. Test helpers and
fixtures were kept outside the repository; disposable databases, recovery
containers/volumes and temporary browser accounts were removed afterward.

| Verification | Result and scope |
| --- | --- |
| Static checks | 555 Python files: zero Pyright errors/warnings; Django system and migration-consistency checks passed; frontend lint and production build passed |
| Fresh database | All 288 migrations replayed on a separate empty PostgreSQL database |
| Shared numerical runtime | 75 checks: 40 warmed candle operands, ten TA-Lib comparisons, cumulative fills, position inputs, atomic capital/protection rejection and graph handoff; database access forbidden during the numerical checks |
| Expressions and derivatives | 59 further checks: arithmetic, named formulas, rolling calculations, Boolean UNKNOWN, crossings, capture/re-entry/expiry, frozen reward/risk, CE/PE three-strike ITM/OTM selection, lot/tick validation; no database access during evaluation |
| Account workflows | 109 checks in a disposable database: ordinary-user ownership, Studio revisions, watchlists/support, Paper admission and persisted fills/exits/recovery, Terminal admission and persisted fills/exits, synthetic Live cumulative reports and durable writes, AI credits/renewal and explicit watchlist confirmation |
| Runtime/authentication regressions | 86 checks covering SHM, calendar aggregation, all four manual order types on both sides, four-mode ledger/snapshot flows, JSON streams, login/refresh/CSRF/revocation and metrics |
| Billing | 29 checks with mocked payment transport: capture, duplicate delivery, renewal, refund and completion/refund accounting; no real payment initiated |
| Deployment policies/catalog | 52 checks covering Public, Development and Private policy, scopes, pricing, enquiry ownership and catalog validation; all three Compose queue configurations passed; Public and Private Django deployment security checks passed with isolated HTTPS-origin settings |
| Encrypted recovery | Nine checks against a disposable Compose project using the repository backup/restore implementations: archive checksum, exact ledger/candle/media restoration, restored application ownership, applications left stopped and refusal to overwrite a nonempty target |
| Customer-site browser checks | 55 checks across light/dark desktop/mobile pages, Private contact pricing and Billing; no browser exceptions or HTTP 5xx |
| Workspace browser checks | 24 workspace routes in both light and dark themes: 48 checks with no outer horizontal overflow, browser exceptions or HTTP 5xx; temporary ordinary-user session removed afterward |
| Real AI integration | A configured-provider request completed through Django admission, task, separate service and saved answer; its reported 1,790 tokens settled as 1.790 credits; duplicate task delivery made no extra charge; fixture rolled back |

These suites overlap; their check counts are not independent coverage measures.
The backtest persistence check used prepared synthetic candles, Paper/Terminal
used deterministic observations, and Live used synthetic broker reports. None
proves actual broker order transport or exchange fills.

### Measured numerical cost

One Windows 11/Python 3.12.14 process on the 12-logical-CPU development laptop
evaluated a synthetic 20-condition, four-timeframe strategy with 600 prepared
bars per timeframe. The four timeframes were 1m, 5m, 15m and 1H; expressions
combined live LTP with EMA/SMA arithmetic. Across 150 observations per workload:

| Evaluators on the same observation, sequential in one process | p50 | p95 | p99 |
| --- | --- | --- | --- |
| 1 | 0.36 ms | 0.81 ms | 1.21 ms |
| 10 | 2.67 ms | 5.87 ms | 7.12 ms |
| 50 | 29.75 ms | 40.70 ms | 51.30 ms |
| 100 | 58.50 ms | 104.35 ms | 191.95 ms |

This isolates prepared evaluation. It excludes provider delivery, worker IPC,
account admission, durable writes, broker transport/fills and browser delivery.
Host load changes these results. Do not convert them into a supported user count
or a complete tick-to-order latency claim. Repeat the staged measurements in
section 7 on the actual production host with realistic symbols and sessions.

### Findings corrected

- Strategy activate/pause/archive/unarchive now return 404 for an absent or
  foreign strategy instead of exposing an unhandled model lookup as HTTP 500.
- PostgreSQL readiness now checks TCP on 127.0.0.1 in all deployment modes and
  CI. The temporary socket-only initialization server cannot report readiness
  before extensions and the application role have been initialized.
- Deployment now stops application clients before changing PostgreSQL/Redis,
  then migrates and starts the selected stack. Configuration validation and
  optional image building still happen before stopping a working installation.
  Preflight-failure and migration-failure sequencing was checked, and the updated
  Development restart finished with all 12 services running and every diagnostic
  readiness flag passing.
- Stale links to deleted release/implementation documents and obsolete
  derivatives "Coming soon" instructions were replaced with current guides.

### External acceptance still required

At verification time the stored FYERS market-data token had expired. Renew it
using the staff authorization flow in [Integrations](shared/INTEGRATIONS.md#6-fyers-shared-market-data-connection)
before testing actual quotes, history and live ticks. A healthy waiting feed
container does not mean the source is authorized.

Actual Live broker execution, payment-provider test-mode events, Google consent,
production email delivery, full-market-session observation and target-server
capacity still need their configured accounts/domain/host. No real orders,
payments, external support messages or public deployment were performed by this
verification. Private renewal/suspension remains the operator procedure in
section 7, not an automatic licence-enforcement service.
