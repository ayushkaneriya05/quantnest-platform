---
title: Market Screener
description: Build technical filters for a selected stock list and inspect each match or exclusion.
order: 3
---

## Choose the universe

Open **Market Screener**. Select supported active NSE stocks manually, from one of
your named Terminal watchlists or from a saved strategy. Search the list by name
and check the selected stock count. Unsupported watchlist members are not
automatically analyzed as stocks.

The screener evaluates your selected universe, not every listing on an exchange.
Stay within the current request limit shown by the form and your plan.

## Build your own conditions

Choose a default timeframe, add conditions and set whether **AND** requires all
active conditions or **OR** permits any active condition. There are no preset
strategy cards to select; save your own screen for reuse.

For each comparison:

1. Choose the left price or indicator input.
2. Open its parameters and set period, source or output component where relevant.
3. Choose the comparison, including a crossover when that is your intention.
4. Choose the right input or a constant and configure its parameters.
5. Keep the default timeframe or set an offered override.
6. Disable or remove conditions you do not want evaluated.

The screener is a flat AND/OR condition tool. Studio's nested expressions,
capture/confirmation and position-state exits are different functionality; do
not assume every Studio construct is a screener input. Inputs come from the
supported [builder reference](/docs/reference/) with screening restrictions.

## Understand completed-candle results

Screening uses completed candles, not a constantly re-evaluating live-price feed.
Indicator warmup and historical coverage must be available. A crossover compares
the latest and previous known completed observations; a stock simply staying
above a boundary is not a new crossover.

Example: `Close > EMA(20)` AND `RSI(14) > 50` matches only when both completed
calculations are available and true on the chosen observation. It is a filter,
not an order instruction or a recommendation to buy.

## Run and inspect

Choose **Run screen with new observation**. A new execution uses the screen-run
allowance, separate from AI credits and saved-screen capacity. Follow its status
before starting another execution.

Read the matched and excluded counts, search/sort the table and inspect the
per-condition values and candle times. A missing input or insufficient history
is an exclusion, not a successful match or a confirmed bearish result.
Results and their rows are paged; the visible table page is not the entire scope.

## Save, reopen and ask AI

Name the screen and choose **Save named screen** to keep its configuration.
Saving configuration is different from running it and uses saved-screen capacity.
Reopening an earlier result retains its recorded time; it does not make its
prices current.

Select results and choose **Ask AI** to investigate the recorded observation.
That handoff supplies evidence to a conversation. AI research admission/credits
apply separately, and the assistant cannot turn a match into an unconfirmed
trade or deployment.

If a screen returns nothing, first inspect which inputs were false or unavailable,
the selected timeframe and the stock universe. Do not remove a meaningful filter
solely to force matches.
