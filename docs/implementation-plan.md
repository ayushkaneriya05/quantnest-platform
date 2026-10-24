# QuantNest complete implementation plan

**Delivery map and release roadmap: 18 October 2026.**

This retains the engineering companion to the [business plan](business-plan.md).
It describes what the current source implements, what an operator must configure
and what still requires engineering or deployment acceptance. It does not treat
old local checks as proof of a production rollout.

## 1. Accepted scope

- One React frontend for the customer website and authenticated workspace.
- Django API/control plane, PostgreSQL/TimescaleDB, durable Redis, analytical cache,
  Celery/Beat, dedicated execution services and a private research service.
- Three separate deployment configurations: Development, Public and Private.
- Public subscriptions stop at simulated Paper. Private supports personal Live only; it is not sold to customers.
- Existing data integration and Brevo remain. Public hosting uses Oracle; frontend
  uses Cloudflare. Personal Private uses a separate operator-controlled Linux host.
- No public demo, Astro site, marketplace, strategy invitations or customer API keys.
- NSE stocks execute now. Build/Pro list futures/options as Coming soon.

The deployed environment is selected by QUANTNEST_DEPLOYMENT_MODE. Feature/execution
scope uses EXECUTION_ENABLED_SCOPES. Neither DEBUG nor a plan label substitutes
for those responsibilities.

## 2. Current implementation and source ownership

| Workstream | Implemented source | Boundary / remaining acceptance |
| --- | --- | --- |
| Customer website | React site feature, LandingPage and generated deployment routes | Real domain, correct public identity, mobile/theme review on deployment |
| Product catalog | commercial/catalog.py, CatalogRevision and public catalog API | Review/publish prices, terms and numeric allowances |
| Usage | commercial/usage.py and entry-point service calls | Current inventory, reserved/used period credits and per-request limits; validate promised host capacity |
| Payments | commercial/billing.py, reconciliation, webhook delivery and invoices | Merchant onboarding, actual price mappings, sandbox and production acceptance |
| Support | customer_support services, tickets, conversations and delivery | Verified SMTP sender and staff response procedures |
| Custom enquiries | Support requests and replies | All project agreements, payments and delivery are managed separately |
| Personal Private | Separate production stack, shared signup/UI, instance-local accounts and standard Docker deployment | Personal data/broker configuration and host acceptance |
| Account privacy | export and erasure | Documented retention behaviour and provider agreements |
| Research | Django research orchestration and private FastAPI service | Numeric allowances, service/model configuration and provider usage |
| Strategy workflow | strategies, rules_engine and React strategy pages | Existing rule model; no proposed expression-node graph |
| Paper/Live | execution owners, shared calculations, gateways, ledgers and reconciliation | Different fill models; Live qualification and current limitations require explicit acceptance |
| Reports/journal | analytics, trade_journal, audit and React review workspace | Source-specific realized P&L; no fabricated combined equity |
| Operations | mode Compose files, shared deploy/diagnostics and encrypted backup/restore scripts | Real backups, empty-database restoration, health and capacity evidence |

File paths in this table are relative to backend/ unless stated otherwise.
The [documentation index](README.md) links each detailed procedure.

## 3. Initialization and data ownership

### Routine records

Run normal Django migrations on installation and upgrade. They initialize launch
catalog terms. Related services create usage
buckets, reservations, checkout attempts, payment/event records, invoices, tickets,
deliveries when their workflow runs.

Do not prepopulate routine financial or usage records by hand. Do not rewrite
historical migrations or fabricate provider payment rows to grant access.

### Deliberate operator inputs

Keep Admin for business decisions, as agreed:

- Published catalog revisions and provider price mappings.
- Custom project work is managed outside this platform.
- Refund decisions. Provider rates and operating costs are managed outside the application for now.
- Installation provisioning/revocation and accepted Live scope.

The complete model and action map is in [Commercial operations](commercial-operations.md).
There is no separate staff Operations application to build or manually seed.

## 4. Catalog and availability acceptance

1. Confirm the seeded Explore/Build/Pro terms in Admin.
2. Publish changes as a new validated revision; preserve purchased snapshots.
3. Review execution scopes and numeric plan allowances.
4. Supply purpose-specific data and AI evidence before affected public work.
5. Confirm Public rejects a Live scope and the UI explains Private availability.
6. Confirm Development bypasses commercial allowances while retaining execution
   scopes, ownership, funds, validation and other execution invariants.
7. Confirm Private has no quotas or checkout and uses the same registration and site pages;
   confirm Public rejects Live execution.
8. Ensure all customers see the same catalog/support labels through backend APIs.

Admissions belong at user-driven creation, start, deployment, version change and
resume actions. Usage completion/refund still runs asynchronously for admitted
jobs. Do not add commercial plan queries to tick processing or cancel/reduce orders
because a period allowance expires.

Commercial expiry is checked at new user-driven admissions. It does not add a
background gate to admitted execution or to protective/reducing orders. Explicit
session actions, protection rules and market/runtime readiness still apply. Renewal
does not silently resume previously paused trading.

## 5. Integration order

Follow [Third-party setup](third-party-setup.md) and the selected [infrastructure
guide](../infra/README.md). Use separate test and production accounts/configuration.

| Order | Integration | Required outcome |
| --- | --- | --- |
| 1 | Domain, DNS, TLS and canonical gateway | Consistent browser/API callbacks and trusted ingress |
| 2 | Database, Redis and encrypted credentials | Persistent healthy services with preserved encryption keys |
| 3 | Administrator and email | Authenticator enrolment, verified sender, working verification/reset mail |
| 4 | Data source | Fresh operator authorization, instrument/calendar/history preparation, actual usage permission |
| 5 | Research | Authenticated private service, approved model and processing arrangement |
| 6 | Public forms | Turnstile verification and owned support conversations |
| 7 | Billing | Merchant acceptance, reviewed amounts, provider mappings, captured-payment reconciliation |
| 8 | Optional email features | Inbound support replies only if configured |
| 9 | Personal Private | Separate host/secrets, locally provisioned owner and personal broker authorization; optional signed release deployment |
| 10 | Recovery and monitoring | Encrypted backup, isolated restore, real alert delivery and incident runbook |

Google sign-in is optional; password/email authentication remains available.
Public explanatory pages do not need data sockets. No TrueData, external analytics,
external error SDK or additional status SaaS is required.

## 6. Public release procedure

### Prepare

1. Read Public infrastructure instructions completely.
2. Set a reviewed release identity and required secrets from the Public examples.
3. Keep billing disabled while setup and acceptance are incomplete.
4. Provision the Oracle A1 2 OCPU/12 GB host, storage, networking and TLS.
5. Deploy the API/workers/database/cache and the single React Pages project.
6. Apply migrations, enrol Admin 2FA, configure Django Site and provider credentials.

### Verify on the real deployment

Use isolated customer accounts and provider sandbox operations:

- Register, verify email, log in/out, refresh, reset password and exercise 2FA.
- Load avatars through signed same-origin API URLs and use both themes.
- Follow every feature/documentation route and unknown-route recovery.
- Create rules/version notes, inspect differences, backtest and review diagnostics.
- Practise Terminal and deploy/pause/resume/stop Paper with valid price/history data.
- Review journal/report source and P&L basis; export owned data.
- Exhaust and restore allowances through real user/job outcomes.
- Send support/feedback and receive staff replies.
- Exercise captured, duplicate, delayed, failed and uncertain payment/refund outcomes.
- Check cancellation, expiry, explicit resumption and preserved paid terms.
- Confirm product update email preferences, activity history and blocked unsafe account deletion.
- Restore a backup into an isolated environment and check runtime reconstruction.

These are deployment acceptance actions, not claims of a stored test suite.
Do not use a real broker order as a generic health probe.

### Capacity gate

The conservative host starts at one API worker, one execution owner with one
calculation child, one gateway worker, one compute task and two background tasks at
a time. Runtime actor limits are separate from subscription allowances.

The initial eight-actor owner can accommodate Build's five Paper instruments;
Pro's twenty need a larger, measured per-owner capacity before checkout opens.
Public user quotas come directly from the plan. Provision shared capacity and
collect deployment evidence before opening checkout. Raising a limit alone
does not add CPU, memory, broker throughput or data entitlement.

### Activate

Keep accepted provider/setup evidence in operating records. Enable BILLING_ENABLED and only the
features and plans whose dependencies and capacity are ready. Publish accurate
contact/status information. Review real error, support, cost and capacity signals
after launch.

## 7. Personal Private deployment

Private currently serves only the operator. Follow [Private setup](../infra/private/README.md)
for an isolated production host, shared registration and UI, local administrator,
data/broker authorization, backups and upgrades. No customer provisioning, licence
refresh or central subscription service is required. Live code remains shared;
Public continues to reject Live scope.

The retired licensing app has been removed. Older deployments must finish the
licensing retirement migration using the previous release before upgrading.
Source/image releases use the standard Docker deployment flow. Customer
Private plans are deferred.

## 8. Runtime work that remains bounded by current behavior

The [Live operations guide](live-trading.md#operations-and-recovery)
owns the detailed limitations. Track these engineering priorities before making
stronger product promises:

| Priority | Work | Acceptance evidence |
| --- | --- | --- |
| High | Review pending/partial-fill exposure protection | Protection remains correct while broker quantities/orders are unresolved |
| High | Establish measured end-to-end latency at admitted load | Tick, calculation, gateway, broker acknowledgement/fill and convergence stages reported separately |
| High | Validate stop/target group parity | Complex rules, AND/OR groups and full exits follow stated semantics; real broker partial fills remain accounted for |
| High before stronger reporting claims | Complete Live net-cost accounting | Broker fees/corrections reconcile without mixing simulated costs |
| Medium | Define backtest final-exposure policy | Explicit final liquidation or marked-to-market policy and corresponding metrics |
| Release validation | Validate the implemented Terminal/chart changes | Segment sessions, recorded fees, derivatives quantities, backend candle snapshots and reconnect behaviour; see [Terminal guide](trading-terminal.md) |
| When increasing workers | Controlled worker/partition changes on one execution server | Old owners stop before new owners start; pending work and shard ownership remain correct |
| When adding markets | Complete contract lifecycle | Data, calendars, margin, multipliers, expiry/settlement and financial records agree |

Do not describe Python process concurrency as equal latency or exchange-grade HFT.
Runtime latency sampling is currently removed. Production latency needs an explicit profiling run; process presence is not a broker fill guarantee.

## 9. Future roadmap

### Additional broker

Implement authentication, submission/cancellation, funds, normalized orderbook and
positions, stable identity/tag mapping, cumulative fill observations, reconnect,
REST recovery, account limits and source-specific acceptance. An unfinished broker
choice must remain unavailable.

### Derivatives or another market

Add contract identity, provider mappings, session/calendar rules, quantity/price
increments, lot/multiplier economics, selection/expiry/roll, margin and settlement.
Exercise backtest, Paper, Live, Terminal, charts and reports deliberately; a model
enum or market label does not enable execution.

### More users

Measure CPU/RSS, cache pressure, locks, queues and broker account throughput. Scale
resources and admission on the one execution server. Multi-server execution is a
future architecture project and has no active runtime settings or transport.
Preserve one owner per actor/account partition and safe financial serialization.

### Builder evolution

The current model compares two typed operands within AND/OR rule groups, including
restricted arithmetic expressions. A general expression DAG, arbitrary transform
graph, temporal event-node editor and an expression runtime are **not implemented**.
If justified later, design migration, validation, lookback, completion-time
semantics, UI and parity as one separate feature. The detailed future design is
now in [Strategy builder plan](strategy-builder-plan.md), with the full original
proposal retained as an explicitly marked archive. Implementation is deferred
until current production behavior is stable; this is not a newly enabled capability.

## 10. Keeping delivery reviewable

For each change, record the user action, API owner, admission rule, data mutation,
background outcome, failure recovery and documentation update. Prefer one source
of truth and existing components over duplicate static exports or extra services.

Keep deployment commands in infra, provider account steps in Third-party setup,
business workflows in Commercial operations and execution internals in the
trading guides. Update this plan when a remaining item is actually accepted;
do not mark it complete because source code or a local build exists.
