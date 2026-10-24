# Your deployment checklist: start here

**Repository and provider documentation reviewed: 24 October 2026.**

These guides explain the actions you, the operator, need to take. They start from
the current repository and finish with a configured platform. You do not need to
install PostgreSQL, Redis, Celery or Python application packages manually when
following the Docker procedure.

## 1. Choose the guide

| What you want to do | Follow this walkthrough | Where you run it |
| --- | --- | --- |
| Learn and develop on your Windows computer | [Development setup](development/SETUP.md) | PowerShell, from `E:\QuantNest` |
| Run the customer website with research, backtests and Paper | [Public setup](public/SETUP.md) | Ubuntu server plus Cloudflare dashboard |
| Run your own personal Paper/Live instance | [Private setup](private/SETUP.md) | A separate Ubuntu server and your browser |

Do Development first. Then choose Public, Private, or both on separate servers.
Public and Private use different databases, credentials and users. Logging into
one does not create an account or copy strategies in the other. Both use the same
site, registration and workspace interface; execution scopes control access.

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
| Private server address | Your separate personal server's reserved public IP |
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
