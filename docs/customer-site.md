# Customer website, workspace and shared frontend

**Source reviewed: 7 November 2026.** One React/Vite application serves the
marketing website, authentication pages and signed-in workspace. This guide owns
current navigation, content, metadata, shared UI, pagination, error behavior and
build delivery. The old pagination proposal is replaced by the implementation
reference below.

Use [Authentication](authentication.md), [Commercial](commercial-operations.md)
and [Customer Support](customer-support.md) for their business/security workflows.
Detailed execution belongs to the five [feature guides](README.md).

## Contents

- [Entry points and navigation](#entry-points-and-navigation)
- [Public pages and offering boundaries](#public-pages-and-offering-boundaries)
- [Authoritative metadata and configuration](#authoritative-metadata-and-configuration)
- [Workspace layout and shared UI](#workspace-layout-and-shared-ui)
- [Feedback, notifications and activity](#feedback-notifications-and-activity)
- [Shared pagination and resource selectors](#shared-pagination-and-resource-selectors)
- [Documentation, content and metadata](#documentation-content-and-metadata)
- [Forms, pricing and account links](#forms-pricing-and-account-links)
- [Build output and delivery](#build-output-and-delivery)
- [Implementation ownership](#implementation-ownership)
- [Extension examples and release checks](#extension-examples-and-release-checks)

## Entry points and navigation

[`AppRoutes.jsx`](../frontend/src/app/AppRoutes.jsx) is the frontend route map.
`main.jsx` supplies the data router and theme/store providers; feature routes are
lazy-loaded with the shared loader. Unknown routes render the themed NotFound page.

| Area | Entry/layout | Responsibility |
| --- | --- | --- |
| Home | `/`, `LandingPage.jsx` | Explain the workflow, feature discovery and next action |
| Public pages | `SiteLayout` / `CustomerPages` | Product, pricing, contact, documentation and policies |
| Auth | `/login`, `/register`, reset and Google completion routes | Account entry/recovery with the same shared controls |
| Shared strategy | `/strategy/view/:id` | Current publicly shared strategy configuration, not account/trading results |
| Workspace | `ProtectedRoute` → `AppLayout` | Authenticated product navigation, scope gating and page state |
| Operations | `/admin/` through backend ingress | Separate staff/OTP Django Admin, not React workspace permissions |

The initial user path is home → registration/sign-in → Overview or requested
workspace page → research/rules/test/Paper/review. Authentication initializes before
protected content. Public content does not mount the authenticated trading layout
or its market connection merely because it shares the same build.

Workspace routes include:

| Task | Route |
| --- | --- |
| Overview | `/overview` |
| Profile/Account/Security/Notifications settings | `/settings/profile?tab=…` |
| Billing | `/settings/billing` |
| Requests and replies | `/support` |
| AI chat / screener | `/research`, `/screener` |
| Strategies / create / details / Studio | `/strategies`, `/strategies/create`, `/strategies/:id/edit`, `/strategies/:id/studio` |
| Versions / sharing | `/strategies/:id/versions`, `/strategies/:id/permissions` |
| Historical tests | `/backtests` and setup/results/trades/charts/Monte Carlo subroutes |
| Automated Paper | `/paper`, `/paper/portfolio`, `/paper/capital`, `/paper/analytics` |
| Manual simulation | `/terminal` |
| Broker connections / logs | `/brokers`, `/brokers/logs` |
| Charge profiles | `/brokers/charge-profiles` (retained route, available as a shared trading tool) |
| Live deployments / portfolio / logs | `/live/strategies`, `/live/portfolio`, `/live/logs` |
| Journal / performance / activity / notifications | `/journal`, `/reports`, `/activity`, `/notifications` |

Paper/Terminal routes require `paper` execution scope. Live/broker routes require
`live`, except the shared charge-profile route. AppLayout handles direct unavailable
links as well as sidebar visibility. Server-side ownership/scope/allowance checks
remain authoritative.

There is no separate Private registration/menu theme or mode-based removal of
site pages. Effective scopes, account limits and checkout availability can differ
without creating another frontend application.

## Public pages and offering boundaries

| Route/group | Customer purpose |
| --- | --- |
| `/product`, `/features`, `/features/:slug` | Explain what each current tool accepts, does and returns |
| `/pricing` | Display the published plans/allowances and link to reviewed billing |
| `/private` | Explain that customer Private/Live is not currently offered |
| `/custom-development` | Describe separate software development enquiries; not a project-management workspace |
| `/docs`, `/docs/:document`, `/docs/reference` | Task guides and backend-driven builder input reference |
| `/about`, `/faq` | Operator/product context and common questions |
| `/contact`, `/feedback` | Request help, send feedback or discuss a requirement |
| `/status`, `/changelog` | Editorial service information; no claim of external automatic monitoring |
| `/trust`, `/security`, `/methodology` | Controls and data/simulation explanations |
| `/privacy-policy`, `/terms-of-service`, `/refunds` | Published policy text and customer responsibilities |

Public catalogue defaults advertise **NSE-stock research/testing/simulation**.
Explore lists stocks; Build/Pro also list futures/options as **Coming soon**, with
no release date. The current catalogue validator prevents publishing those F&O
market flags as available. Internal contract/execution capabilities are described
in technical guides; they are not a reason to promise public access early.

Public plans do not offer customer Live trading or customer Private deployments.
Personal/operator Private retains separate Live code/use. The archived earlier
Private marketing source is outside the frontend bundle and is not current copy.

Custom development remains an enquiry offering. Specifications, contracts, project
delivery, milestones and project payments are outside this product's current
workflow. A support request does not create a project record or subscription.

## Authoritative metadata and configuration

| Information | Source | Consumers |
| --- | --- | --- |
| Published plans, prices, limits, market flags, feature summaries | Active database commercial catalogue | Pricing, feature discovery and Billing |
| Execution scopes and checkout availability | Public catalogue response from server settings | Sidebar, AppLayout and checkout UI |
| Contact/legal name/support hours | Backend settings exposed in catalogue | Footer, contact, Support |
| Support request/status labels | `customer_support/catalog.py` | Public forms and signed-in Support |
| Enums and full `StrategyStudio` specification | `/api/v1/common/enums/` | `EnumsProvider`, Studio, tables and builder reference |
| Pagination defaults | Same enums response, from `StandardPagination.defaults()` | Shared pagination component/hook |
| Owned resource labels | `/api/v1/common/choices/` | Searchable selectors without full model payloads |
| Research limits and defaults | `/api/v1/research/schema/` | Account-specific research controls, not another operand catalogue |
| Editorial explanation | `features/site/content/` | Public page composition |
| Actual routes | `AppRoutes.jsx` | Router and build-generated route assets |

`PlatformProvider` loads `/api/v1/public/catalog/`, validates the expected shape,
coalesces concurrent loads and holds it in memory. Startup, explicit retry and
billing refresh load it; there is no continuous catalogue polling interval.
An open page may need a reload/explicit refresh after a catalogue publication.

Invalid/missing platform configuration must show load/retry state rather than
invent a fallback paid allowance. Editing a price/limit only in a React component
does not change billing or server admission.

The enum provider similarly owns shared specification loading/retry. UI consumers
use the canonical labels/templates/contexts. Provider/contract identifiers used
for logic are distinct from readable display labels.

Use `QUANTNEST_LEGAL_NAME`, `QUANTNEST_SUPPORT_EMAIL` and
`QUANTNEST_SUPPORT_HOURS` for operator identity. `VITE_SITE_URL` is a public
canonical/build origin; `VITE_TURNSTILE_SITE_KEY` is a public widget key. SMTP,
provider, signing, gateway and payment secrets stay outside Vite browser values.

## Workspace layout and shared UI

`AppLayout` owns the responsive sidebar, compact main header, page actions/custom
header area, bounded content region, error boundary and scope notice. Pages
register title/actions through shared page contexts instead of nesting another
large header in every card.

Use the shared primitives in `src/shared/components/ui/` and shared composed
components:

| Component/boundary | Intended use |
| --- | --- |
| `PageTabs` / common Tabs | Consistent selected/hover states; content tab groups fit their items instead of spanning unused page width |
| `Button`, `Input`, `Select`, `DatePicker`, `TimePicker` | Consistent size, focus, label and disabled behavior |
| Checkbox/radio/switch | Theme-aware selection; retain real accessible state/labels |
| `Card`, `Table`, shared pagination | One clear content boundary and compact data presentation |
| `RefreshButton` | Same refresh icon/loading/tooltip; only where it reloads meaningful data |
| `GlobalLoader`, `WorkspaceState` | Shared brand loader and persistent content loading/error/empty/retry states |
| Dialog/custom confirmation | Shared theme, separated buttons and bounded scrollable body |
| `BrandLogo`, `UserAvatar` | Canonical emblem/wordmark and bounded signed-avatar retrieval |
| `formatters.js` | Consistent date/time/currency/number presentation |

Use semantic background/foreground/border/brand/success/loss tokens in both
themes. Numeric financial displays normally use common two-decimal formatting;
integer counts/lots and explicit three-decimal AI credits have their own intended
precision. Input validation and stored values must not be reduced to display
precision; currency contracts can need finer ticks.

Theme supports light/dark/system with shared persisted preference and startup
application. Keep text contrast and hover states readable, honor reduced motion,
and use keyboard focus rather than rely on color alone. Global brand loaders use
the same emblem geometry as the actual logo.

Long names use deliberate truncation/tooltips or wrapping in min-width-zero
containers. Chat-list titles should not expand into unbounded multi-line blocks.
Tables scroll inside their region; dialogs should not gain competing outer/body
scrollbars. Avoid double card borders and extra page-top/card gaps.

Browser reload/close with unsaved work can invoke the browser's native unload
prompt. In-app navigation can use the application's shared confirmation. A browser
does not permit replacing its native unload dialog with arbitrary React content;
do not remove protection merely to make that browser UI look themed.

## Feedback, notifications and activity

Use `useNotifications()` for user-action outcomes: success/error/info/warning.
Use `getApiErrorMessage()` for meaningful backend failures. One shared container
renders feedback above dialogs; duplicate local success banners are unnecessary.

Field validation belongs beside its input. Content-load failures need a persistent
retry state; an execution error/status remains relevant page content. Background
refresh must not repeatedly produce error toasts. Preserve drafts after a failed
mutation so the user can correct/retry them.

The Notification Centre is a persistent owned record list, separate from ephemeral
action toasts. It provides filters, summary/unread counts, server pagination,
mark-read/mark-all and eligible deletion actions. Notification preferences control
supported in-app categories; they are not a newsletter/product-analytics opt-in.
Audit Activity History provides scoped action/entity/date/search filters and
details; it is not a public operator log or a replacement for trade history.

User/session change clears private notification/stream state. Reconnect restores
current snapshots. Public application-error reporting accepts only fixed
content-free categories, not user prompts/strategies or visitor analytics.

## Shared pagination and resource selectors

This is the current list-loading reference. It describes implemented contracts,
not future migration phases.

### Record tables and lists

`backend/common/pagination.StandardPagination` is the shared table/list contract:

| Query | Behavior |
| --- | --- |
| `page` | Positive decimal integer, default 1 |
| `page_size` | One of 10, 25, 50 or 100; default 25 |
| Invalid input | Validation error, not an unbounded array request |
| Page beyond current final page | Clamp to the actual last page, including after deletion/filter changes |

Example response shape (illustrative empty page):

```json
{
  "count": 0,
  "page": 1,
  "page_size": 25,
  "next": null,
  "previous": null,
  "results": []
}
```

The backend applies ownership → validated filters → deterministic ordering with
an ID tie-breaker → database page → lightweight serialization. Domain summary
endpoints calculate the whole filtered scope, not the visible page.

`Pagination.jsx` displays result range, row-size choice, icon first/previous/next/
last controls and a direct page input. Enter submits a validated page; Escape
restores the current value. Loading disables navigation; compact mode omits first/
last icons. Empty state remains a usable page 1 rather than an invalid page zero.

`usePagination()` owns URL page state and server-clamped page acknowledgement;
domain hooks own fetching. `useQueryState` / `useQueryDateState` keep filters in
the URL. Filter/page-size changes reset to page 1; browser Back/Forward restores
the relevant URL state. Namespaces separate multiple lists on the same page.

Search is sent to the server with bounded/debounced requests where appropriate.
Aborted/obsolete responses must not replace a newer filter/page/account. A refresh
reloads the current list/summary rather than accumulating duplicate items.

Trade tables, backtests, strategies/versions, research runs/evidence, support,
notifications, logs, journal and reporting use their feature contracts. A global
claim that every array is paginated would be incorrect: small fixed metadata,
bounded snapshots and named-watchlist collections have intentional different jobs.

### Resource dropdowns

`GET /api/v1/common/choices/?resource=…` is an authenticated, lightweight selector
contract. Supported resources include strategies, strategy versions, named
Terminal watchlists, charge profiles, broker accounts, Paper accounts, Live
allocations, completed/filtered backtests, saved screens and strategy tags.

It returns `results`, `has_more`, `page` with **20 options plus one internal
look-ahead**, not a full table COUNT. Query by selected `id` restores a label
without downloading all records. Strategy versions require `strategy_id`.
Allowed filters and ownership are defined per resource; full strategy definitions
and secrets are not serialized as dropdown options. Global tags are intentionally
shared; user resources remain scoped.

Do not use `fetchAllPages` to rebuild the whole resource collection in the browser.
Use a searchable resource Select and request the selected value explicitly.

### Charts, live exposure and evidence

- Chart history uses a time cursor and bounded candle windows, not page-number
  table pagination. See [Terminal charts](trading-terminal.md#chart-history-and-live-candles).
- Full-scope open P&L uses a compact `valuation_positions` vector independent of
  the visible positions page. Ticks update its shared marks without reloading
  every table page.
- Research evidence table rows live in database rows and page on the server;
  slicing one giant stored JSON response in the browser is not equivalent.
- Live financial/revision events refresh relevant snapshots; price display
  coalescing is separate from financial list loading and execution.

## Documentation, content and metadata

`features/site/content/docs/*.md` are concise customer articles bundled with Vite.
Each uses title/description/order frontmatter. `Documentation.jsx` derives slugs
from filenames, renders Markdown/GFM, searches the local article set and supplies
adjacent-guide navigation. Unknown article slugs render NotFound.

`/docs/reference` reads timeframes/operand choices from the shared Studio metadata.
It is not a manually maintained second indicator list. Repository `docs/` supplies
the deeper user/operator/technical guides and is not automatically bundled into
the customer article set.

`features.js` contains task-focused feature copy; `general.js` contains company,
service and policy text; `config.js` owns public brand URL/widget settings and FAQ
content. `CustomerPages` chooses the layouts; `SiteIllustration`/illustration
components supply code-native explanatory artwork. Artwork must not imply actual
performance or expose fake working order controls.

`SiteMetadata` updates canonical URL, Open Graph preview and Organization JSON-LD
from the canonical site URL and backend contact identity. It observes later title/
description changes from lazy pages. This is metadata management, not product
analytics. Page-specific title/description remains the feature page's responsibility.

The application is a client-rendered SPA. A sitemap and canonical tags improve
discovery but are not a promise that every crawler/social preview renders every
client-side route exactly like a browser.

## Forms, pricing and account links

Public Contact/Feedback form options come from the backend support specification.
Guests submit `/api/v1/public/enquiries/` with configured Turnstile verification;
signed-in users submit owned `/api/v1/support/tickets/`. The form makes email
read-only for the signed-in identity. Replies/verified guest-ticket association
are described in [Support](customer-support.md).

Turnstile remains implemented for public enquiries. Development+DEBUG bypasses
server verification; production requires matching secret, token action `enquiry`
and allowed hostname. Removing a widget alone would leave the API refusing guests.

Pricing uses the published catalogue and display divisors. Paid buttons lead to
Billing for current totals/verified email/explicit renewal consent. Razorpay's
browser callback does not grant access on its own; server payment verification
does. A unavailable checkout state is displayed instead of an invented payment path.

Account settings link to Billing/Support/guides, export records and settled-account
shutdown. Profile edits, Security and Notifications use shared tabs. No newsletter,
product-analytics preference, standalone onboarding checklist or project-delivery
workspace is part of the current customer flow.

## Build output and delivery

From the repository root:

```powershell
npm ci --prefix frontend
npm run build --prefix frontend
```

`frontend/scripts/build.mjs` runs Vite and derives route artifacts from AppRoutes,
feature slugs and customer Markdown. It does not fetch a backend catalogue during
build; live catalogue configuration loads at runtime.

| Generated output | Purpose |
| --- | --- |
| `index.html`, hashed assets | Main React shell and code |
| `404.html` | Recovery shell for unknown/deep paths as configured by hosting |
| `_redirects` | Explicit known frontend route rewrites |
| `_routes.json` | Limit edge function invocation to backend/API/Admin/socket/static/health paths |
| `routes.caddy`, `security.caddy` | Private ingress frontend matcher and CSP |
| `_headers` | Static cache/security policy |
| `sitemap.xml`, `robots.txt` | Public route discovery and crawler guidance |

Production canonical `VITE_SITE_URL` must be HTTPS. Build verifies required brand
and font assets. No secret gateway/provider key belongs in generated static files.
Static assets can cache strongly; authenticated API/Admin responses cannot.

Development uses the Vite proxy; Public uses the configured edge gateway; Private
uses its ingress topology. All preserve same-origin browser paths. The edge
backend-path handler is transport, not another customer-site application. See
[Public deployment](../infra/public/README.md),
[Private deployment](../infra/private/README.md) and
[Development](../infra/development/README.md) for actual ingress configuration.

## Implementation ownership

| Source | Responsibility |
| --- | --- |
| [AppRoutes.jsx](../frontend/src/app/AppRoutes.jsx) | Route authority and lazy page imports |
| [PlatformProvider.jsx](../frontend/src/shared/context/PlatformProvider.jsx) | Catalogue load/coalescing/retry and execution scopes |
| [EnumsContext.jsx](../frontend/src/shared/context/EnumsContext.jsx) | Shared enum/Studio metadata |
| [SiteLayout.jsx](../frontend/src/features/site/SiteLayout.jsx), [CustomerPages.jsx](../frontend/src/features/site/CustomerPages.jsx) | Public shell/page composition |
| [SiteMetadata.jsx](../frontend/src/features/site/SiteMetadata.jsx) | Canonical/social/organization metadata |
| [Documentation.jsx](../frontend/src/features/site/Documentation.jsx) | Customer articles/search/live builder reference |
| [AppLayout.jsx](../frontend/src/shared/components/layout/AppLayout.jsx) | Authenticated shell, scopes and page actions |
| [Pagination.jsx](../frontend/src/shared/components/Pagination.jsx), [usePagination.js](../frontend/src/shared/hooks/usePagination.js) | Common list controls and URL state |
| [pagination.py](../backend/common/pagination.py), [choices.py](../backend/common/choices.py) | Server table and selector contracts |
| [formatters.js](../frontend/src/shared/utils/formatters.js), [shared UI](../frontend/src/shared/components/ui) | Common presentation/controls |
| [build.mjs](../frontend/scripts/build.mjs) | Static route/security/discovery output |

## Extension examples and release checks

### Add an ordinary customer article

Add a Markdown file under the customer article directory with valid frontmatter,
use the actual implemented workflow, link the appropriate feature route and rebuild.
The article slug/navigation/build discovery derive from that file. A deep technical
repository guide is linked separately; copying the whole guide into both places
creates competing sources.

### Add a paginated financial table

Scope/filter/order its queryset on the backend, select related data before
serialization and use StandardPagination. Return full-filter aggregates separately.
Use `usePagination` and `Pagination`, cancel stale loads and connect relevant
financial refresh events. Do not compute total P&L from the currently visible rows.

### Add a new selectable account resource

Declare safe fields/search/ownership in the choices registry, then use the common
resource Select. Fetch the selected ID label directly. Do not expose credentials
or load whole account histories for a dropdown.

Release checks should cover public deep links, signed-out protected routes,
both themes, keyboard focus, reduced motion, narrow/long-text layouts, metadata
load/retry, form failures, scoped resource search, pagination/filter/back history,
shared action feedback, real gateway/cookie handling and build-generated routes.
UI consistency does not replace server authorization or prove a provider/payment
integration is available.
