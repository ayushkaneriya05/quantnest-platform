---
title: Journal and Performance Reports
description: Review recorded closes, add private lessons and distinguish realized results from current exposure.
order: 9
---

## Choose the source before reading a result

Open **Trade Journal** or **Performance Reports**. Select Terminal or Paper; Live
appears only on deployments where that execution scope is enabled. Customer
Live trading is not part of the current public offer.

Use dates and the offered instrument/account/review filters. A Terminal account
and a Paper session are separate records. Keep the selected source and charge
basis consistent when comparing reports.

## What counts as a recorded close

A closed-trade row represents recorded exited quantity. Manual Terminal reductions
and broker partial closes can produce separate rows rather than one combined
round trip. Open positions are not added to closed-trade win/loss totals.

Use shared page controls to move through the filtered records or enter a page
number. Searching and date changes apply to the full filtered set; summaries are
not limited to the currently visible page.

## Save your review

1. Choose **Review** on a recorded close.
2. Read instrument, source/account, side, quantity, entry/exit, costs and exit reason
   where recorded.
3. Describe the setup, what happened, any mistake tags and what you would change.
4. Add an execution rating if useful, then save.

The review does not edit prices, trades or P&L. Ratings are your own assessment,
not an objective strategy score. Notes stay private and are included in an AI
handoff only when you explicitly choose that option.

## Read Performance Reports

Realized summaries describe closes in the selected date period. Review P&L,
charges, win/loss counts and available day/instrument/strategy breakdowns. A
high win rate alone does not show average loss size or concentration risk.

| Value | Interpretation |
| --- | --- |
| Gross realized P&L | Price gain/loss before recorded fees |
| Charges | Costs actually recorded by that simulation/source |
| Net realized P&L | Gross result minus recorded charges |
| Unrealized P&L | Current marked value of remaining open exposure, before closing costs |
| Unpriced exposure | An open position without a usable mark; coverage is incomplete |

The report's current open valuation is separate from the selected historical
close-date window. It updates from prices across the full selected exposure,
including rows not visible on the current page. Those price changes do not
rewrite old realized results.

Historical equity ratios and account drawdown may be unavailable when the needed
equity series is not recorded. Missing metrics are not zero risk. For an enabled
real-broker source, absent integrated broker fees must not be read as zero actual
fees or a verified after-fee result.

## Ask AI about a selected result

Choose Ask AI from the supported review/report flow. Check the source, period,
account scope and whether private notes are included. Ask a specific question,
such as “Compare average winning and losing closes after the recorded charges.”

The assistant receives selected evidence, not unrestricted access to every record.
Missing evidence cannot prove why a trade happened. Opening an older report or
answer does not refresh its observation. See [AI Research](/docs/research/).

## Retain records you need

Removing a stopped Paper deployment deletes its execution history; it is not
archiving that history for later reports. Use [account export](/docs/controls/)
or retain needed records before removal. Archiving a strategy and removing a
deployment are different operations.
