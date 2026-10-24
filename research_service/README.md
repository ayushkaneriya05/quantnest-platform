# QuantNest AI research

The research assistant replaces the old AI Engine. Django owns users, jobs,
history, market-data loading, screening calculations, saved evidence and strategy
confirmed actions. This private FastAPI service calls Gemini and requests nine
allowlisted Django tools. It has no trading credentials, database connection,
order API or strategy activation API.

## Setup and startup

Follow the beginner [Development](../infra/development/SETUP.md),
[Public](../infra/public/SETUP.md) or [Private](../infra/private/SETUP.md) walkthrough.
[Gemini integration setup](../infra/shared/INTEGRATIONS.md#5-gemini-ai-research)
explains obtaining the provider key, selecting a supported model and verifying
the first response.

For Compose, use the selected mode's `research.env` for `GEMINI_API_KEY`,
`GEMINI_MODEL` and `RESEARCH_SERVICE_TOKEN`. Put the same service token in that
mode's `backend.env`. These files are separate from native `backend/.env` and
`research_service/.env`; do not merge the two deployment methods.

Development enables the `research` profile. Public/Private include it in their
normal full deployment. Docker installs the locked dependencies and supplies
internal service/tool URLs. The browser calls Django only; do not expose 8001.

Research and screening jobs run on the existing **compute** Celery queue.
Background and Beat services handle maintenance/expiry. There is no separate
research Celery queue or worker command to add. Screening does not require a
Gemini request; AI answers additionally need the internal FastAPI service.

If maintaining a native setup, configure the two internal URLs and matching
tokens explicitly and keep its processes separate from Compose. Use a model
supporting Interactions function calling and structured output; a configured
default name is not a guarantee of access for your Google project.

## Workflow

1. Open AI Research Assistant and ask a question. Starter cards fill the composer
   without sending. Stock attachments are optional for general explanations;
   named stocks use the existing instrument search, with explicit selection for
   ambiguous names. Attach a terminal watchlist, owned strategy, or owned
   completed backtests within the request allowance when useful.
2. Each conversation is a `ResearchSession`; each question is a `ResearchRun`.
   API admission freezes selected attachments, effective strategy snapshots and the
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
   failed calls; ten-minute deadline; 12 conditions/group; five charted stocks
   per chart tool with at most eight indicators. Public stock/attachment sizes
   come from catalog allowances; Private/Development have no plan ceilings.
   Symbol resolution may suggest a stock for a new request but cannot expand
   the current run's accepted universe.
- Default timeframe: daily. Intraday warmup is capped at 60,000 source minutes;
  daily/weekly history at 2,000 trading sessions. This permits daily EMA 50 warmup.
  Loaded frames, calculated indicators and identical artifacts are reused within
  a run. Charts are bounded to 120 bars and stay outside model tool responses.
- NSE stocks and one direct execution route per draft instrument in this version.
- Warmup comes from the shared execution compiler and `MarketSessionCalendar`.
  Data comes through `marketdata.candles.prepare_frames` and the common history
  path, including missing-candle provider backfill and coverage checks. Candle series are indexed by scheduled close,
  including holiday-aware weekly closes, so incomplete future bars are excluded.
- Returns/volatility in comparison tables use 20 completed bars. Volatility is
  the sample standard deviation of bar returns, not annualized volatility.
- Screening condition outcomes use `research.evaluation.evaluate_conditions`
  with the shared execution compiler/evaluator, including crossover semantics.
  Undefined ratios render as N/A; empty trade totals are zero.
- Backtest diagnostics describe the evaluation and admission outcomes recorded
  with that run. Older runs may not include the current diagnostic fields.
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
is part of the versioned migration history applied by the normal deploy flow.

## Verification

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
cd ../frontend
npx eslint src/features/research src/shared/services/researchApi.js
npm run build
```

Validate the research workflow against your configured deployment before release.
A real Gemini request requires your service token/API key and running services.
Logs record tool latency, provider token usage, failures and action outcomes;
they do not include credentials or request headers.

Provider documentation: [Interactions](https://ai.google.dev/gemini-api/docs/interactions-overview),
[function calling](https://ai.google.dev/gemini-api/docs/function-calling),
[structured output](https://ai.google.dev/gemini-api/docs/structured-output).
