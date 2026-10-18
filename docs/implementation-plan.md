# QuantNest complete implementation plan

**Delivery map and release roadmap: 16 October 2026.**

This retains the engineering companion to the [business plan](business-plan.md).
It describes what the current source implements, what an operator must configure
and what still requires engineering or deployment acceptance. It does not treat
old local checks as proof of a production rollout.

## 1. Accepted scope

- One React frontend for the customer website and authenticated workspace.
- Django API/control plane, PostgreSQL/TimescaleDB, durable Redis, analytical cache,
  Celery/Beat, dedicated execution services and a private research service.
- Three separate deployment configurations: Development, Public and Private.
- Public subscriptions stop at simulated Paper. Private may include qualified Live.
- Existing data integration and Brevo remain. Public hosting uses Oracle; frontend
  uses Cloudflare. Private hosting is portable to a customer-controlled Linux host.
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
| Support | customer_support services, tickets, conversations and delivery | Verified sender; optional inbound domain; staff response procedures |
| Custom work | Engagement, quotation revisions, acceptance and milestone payments | Staff scope/price/contract decisions and real deliverable acceptance |
| Private distribution | installations models, provisioning, signing, local licence refresh and release tools | Central signing setup, signed artifact delivery and customer host acceptance |
| Consent/privacy | email preference, newsletter confirmation, export and erasure | Documented retention behaviour and provider agreements |
| Research | Django research orchestration and private FastAPI service | Numeric allowances, service/model configuration and provider usage |
| Strategy workflow | strategies, rules_engine, risk_management and React strategy pages | Existing rule model; no proposed expression-node graph |
| Paper/Live | execution owners, shared calculations, gateways, ledgers and reconciliation | Different fill models; Live qualification and current limitations require explicit acceptance |
| Reports/journal | analytics, trade_journal, audit and React review workspace | Source-specific realized P&L; no fabricated combined equity |
| Operations | mode Compose files, shared scripts, Public Oracle provisioning and timers | Real backups, isolated restoration, alert delivery and capacity evidence |

File paths in this table are relative to backend/ unless stated otherwise.
The [documentation index](README.md) links each detailed procedure.

## 3. Initialization and data ownership

### Routine records

Run normal Django migrations on installation and upgrade. They initialize launch
catalog terms. Related services create usage
buckets, reservations, checkout attempts, payment/event records, invoices, tickets,
deliveries, quotation revisions and licence state when their workflow runs.

Do not prepopulate routine financial or usage records by hand. Do not rewrite
historical migrations or fabricate provider payment rows to grant access.

### Deliberate operator inputs

Keep Admin for business decisions, as agreed:

- Published catalog revisions and provider price mappings.
- Quotations, project scope, milestone acceptance and Private contracts.
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
7. Confirm Private uses current signed licence validity with unlimited software usage, with no hosted
   subscription checkout.
8. Ensure all customers see the same catalog/support labels through backend APIs.

Admissions belong at user-driven creation, start, deployment, version change and
resume actions. Usage completion/refund still runs asynchronously for admitted
jobs. Do not add commercial plan queries to tick processing or cancel/reduce orders
because a period allowance expires.

Running activity may be paused by the lifecycle when entitlement ends; protection,
reductions, reconciliation and account history must remain usable. Renewal does
not silently resume previously paused trading.

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
| 8 | Optional email features | Newsletter confirmation and/or inbound support replies only if configured |
| 9 | Private distribution | Central signing keys, contract, provisioned identity, delivered verification keys and signed release |
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
- Send support/feedback and receive staff replies; confirm optional newsletter flow.
- Exercise captured, duplicate, delayed, failed and uncertain payment/refund outcomes.
- Check cancellation, expiry, explicit resumption and preserved paid terms.
- Confirm product update email preferences, activity history and blocked unsafe account deletion.
- Restore a backup into an isolated environment and check runtime reconstruction.

These are deployment acceptance actions, not claims of a stored test suite.
Do not use a real broker order as a generic health probe.

### Capacity gate

The conservative host starts at one API worker, one execution owner with one
calculation child, one gateway worker, one compute task and one background task at
a time. Runtime actor limits are separate from subscription allowances.

The initial four-actor per-user ceiling cannot satisfy Build's five or Pro's
twenty Paper instruments. Resolve that mismatch with actual resource/admission
provisioning and evidence before enabling their checkout. Raising a limit alone
does not add CPU, memory, broker throughput or data entitlement.

### Activate

Keep accepted provider/setup evidence in operating records. Enable BILLING_ENABLED and only the
features and plans whose dependencies and capacity are ready. Publish accurate
contact/status information. Review real error, support, cost and capacity signals
after launch.

## 7. Private delivery procedure

1. Agree workflows, qualified brokers, licence validity, hosting responsibilities,
   term/maintenance/support and acceptance criteria.
2. Qualify the Live arrangement separately if included; retain independent broker
   access and incident responsibility.
3. Create the central contract and provision the installation.
4. Deliver the signed release, public verification keys, installation identity and
   activation secret through a protected channel.
5. The customer follows infra/private/README.md on their own Linux host.
6. Create local accounts and Admin; central account records are not copied automatically.
7. Import/refresh the local licence, prepare data and exercise agreed workflows.
8. Verify expiry/offline/revision/revocation behavior and explicit resumption.
9. Validate broker identity, cumulative fills, unknown outcomes and reconciliation
   on an approved test arrangement before real Live activation.
10. Hand over backup/restore, monitoring, upgrade and incident instructions.

Private saves accepted licence/revision state in PostgreSQL and mounts verification
keys read-only; there is no separate licence-state volume. Oracle is used by the
central signing authority; customer hosts need no OCI credentials for ordinary
local licence verification.

## 8. Runtime work that remains bounded by current behavior

The [technical reference](execution-technical-reference.md#20-current-limitations-and-verification-boundaries)
owns the detailed limitations. Track these engineering priorities before making
stronger product promises:

| Priority | Work | Acceptance evidence |
| --- | --- | --- |
| High | Review pending/partial-fill exposure protection | Protection remains correct while broker quantities/orders are unresolved |
| High | Establish measured end-to-end latency at admitted load | Tick, calculation, gateway, broker acknowledgement/fill and convergence stages reported separately |
| High | Validate stop/target group parity | Complex rules, multiple matching groups, partial exits and breakeven follow stated semantics |
| High before stronger reporting claims | Complete Live net-cost accounting | Broker fees/corrections reconcile without mixing simulated costs |
| Medium | Define backtest final-exposure policy | Explicit final liquidation or marked-to-market policy and corresponding metrics |
| Medium | Improve chart reconciliation/aggregation | Session-aligned timeframe boundaries and reconnect history/volume correction |
| When adding nodes | Controlled topology/partition changes | Drain, ownership fencing, replication gaps and restart recovery demonstrated |
| When adding markets | Complete contract lifecycle | Data, calendars, margin, multipliers, expiry/settlement and financial records agree |

Do not describe Python process concurrency as equal latency or exchange-grade HFT.
Existing telemetry measures local stages, not an unconditional broker fill guarantee.

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
resources and admission first. Add execution nodes with shared PostgreSQL/runtime
Redis and local observation replication only after the topology procedure is accepted.
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
technical reference. Update this plan when a remaining item is actually accepted;
do not mark it complete because source code or a local build exists.
