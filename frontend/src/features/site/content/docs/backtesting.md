---
title: Backtesting, Costs and Monte Carlo
description: Preview workload, run historical tests and understand prices, timestamps and results.
order: 5
---

## Prepare the strategy

Save and validate your Studio changes first. A normal new backtest captures the
strategy's current saved configuration; it does not use unsaved editor changes
or change the version already running in Paper. Existing results retain their
original rules, dates and cost assumptions after later edits.

Public availability follows the published NSE-stock workflow. Derivative sections
below apply only where that functionality is enabled, not to a new public offer.

## Configure and start

1. Open **Backtesting Lab → New Backtest** and choose your strategy.
2. Enter a meaningful name and inclusive start/end dates. Do not select future dates.
3. Enter initial virtual capital and a deliberate slippage assumption.
4. Choose an owned Charge Profile, or intentionally turn charges off for comparison.
5. Choose **Preview workload and credits**. Review the required history, assumptions
   and credit amount. Changing rules or dates requires a fresh preview.
6. Confirm the test and follow its status and progress message.

Your own browser or Terminal does not need to remain open for accepted work to
run. Refreshing the results page reloads its saved state; submitting another run
creates separate work and may reserve another allowance.

## Status and progress

| Status | Meaning and action |
| --- | --- |
| Pending | Saved but not yet queued |
| Queued | Waiting for a processing slot; other backtests or research may be ahead |
| Running | Preparing history, evaluating rules or saving results; read the stage message |
| Completed | Final results were saved |
| Failed | Read the recorded error before retrying |
| Cancelled | Cancellation was accepted; an active worker still needs to stop and finish cleanup |

Preparing history may stay near the beginning of progress while missing ranges
download. That percentage alone does not measure rule-evaluation speed. Do not
keep launching duplicates while the current run is preparing data.

## History, warmup and timeframes

The test fetches missing required history and prepares enough earlier bars for
indicators and rolling windows. Warmup prepares values; it does not trade before
your requested interval. Separate signal and traded instruments both need the
history their rules and execution require.

Candles follow exchange/segment sessions and holidays. Higher-timeframe inputs
become available only when their bars complete. Missing data is not filled with
invented trades, and a quiet instrument need not have a trade every minute.
Read coverage warnings before interpreting a result as evidence about your rules.

## Credits and cancellation

The preview uses the current plan's credit conversion and includes source history
needed for warmup. Admission reserves the reviewed amount. Successful completion
uses that accepted amount; a smaller observed dataset does not reduce it later.
Failed or cancelled processing releases the reservation. An already completed
run does not become free because you delete it.

Use Cancel for eligible pending, queued or running work and wait for its final
state. A rerun uses the saved run configuration and cost assumptions and requires
new admission. To test revised Studio rules or new rates, configure a new run.
See [Billing and Usage](/docs/billing/).

## Entry and exit prices

Backtesting generates observations from candle OHLC data; it is not historical
exchange-tick replay. Current market entries/exits use the **traded instrument's
available quote at signal time**, then apply configured slippage and tick rounding.
They do not deliberately wait for a later high, low, close or next candle open.

If an index provides the signal for an option, the option's own price supplies
the fill and P&L. The index's signal level is not the option execution price.
Missing required traded pricing cannot be replaced by the underlying price.

For example, an exit signalled at 196.22 executes from 196.22 with zero slippage
and a valid tick size; a later high of 196.38 does not replace it. This is a
zero-latency simulation assumption, not a guarantee of an achievable live price.

### Why a one-minute test can show seconds

The candle model orders simulated observations Open → Low → High → Close for Buy
direction, and Open → High → Low → Close for Sell direction. Interior observations
can appear around 20 and 40 seconds into a one-minute interval. Those seconds
are synthetic times used by the model, not recovered exchange fill timestamps.
It does not interpolate every price between the four observations.

Stop loss takes precedence over Target and Exit when their conditions match at
the same evaluation. The candle's assumed observation order can affect which
condition is encountered first. A candle alone cannot prove the true intrabar path.
Older saved runs keep their own recorded model until rerun.

## Read the results

- Inspect equity, drawdown and trade counts as well as net profit.
- In Trades, compare instrument, side, size, entry/exit, duration, gross P&L,
  charges and the recorded exit reason where shown.
- Check capital use, slippage, costs, date range and concentration in a few
  instruments or days before comparing two runs.
- Use available entry diagnostics for no-trade runs. Missing diagnostics cannot
  establish why a condition failed.
- Undefined ratios are N/A; an empty total is zero. Neither implies a good strategy.
- A remaining position is closed at its last available completed close with
  modeled costs/slippage and an end-of-backtest reason. This is a test-ending
  assumption, not a strategy exit signal.

Costs are frozen with the run. Same-day versus across-date equity treatment uses
the relevant holding dates, rather than assuming a CNC product always means
delivery charges. See [charge profiles](/docs/charges/).

## Futures/options history, where enabled

Fixed contracts keep their exact identity. Automatic expiry and ATM/ITM/OTM
policies use historical underlying observations to select a contract, then use
that expired contract's own prices. An open position pins its selected contract.
There is no automatic rollover or coordinated multi-leg execution.

Actual expired pricing, strike and expiry are separate from lot/tick/multiplier
terms. Dated sourced terms are preferred. When unavailable or changing, the
accepted plan can record a current-template assumption. Inspect that assumption:
today's lot size is not proof of the historically tradable lot size. Reconstructed
strike grids are also not a complete record of historical listing times.

Reviewed daily futures MTM and qualified final cash-settlement records are used
where available. Missing official settlement is not invented from a chart close;
read the reported coverage/assumptions and contact Support for missing required
records. Physical delivery and general rollover are not simulated. Collateral
estimates do not reproduce broker portfolio margin.

## Monte Carlo

From a completed eligible result, open Monte Carlo, choose the available settings
and simulation count, and review its separate run allowance. The current request
maximum is shown by the form. This explores recorded trade outcomes; it does not
generate new market evidence or establish future profitability.

Cancel eligible pending/queued simulations from their history card. A simulation
already running must finish. Keep its sampling assumptions in mind: it does not
rerun contract selection, sizing and market execution under every possible regime.

## Continue the investigation

Attach completed tests to [AI Research](/docs/research/) within the current
attachment allowance. Ask a specific question about differences in rules, periods,
costs or losing trades. For practice with received live prices, explicitly deploy
a saved version to [Paper](/docs/paper/); a completed backtest does not deploy it.
