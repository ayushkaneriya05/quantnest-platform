# Customer website and workspace integration

**Source review: 16 October 2026.** One React/Vite application serves the public
website and authenticated workspace. There is no separate Astro application or
generated backend-data export. User/operator workflows are in
[Commercial operations](commercial-operations.md); this guide owns frontend structure.

## 1. Entry points and layouts

| Area | Route / owner | Responsibility |
| --- | --- | --- |
| Home | / and pages/LandingPage.jsx | Product explanation, feature discovery, plans and next actions |
| Public customer pages | SiteLayout + CustomerPages | Product, features, services, company, trust, forms and policies |
| Public documentation | /docs and /docs/:document | Searchable customer guides and builder reference |
| Shared strategy | /strategy/view/:id | Anonymous current public configuration |
| Authentication | auth feature routes | Sign-in, registration, reset and Google completion |
| Workspace | ProtectedRoute + AppLayout | Authenticated product pages and scope notices |
| Unknown routes | NotFoundPage | Themed recovery and useful navigation |

[AppRoutes.jsx](../frontend/src/app/AppRoutes.jsx) owns actual frontend routes.
A feature page is lazy-loaded; public content does not mount the trading workspace
or initialize its live-data sockets.

The former dashboard folder/layout layer is not a routing requirement. Domain
features own their pages, components, hooks and API callers. Reusable UI and
contexts remain in frontend/src/shared/; that folder is application code.

## 2. One source of truth

| Information | Owner | Frontend consumer |
| --- | --- | --- |
| Published plans/prices/limits/markets and feature descriptions | Backend commercial catalog | PlatformProvider, pricing, PlanMarkets, Billing |
| Effective scope and contact identity | Public catalog response | Layout guards, footer, contact and account pages |
| Support types/status labels | Backend customer_support/catalog.py | Public forms and workspace Support |
| Operand/timeframe/default choices | Backend common enums | EnumsContext, builder and builder reference |
| Routes | AppRoutes.jsx | Router and build-generated route files |
| Product explanations | features/site/content | Customer layouts and illustrations |

PlatformProvider loads /api/v1/public/catalog/, validates its response shape,
shares concurrent requests and keeps the catalog in memory while the app is open.
It loads on startup and refreshes explicitly for billing actions or a retry;
there is no timer or window-focus polling. Reload the page to see catalog changes
published while it was open. Loading/error states remain visible rather than
inventing fallback plan entitlements.

Changing plan limits in a frontend component does not change backend admission.
Purchased terms remain tied to their catalog revision.

Set QUANTNEST_LEGAL_NAME, QUANTNEST_SUPPORT_EMAIL and QUANTNEST_SUPPORT_HOURS on the
backend to change organization/contact details. There are no separate frontend
copies. VITE_SITE_URL is the browser/build canonical URL; VITE_TURNSTILE_SITE_KEY
is a public widget key. Secrets are server/platform configuration.

## 3. Public information architecture

The home page proceeds through:

1. Who the workspace serves and its primary registration/product action.
2. The research → rules → historical test → Paper → review workflow.
3. Direct access to all public feature pages.
4. Conversational research explanation.
5. A separate custom development offering and an unavailable-to-customers Private notice.
6. Authoritative Explore/Build/Pro pricing.
7. FAQ and documentation.
8. A final registration/contact action.

Terminal is an available feature, with its own feature explanation; there is no
separate oversized homepage Terminal section or dashboard screenshot.

Other pages have different jobs:

| Page group | Customer question |
| --- | --- |
| Product / features | What can I do and what input/result should I expect? |
| Individual feature | How does this task work and what are its limits? |
| Pricing | Which allowance fits my current use? |
| Private | How can supported Live run in my own agreed installation? |
| Custom development | How do I request software against my specification? |
| Documentation / FAQ | How do I complete a task or resolve a common issue? |
| About / trust / security / methodology | Who operates it and what should I understand? |
| Contact / feedback | How do I ask, report or suggest something? |
| Privacy / terms / refunds | What responsibilities and rights apply? |
| Changelog / status | What is current and what has the operator announced? |

Status/changelog content is editorial. It must not be mistaken for an external
automated monitoring service.

## 4. Content and illustration files

- [features.js](../frontend/src/features/site/content/features.js) contains task-focused
  feature copy: capabilities, steps, inputs, outputs and limits.
- [general.js](../frontend/src/features/site/content/general.js) contains service,
  company and policy explanations.
- [content/docs](../frontend/src/features/site/content/docs) contains customer Markdown
  guides with title/description/order frontmatter.
- [Documentation.jsx](../frontend/src/features/site/Documentation.jsx) loads guides,
  supports local search/navigation and renders the backend-driven builder reference.
- [CustomerPages.jsx](../frontend/src/features/site/CustomerPages.jsx) selects
  page-specific layouts.
- [SiteIllustration.jsx](../frontend/src/features/site/SiteIllustration.jsx) and
  [illustrations](../frontend/src/features/site/illustrations) select contextual,
  code-native animated figures.
- [site.css](../frontend/src/features/site/site.css) owns public-site presentation.

Each feature has its own illustration. Controls explains sessions/security/activity;
Private displays an unavailable-to-customers notice. Generic workflow/configuration artwork
should not be repeated across unrelated pages.

Figures explain the workflow. They do not fabricate execution results or expose
working trading controls. Motion respects reduced-motion preference; explanatory
selectors remain keyboard usable. Keep component layout responsive and text readable
rather than enforcing fixed screenshot dimensions.

## 5. Support and payment actions

Public enquiries call /api/v1/public/enquiries/. Signed-in support uses the owned
ticket APIs. Both use the same backend labels and shared HTTP error handling.
Anonymous forms require the configured Turnstile action/hostname verification.

Product usage and website visits are not tracked. Application error reporting
accepts fixed categories without support or strategy content. Account settings
provide data export and safe deactivation/deletion.

Billing has Plan and renewal, Usage and limits, and Payments and invoices.
The backend calculates checkout totals and verifies provider state. A successful
browser callback is not authority to grant access.

For detailed ticket replies, subscription payment recovery, privacy actions
and personal deployment setup, follow Commercial operations.

## 6. Markets and Live communication

Explore shows NSE stocks. Build/Pro show NSE stocks and **Coming soon** futures/
options. The current catalog does not enable derivatives or provide a release date.

Public plans are simulation products. Customer Live and Private deployments are
not offered. Personal Live code remains available only on the separate operator
instance. Previous Private marketing source is archived outside the application bundle.

Navigation shows Broker Integration and Live Trading only when Live scope is
enabled. Direct links still enforce the execution-scope notice in AppLayout. Charge Profiles belongs to Trading Tools,
even though its retained route is /brokers/charge-profiles; it is not broker-owned.

## 7. Theme, responsive layout and account navigation

ThemeProvider resolves light, dark or system preference, applies the document
theme/color scheme, and shares persisted changes across tabs. Initial document
setup avoids a flash while React starts. Workspace theme selection is in Profile.

Use semantic background/foreground/border tokens for new components. Modals,
dropdowns, chart colors, skeletons and disabled states need both themes. Long names
and version notes must truncate/wrap within min-width-zero containers; tooltip
content must remain readable.

Use the existing mobile sidebar/drawer, wrapping page actions, responsive form
grids and bounded dialog body scrolling. Tables may scroll horizontally within
their container; the whole page should not overflow.

The profile menu uses full clickable item areas. Profile, Account, Security and
Notifications tabs are selected through ?tab=. UserAvatar resolves the signed
same-origin image URL and bounded refresh. The plan name comes from current account
data rather than the retired Starter label.

The standalone Getting Started workspace checklist is removed. The menu links to
/docs/getting-started/. Account API keys, marketplace permissions, invitations and
public demonstration tooling are outside current scope.

### User feedback

Use `useNotifications()` from `src/shared/hooks/useNotifications` for the outcome
of a user action. Call `notify.success(...)`, `notify.error(...)`, `notify.info(...)`
or `notify.warning(...)` in its event handler. Format API failures with
`getApiErrorMessage`. The single `NotificationContainer` in `App.jsx` displays
these notifications across the customer site, authentication and workspace.
Remove local success/error banners and message state when they duplicate this
action feedback; keep the form and its draft available after a failed request.

Field validation stays beside the relevant input. Failed content loads use
`WorkspaceState` or the feature's persistent error/retry view. Saved execution
statuses, account restrictions and email confirmation results remain part of the
page content. Background polling should not repeatedly create toasts.

Notifications are announced to assistive technology and stay visible above
dialogs. Clicking a notification does not dismiss the open dialog. Authentication
changes clear previous notifications, so dispatch sign-in/sign-out state changes
before adding the outcome notification, then navigate normally.

## 8. Build and deployment output

From the repository root:

```sh
npm ci --prefix frontend
npm run build --prefix frontend
```

[build.mjs](../frontend/scripts/build.mjs) runs Vite and derives route assets from
AppRoutes, feature slugs and customer Markdown files. No Python or backend fetch is
required during the build.

| Output | Purpose |
| --- | --- |
| index.html and hashed assets | Main React application |
| 404.html | React recovery shell with unknown-route HTTP status |
| _redirects | Explicit known frontend routes/deep links |
| _routes.json | Limit Cloudflare Function invocation to backend routes |
| routes.caddy / security.caddy | Private route matcher/security headers |
| _headers | Static asset caching and security policy |
| sitemap.xml / robots.txt | Public discovery and crawler guidance |

The Cloudflare catch-all Function is still required for owned API, Admin,
WebSocket, health and Django static routes. It validates/configures its upstream
and adds trusted headers. It is not a second customer application.

Vite's QUANTNEST_API_PROXY_TARGET configures only the development server's upstream.
The browser always uses same-origin /api/v1/. Production does not need a separate
VITE_REACT_APP_API_URL. Follow [Public](../infra/public/README.md) or
[Private](../infra/private/README.md) for deployment instead of treating Vite as a
production server.

## 9. Change and release checklist

1. Update the owning backend catalog/metadata when changing data or entitlement.
2. Update explanatory copy/illustrations to match actual functionality.
3. Add routes in AppRoutes; add feature/doc content in its owning directory.
4. Use the shared API and session components.
5. Keep provider/secrets/hosting details out of ordinary product copy except where
   relevant to a customer's decision or privacy disclosure.
6. Review phone/tablet/desktop widths, both themes, keyboard focus and reduced motion.
7. Review loading, empty, denied, failed and successful states.
8. Check deep links, unknown pages, documentation search and real gateway callbacks.

The current site is a client-rendered React application. A sitemap and metadata
do not make it server-rendered or guarantee indexing. Keep that boundary clear
when planning search acquisition improvements.
