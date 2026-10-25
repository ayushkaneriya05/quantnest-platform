# QuantNest business plan

**Revised against the current product: 23 October 2026.**

This is the business direction for QuantNest. The [implementation plan](implementation-plan.md)
maps it to delivered code and remaining release work. [Commercial operations](commercial-operations.md)
explains customer and operator actions. Prices below describe the launch seed;
published catalog terms and the customer's purchase determine actual entitlement.

## 1. Product and positioning

QuantNest helps people research an idea, express their own rules, test historical
behavior, practise in simulation and review recorded outcomes. Customers supply
their trading logic. QuantNest sells software and development services.

The hosted workspace provides AI-assisted research, screening, strategy building,
version history, backtesting, a manual simulated Terminal, automated Paper,
journaling, reports and account controls. It does not sell investment advice,
ready-made return claims, managed money or a public strategy marketplace.

Private is an operator-managed personal production instance. It is not offered to
customers and has no sales, contract activation or licence renewal workflow.
Personal Live code remains available separately from Public simulation.

Current execution supports NSE stocks with DIRECT routes. NSE futures and options
appear as **Coming soon** in Build and Pro; they are not enabled products.
Additional markets and global distribution remain future work.

## 2. Customers and an initial focus

| Customer | Problem QuantNest can address | Suitable offer | Qualification |
| --- | --- | --- | --- |
| Individual systematic trader | Disconnected research, rule changes and manual review | Explore, then Build or Pro | Own logic; understands simulated results |
| Developer or quantitative researcher | Needs a workflow around reusable rules and evidence | Workspace plus a scoped integration/tool project | Clear data and execution requirements |
| Educator or training business | Needs software for structured practice | Custom simulation tooling or an agreed deployment | Audience, data permissions and teaching scope reviewed |
| Registered financial firm or technology team | Needs a specific internal tool or adapter | Paid discovery, development and maintenance | Contract, security review and responsibilities agreed |
| International customer | Similar workflow in another market | Discovery first | Market, provider, privacy, billing and local requirements must be implemented/reviewed |

Start with individual users who already know why they want to backtest or practise
their own rules, plus narrowly scoped software projects. Selling every segment
at once creates support and delivery obligations that one founder cannot sustain.

Do not assume demand from growth in retail accounts alone. Validate willingness
to pay with customer interviews, actual activation, paid conversions and repeat use.

## 3. Offers and revenue

### Hosted subscriptions

Use a free workspace to let a customer complete a small real workflow, then charge
for additional capacity. Keep the explanation simple: more saved work, more
research/testing allowance and more Paper capacity.

| Plan | Launch base price, monthly INR | Intended use |
| --- | --- | --- |
| Explore | Free | Try the available workflow at small limits |
| Build | ₹499 before applicable tax | Regular individual research, testing and Paper practice |
| Pro | ₹1,499 before applicable tax | Larger saved work and more frequent use |

A free plan is not unlimited access. Execution scopes, numeric allowances,
per-request bounds and host admission still apply. Live is not included in hosted
plans. No demo route, public result simulator or recorded demo video is currently offered.

Current seed allowances:

| Allowance | Explore | Build | Pro |
| --- | ---: | ---: | ---: |
| Saved strategies | 3 | 10 | 50 |
| Backtest credits per period | 5 | 20 | 100 |
| AI research credits per period (1 credit = 1,000 tokens) | 150 | 500 | 1,500 |
| Screener runs per period | 10 | 100 | 300 |
| Saved screens | 2 | 10 | 30 |
| Stocks per research request | 5 | 20 | 50 |
| Monte Carlo runs per period | 1 | 5 | 10 |
| Active Paper deployments | 1 | 1 | 3 |
| Active Paper instruments | 1 | 5 | 20 |
| Source candles per backtest | 100,000 | 250,000 | 1,000,000 |

Launch Public catalogs allow three attached results per research request and
1,000 Monte Carlo simulations per run; these values are catalog-managed rather
than fixed code ceilings. Private has no plan ceilings. One backtest credit covers up
to 100,000 source instrument-candles including warmup, rounded up. The catalog
owns this unit. There is no automatic paid overage or allowance rollover.

These are seed values, not a second configurable catalog. To change limits or
pricing, publish a new validated catalog revision in Admin as described in
Commercial operations. Preserve purchased terms and provider price mappings.

### Personal Private

Private has no current customer revenue or acquisition target. Preserve its
separate environment and shared execution code for personal use. Any future
customer offering requires its own product, broker/compliance and operating
review before adding contracts, billing or marketing.

### Custom development

Offer paid discovery when the scope is uncertain, then a written deliverable with
milestones, acceptance criteria, exclusions and maintenance options. Useful early
projects include research/reporting tools, workflow automation, data integration,
internal dashboards and integrations. Scope execution-related work separately
and assess applicable requirements before acceptance.

Custom development requests and replies use Support. All subsequent project agreements, payments, delivery and management are handled separately outside QuantNest.


Avoid promising an exchange, instrument, broker or execution capability simply
because an adapter interface exists.

## 4. Affordable acquisition and customer communication

1. Explain one coherent workflow on the home page and link every feature.
2. Publish practical guides using the customer's own logic and neutral examples.
3. Use product updates and educational articles to demonstrate workflow quality.
4. Invite qualified prospects into Explore and offer a clear contact route for
   custom software work.
5. Ask for feedback after a completed research/test/Paper/review task.
6. Review customer feedback and subscription records without tracking website visits or product usage.

Focus marketing on clarity, repeatability, saved configuration, reviewable evidence
and customer control. Avoid profit promises, invented testimonials, fabricated
performance, unsupported uptime claims and implying regulatory approval.

The site includes product/features, pricing, documentation, services, a Private availability notice,
contact, feedback, FAQ, about, trust/security, methodology, policies, changelog
and status. Status is operator-published information, not independent
automated availability evidence.

## 5. Regulation, data and business readiness

This plan records operating decisions rather than a legal determination. Providing
software that executes a customer's own logic still requires review of how APIs,
orders, hosting, access, data and commercial responsibilities actually work.

For launch:

- Keep Public execution limited to simulation through Paper.
- Review purpose-specific data rights for display, storage, derived calculations,
  backtesting, screening, simulation, research and hosted multi-user use.
- For personal Live, verify the applicable broker authentication/IP
  requirements, release, account ownership and recovery procedure.
- Establish the business identity, terms, privacy, refunds, tax/invoicing treatment,
  merchant acceptance and processor arrangements.
- Keep provider permission evidence and expiry in operating records. Application
  execution scopes control execution availability and do not establish external rights.
- Review current primary SEBI, exchange and broker requirements with a qualified
  adviser before offering an arrangement that depends on their interpretation.

Running on a customer server is not described as an exemption. Disclaimers alone
do not establish compliance. Do not reuse old market-growth statistics or circular
dates as current evidence without checking the primary publication.

## 6. Hosting and integration choices

| Concern | Initial choice |
| --- | --- |
| Public backend | Oracle A1 VM, 2 OCPUs / 12 GB |
| Public frontend | One React application on Cloudflare Pages |
| Persistent services | PostgreSQL/TimescaleDB, persistent queue/coordination Redis and disposable research-cache Redis |
| Transactional email | Existing Brevo SMTP |
| Support replies | Customer workspace and staff Admin; outgoing notifications through SMTP |
| Payments | Razorpay after merchant and release acceptance |
| Research | Private FastAPI service with reviewed Gemini processing |
| Market data | Existing source integration; no TrueData migration |
| Backups and health | Local encrypted database/media backups copied off-host; shared diagnostics and Docker logs |
| Private hosting | Separate operator-controlled Linux host for personal use |

Avoid adding analytics SaaS, a second website framework or more infrastructure
providers before a real requirement justifies them. Optional Google sign-in and
public form protection retain their existing integrations.

The free hosting allocation is a budget target, not a capacity or uptime promise.
The initial per-user runtime actor ceiling is four: Build and Pro's Paper promises
exceed that ceiling. Checkout must remain unavailable for an unsatisfied capacity
promise until admission and real host resources are provisioned and validated.

## 7. Financial discipline

Track workspace subscription receipts and custom-project receipts
separately. Measure captured payments, taxes, provider fees, refunds, AI/data
costs, hosting, delivery time and support effort.

Useful calculations:

- Contribution = recognized revenue less directly attributable delivery costs.
- Project profitability = agreed fee less development/support effort and provider costs.
- Free-user cost = measured AI/data/compute/support cost for the allowed workflow.
- Upgrade value = capacity a customer needs after completing a useful free task.

Use actual provider bills and observed usage in your accounting records. Missing
cost observations are not zero cost. In-app operator profit/cost reporting is
deferred; research runs retain token/request usage for review.

Avoid permanent discounts without a reason. The implementation preserves accepted
founding terms for the defined protection period; a new price needs new terms and,
where required, a newly authorized payment arrangement.

## 8. Growth sequence

### First: trustworthy launch

Finish provider setup and launch acceptance. Make the whole supported workflow
usable, explain simulation assumptions, answer support requests and establish
backup/recovery habits. Sell only capacity the host can deliver.

### Then: retention and selected service revenue

Improve the most common failure points and documentation from actual customer use.
Choose small, repeatable custom projects. Build reusable adapters or workflows
when a paid customer need justifies the maintenance burden.

### Later: market and instrument expansion

Treat derivatives and another market as complete product additions: contracts,
calendars, data coverage, lot/tick/multiplier rules, margin, settlement, expiry,
reports, execution/reconciliation and permissions. International expansion also
needs local business, payment, privacy and support decisions.

### Defer until justified

A strategy marketplace, public demo tooling, user-to-user strategy invitations,
customer API keys, broad broker support and a new expression graph editor are
outside current scope. Customer requests and economics should determine whether
any becomes a funded roadmap item.

The [future strategy builder plan](strategy-builder-plan.md) preserves and extends
the original expressions/anchors/sequences proposal. It defines a staged path
from richer stock rules to qualified cross-instrument and global-market support,
after production stabilization. It does not change the current plan catalog.

## 9. Decisions and evidence to maintain

Keep a short review record for:

1. Which customer completes which useful task and how frequently.
2. Conversion from Explore, cancellations and refund reasons.
3. Cost and latency at actual admitted load.
4. Data/AI/broker/merchant approvals and approaching expiry.
5. Repeated support questions and the product/documentation fix.
6. Personal infrastructure costs kept separate from customer-project revenue.
7. Whether the next feature improves retention, revenue or reliability enough to
   justify its ongoing complexity.

Use the [implementation plan](implementation-plan.md) for delivery order,
the [provider guide](third-party-setup.md) for account setup and
[Commercial operations](commercial-operations.md) for day-to-day procedures.

