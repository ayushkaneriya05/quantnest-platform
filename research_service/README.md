# QuantNest AI research

The research assistant replaces the old AI Engine. Django owns users, jobs,
history, market-data loading, screening calculations, saved evidence and strategy
confirmed actions. This private FastAPI service calls Gemini and requests nine
allowlisted Django tools. It has no trading credentials, database connection,
order API or strategy activation API.

## Start locally

From the repository root, install the backend and research dependencies:

```powershell
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.venv\Scripts\python.exe -m pip install -r research_service/requirements.txt
```

Set a random `RESEARCH_SERVICE_TOKEN` in `backend/.env` and put the same value in
`research_service/.env`. Also set `GEMINI_API_KEY` in the service environment.
Examples are in each directory's `.env.example`. The API key stays exclusively
in the FastAPI service. Use a Gemini model supporting Interactions function
calling and structured JSON output; `GEMINI_MODEL` is configurable.

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe -m celery -A backend worker -Q research --pool=solo -l info
```

Run Django's ASGI server and Redis using your existing setup. In another shell,
from the repository root:

```powershell
.venv\Scripts\python.exe -m uvicorn research_service.main:app --host 127.0.0.1 --port 8001 --env-file research_service/.env
```

Install `python-dotenv` when using Uvicorn's `--env-file` option (included in this
service's requirements). For separate containers, configure
`RESEARCH_SERVICE_URL` on Django and `RESEARCH_INTERNAL_API_URL` on FastAPI.
Keep FastAPI on a private interface/network; the browser calls Django only.
Disable response buffering on the internal streaming endpoint if proxied.

The dedicated Celery queue must have a worker. Screening also uses this queue
and works without FastAPI or Gemini. The existing Beat service expires abandoned
jobs. Restart Django/ASGI, Celery and Beat after changing registrations.

## Workflow

1. Open AI Research Assistant and ask a question. Starter cards fill the composer
   without sending. Stock attachments are optional for general explanations;
   named stocks use the existing instrument search, with explicit selection for
   ambiguous names. Attach a terminal watchlist, owned strategy, or up to three
   owned completed backtests when useful.
2. Each conversation is a `ResearchSession`; each question is a `ResearchRun`.
   The worker freezes resolved attachments, effective strategy snapshots and the
   observation cutoff. The pending reply displays actual research stages, then
   becomes a complete validated answer. Refresh/reconnect restores saved turns.
3. Inline citations open a details drawer with backend tables, condition outcomes,
   charts and readable rules. Numbers come from Django tools; Gemini writes the
   narrative. Missing data is an exclusion, never a failed trading condition.
4. Follow-up questions keep prior run/evidence references and the latest validated
   draft, even beyond the six recent answers sent to the provider. Earlier evidence
   is retrieved through a tool restricted to the current conversation. Its original
   run and observation time remain visible.
5. Review a proposed strategy draft, watchlist addition, or single backtest. Only
   explicit confirmation executes the action. Django validates permissions and
   settings, creates resources atomically, and records the outcome. Repeating the
   same confirmation returns the recorded result. Each new experiment requires
   its own preview and confirmation.
6. Backtest previews include the exact approved snapshot, dates, capital, slippage
   and charge profile. Execution uses shared backtest creation/start services and
   queues work after commit. Strategy changes after preview cannot change the
   approved experiment. Queue failures retain the created run for an explicit retry.
7. Completed backtests can be attached from their existing **Research review**
   action. Reviews and comparisons use actual trades, costs, configuration
   differences, monthly/instrument/exit breakdowns, and recorded diagnostics.
   Older runs without diagnostics state that entry-blocking causes were not recorded.

The standalone Market Screener uses backend presets, named saved screens, the
existing rule editor/evaluator, and the same evidence components. Results can be
searched, sorted and selected for AI research with their exact saved observation.
Saving a screen reuses `ResearchSession`, without another history model. The unused
Alternative Data placeholder is removed from navigation until it has a data source.

## Contracts and limits

- REST: `/api/v1/research/sessions/`, `/runs/`, `/schema/`; user-scoped, paginated
  conversations and turns. Detail endpoints have no recent-history restriction.
- Actions: `/runs/{id}/cancel/`, `/runs/{id}/propose-action/`,
  `/actions/{id}/confirm/`; evidence: `/runs/{id}/evidence/{E1}/`.
- WebSocket: `/ws/research/`, using the existing authenticated cookies. Compact
  `{type: "research.update", run: {id, session, revision, status, progress_message,
  error_message}}` events omit artifacts. Clients reject older revisions and load
  completed replies through REST.
- Private tool gateway: `/api/v1/research/tools/`. Requires the service token and
  a signed, expiring token binding one active run to its user. IDs come from that
  run's frozen context; the model cannot choose another user or arbitrary routes.
- Tools: `screen_instruments`, `compare_instruments`, `analyze_stock`,
  `resolve_instruments`, `get_strategy_snapshot`, `get_backtest_report`,
  `compare_backtests`, `get_conversation_evidence`, `validate_strategy_draft`.
- One active run per user; eight tool attempts reserved before work, including
  failed calls; ten-minute deadline; 50 active NSE stocks; 12 conditions/group;
  three completed backtests; five charted stocks with at most eight indicators.
- Default timeframe: daily. Intraday warmup is capped at 60,000 source minutes;
  daily/weekly history at 2,000 trading sessions. This permits daily EMA 50 warmup.
  Loaded frames, calculated indicators and identical artifacts are reused within
  a run. Charts are bounded to 120 bars and stay outside model tool responses.
- NSE stocks and one direct execution route per draft instrument in this version.
- Warmup comes from `IndicatorRequirementAnalyzer` and `MarketSessionCalendar`.
  Data comes from `StrategyMarketDataService`, including missing-candle broker
  backfill and coverage rechecks. Candle series are indexed by scheduled close,
  including holiday-aware weekly closes, so incomplete future bars are excluded.
- Returns/volatility in comparison tables use 20 completed bars. Volatility is
  the sample standard deviation of bar returns, not annualized volatility.
- Screening condition outcomes use `RuleEvaluator.evaluate_rule`, including
  crossover semantics. Undefined ratios render as N/A; empty trade totals are zero.
- Backtest diagnostics count actual entry signals, time/event restrictions,
  cooldown, existing positions, sizing/capital/route rejection, queued entries and
  fills. They add counters at existing decision points without new tick-path queries.
- Reloading saved results keeps original dates. Refresh analysis creates a new
  observation. Closed candles and separately timestamped quotes remain distinct.
- Gemini requests use `store=False`; complete interaction steps are preserved
  locally for tool results. Django stores the application conversation/evidence.
  Prompt contents and selected data still go to the configured Gemini API.
- REST polling recovers missed socket events. Cancellation prevents subsequent
  tool publication and prevents an in-flight job from overwriting cancelled state.
  Provider work already submitted may still consume tokens after cancellation.

## Migrations and removal

`research.0001_initial` adds the two research models.
`research.0003` adds session context, revisions, attempt counters and `ResearchAction`.
`research.0004` converts saved attachments and provenance once, retaining research
history and already-created drafts. `backtesting.0018` adds aggregate diagnostics.
`research.0002_remove_old_ai_engine` irreversibly drops only the four removed AI
Engine tables and deletes its obsolete content types. This removes the unused
AI recommendations, regime, health and overfit history as approved. The migration
has not been run against your trading database by this implementation.

## Verification

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py test research backtesting --settings=research.test_settings
..\.venv\Scripts\python.exe manage.py check --settings=research.test_settings
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=research.test_settings
cd ..
.venv\Scripts\python.exe -m unittest research_service.tests -v
cd frontend
npx eslint src/features/research src/shared/services/researchApi.js
npm run build
node --test --test-concurrency=1 tests/research-workspace.test.mjs tests/auth-session.test.mjs tests/ui-regressions.test.mjs
```

Tests use an isolated SQLite database and mocked Gemini/broker responses. A real
Gemini request requires your service token/API key and running services.
Browser tests use headless Chrome/Chromium and compiled CSS from the production
build. Logs record tool latency, provider token usage, failures and action outcomes;
they do not include credentials or request headers.

Provider documentation: [Interactions](https://ai.google.dev/gemini-api/docs/interactions-overview),
[function calling](https://ai.google.dev/gemini-api/docs/function-calling),
[structured output](https://ai.google.dev/gemini-api/docs/structured-output).
