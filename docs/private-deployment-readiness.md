# Personal Private deployment readiness

Reviewed against the current working tree on **18 November 2026**. This guide
records what was checked, the fixes made and what still prevents an unconditional
"all functionality ready" verdict. Use [Private setup](../infra/private/SETUP.md)
for installation and [shared release readiness](release-readiness.md) for the
earlier architecture, SQL integration and performance evidence.

## Verdict

The shared architecture is suitable for a personal Private installation: one
frontend, API, data feed, execution group, broker-event service, background and
compute workers, scheduler and internal AI service. Private enables Paper and
Live scopes, disables public checkout and has no commercial allowance ceilings.

**It is not yet verified for unrestricted personal Live use across every
instrument and strategy type.** Cash short entry/product compatibility and
commodity-ledger allocation are concrete remaining gaps. Live expiry/clearing
and complete broker charges are also outside the currently implemented ledger.
Stock long and capital-ledger derivative workflows still require acceptance with
your own configured account, data access and deployment host.

This pass fixed source-feed startup and daily-token replacement. It did not
silently change the requested CNC/MARGIN product policy, add another execution
engine, apply migrations to your database or place a real broker order.

## What was verified in this pass

| Evidence | Result | Boundary |
| --- | --- | --- |
| Compose topology/preflight | Development, Public and Private effective configuration checks passed; the Oracle documentation follow-up checked 116 infrastructure links/anchors | Synthetic environment files, not your server secrets, DNS or certificates |
| Execution kernel | 153 assertions passed: four-mode financial transitions, order matching, cumulative broker fills, replay, warmed features, capture/re-entry and schedules | Synthetic observations; no provider or database calls |
| Source authorization | 18 assertions passed for waiting, initial consent, unchanged credentials, rotation, expiry, failed replacement retry, stale callbacks and shutdown | Fake SDK socket and saved-token reader; no FYERS request |
| FYERS adapter | 17 assertions passed for request formats, timeouts, uncertainty, cancellation, normalized order clocks and OAuth; includes explicit reproduction of product/funds limitations | Mock transport; reproducing a limitation is not acceptance of that workflow |
| Actual Private stack startup | Pending in this pass | Docker Desktop is manually paused |
| Current Private database integration | Earlier working-tree audit passed 65 assertions, including Paper projections, recovery and late/duplicate Live fills | Evidence from the preceding audit; it was not rerun in this pass while Docker was paused |
| Frontend | Earlier working-tree lint and production build passed; no frontend source changed in this pass | This is not a complete browser interaction audit on the private hostname |
| Real provider acceptance | Pending | No real broker mutation, FYERS consent, SMTP delivery or chargeable AI request was performed |

The source checks in this pass used temporary fixtures outside the repository:
`%LOCALAPPDATA%/Temp/verify_quantnest_private_feed_20261118.py`,
`verify_quantnest_private_broker_20261118.py` and
`run_quantnest_private_feed_20261118.py`. The shared kernel fixture is
`quantnest_release_kernel_20261117.py`. They are local verification evidence,
not a committed regression suite.

## Functionality and readiness matrix

| Area | Current Private behavior | Before relying on it |
| --- | --- | --- |
| Customer site and workspace | Same pages, registration/login and navigation as Public; scope metadata enables Live/Paper navigation | Confirm deep links, callback URLs, theme and browser reconnect through the private hostname |
| Authentication | JWT sessions/revocation, 2FA, recovery codes and staff OTP remain active | Create the administrator, enrol its OTP, use a separate ordinary trading account and verify recovery/email |
| Strategy Studio | One specification/validator/compiler; saved versions, fixed contracts, automatic expiry/strike policies, sizing and schedules | Validate the exact saved version, qualified contract metadata and its execution mode |
| Historical data and charts | Common provider history loader, confirmed coverage, session calendars, shared live buffers and chart streams | Verify actual history entitlement, instrument catalogue, holidays and chart/history acquisition |
| Source feed | Waits before consent; reloads changed/expired source authorization on its control scan | Complete initial/daily FYERS sign-in; verify authenticated subscriptions and history readiness |
| Backtests and Monte Carlo | Run in compute Celery worker, using shared evaluation/financial logic and documented OHLC approximation | Confirm a bounded end-to-end job on known data and inspect trades/costs, not only task receipt |
| Manual Terminal | Simulated only, including in Private; shared account owner, four user order types and received-observation matching | Exercise submit, trigger, amend, cancel, protection, partial manual close and gross/charges/net history |
| Automated Paper | Separate simulated wallet/accounts, saved-version sessions and owned positions; no commercial quotas | Verify rules/fills and pause/resume/stop, capital/version application and restart recovery |
| Live deployment | Owned strategy/version/broker checks, fixed capital, required stop condition, fresh broker funds and account ownership | Accept only supported product/ledger workflows; see the concrete gaps below |
| Live order path | Durable UNKNOWN order before broker I/O; bounded submission; cumulative broker reports establish actual fills | Verify account-specific order/cancel/fill/reconnect with a deliberately authorized real test |
| Broker events and reconciliation | Socket updates and minute REST reconciliation use the same owned-order processor | Verify both paths; aggregate broker positions do not overwrite session ownership |
| Live fees | Trade reporting distinguishes its pre-fee basis; full actual broker charges are not supplied by orderbook normalization | Do not treat Live results as complete after-fee broker P&L |
| Derivative settlement | Reviewed simulation settlement exists; Live requires an account-specific broker/clearing adapter | Ordinary closing before expiry is separate from automatic MTM/expiry assignment/clearing |
| AI Research and Screener | Separate research service, deterministic tools, owned evidence and confirmed actions; Private has no token allowance ceiling | Configure the provider, prove a real answer and action confirmation; direct market analysis remains active NSE stocks |
| Journal, reports and valuation | Source-specific owned records, server paging and streamed open marks | Compare browser marks and closed records with their source; undefined metrics remain unavailable |
| Support, notifications and exports | Owned support conversations/replies, background email, notifications and account exports remain available | Verify SMTP and attachment/media access; anonymous enquiries additionally need Turnstile configuration |
| Commercial | Public catalog remains visible, checkout is disabled and no commercial usage reservations are created | Keep billing disabled; technical correctness, ownership and available capital still apply |
| Backup/recovery | Encrypted database/media backups, matching-mode restore and separate credential keys | Complete an actual disposable restore; a DB backup cannot restore the broker's external order state |

## Fix applied: source authorization lifecycle

Previously, `FyersLiveFeedClient.connect()` raised before initial authorization.
The first deployment starts `feed` before an administrator can complete consent,
so its process repeatedly exited. Later, saving a new daily source token did not
replace the SDK socket's token automatically.

The FYERS client now:

1. Starts without a socket when no usable source token exists and reports that
   authorization is required.
2. Reads local saved-token state at most once per five-second control interval.
   This performs no provider HTTP request and is outside tick handling.
3. Replaces the transport when the token changes; expiry closes the old socket.
4. Invalidates the old transport's callbacks before closing it. A delayed old
   authentication acknowledgement or tick cannot revive the replaced connection.
5. Uses the existing subscription/history rebuild and execution-generation path
   after the new provider authentication acknowledgement.
6. Cleans up a partially failed replacement so the same saved token can retry.

The five-second interval applies to consent/token changes. It is not added to
candle completion, rule evaluation, signal generation or order handling. Daily
FYERS sign-in remains an operator action. This change does not automate passwords,
TPINs or OTPs and does not certify every prolonged SDK/network outage.

Implementation: `backend/marketdata/fyers.py`, over the existing
`MarketObservationClient` control thread. A running feed needs the updated code
loaded through the normal restart/deployment procedure.

## Concrete Live gaps and account prerequisites

### Cash short entries and the selected product

`execution.types.Contract.product` maps STOCK/ETF/BOND to CNC and derivatives to
MARGIN, matching the requested product policy. However,
`StrategyDeploymentService.validate_snapshot()` permits a fixed stock Sell-entry
strategy when its strategy type is Intraday. The FYERS payload still uses CNC.

The adapter fixture confirms that a stock Sell request is sent with
`productType=CNC`; declaring the strategy Intraday does not change it. FYERS
documents separate CNC, INTRADAY and MARGIN products and describes cash short
selling as an intraday sell-first/buy-back workflow. Therefore this accepted
strategy cannot be certified as an independent cash short under the current
product model. An available external delivery holding is not a replacement for
the platform's session-owned short position.

Resolve this before enabling cash short strategies in personal Live: either add
an explicit supported Intraday product workflow, or reject those Live entries
under the CNC-only policy. This audit keeps the earlier product policy intact;
it does not silently change the broker product or remove simulation shorting.

Sources: [FYERS API product types](https://fyers.in/api-docs/v3/api/appendix/product-types/)
and [FYERS cash short-selling explanation](https://support.fyers.in/portal/en/kb/articles/what-is-short-selling).

### Commodity funds are not represented separately

`FyersAdapter.get_funds()` reads `equityAmount` for each fund heading.
`LiveExecutionService._allocation_terms()` then uses that capital-ledger
`net_equity`. The runtime's account-level available amount is likewise based on
that snapshot; there is no separate commodity-ledger allocation.

The fixture supplied a response with zero capital balance and positive commodity
balance. The resulting `net_equity`/available margin remained zero, and Live
allocation failed. A mixed account also cannot correctly distinguish capital
from commodity spending through this single ledger.

MCX/commodity Live trading therefore needs a ledger-aware funds/allocation path
before it is accepted as supported. Adding `commodityAmount` to capital balances
would be incorrect; these are distinct broker ledgers. Simulation can use its
own configured balances/margin assumptions without proving Live readiness.

Source: [FYERS Funds API](https://fyers.in/api-docs/v3/api/account/funds/).

### Delivery holding authorization

QuantNest does not implement an eDIS/TPIN/holdings-authorization UI. With CNC
delivery exits, the actual broker account must already have the applicable
DDPI/POA or same-day authorized holdings. A successful QuantNest sign-in or broker
OAuth exchange does not establish that authorization. Verify this before relying
on an unattended exit of carried cash holdings.

Source: [FYERS eDIS and DDPI APIs](https://fyers.in/api-docs/v3/api/account/edis-ddpi/).

### Ordinary orders versus settlement and fees

Live settlement deliberately rejects generic market-wide settlement prices:
`execution.settlements.apply_settlement()` requires a future account-specific
broker/clearing report adapter for Live. It does not infer assignment, physical
delivery, official cash settlement or daily broker cash movements from the last
chart candle. Automatic rollover and coordinated multi-leg execution are also
not delivered by the independent-contract order model.

Current Live order normalization does not supply final broker fees; report labels
say pre-fee where appropriate. Configured simulation charge profiles are not
verification of an actual broker contract note. These limitations must remain
explicit in a Private trading acceptance plan.

## Deployment and integration prerequisites

1. **Build the release.** The preceding audit's normal backend Dockerfile build
   was blocked at `mirror.gcr.io` by a TLS handshake timeout. Its incremental Linux
   audit image is useful test evidence, not a substitute for the final locked
   backend/research/frontend builds.
2. **Cut over migrations together.** The four migrations prepared in the shared
   audit remain part of this release: Execution `0008_order_checkpoint`, Paper
   `0026_position_execution_time`, Terminal `0023_execution_times` and Commercial
   `0017_derivatives_simulation`. Back up, finish compute jobs, review broker
   exposure and stop old application writers before the normal upgrade. This
   feed fix adds no new migration.
3. **Configure the real host.** Use a stable host address, correct HTTPS origin,
   separate DB/admin passwords, persistent volumes and retained encryption keys.
   Configure broker app/source callbacks against that same browser hostname.
4. **Load and review data.** Sync instruments and applicable historical/current
   holidays; review exchange/segment sessions. Choose representative fixed and
   automatic derivative contracts and confirm their own history.
5. **Complete integrations.** Source consent and individual broker consent are
   separate. Check the actual trading account/permissions, funds, SMTP, AI provider
   and optional Google/anonymous-form verification.
6. **Run simulated acceptance first.** Build/save a known strategy; run a bounded
   backtest, Paper entry/exit and manual Terminal order lifecycle. Inspect exact
   owned records and fees. Exercise controls and recovery while services run.
7. **Accept personal Live deliberately.** For an explicitly chosen supported
   account/product, verify a small order, actual broker fill, local projection,
   cancellation and exit/reconnect. This check must not be initiated merely by
   diagnostics, the deployment helper or an automated readiness review.
8. **Prove operations.** Perform a disposable encrypted restore, inspect the
   restored owned state, and measure CPU, RSS, command backlog and source-to-signal
   versus signal-to-broker timings on the target machine.

Only Caddy publishes host ports in the Private stack. Database, Redis, internal
research and API containers remain behind its networks. The API health endpoint
checks dependencies; worker diagnostics add execution-worker presence. Neither
proves market-data authentication, broker account authorization, provider history,
successful external email or actual trading capability.

## Operator commands

After configuring the real environment files, follow the full
[Private setup](../infra/private/SETUP.md). These commands are for that actual
deployment, not proof that it has already been performed:

```sh
python3 infra/shared/scripts/deploy.py --root . --mode private --build
python3 infra/shared/scripts/diagnostics.py --root . --mode private
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml exec api python manage.py deployment_health --require-mode private --workers --metrics
docker compose --env-file infra/private/backend.env -f infra/private/compose.yaml logs --tail=100 feed execution broker-events
```

An authorization-waiting feed can be a correct first-install state. Treat
`market_data_connected=false`, missing subscriptions/history, unresolved UNKNOWN
orders or broker authentication errors as trading acceptance issues even if the
application health endpoint returns 200.
