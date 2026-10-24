# QuantNest: third-party configuration and launch guide

For the ordered beginner procedure, use [Start here](../infra/START-HERE.md)
and [Integration setup](../infra/shared/INTEGRATIONS.md). The mode-specific
`SETUP.md` files own first-deployment instructions; this document retains the
deeper provider and broker contract reference.

**Configuration review: 16 October 2026.** Read this with the [implementation plan](implementation-plan.md), [commercial operations guide](commercial-operations.md) and [Live trading guide](live-trading.md). For complete host commands and each script's purpose, start with the [three-mode infrastructure guides](../infra/README.md). This document owns external account setup; infrastructure READMEs own deployment commands.

This guide distinguishes preparing software from activating external accounts. No merchant account, domain ownership, data permission, Live approval or deployed recovery test is inferred from working code. Configure test accounts first. Keep real secrets out of Git, screenshots, tickets and browser build variables.

Use [Commercial operations](commercial-operations.md) for database initialization,
feature controls, no-code Public plan changes and personal Private setup, operator actions and
the frontend-to-backend lifecycle of billing, support, account privacy and deployment.
Migrations create launch terms; provider identifiers and
customer contracts must be configured by the operator. Keep permission evidence
in operating records rather than application approval rows.

## 1. What runs where

| Component | Platform | Responsibility |
| --- | --- | --- |
| Public site and React workspace | One Cloudflare Pages project | Static pages, explicit application rewrites and scoped backend proxy |
| API, PostgreSQL, Redis, workers, market feed and Paper | Oracle A1 Ubuntu ARM64 | Persistent application services |
| Private AI service | Oracle private container/network | Paid Gemini calls and authenticated internal tools |
| Backups | Operator-managed off-host storage | age-encrypted PostgreSQL/media archives |
| Payments | Razorpay | Captured payments, mandates, refunds and authoritative billing periods |
| Email | Brevo | SMTP for account and support notifications |
| Sign-in | Google OAuth | Existing redirect-based OAuth flow |
| Application errors | Application logs | Fixed error categories; no external error service |
| Host monitoring | Oracle Monitoring and Notifications | Readiness, capacity, persistence and backup alarms |
| Historical/streaming observations | Existing FYERS source | Retained pipeline, with purpose-specific permissions |

The personal Private host follows [Private deployment](../infra/private/README.md).
It has no central activation dependency. Public and personal hosting use separate secrets, data and backups.

Configure the domain/gateway first, then database/email, operator authentication
and market data, AI/forms, and finally payments. Google sign-in can be configured
when needed. Customer Support replies use the workspace, with SMTP notifications.

Public Workspace ends at simulated Paper. Personal Live uses its own broker authorization; customer Live is not offered. Terminal, Paper and Live records remain distinct.

### Initial identity

- Planned domain: `quantnest.site`; it has not yet been purchased or verified.
- Working business name: QuantNest. This is not a claim of incorporation or trademark registration.
- Initial contact: `ayushkaneriya05@gmail.com`.
- Support hours: Mondayâ€“Friday, 10 amâ€“6 pm IST, with no response-time SLA.
- After buying the domain, a Brevo-verified sending address does **not** require running your own email server. A receiving inbox is separate from sending mail; customers reply to tickets through workspace Support.

## 2. Prepare accounts and a configuration inventory

1. Use a password manager. Enable MFA on Oracle, Cloudflare, Razorpay, Brevo, Google and source-control accounts.
2. Keep billing/test and production credentials separate. Use separate callback URLs and provider secrets for staging.
3. Record the owner, purpose, expiry and rotation procedure for every credential.
4. Choose one mode and copy only its environment examples to untracked `backend.env` and `research.env` files. The separate Compose stacks and mode boundaries are documented in [the infrastructure guide](../infra/README.md). Empty values mean an integration is not configured; do not replace them with fake production secrets.
5. Review actual domain/legal/tax/merchant/source/AI arrangements and keep the evidence in your operating records. Publish reviewed plan prices/allowances through Commercial â†’ Catalog revisions.
6. Keep BILLING_ENABLED=False until merchant configuration, webhook acceptance and capacity are ready.
7. Use synthetic data and the Live execution scope disabled while preparing the deployment.

`DEBUG` is a Boolean setting: use `DEBUG=False` for production. Set the separate `QUANTNEST_DEPLOYMENT_MODE` value to `public` or `private`; do not put an environment name such as `release` in `DEBUG`. Use `infra/development` only on developer machines, `infra/public` for the hosted Paper product, and `infra/private` for a personal production instance. Do not combine a mode's Compose file with another mode's environment files.

Only public `VITE_` settings belong in the React browser build. They must never contain payment secrets, SMTP passwords, Gemini keys, database credentials or OCI private keys. Compose supplies internal service URLs and mode policy; use the selected mode's examples rather than merging unrelated provider/operator variables.

## 3. Linux host and recovery storage

Prepare a Linux Docker host with a stable address, persistent disk and enough
memory for the configured limits and image builds. An Oracle VM is one hosting
option; provision it through the console using your actual tenancy capacity and
budget. Application deployment does not require Terraform, Vault, OCI SDKs or
instance-principal IAM policies.

Install Docker/Compose, Python 3.12 and age. Restrict administration access and
open 80/443 for Caddy HTTPS. Database/Redis/research ports stay private. For Public,
keep the Pages gateway token configured; for Private use the direct personal
Caddy hostname. Environment files are managed by the operator and kept out of Git.

Follow [Public setup](../infra/public/README.md) or
[Private setup](../infra/private/README.md). The
[shared runbook](../infra/shared/scripts/README.md) documents encrypted database/media
backups, an off-host copy and empty-database recovery. Keep encryption keys and
reviewed image tags separately. No cloud upload or monitoring timer is installed.

## 4. Cloudflare: domain, Pages, TLS and proxy

### 4.1 Domain and DNS

1. Purchase the domain only after completing name/trademark checks appropriate to your business.
2. Add it to Cloudflare and follow the registrar's nameserver instructions. Verify ownership and propagation.
3. Choose one canonical public origin, for example `https://quantnest.site`. Redirect `www` consistently.
4. Give the backend ingress a DNS-only origin hostname pointing at the Docker host. Open 80/443 so Caddy can obtain its publicly trusted certificate.
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
4. Enquiry forms use action `enquiry`.
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
2. The launch seed base amounts are â‚¹499 and â‚¹1,499. Read the active catalog revision rather than assuming these never change; add only the approved applicable tax.
3. Record each provider plan ID in Operations Admin â†’ Price mappings, linked to the immutable catalog revision, plan, total in paise and tax basis points.
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

## 6. Brevo SMTP

### 6.1 Existing SMTP

1. Keep the current Brevo account; enable MFA and review its sending limits.
2. Verify an authorised sender. The personal Gmail contact can receive support mail during preparation; production branded sending should use a verified owned domain.
3. Follow Brevo's exact DNS verification instructions for SPF/DKIM/DMARC where applicable. Do not add a second independent SPF record.
4. Set the existing Django `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` and `DEFAULT_FROM_EMAIL` using the Brevo SMTP values.
5. Use the SMTP key for SMTP, not an assumed account login password or API key.
6. Test registration verification, password reset and service notifications with an authorised test address.
7. Keep the Celery background worker running for support emails. These tasks retry failures up to five times; check worker logs when retries are exhausted. A failure to publish an optional email is logged, while the saved ticket/reply remains available in the workspace.

Customers reply through workspace Support; staff reply in Admin. Brevo SMTP sends the existing support notifications. No inbound email webhook or receiving domain is required by the application.

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

The FYERS adapter admits subscriptions after a successful server `cn` message,
which the [FYERS Data Socket documentation](https://fyers.in/api-docs/v3/api/websockets/data-socket/overview/data-socket-connect-and-subscribe/)
identifies as a connection message. This avoids sending subscriptions before a slow
SDK reconnect actually opens. Reauthentication resets cumulative-volume baselines
and forces history preparation before the feed is considered ready for execution.
The subscription thread's heartbeat is separate from each symbol's observations.
Inspect subscription state and incoming ticks when diagnosing frozen prices;
quiet symbols do not lose price validity after a fixed age threshold.

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
2. Record the personal broker/data arrangements, server setup and reviewed release.
3. Configure the personal broker application/callback/static-IP and authentication requirements for the accepted hosting route.
4. Test account-scoped order matching, the verified QN tag fallback, saved-session ownership, cumulative fills, REST/WebSocket reconciliation, unknown outcomes and protective reductions.
5. Keep unmatched activity outside strategy P&L. Do not overwrite individual strategy positions from account-wide broker totals.
6. Enable personal Live only after verifying applicable broker requirements. Private mode does not establish a compliance exemption.
7. Verify direct broker access and incident procedures remain available independently of the application.

No TrueData account, key, adapter or replacement source is required by this implementation.

### 9.3 FYERS wire contracts and adding a broker

Reviewed on 19 October 2026 against the official V3 references and the installed,
pinned Python SDK `fyers-apiv3==3.1.18`. This covers the APIs QuantNest consumes;
unused holdings, trade-book, position-book, smart-order and GTT APIs are not added.

#### Exact vendor formats

| Operation | Format used by QuantNest | Official reference |
| --- | --- | --- |
| OAuth redirect | `auth_code`, `state`; exact registered redirect URI | [Generate auth code](https://fyers.in/api-docs/v3/api/authentication/individual-app/generate-auth-code/) |
| Token exchange | SDK `set_token` then `generate_token`; successful `s` and `access_token` | [Validate auth code](https://fyers.in/api-docs/v3/api/authentication/individual-app/validate-auth-code/) |
| Profile | `data.name`, `fy_id`, `email_id`, `mobile_number` | [Profile](https://fyers.in/api-docs/v3/api/account/profile/) |
| Capital ledger | `fund_limit`, exact `title`, `equityAmount` | [Funds](https://fyers.in/api-docs/v3/api/account/funds/) |
| Submit | `symbol`, `qty`, numeric `type`/`side`, `productType`, prices, `DAY`, disclosed quantity, AMO flag, tag, slicing flag | [Single order](https://fyers.in/api-docs/v3/api/trading/order-placement/sync/single-order/) |
| Cancel | `DELETE /api/v3/orders/sync` with JSON `id`; inspect `s`, `code`, `message` | [Cancel single order](https://fyers.in/api-docs/v3/api/trading/order-management/sync/cancel-single-order/) |
| Order book | `orderBook` list; `id`, `exchOrdId`, `qty`, `filledQty`, `remainingQuantity`, `tradedPrice`, `status`, `side`, `symbol`, `productType`, `orderTag` | [Order schema](https://fyers.in/api-docs/v3/api/trading/order-book/get-order-by-order-id/) |
| Order stream | Only SDK `OnOrders`; callback `{s, orders}` with the same camel-case order keys | [Order events](https://fyers.in/api-docs/v3/api/websockets/general-socket/general-socket-order-events/) |
| Broker clocks | `orderDateTime`: IST `DD-MMM-YYYY hh:mm:ss`; raw `update_time_epoch_oms` retained by the SDK mapper as `brokerUpdateTime` | [Socket mapping](https://fyers.in/api-docs/v3/api/websockets/general-socket/overview/general-socket-subscribe/) |
| Quote snapshot | Check top-level `s`, then each `d` entry's `s`/`n`; read `v.lp`, OHLC, changes, volume and epoch `tt` | [Quotes](https://fyers.in/api-docs/v3/api/market-data/quotes/) |
| History | Explicit timeframe mapping; `date_format="0"`, epoch-string bounds, `cont_flag="1"`; six-value candle arrays | [History](https://fyers.in/api-docs/v3/api/market-data/historical-data/) |
| Streaming symbols | Dictionary `type="sf"`, `ltp`, day OHLC, `vol_traded_today`, `last_traded_time`, quantity and average price | [Symbol update](https://fyers.in/api-docs/v3/api/websockets/data-socket/data-socket-symbol-update/) |
| Streaming indices | Dictionary `type="if"`; price/day fields, without trade time or volume. Local receipt time timestamps the observation; volume delta is zero | [Index update](https://fyers.in/api-docs/v3/api/websockets/data-socket/data-socket-indices-update/) |
| Market status | NSE equity matches `exchange=10`, `segment=10`, `market_type="NORMAL"`, `status="OPEN"` | [Market status](https://fyers.in/api-docs/v3/api/market-information/market-status/) |
| Instrument master | Ticker-keyed JSON; documented camel-case identity, contract and trading fields. Expiry uses epoch seconds; `lastUpdate` uses `YYYY-MM-DD` | [Symbol Master JSON](https://fyers.in/api-docs/v3/api/market-information/symbol-master/symbol-master-json/) |

The seven public master files were also inspected for their actual key/value
types. Presentation fields `short_name`, `display_format_mob`, `has_options` and
`has_futures` come from those public files; they are optional. No alternate field
names are probed. Invalid required fields fail mapping instead of silently
assigning NSE, stock type, a lot size or a tick size.

The SDK can deliver a transport exception to its error callback as well as a
protocol-error dictionary. That vendor boundary logs either value; only a
dictionary carrying the known `invalid_symbols` key changes the subscription set.
Required trading and market payloads each have one schema. Optional unfilled-order
fields may be absent in an initial acknowledgement and remain zero/empty until the
broker reports a fill or exchange ID; that does not fabricate a trade.

Placement and cancellation use direct HTTPS requests to the documented synchronous
endpoint with `Authorization: app_id:access_token`, a JSON body and a ten-second
timeout. The pinned SDK catches request exceptions and fabricates error responses;
using that for mutations would lose the distinction between broker rejection and
an unknown transport outcome. Network, malformed-response and server failures now
propagate to the existing recovery path. Explicit broker JSON errors remain broker
errors; response code `201` remains unacknowledged. Other REST operations and both
socket transports use the pinned SDK.

This calls the same FYERS API as SDK `place_order`/`cancel_order`; the direct path
preserves request exceptions and applies a finite timeout. It is not a measured
latency advantage over the SDK. An unknown submission must be reconciled before
another order is sent for that request.

#### Funds and order semantics

- Cash maps to Clear Balance; available margin to Available Balance; used margin
  to Utilized Amount; collateral to Collaterals; realized P&L to Realized Profit
  and Loss. Exact title lookup preserves zeros and negatives.
- `net_equity` is the existing schema's name for Total Balance in the capital
  ledger. It is not demat asset valuation. Commodity balances are not added to
  equity balances; current execution is NSE stock execution.
- FYERS Funds does not report withdrawable cash or unrealized P&L. Both are null
  in new snapshots; the migration clears the old guessed FYERS values.
- Place-order response `201` remains UNKNOWN pending reconciliation, including
  when a broker ID is present. It is not safe to submit the same request again.
- `isSliceOrder=False` keeps one local order mapped to one broker order. Live
  submission still supports MARKET only; no unsupported order modes are inferred.
- A cancel acknowledgement does not write fills. Order observations establish
  final state. REST and WebSocket use the same cumulative-fill handler.
- Broker order time and broker event time remain separate from local receipt
  time. See [timestamp handling](live-trading.md#broker-timestamps)
  for the limits of reconstructing historical execution times.

#### Source ownership and common interfaces

| File | Responsibility |
| --- | --- |
| `backend/brokers/base.py` | Broker-neutral interface, local session validity, verification, JSON conversion, API log storage |
| `backend/brokers/services.py` | One adapter registry; customer connection, activation, account metadata, session and funds-snapshot orchestration |
| `backend/brokers/fyers.py` | `FyersAuth` for individual-app OAuth; `FyersAdapter` uses each credentialâ€™s App ID/Secret for trading REST and streams |
| `backend/brokers/websocket/base_websocket.py` | Common connection state and normalized order callbacks |
| `backend/brokers/websocket/fyers_websocket.py` | FYERS SDK connection, `OnOrders` subscription and SDK mapper extension |
| `backend/marketdata/providers.py` | Select the configured market-data provider |
| `backend/marketdata/fyers.py` | FYERS quote/history/status APIs and market socket transport/normalization |
| `backend/marketdata/live_feed.py` | Provider-neutral subscriptions, history preparation, memory buffers and UI publication |
| `backend/instruments/fyers.py` | FYERS master URLs, source filters and instrument decoding |
| `sync_instruments` management command | Provider-neutral download orchestration and database upserts/cleanup |

Every broker adapter returns these common shapes:

1. `connection_details()` returns the registered installation callback URL for setup. `generate_auth_url(state)` accepts signed browser state from the common connection view. The adapter's `configuration_serializer` validates that broker's credential fields; the common API selects it by `broker_name`.
2. `get_profile()` returns `name`, `account_reference`, `email`, `mobile`.
   The customer UI and credential verification consume those keys directly.
3. `get_funds()` returns `cash_balance`, `available_margin`, `used_margin`,
   `collateral`, `withdrawable_balance`, `net_equity`, `realized_pnl`,
   `unrealized_pnl` and `raw_payload`. Monetary fields are Decimal or explicitly
   nullable where the database supports it; API serialization converts Decimals
   to strings. `record_funds_snapshot()` does not decode vendor payloads.
4. `get_orderbook()` returns canonical order dictionaries. Its order stream emits
   the same dictionary: broker/exchange IDs, tag, symbol, product, side, quantities,
   cumulative average price, local status, rejection text and ISO broker clocks.
5. `place_order(payload, session)` accepts QuantNest's instrument, side, quantity,
   MARKET order type, product and unique order tag. It returns canonical broker ID,
   exchange ID, status and message. An acknowledgement is not a fill.
6. `create_order_stream()` returns a `BaseBrokerWebSocket` implementation. Connect,
   disconnect, subscription and order callback registration have one interface.

To integrate another broker:

1. Add its class in `backend/brokers/<broker>.py`, subclassing
   `BaseBrokerAdapter`. Implement its authentication, profile, funds, submission,
   cancellation, orderbook and stream factory. Keep its SDK, key mappings,
   timestamps, product/status codes and request limits inside that integration.
2. Implement its stream adapter in `backend/brokers/websocket/`; normalize events
   before emitting them. Subscription names and SDK callbacks belong there.
3. Register the class in `BROKER_ADAPTERS`, and add/enable its public connection
   metadata in `BROKER_CATALOG`. Add credentials and a callback appropriate for
   that broker's real authorization protocol, rather than reusing FYERS's route.
4. Preserve account-scoped order IDs, verified tags, cumulative fill values and
   the saved QuantNest session. Keep ambiguous submissions pending recovery.
   Do not import broker net positions into strategy positions.
5. Follow the execution acceptance checks in the reference before enabling Live.
   Adding an adapter does not itself add futures/options, a new calendar, symbol
   identity or market routing support.

#### Operator upgrade and daily authorization

1. Stop the API, Celery and runtime services using your selected mode's guide.
2. Install the pinned backend dependencies and run `python manage.py migrate`
   from `backend/`. This includes `brokers.0012_documented_fyers_contracts` and
   `marketdata.0008_documented_fyers_contracts` and `brokers.0013_individual_app_credentials`. No manual Admin data insertion
   is required for these changes.
3. Set `FYERS_CLIENT_ID`, `FYERS_SECRET` and the exact market-source callback.
   The adapter declares the enhanced source-account limits directly: 5,000 Data
   Socket symbols and 500,000 Data API requests per day. Shared request pacing is
   120 ms (within 10 requests/second and 500/minute). There is no plan setting.
   Quotes, history and SDK symbol conversion share this Redis request budget.
   The provider still controls available history and access to expired contracts.
   The current application uses minute/daily history and SymbolUpdate; the extra
   seconds-history and TBT entitlements do not require another runtime service.
   For Live, each user creates an individual FYERS app and saves its App ID and
   App Secret through Broker Integration. Global trading App ID/Secret settings
   have been removed. `BROKER_FYERS_REDIRECT_URI` remains the installation-wide
   callback, defaulting to `BACKEND_URL` plus the broker callback path.
4. Start the API. Complete source authorization using the staff flow above and
   broker setup through **Broker Integration â†’ Connect â†’ Save and connect** for each user.
5. Start/restart the `market-data` runtime after source authorization, then the
   remaining services for your mode. An existing market socket does not acquire a
   newly stored source token automatically. Broker-events supervision notices a
   new broker session and recreates that account's order stream.
6. FYERS documents daily expiry at 06:30 IST. `FyersAuth` stores the next such
   boundary; there are no guessed `expires_in`, `expiresIn` or alternate token
   keys. Authorize again after the daily boundary and restart the market-data
   runtime after the new source token is stored. Broker token expiry follows the
   same provider schedule. Existing expiry records change on fresh authorization.

An individual FYERS app serves its creator. QuantNest now implements that ownerâ€™s
app connection, with backend token exchange. A saved secret is never returned to
React; it is entered once through the authenticated configuration form and
encrypted in the database. An individual app is not permission to operate a
centrally hosted third-party trading service. Follow the arrangement applicable
to the actual deployment; see [FYERS app types](https://fyers.in/api-docs/v3/getting-started/create-an-app/).

### 9.4 Individual-app connection: step by step

QuantNest now supports **each user bringing their own FYERS individual API app**.
It does not use one shared QuantNest trading App ID/Secret. Source authorization
remains the administrator's separate `MarketDataToken` connection; connecting a
broker does not replace the platform's data source or create another market feed.

#### What the installation operator configures

1. Configure `BACKEND_URL` and `FRONTEND_URL` for this installation. Use HTTPS
   outside local development. The default trading callback is:
   `BACKEND_URL` + `/api/v1/brokers/credentials/fyers/callback/`.
2. If the externally reachable callback differs, set
   `BROKER_FYERS_REDIRECT_URI` to that exact URL. It must use the same callback
   path and have no query string, fragment or credentials. The workspace reads
   this configured URL from the broker catalog and displays it for copying.
3. Use the same browser hostname for API requests and the callback. Local Vite
   normally proxies the API on `localhost`; a login started against `127.0.0.1`
   cannot return its cookie to `localhost`. Keep the frontend proxy and callback
   on the same hostname. A Private installation normally uses one HTTPS origin.
4. Establish the execution server's approved public outbound static IP. Give the
   owner that address for their FYERS app configuration. Order requests originate
   from the execution backend, not from the customer's browser address.
5. Configure `CREDENTIAL_ENCRYPTION_KEYS` before saving app credentials. Back up
   the database together with its encryption keys. Rotation uses the existing
   `rotate_credential_encryption` command; there is no plaintext secret fallback.
6. Use the mode's execution scope and personal broker setup for Live. App
   configuration alone does not grant Live execution. Public Workspace keeps
   its existing scope boundary.

No global trading App ID or App Secret belongs in an environment file. The
source's `FYERS_CLIENT_ID`/`FYERS_SECRET` remain required for the separate source
integration. These are not used for customer trading requests.

#### What each user does

1. Sign in to their own FYERS API dashboard and create an **Individual App**.
   FYERS documents this app type for its creator's own trading account.
2. Open QuantNest **Broker Integration â†’ Connect**. Copy the exact Callback URL
   shown in the setup dialog into the FYERS app's Redirect URL.
3. Configure the approved execution-server static IP and Order Placement
   permissions in FYERS. These permissions include transaction information needed
   for account verification, funds and order reconciliation. Source market-data
   permissions/configuration remain separate.
4. Copy the complete FYERS **App ID**, including its suffix, and **App Secret**
   into the QuantNest dialog. The App ID is not the FYERS trading-account ID.
5. Select **Save and connect**. QuantNest saves the secret encrypted, creates a
   signed browser-bound sign-in request and redirects to FYERS.
6. Enter the account's password/OTP only on FYERS. After authorization, FYERS
   redirects to the registered QuantNest callback with `auth_code` and `state`.
7. The backend verifies the browser cookie, state signature, fifteen-minute
   window, active owner, unchanged saved app credentials and single-use nonce.
   It exchanges the code using this user's App ID/Secret and verifies the profile.
8. A successful connection becomes active and the workspace returns to Broker
   Integration. Broker-events supervision starts or recreates its order stream
   using `saved App ID:that credential's access token`.
9. Review the account details and session expiry before deploying a Live strategy.
   A connection does not automatically start stopped/paused strategies.

The browser does not store the App Secret in local/session storage. The API never
returns a saved secret. The dialog clears the entered value after saving, and
the Admin connection screen only displays metadata. Activity History records
which credential fields changed without storing their values.

#### Reconnect and change app settings

- **Reconnect:** use the existing saved app; no secret entry is needed. Complete
  a new FYERS sign-in after token expiry. The documented daily boundary is
  06:30 IST. A new broker session replaces the old token and causes its supervised
  order stream to reconnect; order/account history stays with the same credential.
- **App settings:** enter the App ID and a replacement App Secret. Leaving the
  secret blank keeps it only when the App ID is unchanged and a secret is saved.
  A new App ID always requires its matching secret.
- **Changing app credentials:** stop running/stopping Live sessions, close open
  positions and reconcile all nonterminal orders first. The server rejects a
  change while these resources depend on the current app. An ordinary reconnect
  with unchanged app credentials can still recover an expired live connection.
- Saving a changed app/secret invalidates its existing broker sessions and clears
  active/verified flags. Any older in-progress callback is rejected. Finish a new
  authorization; the broker stream will use the newly saved App ID/token.
- Sign-in must return the same broker account already linked to this connection.
  App replacement can authorize the same account, but cannot silently reassign
  historical orders, positions or trades to another FYERS account.
- **Disconnect:** retains app settings for reconnect and invalidates sessions;
  the existing session-stop behaviour remains. It does not claim broker-side
  positions have been closed. Use broker access separately when needed.

#### API and code ownership

| User action | API | Backend owner |
| --- | --- | --- |
| Load connection cards / callback URL | `GET /api/v1/brokers/credentials/catalog/` | `BrokerService.get_broker_catalog`; adapter `connection_details` |
| Save app credentials | `POST /api/v1/brokers/credentials/configure/` | `BrokerConfigurationSerializer` and `configure_connection` |
| Start / repeat authorization | `POST /api/v1/brokers/credentials/<id>/connect/` | Owned connection action; signs state and sets an HttpOnly cookie |
| Complete FYERS redirect | `GET /api/v1/brokers/credentials/fyers/callback/` | State/cookie checks, `FyersAuth`, profile verification, owned session |
| Disconnect | `POST /api/v1/brokers/credentials/<id>/disconnect/` | Common connection/session lifecycle |

Configuration JSON contains `broker_name`, `client_id`, and `api_secret`; the
last field is optional only when retaining a saved secret. Responses include
metadata and App ID, without the secret. Credential list/detail endpoints are
read-only. Duplicate raw CRUD, `auth-url`, `create-session`, and manual
`exchange-auth-code` endpoints were removed so callers cannot bypass the flow.
Session history, normalized profile/funds and orderbook read APIs remain.

FYERS setup lives in `FyersAppDialog.jsx`; its App ID and App Secret validation
lives in `FyersConfigurationSerializer` beside `FyersAdapter`. The
`brokerSetupDialogs` registry in `BrokerConnections.jsx` selects a setup form by
broker name. FYERS instructions, callback guidance and session-expiry details
appear in that FYERS form, rather than on the shared connections page.

When adding a broker, implement its own setup form and adapter configuration
serializer, authentication and credential persistence requirements. Do not
reuse FYERS field labels, validation or callback assumptions. The current
persistence flow stores App ID and encrypted App Secret; a broker needing other
stored credentials also needs the corresponding encrypted fields and lifecycle
handling. Register the adapter and its form before enabling the catalog entry.
Zerodha and Angel One remain unavailable until their integrations are implemented.
The common service orchestrates credential changes; vendor App ID/Secret usage
belongs to `FyersAdapter`. `BaseBrokerAdapter` contains no FYERS app credentials.

#### Existing installations

1. Stop API, Celery and runtime processes; install the updated code and run
   `python manage.py migrate` from `backend/`.
2. Migration `brokers.0013_individual_app_credentials` removes unused API-key and
   TOTP-secret columns. Legacy shared-app connections lose their placeholder App
   ID/secret and active/verified flags; their old sessions are invalidated.
3. Existing orders, positions, trades, allocations, account identity and ownership
   are retained. No new App ID or secret is invented, and no Admin data insertion
   is needed. A legacy blank app can be configured for recovery, with profile
   matching preserving its previously linked trading account.
4. Start the services and complete individual-app setup from Broker Integration.
   New sign-in is required for retired shared-app connections. Review existing
   strategy session state explicitly; this migration does not restart strategies.

Official references: [Individual app setup](https://fyers.in/api-docs/v3/getting-started/create-an-app/individual-app/),
[authorization](https://fyers.in/api-docs/v3/api/authentication/individual-app/generate-auth-code/)
and [permission templates](https://fyers.in/api-docs/v3/getting-started/create-an-app/permission-templates/).

## 10. Deployment checks

Run the shared `diagnostics.py` for your mode and inspect bounded Docker logs,
CPU/RAM usage and disk space. The API readiness endpoint checks the database and
runtime coordination Redis; `deployment_health --workers` checks the execution
worker count. These checks do not verify live provider permissions.

Keep encrypted backup copies off-host and practice recovery into an empty
deployment. External cloud monitoring can be added later; first-release tooling
does not provision alarms, signing keys or automatic uploads.

## 11. Production activation and evidence

Before accepting customers, record evidence for:

- Domain ownership, canonical TLS origin and functional callbacks.
- Legal identity/contact/tax/refund decisions and processor agreements.
- Merchant acceptance, mandate behaviour and sandbox payment scenarios.
- Purpose-specific FYERS data rights and paid AI processing review.
- Verified Brevo sender and outgoing account/support notifications.
- Actual ARM64 image startup and resource admission measurements.
- Restored encrypted backups and worker/crash recovery.
- Privacy/tenant isolation, owned exports and safe account shutdown.
- Personal-only Private with instance-local accounts, shared registration/UI, no quotas or checkout and applicable broker authorization.

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
| Research unavailable | Public numeric allowance where applicable, service health/token and model/budget configuration |
| Paper remains blocked after renewal | Explicit resumption, current inventory limits and independent risk/manual restrictions |

Use redacted diagnostics. Do not paste provider secrets into support tickets or logs.
