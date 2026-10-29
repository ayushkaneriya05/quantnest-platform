# External accounts and first platform configuration

Use this alongside your [Development](../development/SETUP.md),
[Public](../public/SETUP.md) or [Private](../private/SETUP.md) walkthrough.
Steps are based on the current source and official provider documentation checked
on 24 October 2026. Dashboard wording and account entitlements may differ.

## 1. What to configure, and when

| Integration | Development | Public | Personal Private |
| --- | --- | --- | --- |
| FYERS market-data app | When enabling the feed/history | Needed for data-dependent functionality | Needed for data-dependent functionality |
| Gemini research | Optional `research` profile | Key/token needed by the supplied full deployment | Key/token needed by the supplied full deployment |
| Brevo SMTP | Console email works initially | Configure outgoing account/support email | Configure outgoing account/support email |
| Turnstile | Bypassed with Development and DEBUG true | Needed for anonymous enquiry forms | Needed for anonymous enquiry forms |
| Google login | Optional | Optional; username/password remains available | Optional; username/password remains available |
| FYERS personal trading app | Only intentional Live development | Not used for Public Live; Live is disabled | Configure before your own Live deployment |
| Razorpay | Only a separate billing test environment | Optional after checkout acceptance | Not used; billing is disabled |

The API calls internal services using Docker names. Provider dashboards need the
externally reachable callback URLs below, never `http://api:8000`.

## 2. Keep the different keys separate

| Value | Obtain from | Store in |
| --- | --- | --- |
| `FYERS_CLIENT_ID`, `FYERS_SECRET` | Your market-data app | Selected mode's `backend.env` |
| Personal trading App ID/Secret | Your individual trading app | Signed-in Broker Integration form; secret encrypted in DB |
| `GEMINI_API_KEY`, `RESEARCH_MODEL` | Google AI Studio/project | Selected mode's `research.env` |
| `RESEARCH_SERVICE_TOKEN` | Generate yourself | Identical value in `backend.env` and `research.env` |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Brevo SMTP page | Selected mode's `backend.env` |
| `TURNSTILE_SECRET_KEY` | Cloudflare Turnstile widget | Selected mode's `backend.env` |
| `VITE_TURNSTILE_SITE_KEY` | Same Turnstile widget | Development `frontend.env`, Public Pages build setting, or Private `backend.env` build input |
| Google OAuth client ID/secret | Google Auth Platform | Django Admin -> Social applications |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Razorpay API keys for the selected mode | Public `backend.env` |
| `RAZORPAY_WEBHOOK_SECRET` | Secret you choose when creating the Razorpay webhook | Same Public backend setting |
| `QUANTNEST_PROXY_TOKEN` | Generate yourself | Public backend and Pages Function secret; Private backend/Caddy runtime |

The Google OAuth secret and Gemini API key are different credentials. A Brevo
SMTP key is different from a Brevo API key. A Turnstile site key is intentionally
public; all the other provider secrets stay server-side.

## 3. Callback worksheet

Replace domains before entering these URLs into a dashboard. Include the trailing
slash exactly. Production `BACKEND_URL` equals the canonical browser origin.

| Purpose | Development | Public | Personal Private |
| --- | --- | --- | --- |
| Google OAuth | `http://localhost:8000/api/v1/users/auth/google/callback/` | `https://app.example.com/api/v1/users/auth/google/callback/` | `https://personal.example.com/api/v1/users/auth/google/callback/` |
| Shared FYERS data | `http://localhost:8000/api/v1/market/fyers/callback/` | `https://app.example.com/api/v1/market/fyers/callback/` | `https://personal.example.com/api/v1/market/fyers/callback/` |
| Personal FYERS trading | `http://localhost:8000/api/v1/brokers/credentials/fyers/callback/` | Not enabled for Public Live | `https://personal.example.com/api/v1/brokers/credentials/fyers/callback/` |
| Razorpay webhook | Needs a reachable, separately configured test endpoint | `https://app.example.com/api/v1/billing/webhooks/razorpay/` | Not used |

`/google-callback` is the React completion page, not the Google-registered backend
callback. `origin.example.com` is only Public's gateway upstream; do not use it
for ordinary user login, Google/FYERS callbacks or the Razorpay webhook.

## 4. Brevo: outgoing account and support email

Do the provider setup before production registration/password recovery is used.

1. Create/sign into your [Brevo account](https://app.brevo.com/).
2. Add the domain you will send email from. Add the exact DNS records shown by
   Brevo, then wait for authentication to succeed. Use the provider's actual
   verification/DKIM/DMARC values, not invented example DNS values.
3. Add a sender such as `QuantNest <no-reply@your-domain>` and complete its
   verification if required. This sender is not your technical SMTP login.
4. Open the SMTP settings. Copy the **SMTP login** and create an **SMTP key**.
   Use the SMTP key as the password, not a REST API key.
5. Enter in the selected mode's `backend.env`:

   ```dotenv
   EMAIL_HOST_USER=YOUR_SMTP_LOGIN
   EMAIL_HOST_PASSWORD=YOUR_SMTP_KEY
   DEFAULT_FROM_EMAIL=QuantNest <no-reply@your-domain.example>
   QUANTNEST_SUPPORT_EMAIL=support@your-domain.example
   QUANTNEST_LEGAL_NAME=Your actual operator or business name
   ```

   Replace the sample sender domain. `QUANTNEST_SUPPORT_EMAIL` should be a real
   mailbox you can monitor. It is a contact address, not SMTP authentication.
6. Production code defaults to `smtp-relay.brevo.com`, port `587`, STARTTLS.
   If another SMTP provider is used, set its `EMAIL_HOST`, `EMAIL_PORT` and
   `EMAIL_USE_TLS` appropriately; follow its own instructions.
7. Deploy/recreate the backend services to load the settings. Register a test
   user, request password recovery, and reply to a test Support ticket in Admin.
8. Check delivery in the recipient inbox and Brevo transactional logs. Also
   inspect the `background` worker if queued support notifications do not arrive.

Development sets console email instead. Look in API/background logs for the
message and use its link; it is not supposed to reach a mailbox. To test real
email locally, replace the console `EMAIL_BACKEND` with Django's SMTP backend and
supply your SMTP values.

Inbound email parsing, Brevo delivery webhooks and in-platform custom-project
management were removed. Support replies remain in the platform and trigger
outgoing email; an ordinary mailbox reply is not automatically imported.

Reference: [Brevo SMTP setup](https://help.brevo.com/hc/en-us/articles/7924908994450-Send-transactional-emails-using-Brevo-SMTP).

## 5. Gemini: AI research

1. Sign into [Google AI Studio](https://aistudio.google.com/).
2. Select/create the project intended for this environment and create a Gemini
   API key. Review that project's access, quota and billing before using it.
3. Select a model actually available to that project. QuantNest calls the
   **Interactions API**, using function calls and structured output; a model
   name existing elsewhere does not prove it supports this request format.
4. Edit the selected mode's `research.env`:

   ```dotenv
   RESEARCH_SERVICE_TOKEN=YOUR_RANDOM_SHARED_SERVICE_TOKEN
   RESEARCH_PROVIDER=gemini
   GEMINI_API_KEY=YOUR_GEMINI_KEY
   RESEARCH_MODEL=YOUR_AVAILABLE_SUPPORTED_MODEL_ID
   ```

5. Put the exact same `RESEARCH_SERVICE_TOKEN` in that mode's `backend.env`.
   This is generated by you and authenticates internal requests; Google does not
   issue it. Do not use the Gemini API key as this token.
6. Confirm the example model ID against your project before deploying. The
   `gemini-3.5-flash` value in the repository is a configurable default, not a
   guarantee of access for your key.
7. Enable Development's `research` profile, or run the normal full production
   deploy. Both `compute` and `research` must be running; no separate `research`
   Celery queue should be started.
8. Sign in as an ordinary user and send one small question in AI Research
   Assistant. Confirm the run finishes, then try one selected stock after data
   authorization. Check provider usage in your Google project.
9. The completed reply displays reported tokens as credits (1,000 tokens per
   credit). Compare this with Billing. No per-request customer token budget is
   required. For an existing installation, follow the coordinated
   [research credit rollout](../../docs/ai-research.md#deployment-and-verification)
   before publishing the new catalog.

The internal service's `/health` only confirms service startup. A successful
research answer verifies more of the key/model/tool path. The browser never
receives the Gemini key. Do not publish port 8001 or the internal Django tool
endpoint; Compose and the gateway already keep that path internal.

References: [Gemini keys](https://ai.google.dev/gemini-api/docs/api-key),
[Interactions](https://ai.google.dev/gemini-api/docs/interactions-overview).

## 6. FYERS: shared market-data connection

This app supplies historical candles, quotes and the provider's live data feed.
It is separate from the personal trading connection used to submit orders.

1. Sign into the FYERS API dashboard using the account authorized to supply this
   data. Follow [app creation](https://fyers.in/api-docs/v3/getting-started/create-an-app/individual-app/).
2. Create/select the app for market data. Set the exact **data callback** from
   the worksheet above. Choose the Market Data permission template needed for
   history/quotes and ensure the intended live data access is enabled.
3. Copy the complete App ID and App Secret into `FYERS_CLIENT_ID` and
   `FYERS_SECRET` in the mode's `backend.env`. Recreate services after editing.
4. Confirm the hostname reaches this instance. Development uses the local
   callback only where FYERS permits that URI. If its dashboard rejects it, use
   an approved HTTPS development endpoint and configure both application URLs
   consistently; do not enter a callback the app cannot receive.
5. Create/enrol the staff administrator as shown by the mode guide. Sign into
   `/admin/` in your browser. In the **same browser**, open:

   | Mode | Start authorization |
   | --- | --- |
   | Development | `http://localhost:8000/api/v1/market/fyers/login/` |
   | Public | `https://app.example.com/api/v1/market/fyers/login/` |
   | Private | `https://personal.example.com/api/v1/market/fyers/login/` |

6. Complete FYERS login/consent on FYERS's own page. Return through the callback
   within the ten-minute flow window, using the same browser and hostname.
7. Inspect `/api/v1/market/fyers/token/status/` as staff and the feed logs. The
   status reports active/expiry metadata; do not copy tokens into the frontend.
8. Search an instrument, open its chart and request history. During its market
   session, observe live updates. Subscriptions follow actual chart/watchlist/
   strategy demand, so a quiet feed with no requested instrument is not a failure.
9. Repeat sign-in when the saved session expires. The current flow does not
   promise unattended refresh-token renewal; do not add automated password/OTP
   login scripts. Broker/data reauthorization is an operator action.

For disconnects, distinguish authentication errors from network failures. TLS EOF,
DNS lookup failures and connections closed without a response need a connection
check, not another sign-in. The FYERS SDK can report these HTTP failures as
`-99 / Bad request`; QuantNest's history/quote adapter uses the documented REST
endpoints directly with 5-second connect and 15-second read timeouts so the real
failure category is retained. The WebSocket still uses the SDK's reconnect flow.
History preparation stops issuing further requests when its connection generation
changes and resumes through the existing preparation loop. A subscription
acknowledgement timeout is logged before QuantNest deliberately reconnects; the
SDK's subsequent `code=200` close message is not an HTTP history response.

The code supports one shared configured data provider per instance. An individual
app is limited to its creator's login; using that account to power a public
multi-user site also needs the appropriate data-use/display permissions from the
provider. A working API key alone does not establish those rights. Confirm this
for Public before offering data-dependent features to customers.

References: [FYERS individual apps](https://fyers.in/api-docs/v3/getting-started/create-an-app/individual-app/),
[permission templates](https://fyers.in/api-docs/v3/getting-started/create-an-app/permission-templates/).

## 7. Turnstile: anonymous enquiries

1. Open Cloudflare's Turnstile dashboard and add a widget for this environment.
2. Choose Managed mode and allow the exact browser hostname, such as
   `app.example.com` or `personal.example.com`. Hostnames are not full URLs.
3. Copy its public site key and private secret key.
4. Put the secret in backend `TURNSTILE_SECRET_KEY`. Supply the public key as
   `VITE_TURNSTILE_SITE_KEY` in the location shown in the key table.
5. For Public, rebuild/redeploy Pages after changing its public key. For Private,
   rebuild the frontend image with `deploy.py --build`. Recreate the backend when
   its secret changes.
6. Open a private/incognito browser window, visit the enquiry page, complete the
   widget and submit one request. Confirm the ticket in Operations Admin.

The existing frontend sends the `enquiry` action; the backend validates it and
the allowed hostname. You do not need to write a new widget or Siteverify client.
Development with DEBUG true bypasses this check, so local success does not verify
production widget credentials. Signed-in Support requests do not require this
anonymous challenge.

Reference: [create a Turnstile widget](https://developers.cloudflare.com/turnstile/get-started/widget-management/dashboard/).

## 8. Google sign-in: optional backend client

Configure this after the database and Admin exist. Ordinary username/password
registration works independently.

1. Open Google Cloud/Google Auth Platform and select a project for the environment.
2. Configure app branding, contact and audience. If in Testing, add the Google
   accounts that should be allowed to test. Follow Google's publishing process
   before expecting access by your intended public audience.
3. Create an OAuth client with application type **Web application**. Add the
   exact Google callback from the worksheet as an authorized redirect URI.
4. Copy its client ID/secret. In QuantNest `/admin/`, open **Social applications**
   under Social Accounts and add one with provider Google and a descriptive name.
5. Store the client ID and secret there. Associate it with the Site configured
   by `configure_site` (`SITE_ID=6` in current settings). The domain should be your
   mode's `FRONTEND_URL` host. Leave one unambiguous Google application for that Site.
6. Use **Continue with Google** from the website and finish the redirect. Confirm
   the expected QuantNest account/session is created.

There is no Google OAuth secret `VITE_*` variable. The backend handles the code
exchange. Its requested identity scopes are openid/profile/email; no unrelated
Drive or Gmail access is needed. An existing password account with the same email
is not silently merged; use that account's password when the application asks.

Reference: [Google web-server OAuth configuration](https://developers.google.com/identity/protocols/oauth2/web-server#creatingcred).

## 9. Personal FYERS trading: Private or intentional Live Development

Complete the data setup and Paper acceptance first. Public mode cannot enable
Live by adding a broker key or editing the browser.

1. In FYERS, create/select your own individual trading app. Set the **trading
   callback** from the worksheet, which is different from the data callback.
2. Grant the appropriate order permission template and set the approved static
   server IP where FYERS requires it. The address is the host's actual outbound
   public IP, not a container address or Cloudflare's edge IP.
3. Sign into your personal QuantNest user account and open **Broker Integration**.
4. Select FYERS and enter this app's App ID/Secret. Complete the saved connection's
   browser authorization with your own FYERS account. These are not backend
   `FYERS_CLIENT_ID/FYERS_SECRET` settings.
5. Confirm the linked account identity, active session, funds and broker order
   connection. Private already starts `broker-events`; Development additionally
   needs both Live scope and its `live` profile.
6. Save a strategy version and deliberately deploy it to Live, selecting the
   broker account and fixed allocation. Keep the broker's own terminal available
   to inspect the real order state. A Paper deployment does not become Live.
7. When you choose to perform a real acceptance trade, verify order acknowledgement,
   fill, your local session position, exit and final broker order state. Running
   diagnostics itself does not place a trade.

One strategy can have Live deployments on different broker accounts, but cannot
create duplicate deployments on the same broker account. Reconnect expired
sessions from Broker Integration. Do not change saved App ID/Secret while active
sessions/orders/positions still depend on them; settle and review them first.
Only FYERS is currently enabled; other broker cards are not implementations.

References: [FYERS apps](https://fyers.in/api-docs/v3/getting-started/create-an-app/individual-app/)
and [permissions](https://fyers.in/api-docs/v3/getting-started/create-an-app/permission-templates/).

## 10. Razorpay: optional Public checkout activation

Leave `BILLING_ENABLED=False` during infrastructure/data acceptance. You can
finish the free Public workflow without accepting money. Use a separate reachable
test deployment/database for Test Mode; do not mix test subscriptions with real
customer records or configure a webhook to an unreachable `localhost` URL.

### Provider and application setup

1. Create your merchant account and complete the provider's required activation.
   In its dashboard choose the intended Test or Live environment and obtain the
   matching API key ID/secret. Test and Live IDs, plans and webhooks are separate.
2. In QuantNest Operations Admin, review **Catalog revisions**. Migrations seed
   an active catalog. To change prices/allowances, clone it as a draft, edit/save,
   then use **Publish selected revision for new purchases and Explore**.
3. Decide the applicable tax configuration. Set `BILLING_TAX_BPS` and
   `BILLING_TAX_ID` for your reviewed tax/invoice policy. `100` basis points is
   1%; the repository's `0` is not a statement about taxes you owe.
4. For automatic monthly renewal, create monthly INR Razorpay plans matching the
   **full charge including configured tax** for each paid plan. The code accepts
   monthly period/interval 1. Provider plans cannot be edited in place; create
   new plan IDs for changed totals.
5. In Admin -> **Price mappings**, choose the published catalog, `build` or `pro`,
   provider `plan_...` ID, total in paise and tax basis points. Admin verifies
   the provider amount/currency/interval. Manual payment does not require this
   automatic-renewal mapping.
6. Set Public `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` and a new independently
   chosen `RAZORPAY_WEBHOOK_SECRET`. In the provider's webhook settings enter
   the Public billing callback from the worksheet with that same webhook secret.
7. Enable payment capture/failure, subscription lifecycle/charge, refund and
   dispute notifications supported by your account. In particular include
   `payment.captured`, relevant subscription events, refund events and
   `payment.dispute.*` events. Select actual event checkboxes offered by Razorpay;
   a wildcard here describes a family, not a literal dashboard event name.
8. Recreate backend services, and check provider webhook delivery to your exact
   HTTPS endpoint. A browser GET is not a signed webhook test. Invalid signatures
   should be rejected, not bypassed.

### Accept the flow before turning on real sales

On the separate test deployment, set `BILLING_ENABLED=True` and redeploy. Use a
test user with a verified email address and check:

- Successful capture updates Billing and Usage once and creates an invoice.
- Cancellation/failure does not grant a paid period.
- Duplicate provider deliveries do not grant another period.
- Manual renewal and automatic renewal use the correct totals and plan terms.
- Cancelling renewal preserves the purchased period and stops future renewal.
- An eligible refund is reviewed/processed through the existing Admin flow.
- Period allowances and saved/Paper capacity match the purchased catalog.

For real activation, configure **Live** keys, Live plan mappings and the Live
webhook on the production database, then deliberately enable billing and deploy.
Never mark a payment captured or edit paid-through dates merely to hide a failed
provider integration. A checkout browser success message is not payment authority;
the backend verifies provider state. Plan limits do not increase server capacity.

References: [Razorpay plans](https://razorpay.com/docs/payments/subscriptions/create-plans/),
[subscription webhooks](https://razorpay.com/docs/webhooks/subscriptions/),
and [application billing flow](../../docs/commercial-operations.md).

## 11. Initial platform data and ordinary-user acceptance

After first deployment and Admin OTP enrolment:

1. Run the mode's `sync_market_holidays` and `sync_instruments` commands.
   For the initial stocks-only workflow, `--source NSE_CM` limits the master sync
   to the needed NSE cash source. The scheduled full sync can import other
   instrument metadata; imported metadata does not enable unsupported features.
2. In Admin -> Exchange Configurations, review the exchange/segment, timezone,
   regular hours, weekdays and breaks. Inspect holidays and any special-session
   override. Current-year NSE API holidays are mirrored by segment to BSE/MCX;
   historical years use the installed NSE library for all active segments.
3. Before historical experiments, sync the years being tested using
   `sync_market_holidays --start-year 2024 --end-year 2026`, adjusting years to
   your history and the current year. The command rejects years outside supported
   coverage; it does not silently verify every historical special session.
4. Authorize FYERS data. Load one chart and older history; history downloads are
   on demand rather than a requirement to preload every symbol.
5. Register a normal user. In Charge Profiles, review the generated QuantNest
   default and set your simulation assumptions. Choose the profile where the
   backtest, Paper deployment or Terminal account offers it.
6. Save a small, explicit strategy/version with a tradable stock, Direct routing,
   entry rules, full-position exit/stop/target, position sizing and trading times.
   End time stops new entries; it is not an automatic intraday square-off setting.
7. Preview/run a bounded backtest, review trades/costs/diagnostics, and try research
   and screening. Missing data/provider failures are not evidence of no signal.
8. Add simulated funds to Paper Wallet, then deploy the saved version **from the
   strategy list**. Manage its session in Paper Deployments. There is no separate
   manual Paper account/allocation creation page or percentage allocation.
9. During the instrument's session, inspect live observations and actual rule
   outcomes. A running process does not mean every strategy must immediately trade.
10. Use simulated Terminal separately: configure its account/profile, add a
    watchlist stock, place a deliberate small order and inspect positions/history.
    Its balance is separate from the Paper wallet and real broker account.
11. Send a Support message, reply in Admin, and verify the in-platform reply and
    outgoing email. Custom work remains a request; project execution happens
    outside this system.

Current public market availability and research drafts focus on NSE stocks.
Use a tradable NSE stock for initial acceptance. Index data is for analysis;
do not assume an index can be ordered. Futures/options marketing remains Coming
soon. No setup step in this guide enables an unfinished market/broker adapter.

The detailed user/execution procedures are in [Backtesting](../../docs/backtesting.md),
[Paper](../../docs/paper-trading.md), [Live](../../docs/live-trading.md) and
[Terminal](../../docs/trading-terminal.md).
