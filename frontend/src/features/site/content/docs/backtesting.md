---
title: Backtesting, Costs and Monte Carlo
description: Run a bounded test and inspect results with their assumptions.
order: 5
---
## Configure the test

- Choose your saved strategy, dates, initial capital, slippage and charge profile.
- Turn charges off only if that is an intentional comparison.
- Review the workload and credit estimate before confirming. Changed rules or dates need a fresh estimate.
- For separate signal and traded instruments, the workload includes both data sources. Rules can use the signal market; fills, quantities and P&L use the actual traded contract.

## Testing futures and options

- Choose exact contracts and configure Lots or valid whole-lot Units in Studio.
- Historical derivative terms must be recorded for the requested start date. Today's lot size is not assumed to apply to older contracts.
- An archived contract can be tested when its identity, sourced specifications and provider history are available. Ask the platform operator to resolve missing records.
- Ranges crossing specification changes must be split. Multi-session futures require reviewed daily settlement records. Expiry needs a qualified final cash-settlement record; a quote cannot replace missing settlement data.
- Futures and option-writing collateral are configured estimates, not broker/exchange portfolio-margin calculations.

## Understand credits

- One credit covers 100,000 instrument-candles, including indicator warmup history.
- A successful run uses the reviewed credit amount. A smaller observed dataset does not change that accepted price.
- Processing failures and cancellation restore the reservation. Completed runs keep their accepted charge.

## Read the result

- Inspect trades, costs, drawdown and instrument/date concentration.
- Market entries and exits use the traded quote available when the signal fires, with configured slippage and tick rounding. They do not wait for the next candle high, low or close. If an underlying supplies the signal, execution uses the selected contract's available price.
- This assumes zero execution latency within the candle simulation. Existing results keep their original execution assumptions until rerun.
- Empty totals are zero; undefined ratios are N/A.
- Read recorded entry diagnostics when no trades occurred. If diagnostics were not recorded, the result cannot establish the reason.
- Check coverage and warmup before drawing a conclusion. Any remaining position is closed at its last available completed candle close, with modeled slippage and charges, and marked END_OF_BACKTEST. This is a test-ending assumption, not a strategy exit signal.
- Charge settings are saved with the run. Editing a charge profile later does not change that run or a rerun's saved assumptions.

## Compare and investigate

- Attach completed tests to research within your current request allowance.
- Compare rules, dates, instruments, sizing, charges and slippage before comparing performance.
- Different assumptions can make a direct comparison misleading.

## Monte Carlo and simulation limits

- A bounded Monte Carlo experiment explores the selected recorded trade outcomes, up to 1,000 simulations per experiment.
- Cancel a pending or queued simulation from its history card to restore the reserved run allowance. Running simulations must finish.
- It does not create future market evidence or establish likely profitability.
- Candles do not reveal every price movement or queue position. Read the [simulation methodology](/methodology/) for fill assumptions and coverage limits.
