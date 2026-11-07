# Customer Support, enquiries and account records

**Source reviewed: 7 November 2026.** This guide documents the current request/
reply system from public enquiry to operator response, email delivery and owned
account-record actions. It is a support inbox, not a project-management product.

Related: [Authentication](authentication.md), [Customer site](customer-site.md),
[Commercial operations](commercial-operations.md) and
[integration setup](../infra/shared/INTEGRATIONS.md).

## Contents

- [Scope and records](#scope-and-records)
- [Request types and statuses](#request-types-and-statuses)
- [Public contact and feedback](#public-contact-and-feedback)
- [Signed-in requests and replies](#signed-in-requests-and-replies)
- [Operator workflow](#operator-workflow)
- [Outbound email and verified association](#outbound-email-and-verified-association)
- [Custom-development enquiries](#custom-development-enquiries)
- [Account export, shutdown and retention](#account-export-shutdown-and-retention)
- [Content-free application error reports](#content-free-application-error-reports)
- [API contracts](#api-contracts)
- [Implementation ownership and extension](#implementation-ownership-and-extension)
- [Configuration and worked examples](#configuration-and-worked-examples)
- [Troubleshooting and release checks](#troubleshooting-and-release-checks)

## Scope and records

The same system accepts public enquiries and owned signed-in support requests.
An operator reads them in Operations Admin and can assign status/assignee and
reply. Customers see their own requests/replies in `/support`; guests receive
outbound email and can later gain owned access after email verification.

| Record | Responsibility |
| --- | --- |
| `Ticket` | UUID reference, optional owner, contact name/email, request type, subject/body, status and assignee |
| `Reply` | Ticket message, author, staff marker and creation time |
| `ErasureRequest` | Pending/completed optional-content cleanup after sign-in identity erasure |

There are no current project quotations, workspaces, milestones, deliveries,
project payments, newsletter lists, product-analytics preferences or inbound-email
webhook routing. The archived `private` request type can remain on historical
records, but new customer Private enquiries are not accepted under that category.

The user-facing support page is not a staff-wide dashboard and exposes no arbitrary
ticket ownership/status editor. Operations Admin uses its separate staff/OTP and
model permissions.

## Request types and statuses

Labels come from `customer_support/catalog.py`, exposed inside the public catalogue
and shared by both enquiry forms. Do not duplicate a second list in a page.

| Active request type | Intended use |
| --- | --- |
| `general` | Product/service question |
| `custom` | Separate custom software-development enquiry |
| `support` | Account/product workflow issue |
| `feedback` | Suggestion or usability feedback |
| `grievance` | Complaint requiring operator review |
| `security` | Security report without secrets in its body |

`private` is excluded from selectable options and rejected by request validation;
customer Private/Live is not currently offered. General questions remain possible
without creating a customer installation workflow.

| Status | Meaning / transition |
| --- | --- |
| `received` | Newly created request |
| `awaiting_support` | Customer replied; operator should review |
| `awaiting_customer` | Operator added a staff reply |
| `in_progress` | Operator-set work-in-progress label |
| `resolved` | Operator considers the issue resolved |
| `closed` | Operator closed the current conversation/retained record |

The current API allows an owned customer reply to move a request back to
`awaiting_support`, including after a resolved/closed label. Those labels do not
make the transcript permanently unreplyable. Assignment/status is an operator
decision, not automatically inferred from an email delivery event.

New subjects are trimmed, 3–180 characters; original bodies are 10–10,000.
Replies are trimmed, 2–10,000. UUID references identify requests; they do not grant
anonymous access to a transcript by themselves.

## Public contact and feedback

1. Open `/contact` or `/feedback`, or follow the Custom Development enquiry link.
2. Provide name, email, type, subject and enough detail to reproduce/understand
   the issue. Do not include passwords, broker secrets, API tokens or backup codes.
3. Complete the configured public form verification.
4. Submit. `EnquiryView` validates the Turnstile response and serializer, saves an
   unowned ticket and queues its acknowledgement after transaction commit.
5. The response gives UUID reference, current status and received message. Preserve
   that reference when following up.
6. The operator replies through the staff workflow; the guest receives outbound
   email. Public possession of an email address is not an authenticated inbox login.

### Public form verification

The current implementation **uses Turnstile** for anonymous enquiries. Server
verification checks configured secret, token success, allowed hostname and action
`enquiry`, with a bounded network timeout. Invalid/missing verification is rejected.
Only Development **and DEBUG** bypass this check for local work; Public/Private
production-style forms need matching configuration.

The frontend site key is public. The secret remains server-side. The form resets
its token after submission/attempt so an expired/used challenge is not assumed
reusable. Normal anonymous throttling applies as a separate control.

When the visitor is signed in, `EnquiryForm` instead calls the owned ticket endpoint
and uses the account email. It does not unnecessarily route that user through the
anonymous challenge path.

## Signed-in requests and replies

Open **Support** (`/support`):

1. Choose **New request**, select a backend-provided category and write the issue.
2. The server forces the authenticated account email and saves `user=request.user`;
   sending another email in a payload cannot claim a different account's ticket.
3. The list shows only owned lightweight request summaries, newest updated first,
   using shared server paging and an ID tie-breaker.
4. Select a request to fetch its body and replies. The list does not preload every
   transcript; stale detail/list responses cannot replace a newer selection.
5. Send a reply. It records a non-staff author, moves status to `awaiting_support`
   and refreshes the owned list/detail.
6. Use Refresh to retrieve a staff reply/status change. This page does not have a
   separate realtime-support socket or continuous transcript polling promise.

On narrow screens the selected conversation replaces the list, with an All
requests return action. Long messages wrap; input validation remains alongside
shared action notifications. Failed sends preserve the draft for correction/retry.

The current create/reply handlers are not a generic UUID-idempotent mutation
framework. The UI prevents double submission while busy; after an uncertain
network result, inspect the saved transcript before posting the same message again.

## Operator workflow

In **Operations Admin → Customer Support → Tickets**:

1. Filter request type/status or search subject/email.
2. Open the UUID request and read its original message and existing transcript.
3. Set the appropriate assignee/status for the actual support work.
4. Add a new Reply inline and save. The admin sets the current staff author and
   `staff=true`, updates the request to `awaiting_customer`, and queues outbound
   email with reference/contact information after commit.
5. Existing replies are not editable/deletable through the inline. Send a clear
   correction as another message rather than rewrite what the customer saw.
6. Mark resolved/closed when appropriate; those are operator labels, not evidence
   that the customer received an email or that trading exposure was changed.

Ordinary customers cannot create staff replies or change assignee through their
read/create/reply APIs. A support reply does not activate a plan, place an order,
clear an UNKNOWN broker state or bypass account shutdown preconditions. Use the
owning feature's validated service/operator workflow for those changes.

Publishing support hours uses backend `QUANTNEST_SUPPORT_HOURS`. The default text
is working hours with no response-time SLA; do not display a guaranteed instant
response or 24/7 desk unless operations actually provide it.

## Outbound email and verified association

`queue_support_email()` uses robust `transaction.on_commit` scheduling. A rolled-back
ticket/reply does not send email describing an unsaved message. Queue-publication
failure does not reverse the already committed ticket; logs and the transcript
remain the recovery reference.

`customer_support.send_email` uses Django `EmailMessage` and SMTP settings. It
retries exceptions with bounded backoff (up to five retries). SMTP acceptance is
not proof of inbox delivery; retry after an uncertain send can also duplicate an
email. The system does not maintain a delivery/read receipt state or universal
exactly-once outbound-message ledger.

Brevo can remain the configured **SMTP transport**. There is no Brevo inbound/
delivery webhook, bounce tracking, unsubscribe list or email-to-ticket reply parser
in the current app. Replying to an email does not automatically append to the
workspace conversation; use workspace Reply or the separately published contact
channel for a deliberate operator response.

### Link guest tickets safely

`link_verified_customer_records()` runs during successful login/session refresh.
It associates unowned tickets with the account only if its same email is verified,
using case-insensitive matching. It does not reassign an already owned ticket to
another user or claim guest records just because an unverified address was typed
at signup.

After verification, sign in/refresh and reopen Support. This is not a separate
anonymous “open ticket by reference” endpoint. Changed profile display names do
not change ownership or rewrite the original contact facts.

## Custom-development enquiries

Custom Development is a request type and public information page. Customers may
describe any agreed software tool/service requirement. The current QuantNest app
retains the enquiry and support replies only.

Project scoping, quotation/contract, milestones, acceptance criteria, source-code
ownership, delivery, project billing and maintenance are communicated separately.
There is no customer project dashboard, quotation approval, milestone payment,
delivery upload or project license architecture hidden behind this request type.
Do not route a custom-project payment into the Public Build/Pro subscription APIs.

If future project tooling is introduced, it needs its own deliberate ownership,
financial and delivery design. A support status `in_progress` is not a substitute
for those product records.

## Account export, shutdown and retention

These controls are reached through **Profile Settings → Account** and implemented
in `users/privacy.py`; the export route remains under `/support/` for continuity.

### Complete bounded export

`POST account/export/` returns `quantnest-account-export.json`, limited to two
requests per user per day and **10 MiB total**.

- Records stream through database iterators into a bounded complete JSON file.
- There is no current “1,000 rows per category / 100 strategies” truncation rule.
- If the file exceeds 10 MiB, the operation fails with a scoped-export instruction;
  it does not return a successful silently incomplete document.
- Categories include account identity, strategies/versions, research, backtests/
  trades/Monte Carlo, Terminal/Paper/Live records, journal, invoices/refunds and
  owned support requests.
- Secrets, passwords and recovery codes are not exported. The current support
  export selects request records; it does not promise every Reply transcript or
  every possible operator/system record is included.
- The JSON may contain sensitive user strategy/research/account content; it is
  an authenticated download with no-store caching, not a public report.

The export action's authentication and CSRF still apply. A 403 is not necessarily
the file-size limit; inspect the structured error for session/CSRF/ingress/ownership
or size reason. Larger/specially scoped records need an operator support process.

### Safe disable and identity erasure

The preflight shows Terminal/Paper/Live positions and pending orders and whether
automatic renewal is active. Confirmation rechecks actual state under the user
and account locks. Settle exposure and cancel automatic renewal before proceeding.
The disable action does not force financial exits or declare broker UNKNOWN work
settled.

Successful deactivation:

1. Marks the user inactive and ends browser sessions.
2. Stops eligible execution sessions through their refresh/control path.
3. Disables owned broker connections/sessions.
4. Cancels accepted compute/research work and refunds outstanding reservations once.
5. Retains saved data for a deliberate support reactivation decision.

Identity erasure additionally removes social/email/2FA identity, clears broker
secrets/tokens and avatar, makes strategies private, replaces sign-in names/email,
sets an unusable password and records `ErasureRequest`. It retains required
financial/execution records; this is not deletion of the entire User row.

### Optional-content retention task

`customer_support.retention` runs every five minutes, with a bounded batch of up
to 20 pending erasure requests. It locks user/request, skips an active user or a
started research run still awaiting completion, then:

- Deletes owned research conversations and their associated content.
- Clears optional journal title/notes/lessons/tags.
- Clears bodies/replies/contact content for eligible ordinary support tickets.
- Retains the specifically excluded historical Private, Custom, Grievance and
  Security request categories rather than silently claim their contents were erased.
- Marks that optional cleanup request completed.

Those exclusions and retained payment/execution facts must match the published
privacy statements. The task does not implement an arbitrary age-based purge of
every customer's support history, provider-side erasure or cleanup of all backups.
A stuck worker with no recorded completion can delay erasure and needs operator
inspection rather than repeatedly promising instant deletion.

## Content-free application error reports

`POST /api/v1/support/client-errors/` accepts exactly one `category` field:
`render_failure`, `app_failure` or `load_failure`. It logs the category and returns
received status. The endpoint has a dedicated 60/hour anonymous throttle.

No message text, stack trace, prompt, strategy, email, page content or arbitrary
payload is accepted. This is basic application-error categorization, not product
analytics, website-visitor tracking or automatic creation of a support ticket.

## API contracts

| Method/path | Purpose/authentication |
| --- | --- |
| `GET /api/v1/public/catalog/` | Public request options/status labels and operator contact metadata |
| `POST /api/v1/public/enquiries/` | Anonymous ticket creation with public-form verification |
| `GET/POST /api/v1/support/tickets/` | Owned paginated summaries / new owned request |
| `GET /api/v1/support/tickets/{uuid}/` | Owned original body and replies |
| `POST /api/v1/support/tickets/{uuid}/reply/` | Owned customer reply and awaiting-support state |
| `POST /api/v1/support/account/export/` | Authenticated bounded complete export |
| `POST /api/v1/support/client-errors/` | Fixed content-free categories |
| `GET /api/v1/users/account/preflight/` | Current shutdown prerequisites |
| `POST /api/v1/users/account/deactivate/`, `DELETE /api/v1/users/account/` | Safe disable/identity erasure |

Ticket lists use common `page`/`page_size` (10/25/50/100, default 25) and lightweight
summary serialization; detail prefetches the selected transcript. There is no
current support full-text search/status-filter API exposed by this customer list,
separate staff REST inbox, attachment upload or ordinary customer delete endpoint.

## Implementation ownership and extension

| Source | Responsibility |
| --- | --- |
| [catalog.py](../backend/customer_support/catalog.py) | Single request/status vocabulary and customer-selectable subset |
| [models.py](../backend/customer_support/models.py), [serializers.py](../backend/customer_support/serializers.py) | Ticket/reply/erasure records, lengths and safe projections |
| [views.py](../backend/customer_support/views.py) | Public enquiry, owned lists/create/reply and error-category endpoint |
| [integrations.py](../backend/customer_support/integrations.py) | Public Turnstile verification only |
| [services.py](../backend/customer_support/services.py) | Verified guest-record association and after-commit email scheduling |
| [tasks.py](../backend/customer_support/tasks.py) | SMTP task and bounded optional-content erasure |
| [admin.py](../backend/customer_support/admin.py) | Staff transcript/reply/status/assignee workflow |
| [privacy.py](../backend/users/privacy.py) | Export encoding, exposure checks and account shutdown |
| [SupportPage.jsx](../frontend/src/features/support/pages/SupportPage.jsx) | Customer list/detail/new request/reply/refresh |
| [EnquiryForm.jsx](../frontend/src/features/site/EnquiryForm.jsx) | Guest versus authenticated form routing |
| [account-tab.jsx](../frontend/src/features/settings/components/account-tab.jsx) | Export and preflight-confirmed account actions |

To add a category, define its label/backend validation, decide customer visibility,
operator routing and retention implications, then let shared metadata populate
both forms. Do not add an unrelated project/payment workflow merely by giving a
ticket another status. New side effects belong in validated owning services and
after-commit delivery, not serializer fields controlled by customers.

## Configuration and worked examples

Set operator identity/support hours and Django mail transport using environment
examples. Brevo SMTP defaults are host `smtp-relay.brevo.com`, port 587, STARTTLS;
provide actual credentials and verified sender. Run a worker consuming the default
queue plus Beat for retention. The support email task is not on `compute`.

Public forms also need the frontend site key, backend secret and allowed hostnames.
Do not start another inbound webhook service: none is used. Check real delivery
with a deliberate test message through your SMTP/provider setup.

### Guest becomes a customer

A guest sends a question using an email. It remains unowned. Creating an account
with the same unverified email does not expose it. After verification and successful
login/refresh, unowned matching records link to that account and appear in Support.

### Staff correction

An operator gives an incorrect instruction. Add a new staff reply explaining the
correction instead of editing the old message. Status becomes awaiting customer;
outbound email is queued. The database transcript remains useful even if SMTP
delivery is delayed.

### Export too large

A full account would encode to 12 MiB. The API rejects the export instead of
returning only its first 10 MiB or first 1,000 trades. The user asks Support for
a scoped record extract; an operator validates identity/scope separately.

## Troubleshooting and release checks

| Symptom | Inspect |
| --- | --- |
| Guest form rejected | Token, `enquiry` action, allowed hostname, secret/configuration, throttle and serializer lengths |
| Request saved but no email | Default worker, after-commit publication, SMTP sender/auth/network and task retries; saved ticket is authoritative |
| Guest ticket not in account | Verified same email, successful login/refresh and original ticket still unowned |
| Staff reply not visible immediately | Refresh selected detail; no independent realtime support socket is promised |
| Closed ticket reopens | Customer reply intentionally moves it to awaiting support |
| Duplicate email/message | Uncertain SMTP/network outcome and retry; inspect transcript before resubmitting |
| Erasure pending | Started research without completion, inactive-user precondition, task/Beat and retained-category policy |
| Export fails | Authentication/CSRF/ingress, two-per-day throttle, 10 MiB bound and actual structured error |

Release checks should cover guest/authenticated creation, verification failures,
foreign UUID ownership denial, named category labels, customer/staff replies,
status transitions, SMTP failure/retry without losing records, verified association,
complete/oversized export, exposure-blocked shutdown and retention exclusions.
Source/documentation checks do not prove production email delivery or erase
external provider/backups automatically.
