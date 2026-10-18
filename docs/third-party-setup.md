# QuantNest: third-party configuration and launch guide

**Configuration review: 16 October 2026.** Read this with the [implementation plan](implementation-plan.md), [commercial operations guide](commercial-operations.md) and [runtime reference](execution-technical-reference.md). For complete host commands and each script's purpose, start with the [three-mode infrastructure guides](../infra/README.md). This document owns external account setup; infrastructure READMEs own deployment commands.

This guide distinguishes preparing software from activating external accounts. No merchant account, domain ownership, data permission, Live approval or deployed recovery test is inferred from working code. Configure test accounts first. Keep real secrets out of Git, screenshots, tickets and browser build variables.

Use [Commercial operations](commercial-operations.md) for database initialization,
feature controls, no-code Public plan changes and Private licence renewal, operator actions and
the frontend-to-backend lifecycle of billing, support, consent and licensing.
Migrations create launch terms; provider identifiers and
customer contracts must be configured by the operator. Keep permission evidence
in operating records rather than application approval rows.

## 1. What runs where

| Component | Platform | Responsibility |
| --- | --- | --- |
| Public site and React workspace | One Cloudflare Pages project | Static pages, explicit application rewrites and scoped backend proxy |
| API, PostgreSQL, Redis, workers, market feed and Paper | Oracle A1 Ubuntu ARM64 | Persistent application services |
| Private AI service | Oracle private container/network | Paid Gemini calls and authenticated internal tools |
| Licence/release private keys | Oracle Vault | Signing; installations receive only public verification keys |
| Backups | Oracle Object Storage | Encrypted recovery artifacts; site illustrations are bundled assets |
| Payments | Razorpay | Captured payments, mandates, refunds and authoritative billing periods |
| Email | Brevo | Existing SMTP, authenticated delivery events, newsletter confirmation and inbound support replies |
| Sign-in | Google OAuth | Existing redirect-based OAuth flow |
| Application errors | Application logs | Fixed error categories; no external error service |
| Host monitoring | Oracle Monitoring and Notifications | Readiness, capacity, persistence and backup alarms |
| Historical/streaming observations | Existing FYERS source | Retained pipeline, with purpose-specific permissions |

Private customer hosts follow [Private deployment](../infra/private/README.md) on
their own Linux/Docker platform. They do not need an Oracle account for local
licence verification. Central signing/backup/monitoring setup below applies to
the Public operator; customer host monitoring/backup ownership is agreed separately.

Configure integrations in dependency order: canonical domain/gateway → database
and email → operator authentication and data preparation → approved AI/forms →
payments → Private signing/distribution when offering that service. Google sign-in,
newsletter sync and inbound email are optional. Leave their groups unconfigured
until you intend to support those workflows; basic support still works in-app.

Public Workspace ends at simulated Paper. Private Live activation is separately qualified. Terminal, Paper and Live records remain distinct.

### Initial identity

- Planned domain: `quantnest.site`; it has not yet been purchased or verified.
- Working business name: QuantNest. This is not a claim of incorporation or trademark registration.
- Initial contact: `ayushkaneriya05@gmail.com`.
- Support hours: Monday–Friday, 10 am–6 pm IST, with no response-time SLA.
- After buying the domain, a Brevo-verified sending address does **not** require running your own email server. A real receiving inbox or Brevo inbound domain is a separate configuration.

## 2. Prepare accounts and a configuration inventory

1. Use a password manager. Enable MFA on Oracle, Cloudflare, Razorpay, Brevo, Google and source-control accounts.
2. Keep billing/test and production credentials separate. Use separate callback URLs and provider secrets for staging.
3. Record the owner, purpose, expiry and rotation procedure for every credential.
4. Choose one mode and copy only its environment examples to untracked `backend.env` and `research.env` files. The separate Compose stacks and mode boundaries are documented in [the infrastructure guide](../infra/README.md). Empty values mean an integration is not configured; do not replace them with fake production secrets.
5. Review actual domain/legal/tax/merchant/source/AI arrangements and keep the evidence in your operating records. Publish reviewed plan prices/allowances through Commercial → Catalog revisions.
6. Keep BILLING_ENABLED=False until merchant configuration, webhook acceptance and capacity are ready.
7. Use synthetic data and the Live execution scope disabled while preparing the deployment.

`DEBUG` is a Boolean setting: use `DEBUG=False` for production. Set the separate `QUANTNEST_DEPLOYMENT_MODE` value to `public` or `private`; do not put an environment name such as `release` in `DEBUG`. Use `infra/development` only on developer machines, `infra/public` for the hosted Paper product, and `infra/private` for a licensed customer-owned installation. Do not combine a mode's Compose file with another mode's environment files.

Only public `VITE_` settings belong in the React browser build. They must never contain payment secrets, SMTP passwords, Gemini keys, activation tokens, database credentials or OCI private keys. Compose supplies internal service URLs and mode policy; use the selected mode's examples rather than merging unrelated provider/operator variables.

## 3. Oracle Cloud Infrastructure

### 3.1 Tenancy, region and resource budget

1. Register/sign in to OCI. Enable MFA for the tenancy administrator.
2. Choose the tenancy's **home region** and verify Always Free eligibility and actual quotas in the Console.
3. Create a `quantnest-production` compartment. Keep staging resources/credentials separately scoped.
4. Prepare one Ubuntu ARM64 `VM.Standard.A1.Flex` instance with **2 OCPUs and 12 GB RAM**, matching the agreed host.
5. Use a 50 GB boot volume and a 150 GB data volume only where the actual tenancy confirms the free allocation.
6. Enable usage/budget alerts and compartment quotas. Review the cost estimate before creating any resource. Capacity availability, free quotas and UI labels can change.
7. Keep the deployment conservative: one numerical calculation worker and one heavy compute queue worker initially. Measure the host before increasing admission.

Oracle's current quotas and reclamation conditions are described in [Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm). Free infrastructure is not an uptime guarantee. Do not generate artificial activity to avoid reclamation.

### 3.2 Network and host access

1. Create a VCN, subnet, Internet Gateway and appropriate route table.
2. Allow inbound SSH only from your administrator IP/CIDR. Use an SSH key, disable password authentication and keep the private key in your password manager.
3. Reserve a stable public address for the accepted API/source arrangement.
4. Expose only HTTPS ingress. PostgreSQL, Redis, research endpoints and execution transports must have no public published ports.
5. Restrict origin access at the firewall/security-group layer where feasible and enforce the configured edge token at application ingress.
6. Set host firewall rules consistently with the OCI security list/NSG. An OCI rule alone does not configure the Linux firewall.
7. Mount the data volume at the documented deployment path. Verify its device/UUID and ownership before formatting or mounting; never run a formatting command against an unverified device.
8. Use Ubuntu 24.04 ARM64 and verify `uname -m` reports ARM64/aarch64. After mounting the verified data disk at `/mnt/quantnest-data`, run `sudo bash infra/public/scripts/bootstrap_host.sh /mnt/quantnest-data /opt/quantnest/current`. It installs Docker/Compose, age, the locked OCI operations environment and timer units, and moves Docker's configured data root onto the mounted disk for a fresh host. It does not format a device or migrate an existing Docker installation.
9. Copy `infra/public/operations.env.example` to `/etc/quantnest/operations.env`; give the `quantnest` service user read access and restrict it to mode 600. Create the application environment files directly from the Public examples, owned by the deployment operator with mode 600. Ensure the service user can read the release and its mode environment files.
10. Start the reviewed stack with `python infra/shared/scripts/deploy.py --root . --mode public --build`. Run diagnostics, start `quantnest-backup.service` once and verify its uploaded marker. Then enable `quantnest-backup.timer` and `quantnest-monitor.timer` with `systemctl enable --now`. Confirm the OCI alert subscription before relying on alarms. The timer operations environment is separate from container app secrets.

### 3.3 Storage and backups

1. Create a private Object Storage bucket for backups in the production compartment.
2. Keep public access disabled. Encrypt backup files before upload; retain the decryption identity outside the VM.
3. Configure retention/lifecycle to fit the actual storage quota. The shared archive contains the database (including billing/outbox and local licence records), private media and general/runtime Redis snapshots. Preserve environment files, activation/encryption credentials, public verification keys, TLS material and the exact release separately; they are not included in that archive. There is no separate licence-state volume.
4. Public workflow illustrations and branding are bundled frontend assets. No public media bucket or video-hosting configuration is required for the current customer site.
5. Restore to an isolated environment and verify financial records and runtime recovery. A successful upload is not a tested backup.

The shared restore command uses the Timescale pre/post-restore hooks and restores application ownership after administrator-led recovery. Follow the [TimescaleDB recovery sequence](https://www.tigerdata.com/docs/deploy/self-hosted/backup-and-restore/logical-backup) and test the encrypted format-2 archive against an empty recovery project before production use.

See [Object Storage documentation](https://docs.oracle.com/en-us/iaas/Content/Object/Concepts/objectstorageoverview.htm) and [pre-authenticated requests](https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/usingpreauthenticatedrequests.htm).

### 3.4 Instance principals and permissions

1. Create a dynamic group matching only the intended production instance/compartment.
2. Give narrowly scoped access to the specific backup bucket, licence/release signing keys and monitoring namespace.
3. Do not grant `manage all-resources in tenancy` to the application.
4. Keep separate principals/roles for licence signing, release signing, backups and provisioning when practical.
5. Verify that the runtime can perform its required operation and is denied access to an unrelated bucket/key/secret.
6. Avoid embedding a broad OCI user API private key inside containers. Instance principals use the instance's accepted identity.

Read [instance-principal authentication](https://docs.oracle.com/en-us/iaas/Content/Identity/Tasks/callingservicesfrominstances.htm). An instance principal is shared by processes able to access the instance identity; network/container isolation and IAM scope still matter.

### 3.5 Vault, licence signing and rotation

1. Create a standard shared Vault in the approved compartment; check pricing before selecting a dedicated/virtual-private vault.
2. Create an HSM-protected **ECDSA P-256** licence key. Keep software-release signing on a separate key.
3. Record the key OCID, key-version OCID and cryptographic endpoint.
4. Set `OCI_LICENSE_KEY_ID`, `OCI_LICENSE_KEY_VERSION` and `OCI_SIGNING_ENDPOINT` in the Public backend environment. The SDK derives its region from the instance principal. Put the separate release key's `OCI_RELEASE_KEY_ID`, `OCI_RELEASE_KEY_VERSION` and `OCI_RELEASE_SIGNING_ENDPOINT` in the host operations environment; the [release script guide](../infra/private/scripts/README.md) gives the exact signing command.
5. Export the public verification key for that exact version. Do not export or distribute a private signing key.
6. Store installation verification keys as a JSON mapping from key-version identifier to PEM public key, referenced by `LICENSE_PUBLIC_KEYS_FILE`.
7. The signer uses SHA-256, converts OCI's ECDSA DER signature to the standard 64-byte JWS representation, and produces ES256 tokens.
8. Issue a test lease and verify it locally using the distributed public key. Test wrong installation IDs, altered payloads, stale revisions and unknown keys.
9. Rotation: publish the new public key before issuing with the new version; keep valid older public keys through the overlap period. Track key-version service limits.
10. Keep licences and secrets out of public Object Storage, support tickets and application error events.

Sources: [OCI signing](https://docs.oracle.com/en-us/iaas/Content/KeyManagement/Tasks/usingkeys_topic-To_sign_data_by_using_your_Vault_master_encryption_key.htm), [Python signing contract](https://docs.oracle.com/en-us/iaas/tools/python/latest/api/key_management/models/oci.key_management.models.SignDataDetails.html).

### 3.6 Configuration, monitoring and infrastructure ownership

1. Create application environment files from the selected mode's examples on the host and restrict their ownership/permissions.
2. There is no automatic Vault secret-bundle fetcher in this implementation. Vault signing uses the configured signing key through instance principals; ordinary application secrets remain operator-managed. If adding an external secret manager later, design its startup/rotation behavior explicitly.
3. Keep environment files out of Git, Terraform variables/state, container images and browser builds. Preserve encryption/signing verification material through recovery. Never fetch secrets during tick evaluation.
4. Set alarms for VM memory/CPU, volume capacity, database health, Redis persistence, queue age, worker heartbeat and backup failure.
5. Keep infrastructure logs and sanitised application diagnostics separate. Rotate/bound local logs.
6. Use Resource Manager for reviewed infrastructure code. Pin the OCI provider, inspect its plan, and apply only the reviewed free-eligible resources. Keep state private.
7. Test rebuilding the instance from the repository, configured secrets and encrypted backup rather than depending on the original VM remaining available.

## 4. Cloudflare: domain, Pages, TLS and proxy

### 4.1 Domain and DNS

1. Purchase the domain only after completing name/trademark checks appropriate to your business.
2. Add it to Cloudflare and follow the registrar's nameserver instructions. Verify ownership and propagation.
3. Choose one canonical public origin, for example `https://quantnest.site`. Redirect `www` consistently.
4. Give the Oracle ingress an origin hostname with a valid TLS certificate. Use strict TLS verification rather than disabling certificate checks.
5. Create email DNS records only from the verified Brevo/domain setup instructions; do not guess SPF/DKIM/MX values.

### 4.2 One Pages project

1. Connect the reviewed Git repository to a Pages project.
2. Use repository root as the build root, Node 22.12+ and the locked npm dependencies.
3. Run `npm ci --prefix frontend` and `npm run build --prefix frontend`. The frontend build requires only Node/npm. Plans, features and support labels come from the backend's public catalog at runtime; the builder reference reuses `/api/v1/common/enums/`. There are no JSON exports to generate and no backend request during the build.
4. Set output directory to `frontend/dist`. Use repository root as the build root so the `functions/` directory deploys alongside the static assets.
5. Add public variables from `infra/public/frontend.env.example`: the production site URL and public verification widget key. Set legal name, support email and hours only in the backend environment; both customer pages and workspace load them from the catalog API. There is one React frontend for the full customer site and application.
6. Application requests use `/api/v1/` on the website's origin automatically. No browser API URL environment variable is required; the Pages Function forwards backend routes to `BACKEND_ORIGIN`.
7. Configure separate preview environments. Do not connect a branch preview to production payment keys, private data or Live execution.
8. Verify Home, a documentation page, `/research`, an authenticated deep link, a shared-strategy link and an unknown URL.

The React build produces one entrypoint, lazy-loaded feature pages, a sitemap, robots policy, security headers and explicit frontend rewrites. Cloudflare Functions only handle owned backend routes. Unknown document paths use `404.html` with HTTP 404 and render the themed React recovery page. Routes come from `AppRoutes.jsx`; feature/doc paths expand from their actual frontend content, with no unrestricted fallback. Private Caddy imports the route matcher generated by that same build. Public pages do not initialise trading data sockets.

### 4.3 Pages Function settings

1. Deploy the repository's `functions` directory with the Pages project.
2. Set runtime secret `BACKEND_ORIGIN` to the HTTPS Oracle ingress origin, without an application subpath.
3. Generate a strong random `QUANTNEST_PROXY_TOKEN`. Store the same value in the Pages secret and backend environment; never put it in a `PUBLIC_`/`VITE_` variable. Public mode rejects direct browser calls to the backend. For local public-mode checks, use the Vite gateway described in `infra/development/README.md`; keep production on Cloudflare Pages.
4. The frontend build generates `_routes.json` restricted to API, WebSocket, admin, health and Django static-asset paths. Keep that generated file in the output; other frontend assets and pages are served statically.
5. Configure backend route exhaustion/failure behaviour to fail closed. Do not serve static HTML as a successful API response.
6. Set Django `FRONTEND_URL` and `BACKEND_URL` to the canonical public origin, with appropriate allowed hosts, trusted origins and cookie settings.
7. Verify cookie delivery, login/refresh, POST bodies, a streamed response and WebSocket upgrades through the production origin.
8. Test a direct origin request without the edge token; it must be rejected by the configured public ingress.
9. Rotate the edge token in a coordinated gateway/backend maintenance change. The current backend accepts one configured token; it has no automatic two-token overlap. Confirm the matching value on both sides before restoring traffic.

Cloudflare redirects do not act as an external-origin API proxy; the Function performs that work. [Redirects](https://developers.cloudflare.com/pages/configuration/redirects/), [Functions routing](https://developers.cloudflare.com/pages/functions/routing/), [WebSocket behaviour](https://developers.cloudflare.com/workers/examples/websockets/).

Watch actual Functions requests and CPU usage, including APIs and reconnects. Consult the current [Workers limits](https://developers.cloudflare.com/workers/platform/limits/) and [Pages limits](https://developers.cloudflare.com/pages/platform/limits/) before launch. The current site has no demo video or media-hosting dependency.

### 4.4 Turnstile

1. Create a Turnstile widget for the exact staging/production hostnames.
2. Put its site key in `VITE_TURNSTILE_SITE_KEY` and its secret only in Django `TURNSTILE_SECRET_KEY`.
3. Set `TURNSTILE_HOSTNAMES` to the exact accepted hosts, including a Pages preview hostname only for the isolated preview environment.
4. Enquiry forms use action `enquiry`; newsletter forms use action `newsletter`.
5. Test missing, expired, reused and wrong-host/action responses. Django validates them using Siteverify, not just a browser checkbox.
6. Failed verification should preserve the entered form and offer retry/contact details.

See [server-side validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/).

## 5. Razorpay: test checkout to production billing

### 5.1 Merchant and pricing setup

1. Create/sign in to the merchant account. Enable MFA and complete the required merchant verification/category acceptance.
2. Establish the applicable legal identity, tax/invoicing treatment, support details and refund policy before enabling paid checkout.
3. Start in Test mode. Create a separate test key pair and webhook secret.
4. Set server-only `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` and optionally the previous secret during rotation.
5. Set `BILLING_TAX_BPS` from your reviewed tax decision. Basis points: 100 means 1%. Do not assume zero or a GST rate merely because an example uses it.
6. Keep `BILLING_ENABLED=false` until merchant configuration, webhook acceptance and capacity checks are complete.

### 5.2 Monthly provider plans

1. Create monthly Build and Pro plans with interval one, INR currency and the reviewed checkout total.
2. The launch seed base amounts are ₹499 and ₹1,499. Read the active catalog revision rather than assuming these never change; add only the approved applicable tax.
3. Record each provider plan ID in Operations Admin → Price mappings, linked to the immutable catalog revision, plan, total in paise and tax basis points.
4. Fetch/verify the provider plan before checkout. A mismatched amount/currency/interval is rejected.
5. Protect the founding cohort's accepted price; a new amount may need a new provider plan and renewed mandate authorisation.
6. Do not edit a purchased catalog revision. Publish a new revision for changes and preserve current paid-period terms.

### 5.3 Checkout and callbacks

1. Sign up and verify the test customer's email.
2. Open Billing and Usage, review plan/total/allowances and choose whether to authorise automatic renewal.
3. Automatic checkout creates a provider subscription; manual fallback creates a provider order.
4. Checkout is priced by Django. Never trust a browser-supplied price or `payment.success` message.
5. The browser callback sends only a payment identifier; Django retrieves authoritative provider state and checks ownership, amount and currency.
6. Authorised payments do not grant access. Captured matching payments grant their verified period once.
7. If creation times out, inspect the attempt marked `provider_unknown`. Do not blindly create a replacement mandate/order. Reconcile it using provider records/notes and the QuantNest attempt ID.

### 5.4 Webhook

1. Create a webhook to `https://<canonical-origin>/api/v1/billing/webhooks/razorpay/`.
2. Subscribe to the accepted payment/subscription/refund/dispute events used by your account.
3. Use a strong dedicated webhook secret, separate from the API key secret.
4. QuantNest verifies HMAC-SHA256 over the **raw request body**, retrieves authoritative payment/subscription/refund/dispute state and applies it directly before returning success. It does not store webhook payloads or queue payment-event tasks. Existing payment/refund identifiers prevent duplicate financial application.
5. Test an invalid signature, duplicate event, delayed event and out-of-order authorised/captured events.
6. Keep the old webhook secret during the provider's retry window when rotating.
7. Monitor webhook HTTP failures and unresolved Payment attempts. Provider lookup failures return HTTP 503. Resolve credentials/connectivity and check the attempt through Billing or the Admin reconciliation action; scheduled checkout reconciliation also remains available.

[Razorpay webhook validation/idempotency/order guidance](https://razorpay.com/docs/webhooks/validate-test/).

### 5.5 Renewals, changes, refunds and invoices

1. Test automatic renewal and manual fallback separately. Inspect verified period start/end and usage reset.
2. Cancellation disables future renewal while retaining the paid-through period.
3. Plan changes are scheduled at renewal. Review any changed amount and mandate acceptance before applying it.
4. Submit a first-purchase refund request within the seven-day window. Other applicable remedies remain reviewable.
5. Staff approve processing in Operations Admin. An uncertain refund POST requires provider reconciliation, not a second blind refund.
6. Inspect provider-confirmed refund status, the owned invoice record and credit note.
7. Test abandoned, failed, authorised-only, captured, refunded and disputed scenarios before switching to Live payment keys.
8. Separate Workspace, Private and project receipts in your accounting records. Use the provider's payment statements and application invoices; in-app operator profit/cost reporting is deferred.

The provider's **Live payment mode is unrelated to Live trading capability**. Activating merchant payments does not approve broker execution.

## 6. Brevo: keep SMTP and add service workflows

### 6.1 Existing SMTP

1. Keep the current Brevo account; enable MFA and review its sending limits.
2. Verify an authorised sender. The personal Gmail contact can receive support mail during preparation; production branded sending should use a verified owned domain.
3. Follow Brevo's exact DNS verification instructions for SPF/DKIM/DMARC where applicable. Do not add a second independent SPF record.
4. Set the existing Django `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` and `DEFAULT_FROM_EMAIL` using the Brevo SMTP values.
5. Use the SMTP key for SMTP, not an assumed account login password or API key.
6. Test registration verification, password reset and service notifications with an authorised test address.
7. Keep the Celery default worker running for support emails and newsletter updates. These tasks retry failures up to five times; check worker logs when retries are exhausted. A failure to publish an optional email is logged, while the saved ticket/reply remains available in the workspace.

### 6.2 API and authenticated delivery events

1. Create a scoped Brevo API key; put it only in `BREVO_API_KEY`.
2. Configure a webhook to `/api/v1/support/webhooks/brevo/` for the reviewed delivery/marketing events.
3. Configure Brevo's supported bearer-token authentication. Set the same dedicated token in `BREVO_WEBHOOK_TOKEN`.
4. Test a request without the token and with the wrong token; both must fail.
5. Test a duplicate event, hard bounce and unsubscribe. Marketing withdrawal must not disable essential security/service messages.
6. Track provider delivery events in Operations Admin → Customer support → Email events, and task errors in Celery logs.

Use [Brevo's secured webhook mechanism](https://developers.brevo.com/docs/secured-webhooks); do not assume Razorpay-style webhook signatures.

### 6.3 Newsletter double opt-in

1. Create a dedicated marketing list and approved double-opt-in template.
2. Record `BREVO_NEWSLETTER_LIST_ID` and `BREVO_DOI_TEMPLATE_ID`.
3. Keep newsletter consent separate from registration, checkout and service communication.
4. The form records the policy revision and pending consent, then queues the Brevo confirmation request.
5. Follow the confirmation email. The return route verifies the signed confirmation and provider list/blacklist state.
6. Test confirmation expiry, a reused link, unsubscribe and later withdrawal from account settings.
7. Do not import non-consenting support/custom-development contacts into the marketing list.

[Brevo double-opt-in API](https://developers.brevo.com/reference/create-doi-contact).

### 6.4 Inbound support replies

1. After acquiring the domain, choose a receiving subdomain such as `reply.quantnest.site`.
2. Configure it using Brevo's inbound parse instructions and exact supplied MX records. This is not the same as verifying an SMTP sender.
3. Set `BREVO_INBOUND_DOMAIN` and configure the authenticated inbound webhook at `/api/v1/support/webhooks/brevo-inbound/`.
4. Support acknowledgements/staff replies use a bounded signed Reply-To local part identifying only that ticket.
5. Test an actual reply, a wrong token, a duplicate Message ID, an unrelated recipient and an oversized payload.
6. Inbound email never signs someone in or assigns account ownership based only on the sender address.
7. Attachments/external URLs are not automatically downloaded. Keep broker secrets out of correspondence.

[Brevo inbound parsing](https://developers.brevo.com/docs/inbound-parse-webhooks).

## 7. Google OAuth

1. Open the Google Cloud project used by the existing OAuth integration.
2. Configure the consent screen with the real application name, contact, privacy/terms URLs and approved domains.
3. Use isolated credentials for staging and production. During testing, add authorised test users as required by the project's publication status.
4. Register the exact backend callback from `users/google_auth.py`: `/api/v1/users/auth/google/callback/` on the canonical public origin.
5. Configure the existing server client ID/secret and allowed frontend completion origin. Secrets remain server-side.
6. Test first-time signup, repeat sign-in, denied consent, expired state, invalid redirect and accounts requiring 2FA.
7. Verify the intended internal destination survives authentication. External and protocol-relative destinations must be rejected.
8. A domain purchase/verification does not automatically publish the OAuth application; complete the provider's required consent/publication review.

[Google OAuth web-server guidance](https://developers.google.com/identity/protocols/oauth2/web-server).

## 8. Gemini and the private research service

1. Create/use the reviewed Google project and enable the accepted paid Gemini processing arrangement for private customer content. Follow the separate [research service guide](../research_service/README.md) for its complete API/tool configuration.
2. Review the provider's current data-processing terms and rates for the selected model. Do not assume free-tier processing terms match paid processing.
3. Set `GEMINI_API_KEY` only in the private research service and explicitly set the accepted `GEMINI_MODEL`.
4. Generate a strong `RESEARCH_SERVICE_TOKEN` and configure the same value in Django and FastAPI.
5. Set Django `RESEARCH_SERVICE_URL` to the private service URL, and service `RESEARCH_INTERNAL_API_URL` to the private Django tools endpoint.
6. Keep the FastAPI port private; public users call Django, not the provider or internal tools.
7. Publish the Research feature as Available or Qualified beta when its service, provider configuration and processing arrangement are ready. Paused or Coming soon blocks new research in Public and Private.
8. Confirm budgets: one active turn/user, eight tool attempts, 40,000 aggregate input tokens and 6,000 output/thinking tokens across calls/retries. Unknown failed provider attempts retain conservative budget reservations.
9. Test cancellation, provider timeout, invalid citation, missing evidence and attempted investment recommendations using synthetic/mock inputs first.
10. Reconcile observed usage with provider billing. An unpriced expenditure observation is not proof of free processing or a measured margin.

[Gemini processing/pricing](https://ai.google.dev/gemini-api/docs/pricing), [combined thinking/output ceiling](https://ai.google.dev/gemini-api/docs/thought-signatures).

## 9. Existing FYERS data and qualified broker execution

### Market-data source

1. Retain the current FYERS historical/streaming integration and instrument mappings.
2. Use the existing market-data app credentials/callback from backend configuration; keep its token distinct from customer broker credentials.
3. Configure the exact callback URL in the FYERS app. An active staff administrator starts authentication at `/api/v1/market/fyers/login/`; the callback stores the access token. View its expiry at `/api/v1/market/fyers/token/status/` and complete a fresh sign-in when it expires. Expired, inactive or missing tokens are not refreshed automatically.
4. Check the ingest heartbeat, warmup/coverage, reconnect and closed-candle behaviour on the target host.
5. Obtain and record the necessary usage permissions for display, storage, analytics, simulation, AI processing, downloads and multi-user/Private use.
6. Approve only those `data_*` purposes actually covered. A working token is not redistribution permission.
7. Public explanatory illustrations do not load market data or open trading sockets.

Fyers refresh-token requests, their API endpoint, stored refresh tokens and the unused `FYERS_PIN`/`BROKER_FYERS_PIN` settings have been removed. Broker execution sessions also use fresh broker sign-in after expiry. Apply the `marketdata.0007` and `brokers.0010` schema migrations and restart backend, Celery and runtime processes together after upgrading.

#### Local market-data authorization

1. With the default Development configuration, open `http://localhost:8000/api/v1/market/fyers/login/`.
2. If starting on `127.0.0.1`, the login redirects to the configured callback origin before setting its verification cookie. Hostnames have separate cookies; sign in on the resulting `localhost` administrator page when prompted. Administrator OTP setup follows the [authentication guide](authentication.md).
3. Finish FYERS authorization in the same browser within ten minutes. The callback checks the signed state, browser cookie, current staff account and one-time nonce before exchanging the code. It does not depend on a workspace JWT remaining valid during this redirect.
4. A completed callback clears the flow cookie and opens the frontend. Old callback URLs, expired state or previously used authorization codes cannot be replayed; start a fresh login.
5. In Public mode, use the canonical gateway origin for both login and `FYERS_REDIRECT_URI`. For local Public development through Vite, register `http://localhost:5173/api/v1/market/fyers/callback/` with FYERS and use that gateway. Production requires HTTPS. Do not bypass trusted ingress for the callback.

Errors distinguish a missing cookie, replaced sign-in, expired state and reused
authorization. A missing cookie usually means a changed hostname/browser or
blocked cookies. The sign-in route is included in the error response so an operator
can restart the flow. Do not copy authorization codes or state into logs or tickets.

### Private broker integration

1. Public Workspace does not activate broker Live execution.
2. Record the accepted Private contract, classification, broker arrangement, source permissions, approved release and execution verification.
3. Configure the customer broker application/callback/static-IP and authentication requirements for the accepted hosting route.
4. Test account-scoped order matching, the verified QN tag fallback, saved-session ownership, cumulative fills, REST/WebSocket reconciliation, unknown outcomes and protective reductions.
5. Keep unmatched activity outside strategy P&L. Do not overwrite individual strategy positions from account-wide broker totals.
6. Enable the Live scope only after separate acceptance and broker qualification. Customer hosting is a deployment choice, not a compliance exemption.
7. Verify direct broker access and incident procedures remain available independently of commercial renewal.

No TrueData account, key, adapter or replacement source is required by this implementation.

## 10. Monitoring without extra providers

1. Use the Public Oracle monitoring timer and Terraform alarms described in [host operations](../infra/public/scripts/README.md).
2. Confirm the Oracle Notifications subscription. Verify missing-metric, database, worker, persistence, disk and overdue-backup alerts on the real host.
3. Inspect bounded container logs using the mode-specific Compose commands. Browser errors send fixed categories to these logs; no external error SDK is configured.
4. Product usage and website visits are not tracked. Account erasure and retention controls still apply to saved service records.
5. Private operators run the shared diagnostics and connect their own host monitoring. No Oracle account or external heartbeat service is required on a customer server.

## 11. Production activation and evidence

Before accepting customers, record evidence for:

- Domain ownership, canonical TLS origin and functional callbacks.
- Legal identity/contact/tax/refund decisions and processor agreements.
- Merchant acceptance, mandate behaviour and sandbox payment scenarios.
- Purpose-specific FYERS data rights and paid AI processing review.
- Verified Brevo sender, confirmation and receiving-domain workflows.
- Actual ARM64 image startup and resource admission measurements.
- Restored encrypted backups and worker/crash recovery.
- Privacy/tenant isolation, owned exports and safe account shutdown.
- Separate Private contract/licence and independently accepted Live qualification.

The software can be configured before these external prerequisites exist. Keep the affected feature in qualified beta/unavailable and checkout disabled until they are accepted. Record public, Private non-live and Private Live readiness separately.

## 12. Quick troubleshooting map

| Symptom | Check |
| --- | --- |
| Pages returns an API HTML page | Explicit `_routes.json`, Function deployment and fail-closed setting |
| Origin requests are rejected | Canonical origin, TLS, matching edge token and scoped trusted-proxy handling |
| Login/refresh loops | Same-origin API base, secure cookies, CSRF token/trusted origins and callback URLs |
| Checkout unavailable | BILLING_ENABLED, merchant credentials, catalog price mapping and measured capacity |
| Paid access not applied | Captured provider state, amount/currency, owned Payment attempt, webhook HTTP errors and checkout reconciliation |
| Duplicate renewal/refund concern | Provider notes/receipt and persisted attempt/payment/refund IDs; never repeat an uncertain POST blindly |
| Support email not sent | SMTP credentials/sender, provider limit, Celery default worker, API publication errors and worker retry logs |
| Newsletter remains pending | DOI template/list, signed return link and provider contact/list/blacklist state |
| Support email reply ignored | Receiving MX/domain, bearer token, signed Reply-To and duplicate Message ID |
| Research unavailable | Remaining numeric allowance, Private licence validity where applicable, service health/token and model/budget configuration |
| Licence unavailable | Exact installation ID, public-key version, paid-through/lease/grace, clock and highest revision |
| Paper remains blocked after renewal | Explicit resumption, current inventory limits and independent risk/manual restrictions |

Use redacted diagnostics. Do not paste provider secrets into support tickets or logs.
