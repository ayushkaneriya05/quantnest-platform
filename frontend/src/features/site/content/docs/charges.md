---
title: Charge Profiles and P&L
description: Configure reusable simulation costs and understand gross, charges, net and holding-date treatment.
order: 6
---

## Start with your default profile

Open **Charge Profiles**. A QuantNest default is created for a new account. You
can edit it, create another named profile and make that one default. No broker
connection is required.

The current default cannot be deleted. Set another profile as default first,
then delete the former one if you no longer need it. The name QuantNest is a
starting label, not a guarantee that its rates match your broker or every contract.

## What the fields mean

| Field family | What it models |
| --- | --- |
| Brokerage flat/percentage/cap | Brokerage inputs and the per-order cap used by the calculator |
| Equity delivery and intraday STT | Different modeled treatment for same-date and across-date equity holdings |
| Futures/options sell tax | Configured derivative sell-side tax inputs |
| Commodity futures/options sell tax | Separate commodity inputs where that segment is enabled |
| Exchange transaction charges | Configured equity/F&O turnover rates |
| SEBI fee, stamp duty and GST | Additional configured components and their calculation bases |

Percentage inputs use percentage units: 0.03 means 0.03%, not 3%. Verify rates
against the assumptions you actually want to model. QuantNest does not automatically
keep every profile synchronized with a broker tariff or a changed tax schedule.

For brokerage, the calculator chooses the lower positive flat/percentage amount,
then applies a positive cap. A zero flat amount removes that candidate; it does
not make brokerage free when the percentage is positive. Disable modeled fees
where offered when you deliberately want a no-charge comparison. GST uses the
configured brokerage-plus-exchange-charge base rather than all tax components.

Slippage is separate from fees. It adjusts the simulated execution price; a
charge profile calculates costs on the resulting modeled trade.

## Select a profile where you execute

- **Backtest:** choose a profile and charge inclusion in the new-run form.
- **Paper:** choose charges/profile and slippage when deploying; edit Costs only
  under the stopped/flat conditions offered by the session.
- **Terminal:** choose the account's profile or no modeled fees in Account.

Making a different profile default does not rewrite existing results, accepted
orders or a deployment's already frozen cost settings. A saved backtest rerun
retains that run's assumptions; create a new configured experiment for new rates.

## Charges apply when quantity closes

Terminal and Paper do not deduct a final round-trip charge merely because an
entry filled. Entry and exit cost components are calculated when quantity closes,
using its stored profile and holding dates. Terminal's order ticket therefore
shows estimated funds rather than a potentially misleading charge estimate.

For cash equity, closing on the same application-local date uses modeled
intraday treatment; an across-date close uses delivery treatment. CNC product
mapping alone does not force delivery fees on a same-day close. Other segments
use their own configured calculation branches.

For partial closes, only the closed quantity is charged then. Later closes use
their own closed quantities and retained entry information. Derivative values
also use the contract's quantity multiplier; lots and financial multipliers
are separate concepts.

## Gross, charges and net

Example only: 10 units bought at 100.00 and sold at 102.00 have gross P&L of 20.00
when the multiplier is one. If recorded charges total 3.00, net P&L is 17.00.

Open P&L is a changing price valuation before future closing costs. A profitable
open position can close at a lower price and incur charges. Do not compare an
open gross mark with a closed net result as if they were the same measure.

Zero charges can mean fees were disabled, an old record lacked charges or a
broker source has no integrated fee evidence. It is not proof that a real broker
charged nothing. Simulation profiles are assumptions, not broker contract notes.

## Check a surprising charge

Read the recorded quantity, entry and exit dates, multiplier, profile snapshot,
charge inclusion and breakdown. Editing today's profile will not fix a historical
snapshot. Send the close/run ID and the specific component you question through
[Support](/docs/support/), without sharing broker credentials.
