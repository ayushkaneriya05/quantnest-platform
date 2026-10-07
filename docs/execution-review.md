# Execution journal, reports, and activity

## Separate execution sources

| Source | Authoritative completed records | P&L basis |
| --- | --- | --- |
| Terminal | `trading.ClosedPositionLog` | Manual simulation, before fees |
| Paper | `paper_trading.PaperTrade` | Net of recorded simulated brokerage and taxes |
| Live | `live_trading.LiveTrade` | Recorded realized P&L, before fees |

Reports never combine these ledgers or include backtests. Each stored close counts once, including partial exits. Win rate is winning closes divided by all closes; profit factor is positive P&L divided by absolute negative P&L. Undefined ratios display as N/A. Cash transfers are excluded.

Current unrealized P&L is a separate mark over current positions using cached quotes no more than 60 seconds old. A total is unavailable if any position lacks a fresh quote. Historical date and review-status filters apply to closes, not these current marks. No broker request or position write happens while generating a report.

Historical equity returns, Sharpe, and equity drawdown remain unavailable without a verified historical equity series. Closed P&L is not labelled equity.

## Private reviews

Opening the journal reads source records; saving creates one owned review for a completed close. Financial fields are read-only. Reviews contain notes, lessons, optional execution ratings, and mistake tags. Ratings and tags are user assessments. Tag groups overlap when one close has several tags; their P&L must not be added together.

Every review must link to exactly one completed close from its selected source. Deleting that source record deletes its review. Unlinked development notes are removed by migration; the journal has no separate archive or legacy-note flow.

The journal contains the paginated closes and review editor. Reports contain calculated summaries, daily P&L and instrument/strategy breakdowns, with links to the filtered journal. Source selection sits in the desktop header and in a compact control on smaller screens. The review editor scrolls its body while keeping its footer visible.

## AI research

Ask AI creates a conversation with a frozen, dated execution evidence snapshot. The question is prefilled for review; research starts only when the user sends it. Notes are excluded unless the user selects Include saved journal notes. Only saved excerpts are attached, so unsaved edits must first be saved.

Reports expose Ask AI in the header. Its preview shows the source, period and totals, with optional consent to attach saved notes. Written references are validated against the run's recorded backend evidence. Valid grouped citations are normalized into individually clickable citations; omitted ID declarations are resolved from the validated text. Unknown citations are rejected in the answer, limitations, next steps and clarifying questions.

Evidence includes full period totals, bounded daily/group breakdowns, and selected or strongest/weakest closes. The assistant must distinguish observations, hypotheses, and self-reported assessments. Refresh analysis creates a new snapshot; reloading a saved turn retains its original evidence and date. Removing the execution-context chip clears the attachment for subsequent turns.

## Activity history

Private, read-only events cover strategy configuration versions, lifecycle transitions, broker configuration, capital allocations, paper account resets, successful sign-ins, and explicit sign-outs. The runtime signals inspect configuration fields only. Orders, positions, balances updated during fills, and quote ticks are not audited here.

Values use explicit allowlists. Credential changes record field names without values. Supported resources are strategies, broker accounts, paper accounts, paper/live allocations, paper/live sessions and authentication. Resource choices and labels come from the backend catalog, regardless of whether events already exist. Retired resource events are removed by migration and the database rejects unsupported resource types.

## API entrypoints

- `/api/v1/analytics/reports/`: filtered report.
- `/api/v1/analytics/reports/trades/`: paginated closes and saved reviews.
- `/api/v1/analytics/reports/export/`: filtered CSV (maximum 50,000 closes).
- `/api/v1/analytics/reports/research-context/`: create an owned conversation from calculated evidence.
- `/api/v1/journal/entries/`: private review create, retrieve, edit, and delete.
- `/api/v1/journal/entries/summary/`: review coverage and user assessments.
- `/api/v1/audit/logs/`: private activity history.

Closed-record filters are source, dates, account, strategy, instrument, symbol/name search, and review status. Terminal records have no strategy. Lists use 25 records per page; detail access is always scoped to the user and does not inherit list filters.

## Retired features and migration

Marketplace, community, learning, gamification, reputation/proofs/replays, and platform events have been removed from runtime apps, APIs, dashboard routes, and navigation. Strategy approvals, compliance checks, persisted derived reports, and generated journal insight stores are also removed. Marketplace visibility becomes PRIVATE; core strategy permissions remain.

Apply the prepared migrations with `python manage.py migrate` from `backend` using the project environment. They remove unlinked development notes and retired resource activity, enforce supported records, add report indexes, and delete the retired feature tables and content types. Cleanup migrations are irreversible. Existing applied migrations remain schema history; runtime code has no compatibility flow for the removed features. Restart Django, Celery and the research service after applying changes; the removed analytics schedule no longer runs.
