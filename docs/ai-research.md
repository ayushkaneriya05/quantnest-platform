# AI Research: application flow, providers and period credits

AI Research keeps conversations, calculations and confirmations in Django. A
separate internal service conducts the model conversation. The service has no
database credentials or order-placement API. The browser communicates with
Django, never with the provider or the internal AI service.

## Request to saved answer

1. `AIResearchAssistant.jsx` selects optional stocks, a named Terminal watchlist, a strategy, completed
   backtests or execution evidence. Shared searchable selectors load choices on
   demand. The existing enum context supplies builder labels and parameters.
2. `ResearchRunViewSet.create` validates the transport payload and calls
   `research.services.accept_run`. The service locks the user, checks request-ID
   reuse and the one-active-run constraint, and freezes owned context through
   `context.resolve_context`. Public instrument/attachment limits are checked here.
3. Admission creates a `ResearchRun` and a zero-amount `UsageReservation` for
   `research_tokens`. Its `UsageBucket` identifies the accepted allowance period.
   Public admission requires at least one token of remaining allowance. No token
   estimate or charge is made at this stage. Creation and admission are atomic.
4. `queue_compute_work` dispatches `research.start_research` after the transaction
   commits. Research shares the **compute** queue with backtesting; waiting in
   that queue does not consume the execution deadline or customer credits.
5. The task claims PENDING → RUNNING once. Duplicate delivery cannot make another
   paid provider request. It can reuse previously selected screening evidence,
   preserving its original observation date, or prepare an attached execution
   review. It builds `service_payload` and streams an authenticated HTTP request.
6. `research_service.main` checks the internal service token. `workflow.py` runs
   the provider-independent loop. `providers.py` handles the provider SDK,
   messages, continuation state, normalized usage and bounded retries.
7. Tools return calculated evidence, not persistent actions. Django validates
   each tool against the accepted user/context and returns a compact result.
   Charts and full evidence remain in Django for the user's evidence drawer.
8. A valid structured answer ends the loop immediately. There is no unconditional
   second writing request. At the tool limit, the next model call has no tools
   and must finish from collected evidence. A malformed answer permits one
   bounded format-repair call.
9. `services.complete_run` locks the user and run, verifies citations and drafts,
   independently validates optional action proposals, saves the answer/actions,
   and settles actual reported tokens **in one database transaction**. A database
   error rolls back both the answer and its charge. Invalid optional actions are
   omitted; a fabricated evidence reference still rejects the answer.
10. Compact WebSocket revisions announce progress/completion. `useResearchData`
    loads the saved answer, refreshes the credit balance, and ignores older
    revisions. During an active run, fallback polling fetches only that run.
    Initial loading and reconnect restore persisted conversation snapshots.

## Named watchlists and custom screens

AI context, Market Screener and watchlist-addition previews use the shared
`terminal-watchlists` choice resource. It searches and paginates all watchlists
owned by the current user, displaying their names. A `watchlist_id` identifies
the selection; the backend checks ownership and records `watchlist_name` for
display. Research freezes the supported instruments at admission, so later
watchlist edits do not change completed evidence. New requests read the current
contents of that selected watchlist.

Migration `research.0005` replaces the retired `use_watchlist` flag in saved
contexts with the first owned watchlist, matching the old behaviour. Recorded
instrument snapshots and results remain intact. A deleted watchlist must be
reselected; the backend never silently switches to another one.

New screens start without conditions. Users add conditions with the shared rule
editor or reopen their saved screen. There are no built-in screener presets.
Watchlist additions require a selected destination before confirmation, and
ownership is checked again when the confirmed action executes.

## Credits and allowance periods

| Rule | Behaviour |
|---|---|
| Unit | 1 credit = 1,000 reported AI tokens |
| Explore / Build / Pro | 150 / 500 / 1,500 credits per period |
| Stored amounts | Exact integer token counts; no floating-point ledger math |
| Display | Credits to three decimal places in Research; up to three in Pricing/Billing |
| Success | Settle reported usage only after a validated answer is saved |
| Failure / cancellation | No customer credit charge; provider-side costs may still exist |
| Accepted request exceeds balance | Finish it and record full usage; remaining display is zero |
| Next request | Public rejects admission until a positive balance is available |
| Renewal | New bucket and fresh allowance; no debt carried forward |
| Completion after renewal | Charge the reservation's original period |
| Development | Record actual usage without enforcing the allowance |
| Private | No commercial reservation or allowance enforcement; per-run provider usage is retained |

An 88,654-token answer uses **88.654 credits**. If 10 credits remain and an
accepted answer uses 20, save it and record all 20. This is not a paid overage.
The next request is blocked; the next period starts with its full allowance.

The internal allowance key is `research_tokens`. `TOKENS_PER_CREDIT` and catalog
display divisors keep the API, Billing, Pricing and Operations Admin consistent.
The Admin form accepts credits and converts them to integer tokens on save.
The standalone screener still uses `screens` (one successful run), not AI credits.

`settle_usage` locks and settles only RESERVED rows. Completion callbacks and
duplicate task delivery cannot charge a settled reservation again. Normal
backtest/screener/Monte Carlo reservations keep their existing fixed/workload
pricing; postpaid AI pricing is selected by the allowance definition.

## Provider usage and missing accounting

The adapter sums each model call's **reported total**. Gemini's `total_tokens`
already incorporates provider-defined input, output and reasoning accounting.
Cached and thought counts are descriptive fields, never extra additions to that
total. See [Gemini's reported usage fields](https://ai.google.dev/gemini-api/docs/tokens).
Format-repair calls and successful tool-loop calls belong to the same
successful request's usage.

Missing totals are not estimated. `usage.complete` becomes false; known totals
are retained and settled, the valid answer is delivered, and Django logs an
accounting issue. A retried transport failure can have unknown provider cost;
it also marks accounting incomplete. Customer failures/cancellations remain
uncharged regardless of any observed provider cost.

No input/output customer token budgets or `count_tokens` RPCs remain. Model
context limits, a technical 16,384-token output bound per Gemini call, three
attempts for transient provider errors, normal API throttling, eight tool
executions and a ten-minute deadline bound resource use. The deadline starts
when the compute worker claims the job, not when it enters the queue. Django
supplies the absolute deadline and remaining tool count to the service.

## One tool registry

`backend/research/tool_registry.py` registers each tool's name, description,
argument schema, callable and required context together. It owns the common
execution path: availability, cached evidence, the execution counter, provenance,
and compact results. The provider service does not duplicate tool definitions.

The backend uses these responsibility boundaries:

| Module | Responsibility | Change here when... |
|---|---|---|
| `views.py`, `serializers.py` | HTTP, ownership-scoped resources and typed request fields | Adding an API input or endpoint |
| `context.py` | Resolve owned attachments, freeze the admitted universe and build the model request | Adding a context source |
| `services.py` | Admit, transition and complete runs; publish revisions; settle credits | Changing run lifecycle or admission |
| `tasks.py` | Claim queued work and stream the separate AI service | Changing transport or scheduling |
| `tool_registry.py` | Register and dispatch read-only tools; record/reuse evidence | Exposing a new AI responsibility |
| `tools.py` | Discovery, metadata, market analysis, saved reviews and draft-validation handlers | Changing a calculation/report presented to AI |
| `evaluation.py` | Shared historical data loading, frame/evaluation caches and completed-candle evaluation | Changing market-data calculations |
| `validation.py` | Builder validation, customer-defined rules and answer/citation validation | Changing accepted research inputs/results |
| `actions.py` | Preview and execute confirmed strategy, watchlist and backtest changes | Adding a persistent action |
| `models.py`, `admin.py` | Stored conversations, runs and action records | Changing persistence or admin access |
| `consumers.py`, `routing.py` | Authenticated progress transport | Changing WebSocket delivery |

General educational questions need no data tool. Tools return evidence only.
Persistent changes require a separately confirmed action, even when suggested by AI.

| Tool | Purpose |
|---|---|
| `get_rule_schema` | Fetch builder choices/defaults and requested operand parameters only when needed |
| `resolve_instruments` | Resolve an NSE stock name; selection for a new request remains explicit |
| `screen_instruments` | Evaluate customer conditions on completed candles |
| `compare_instruments` | Compare admitted stocks and condition values |
| `analyze_stock` | Bounded charts, observations and configured indicators |
| `get_strategy_snapshot` | Read the attached frozen strategy |
| `get_execution_review` | Read the attached, owned Terminal/Paper/Live report |
| `get_backtest_report` | Read actual results, costs, diagnostics and saved configuration |
| `compare_backtests` | Compare attached experiments and their configuration differences |
| `get_conversation_evidence` | Retrieve an earlier artifact in the same user's conversation |
| `validate_strategy_draft` | Validate customer-defined rules with the existing builder serializers |

Only context-appropriate tools are supplied. General questions do not carry
full enum metadata, strategy snapshots or reports. The six most recent turns
carry text and evidence references; older evidence is retrieved on demand.

An identical successful tool result is reused before incrementing the tool
counter. The AI service also caches identical calls within its conversation.
Calculation/frame caching is retained. A bounded number of model rounds prevents
repeated cached calls from extending the loop indefinitely.

Adding a read-only capability means adding a deterministic handler to the relevant
section of `tools.py`, then an `add(...)` entry in `tool_registry.registry`. Return
`{"data": ...}`; the dispatcher supplies the tool name, evidence ID and provenance.
Specify `context_field` when it requires an admitted attachment and `minimum=2`
for comparisons needing two records. Retain ownership checks inside the handler
when reading records. No provider change is required. Add an evidence renderer
in `ResearchEvidence.jsx` when it needs a new card.

For a persistent capability, add its `ResearchAction.Type`, a `preview_*` function
and an `execute_*` function to `actions.py`, then register the pair in
`ACTION_HANDLERS`. Previews validate and freeze settings without creating resources.
The shared confirmation path locks user, run and action in that order, checks for
duplicate confirmation, executes inside a transaction and publishes the result.
The executor receives `(run, payload)` and returns the created resource IDs.
Add its user-facing preview/confirmation controls alongside the existing actions.

## Provider interface and HTTP contract

`research_service/schemas.py` is the service's Pydantic HTTP contract. Django's
`context.service_payload` creates that request; FastAPI validates it on arrival.
It is not a separately packaged library and the backend image does not need the
provider SDK or Pydantic at runtime.

Request fields: `prompt`, signed `run_token`, `as_of`, accepted `context`,
recent `history`, selected `tools`, absolute Unix `deadline`, and
`max_tool_calls` remaining. Unknown request fields are rejected.

NDJSON events:

```json
{"type":"progress","message":"Reviewing your question and evidence"}
{"type":"usage","usage":{"provider":"gemini","model":"configured-model","requests":1,"total_tokens":1234,"complete":true,"tool_calls":0}}
{"type":"result","result":{"answer":"A verified explanation","evidence_ids":[],"proposed_actions":[]},"usage":{"provider":"gemini","model":"configured-model","requests":1,"total_tokens":1234,"complete":true,"tool_calls":0}}
```

`heartbeat` keeps idle streams alive. `error` contains a safe message and no
credentials. Usage events are cumulative snapshots, not deltas: the Django task
replaces the recorded snapshot rather than summing events. The final result
supports citations, clarification questions, limitations, artifact references,
validated draft references and optional action proposals.

An adapter implements `Provider.conversation(request, instruction)` and returns
a conversation implementing `step(results, *, final_only, feedback="")`. Its `ProviderStep`
contains plain text, normalized `ToolCall` objects and normalized usage.
SDK objects and thought signatures remain inside the adapter; they are never
stored as application conversation history. `close()` releases SDK clients.

`feedback` contains application schema-validation errors only when a final answer
needs its single permitted format repair. The adapter passes that feedback to the
model while preserving the existing conversation. Rejected tool arguments return
an explicit error object, so they cannot be mistaken for successful evidence.
Blank answers and oversized follow-up text are rejected before Django settlement;
invalid optional action entries are omitted independently of valid proposals.

To add another provider: implement that interface, register its factory in
`PROVIDERS`, add its SDK/key configuration, verify its usage/continuation format, and set
`RESEARCH_PROVIDER`/`RESEARCH_MODEL`. The orchestration, tools, quotas, application
conversations and frontend remain unchanged.

## Actions and data correctness

The AI service cannot create a strategy, place an order or start a backtest.
`ResearchAction` persists a reviewed preview. The user must call confirmation;
`actions.confirm_action` applies it atomically and idempotently.

The UI keeps the three action paths explicit:

- A validated draft opens a rules/settings preview before creating its DRAFT
  strategy, direct instrument routes and initial saved version.
- Watchlist additions require a named destination. The completed action links
  to `/terminal?watchlist=<id>` so the same destination opens in the terminal.
- Backtest configuration prefers the strategy draft created by that reply, then
  its attached strategy. An attached backtest can be selected to rerun its saved
  configuration. Dates, capital, slippage and charges remain visible before
  preview and confirmation; a preview never queues work.

Opening or switching a conversation displays its latest reply. Updates continue
to follow the bottom while the user stays there; reading older turns stops that
automatic scrolling. A new chat fetches active-work status without downloading
unrelated conversation history. Selecting several resolved stocks retains the
earlier selections within the request allowance.

Instrument analysis uses `marketdata.candles.prepare_frames` and the shared
execution compiler/evaluator. Candle completion time, warmup, missing-history
backfill and crossover semantics are unchanged. LTP remains unsupported for
historical screens; it is supported in live strategy drafts. Backtest reports
describe the saved execution configuration, not a universal next-open fill rule.

The internal tool endpoint requires both the service secret and a signed token
binding one running request to its user and deadline. The model cannot enlarge
the admitted universe or retrieve another user's attachments. Saved evidence
retains provenance and original dates. Account/private journal context is sent
to the provider only through explicitly accepted attachments.

## Deployment and verification

Configure the service with `RESEARCH_PROVIDER=gemini`, `RESEARCH_MODEL` and
`GEMINI_API_KEY`. Keep `RESEARCH_SERVICE_TOKEN` identical in Django and the
research service. Compose supplies `RESEARCH_INTERNAL_API_URL`; native setups
must point it to Django's internal `/api/v1/research/tools/` endpoint.

The default model is `gemini-3.5-flash` with `GEMINI_THINKING_LEVEL=low`.
Choose another supported model or increase thinking effort through configuration.
`RESEARCH_PROVIDER_TIMEOUT_SECONDS=60` bounds each model round, including
connection, generation and the single permitted transient-error retry. SDK
retries are disabled. The overall ten-minute deadline still permits multiple
model/tool rounds. Timeouts report provider delay instead of suggesting bad
credentials. Service logs distinguish slot wait, model time, tool time and usage;
the HTTP `200` opens the event stream, whose final result/error determines success.

The Gemini adapter removes size/range bounds and display-only metadata from
provider schemas, retaining their types, field names, required fields and enums.
Strict limits remain in application validation. This prevents nested screen/tool
schemas from exceeding the provider decoder's state limit. Only the adapter
contains this provider-specific schema conversion and the SDK retry workaround.

The `commercial.0016_research_token_credits` migration publishes a new catalog
revision, retaining old published catalogs, conversations and old message
buckets. New token accounting starts empty. It refuses active research or
existing subscriptions requiring a reviewed terms transition. The current
cutover is for a database with no subscriptions/payments.

1. Finish/cancel research and wait for in-flight provider work to stop. Drain
   compute work; do not interrupt a backtest just to update research.
2. Stop the API, compute worker, research service and background/Beat processes
   that use the old research code. Back up the database using your deployment
   instructions. Keep public traffic offline during the catalog/code cutover.
3. Replace both backend and research images from the same revision. Rename
   `GEMINI_MODEL` to `RESEARCH_MODEL` and set `RESEARCH_PROVIDER=gemini`. Delete
   `RESEARCH_INPUT_TOKEN_BUDGET` and `RESEARCH_OUTPUT_TOKEN_BUDGET` if present.
4. Run `python manage.py migrate` and `python manage.py check` in the new backend.
5. Deploy the rebuilt frontend, then restart API, research, compute and the
   usual background/Beat services. No extra queue or worker is needed.
6. Run one general educational question. Verify the saved total tokens, credit
   display (`total / 1000`) and Billing balance. Confirm earlier conversations
   still open. Provider availability and account access must be tested with
   real credentials; mocks cannot establish that.

Automated checks from the repository root (with dependencies installed):

```text
python -m compileall -q backend research_service
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
npm run lint --prefix frontend
npm run build --prefix frontend
```

Repository test suites have been removed. CI runs Django configuration/migration
checks, Python compilation, frontend lint/build, image builds and all three Compose
configuration checks. These checks do not verify runtime behaviour. Before rollout,
manually confirm a general answer, a selected-stock screen, an attached report,
a draft preview/confirmation, cancellation and the saved token/Billing totals.
