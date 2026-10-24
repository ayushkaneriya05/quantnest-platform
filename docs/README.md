# QuantNest documentation

**Source review: 23 October 2026.** The four trading guides describe the current
implementation from customer actions through data preparation, execution,
persistence and operation. They replace the old execution rebuild plan, runtime,
technical-reference and execution-review documents.

## Trading and execution guides

| Functionality | Complete guide | Main topics |
| --- | --- | --- |
| Historical strategy testing | [Backtesting](backtesting.md) | Configuration snapshots, allowances, history/warmup, shared rules, OHLC replay, matching, charges, results and Monte Carlo |
| Automated simulation | [Paper trading](paper-trading.md) | Wallet, fixed allocations, saved-version deployments, live observations, independent units, simulated fills, session controls and runtime operation |
| Automated broker trading | [Live trading](live-trading.md) | Broker setup, fixed allocations, funds, rules, durable submission, cumulative fills, reconciliation, timestamps and recovery |
| Manual simulation | [Trading Terminal](trading-terminal.md) | Watchlists, contracts/lots, stored and live charts, tickets, all order types, position actions, charges, account configuration and calendars |

Each guide contains the user procedure, API map, source/method responsibilities,
worked examples, financial basis and troubleshooting. Paper/Live/Terminal guides
also cover their source-specific Journal and Reports workflows.

For the shared process model, start with
[Paper runtime operations and scaling](paper-trading.md#runtime-operations-and-scaling).
For real order submission/recovery, use
[Live signal to broker order](live-trading.md#signal-to-broker-order).
For data delivery to the UI, use
[Terminal chart flow](trading-terminal.md#chart-history-and-live-candles).

## Other guides

| Your task | Guide | Responsibility |
| --- | --- | --- |
| Understand product direction | [Business plan](business-plan.md) | Customers, positioning, subscriptions and priorities |
| Review delivery scope | [Implementation plan](implementation-plan.md) | Implementation map and remaining release work |
| Build/configure a strategy | [Strategy configuration](strategy-configuration.md) | Current rule schema, sizing, versions, restore and sharing |
| Design the future builder | [Strategy builder plan](strategy-builder-plan.md) | Deferred expression/setup/sequence design and extension contracts |
| First deployment as a beginner | [Start here](../infra/START-HERE.md) | Ordered Development/Public/Private walkthroughs, tools, first user and operations |
| Install/upgrade reference | [Infrastructure](../infra/README.md) | Service commands, environment and migration procedures |
| Configure external accounts | [Integration setup](../infra/shared/INTEGRATIONS.md) | Provider dashboards, key destinations, callbacks and acceptance |
| Review provider wire contracts | [Third-party reference](third-party-setup.md) | Deeper existing provider/broker implementation notes |
| Manage subscriptions/support | [Commercial operations](commercial-operations.md) | Customer/Admin decisions, allowances and routine automation |
| Understand sign-in/security | [Authentication](authentication.md) | Sessions, CSRF, 2FA, OAuth and recovery |
| Maintain the site/frontend | [Customer site](customer-site.md) | Routing, content, shared presentation and feature structure |
| Run research | [Research service](../research_service/README.md) | Separate service setup, tools, models and isolation |

The [original strategy-builder proposal](archive/strategy-builder-original-proposal.md)
is retained as historical input to the future design. Its proposed behaviour and
old paths are not documentation of the current runtime.

## Documentation ownership

- Use lowercase topic names separated by hyphens; retain conventional `README.md` indexes.
- The four mode guides own execution behaviour. Avoid another competing runtime plan/reference.
- Strategy configuration owns authoring/versioning; the future builder plan is explicitly deferred.
- Infrastructure READMEs own exact installation commands and mode-specific environment files.
- Commercial operations owns customer/operator business workflows and allowance policy.
- Backend enums, validation and published catalogue terms remain authoritative for API values and limits.
- Application `/docs/` articles are user-facing help; this folder provides deeper technical/operator detail.

## Keeping documentation current

Trace the frontend action, API validation, saved configuration, asynchronous
command/task, numerical operation and durable result. Explain requested versus
applied state, simulation versus real fills, and gross versus net results.
Update links and Private release packaging when changing filenames.

Code review is not a measured latency guarantee or proof of every production
failure case. Historical migrations remain required even when their retired
features are no longer documented as current functionality.

## Personal Private policy

Private currently serves only the operator on a separate production instance;
customer Live and Private sales are unavailable. See [deployment setup](../infra/private/README.md).
The [old Private marketing source](archive/private-marketing-2026-10-23.md) is
inactive reference material and is not bundled into the application.
