---
title: AI Research Assistant
description: Ask focused questions, inspect evidence and confirm strategy, watchlist or backtest actions.
order: 2
---

## What the assistant can help with

Ask about a concept, analyze supported stocks, compare a selected watchlist,
explain your strategy, turn your specified rules into a draft, or investigate
completed backtests and execution reports.

Direct stock calculations and screening currently use active supported NSE
stocks. An attached report may contain other instrument types; that does not
make option-chain research, unrestricted news/web search or every market a
direct analysis feature. The assistant does not execute broker trades or deploy
strategies on your behalf.

## Start a useful conversation

1. Open **AI Research Assistant → New chat**, or select an existing conversation.
2. Ask the question. General questions do not require a stock selection.
3. For market analysis, choose a relevant timeframe and attach only the context
   needed: stocks, a named Terminal watchlist, your strategy, completed backtests,
   a saved screening observation or an execution review.
4. Read the attachment chips before sending. Remove context you do not want used
   in the next question. For comparisons, select the actual completed tests.

All your named Terminal watchlists are separately selectable. Give them meaningful
names. Only eligible stocks enter direct stock analysis; indices or derivative
members do not become stock inputs simply because they share the list.

Examples of focused requests:

- “Compare the trend and volatility of these stocks on completed daily candles.”
- “Explain why this backtest lost money after charges; separate observations from hypotheses.”
- “Draft my rules: Close above EMA 20 and RSI 14 above 50, with the entry size and exits I specify.”

If a threshold, size or exit is missing, clarify it. A confident-looking answer
is not evidence that an unspecified trading decision was suitable.

## Read the answer and evidence

The explanation can contain citations, result cards, tables, charts, observation
times and limitations. Open **Evidence and calculations** to inspect the
calculation behind a claim and use table paging where available.

A current display quote and the most recent completed candle are different
observations. Compare their timestamps and timeframe. An older cited screen or
report retains its original observation; reopening it does not refresh the market.
Ask for a new analysis when you want a new observation.

AI can misread evidence or make unsupported claims. Check that the cited record
exists and supports the conclusion. Missing history is not proof of a match or
an opportunity. Questions and selected context may be sent to the configured AI
provider; do not include passwords, credentials, private keys or backup codes.

## Actions always need confirmation

| Proposal | What to review | What confirmation does |
| --- | --- | --- |
| Create a strategy draft | Name, instruments, conditions, size and schedule | Saves a draft for your review; does not deploy it |
| Add to a Terminal watchlist | Exact stocks and the named destination list | Adds the selected entries to your owned watchlist |
| Configure a backtest | Frozen rules, dates, capital, profile, slippage and workload | Starts the reviewed historical experiment subject to admission |

Open the action preview and confirm only the change you intend. A follow-up
question is not permission to create resources automatically. Each experiment
has its own confirmation and allowance check. Review the resulting strategy or
run after the action succeeds.

A proposal can be rejected even when the answer is readable—for example, when
its draft is invalid or its referenced data is unavailable. Correct that proposal
or clarify the request; the explanation is not authorization to bypass validation.

## Conversation context and recovery

Follow up in the same chat to refine a result. Previously accepted turns keep
their own context and evidence; changing attachments affects later questions.
Earlier answers do not become current market facts after a refresh.

Opening a chat shows its latest response. Scroll upward when reviewing earlier
turns. Reload/reconnection recovers saved progress; it does not intentionally
start the same research again. One active request is allowed per user, including
across chats. Use Cancel while it is active, then wait for its final status.

## Credits and waiting

The composer shows remaining period AI credits; completed replies show usage.
**1 credit = 1,000 reported AI tokens**, including the model calls needed for
that answer. For example, 22,500 reported tokens consume 22.500 credits.

- Charge occurs after a valid answer is successfully saved.
- Failed or cancelled requests do not charge customer credits.
- An accepted answer can finish after using the remaining balance. It records
  full usage and leaves zero spendable balance; new questions are then blocked.
- A renewed period starts fresh without carrying the previous overrun as debt.
- The answer belongs to the period in which its request was accepted, even if
  completion occurs after renewal.
- If a provider omits usage, accounting can be marked incomplete; a zero or
  partial reported amount is not a promise that the provider used no tokens.

Current plan amounts and request limits are in [Billing and Usage](/docs/billing/).
The separate [Market Screener](/docs/screener/) uses its own run allowance.

Research may wait behind other computation, then spend time on provider responses
and data tools. A progress connection is not a completed answer. If it fails,
read the message, check whether saved evidence is useful and retry deliberately.
Repeated identical prompts can create separate work once the earlier run ends.
