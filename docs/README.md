# QuantNest documentation

**Current-state documentation consolidated: 7 November 2026.** Each topic below
has one current guide. Mode guides own execution; Strategy Studio owns authoring
and shared rule meanings. Authentication, site/workspace, Commercial and Support
each own their current workflows. Retired plans and dated execution reviews are
no longer separate implementation references.

## Strategy creation and use

Start with [Strategy Studio: complete current guide](strategy-configuration.md).
It covers every current operand/operator, fixed and automatic markets, sizing,
formulas, capture/re-entry, schedules, validation, versions, sharing, worked
strategies, document/API examples and implementation ownership.

- [Create and manage a strategy](strategy-configuration.md#2-create-and-manage-a-strategy)
- [Fixed instruments and automatic ATM/ITM/OTM selection](strategy-configuration.md#4-markets-fixed-instruments-and-automatic-contracts)
- [Sizing and initial risk](strategy-configuration.md#5-direction-sizing-and-initial-risk)
- [All 48 inputs and their parameters](strategy-configuration.md#7-all-rule-inputs-and-indicator-parameters)
- [Operators and rolling calculations](strategy-configuration.md#8-comparisons-arithmetic-and-rolling-calculations)
- [Capture, confirmation and re-entry](strategy-configuration.md#10-capture-and-confirmation)
- [Worked strategies](strategy-configuration.md#14-worked-strategies)
- [Backend/frontend specification ownership](strategy-configuration.md#19-implementation-ownership-and-maintenance)

## Trading and execution guides

| Functionality | Guide | Main topics |
| --- | --- | --- |
| Historical strategy testing | [Backtesting](backtesting.md) | Snapshots, allowances, history/warmup, expired derivatives, OHLC replay, signal-time fills, charges, results and Monte Carlo |
| Automated simulation | [Paper trading](paper-trading.md) | Wallet, fixed allocations, saved-version deployments, live observations, simulated fills, session controls and runtime operation |
| Automated broker trading | [Live trading](live-trading.md) | Broker setup/funds, allocations, submission, cumulative fills, reconciliation and recovery |
| Manual simulation | [Trading Terminal](trading-terminal.md) | Watchlists, contracts/lots, charts, tickets, manual order types, position actions, costs and calendars |
| AI Research and Market Screener | [AI Research](ai-research.md) | Conversations/context, deterministic evidence, confirmed actions, screens, token credits, providers and deployment |

The mode guides also cover their Journal and Reports workflows. For runtime
commands/scaling, start with [Paper runtime operations](paper-trading.md#runtime-operations-and-scaling).
For the shared rule-to-order path use [Saved strategy to execution](strategy-configuration.md#15-from-saved-strategy-to-execution).
For chart delivery use [Terminal chart flow](trading-terminal.md#chart-history-and-live-candles).

Shared live-data acquisition and realtime valuation are documented in the mode
guides. [Reviewed derivative settlement](paper-trading.md#derivative-settlement)
is part of the Paper guide and is linked from Backtesting/Terminal/Live. The
separate settlement document and dated data/P&L reviews are retired; their
current behavior and operational limits are retained in these guides.

## Other guides

| Your task | Guide | Responsibility |
| --- | --- | --- |
| Understand product direction | [Business plan](business-plan.md) | Customers, positioning, subscriptions and priorities |
| Plan quantitative capabilities | [Quantitative research roadmap](quantitative-research-roadmap.md) | Data quality, validation, portfolio analytics, ML, architecture and learning |
| Build a separate research product | [AI research assistant transformation](ai-financial-research-transformation.md) | Separate repository, datasets, experiments, portfolio/ML methods and career evidence |
| Find a local quant/fintech role | [Ahmedabad, Gandhinagar and GIFT City career plan](quant-fintech-career-plan-ahmedabad-2026-10.md) | Dated employer research, eligibility, project evidence and interview/application preparation |
| Review delivery scope | [Implementation plan](implementation-plan.md) | Implementation map and remaining release work |
| First deployment as a beginner | [Start here](../infra/START-HERE.md) | Development/Public/Private walkthroughs, tools, first user and operations |
| Install or upgrade | [Infrastructure](../infra/README.md) | Service commands, environment, migrations and backups |
| Configure integrations | [Integration setup](../infra/shared/INTEGRATIONS.md) | Provider dashboards, keys, callbacks and acceptance |
| Review wire contracts | [Third-party reference](third-party-setup.md) | Provider/broker implementation notes |
| Manage subscriptions and allowances | [Commercial operations](commercial-operations.md) | Catalogues, quota admission/completion, checkout, renewal, invoices, refunds and reconciliation |
| Handle customer requests and account records | [Customer Support](customer-support.md) | Public enquiries, owned replies, staff inbox, SMTP, custom enquiries, exports and retention |
| Understand sign-in/security | [Authentication](authentication.md) | Sessions, CSRF, 2FA, OAuth and recovery |
| Maintain the frontend/site | [Customer site](customer-site.md) | Routing, content, shared UI and feature structure |
| Maintain lists | [Implemented pagination](customer-site.md#shared-pagination-and-resource-selectors) | Shared controls, URL state, server filters/summaries, resource selectors and evidence boundaries |
| Start the AI service | [Research service](../research_service/README.md) | Native/Compose configuration and verification |

## Documentation ownership and updates

- Strategy configuration owns current authoring behavior, examples and metadata maintenance.
- The four mode guides own data/financial adapters and session operation; avoid competing runtime plans.
- AI Research owns current assistant/screener behavior, evidence, confirmed actions and provider/accounting contracts.
- Infrastructure owns exact installation commands and environment files.
- Commercial operations owns catalogues, allowance policy, payment and renewal state.
- Customer Support owns enquiries/replies, outbound email and account-record/retention workflows.
- Authentication owns sessions, credentials and administrator access; Customer site owns shared frontend/pagination contracts.
- Backend specification/validation remains authoritative for allowed inputs and defaults.
- Application `/docs/` articles are concise user-facing help; this folder provides technical/operator depth.
- Future quantitative/product research remains explicitly separate from implemented features.

Trace changes through UI, API validation, saved version, prepared inputs, numerical
decision and financial result. Update examples and relative links together. Code
inspection is not a latency guarantee or proof of a real broker fill. Historical
database migrations remain necessary even when retired plans/docs are deleted.

## Personal Private policy

Private currently serves the operator on a separate instance; customer Live and
Private sales are unavailable. See [Private deployment](../infra/private/README.md).
The [old Private marketing source](archive/private-marketing-2026-10-23.md) is
inactive reference material and is not bundled into the application.
