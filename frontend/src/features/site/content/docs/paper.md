---
title: Automated Paper Execution
description: Fund virtual sessions, deploy saved versions and manage orders, capital and running changes.
order: 8
---

## Paper wallet and session balances

Open **Paper Trading → Wallet** and add virtual funds. The Transactions tab records
wallet activity, deployment funding and capital returns. These are simulated
funds, separate from Terminal's account and any real broker balance.

A deployment receives a fixed rupee allocation from the wallet and keeps its own
balance, orders, positions and history. Unrealized profit is not a wallet deposit.

## Deploy from My Strategies

1. Save a validated version and make the strategy Active with Paper enabled.
2. In **My Strategies**, choose **Deploy Paper**.
3. Select the saved version. Review its instruments, signal bindings, conditions,
   sizing, entry schedule and exit rules.
4. Enter the fixed rupee capital amount. Percentage allocation and automatic
   rebalancing are not part of this deployment flow.
5. Review slippage, charge inclusion and the chosen Charge Profile.
6. Confirm, then open **Paper Trading → Deployments** to inspect the session.

There is no separate manual Paper account/allocation creation step. Deployments'
**Deploy strategy** button returns to My Strategies. One Paper deployment is allowed
per strategy/version; deploy a different saved version to compare it separately.
Start or Resume an existing deployment rather than creating a duplicate.

Each session has a readable **Strategy name · S123** identity. Always check that
identity and selected version before changing capital or inspecting results.

## Read status and pending actions

| Status | Meaning |
| --- | --- |
| Running | New entries can be evaluated when data, schedule, rules and funds permit |
| Paused | No new entries; existing positions still receive exit management |
| Stopping | Stop/close work is not yet complete; inspect pending orders/exposure |
| Stopped | The requested stop has completed |
| Error | Read the error and review the session before an explicit recovery action |

Filter the list by status. Rows show allocation, used/reserved and available
capital, lifetime P&L, costs and any current error. **Version pending** means the
requested version is not yet the version applied by execution.

An accepted action is a request, not proof that execution already applied it.
If the service is unavailable, a pending request waits. Inspect the final status,
applied version and resulting orders rather than sending the same action repeatedly.

## How rules become simulated trades

The session prepares each required signal/traded market and indicator history,
then evaluates eligible observations. Close/indicator rules use completed candles;
LTP uses received prices. A chart showing history does not by itself prove the
execution observation stream is ready.

A signal requests an order. A Paper market order fills on a later eligible
received observation of the traded instrument, with modeled slippage. It can
differ from the signal price and may wait when that instrument receives no new
prices. A backtest's signal-time fill and a Paper fill are different models.

Funds, whole-lot sizing, orderability, expiry and the segment's open session still
apply. Multiple instruments own separate positions/setup state but use their
session's available capital. A session with no valid entry should take no trade.

## Entry, exits and re-entry

Stop loss, Target and Exit request full closure of the owned position. Stop loss
wins when multiple exit stages match on the same evaluation. These are monitored
engine conditions; they depend on running execution and observations.

- A simple level Entry may re-enter on another eligible observation while true
  after the previous position is fully closed.
- A crossover requires a new known cross.
- A captured setup requires a new Arm occurrence and later confirmation; an Arm
  that stayed true throughout the trade does not automatically re-arm.

**Entry end is a cutoff for new entries, not a square-off time.** Paper also
checks a pending strategy entry when matching outside the allowed window; it is
not a general instant cancellation timer. Existing exposure follows exit rules.
See the examples in [Strategy Studio](/docs/builder/).

## Change capital while running

Choose **Capital** on the session row and enter the new total allocation.
Increasing it reserves the difference from free wallet funds; an approved decrease
returns the difference. Existing realized gains/losses remain in the session.
You cannot withdraw funds already committed to positions or orders.

No manual restart is normally needed. The execution owner applies the change
against its current commitments. Only one balance change can be pending; wait
for completion and inspect any rejection before submitting another.

Example: a session allocated 5,000.00 has lost 100.00 and is flat. Its remaining
balance is 4,900.00. Increasing allocation by 1,000.00 adds that amount; it does
not erase the 100.00 loss.

## Change the running version

Choose **Version**, select a saved version of the same strategy and review the
change. It must not duplicate another deployment of that strategy/version.

Working orders must settle before a conflicting change. A new version cannot
remove or rebind an owned open contract. Incompatible setup/capture changes can
require the session to be flat. Existing exposure keeps its entry risk basis;
new settings do not rewrite how the original trade entered.

The version is applied asynchronously without a manual stop/restart for a valid
change. Wait until requested and applied versions agree. Saving Studio alone
does not change the session.

## Pause, close and restart

- **Pause:** prevents new entries and resets unfilled setup state as the action
  applies; exit management for open positions remains active.
- **Stop & close:** cancels relevant work and requests closure. Stopping becomes
  Stopped only after positions/orders settle. Use Retry close when shown and
  inspect the error; a button click cannot manufacture a price observation.
- **Start / Resume:** explicitly revalidates the saved version, strategy enablement,
  current capacity and runtime inputs. Renewal does not restart it automatically.

Stopping or closing the browser does not stop server-side execution. Use the
session controls, then verify the resulting state.

## Stopped-session maintenance

| Action | Conditions and effect |
| --- | --- |
| Costs | Stopped and flat; change slippage/profile for later work, retaining recorded trade costs |
| Reset balance | Stopped and flat; restore the target allocation through a wallet transfer without erasing history |
| Remove | Stopped, flat, no working orders/pending commands; return remaining cash and delete deployment history |

Export or retain the records you need before Remove. Reset balance fails if the
wallet cannot fund the difference; it does not create free virtual performance.

## Positions, P&L and review

Open a row's Portfolio and choose Overview, Positions, Orders, History or
Settlements. The session selector identifies the account currently displayed.
Open P&L and summary values update from received marks, including positions on
other pages. Realized results change on financial events, not each price update.
If pricing is unavailable, treat the valuation as incomplete rather than zero risk.

Open P&L is before closing costs. Closed gross P&L, charges and net P&L describe
different amounts. Reviewed futures MTM/cash-settlement events, where enabled,
are separate from order fills and are shown with their source. No physical
delivery or general automatic rollover is supported.

Use Paper Analytics and [Journal/Reports](/docs/journal/) for realized history,
current exposure and your private notes. See [charges](/docs/charges/) for frozen
profiles and same-day versus across-date treatment.

## Capacity and troubleshooting

Public Running, Paused, Stopping and Error sessions count towards deployment and
instrument capacity. Stopped sessions release that active capacity. Creation,
restart and applicable version changes check the current allowance. Expiry of a
subscription does not automatically liquidate a running position.

For no-entry issues, check status, applied version, exact signal/traded sources,
entry time, history/observations, available capital and whether the setup can
re-arm. An order waiting for a later quote is different from a rule never matching.
Use [Support](/docs/support/) with the session/order ID and approximate time.
