---
title: Backtesting, Costs and Monte Carlo
description: Run a bounded test and inspect results with their assumptions.
order: 5
---
## Configure the test

- Choose your saved strategy, dates, initial capital, slippage and charge profile.
- Turn charges off only if that is an intentional comparison.
- Review the workload and credit estimate before confirming. Changed rules or dates need a fresh estimate.

## Understand credits

- One credit covers 100,000 instrument-candles, including indicator warmup history.
- The estimate limits the approved workload; lower completed work releases unused reserved credits.
- Processing failures restore the allowance. Cancellation before work starts releases the reservation; completed work follows the disclosed usage policy.

## Read the result

- Inspect trades, costs, drawdown and instrument/date concentration.
- Empty totals are zero; undefined ratios are N/A.
- Read recorded entry diagnostics when no trades occurred. If diagnostics were not recorded, the result cannot establish the reason.
- Check coverage, warmup and remaining exposure before drawing a conclusion.

## Compare and investigate

- Attach completed tests to research within your current request allowance.
- Compare rules, dates, instruments, sizing, charges and slippage before comparing performance.
- Different assumptions can make a direct comparison misleading.

## Monte Carlo and simulation limits

- A bounded Monte Carlo experiment explores the selected recorded trade outcomes, up to 1,000 simulations per experiment.
- It does not create future market evidence or establish likely profitability.
- Candles do not reveal every price movement or queue position. Read the [simulation methodology](/methodology/) for fill assumptions and coverage limits.
