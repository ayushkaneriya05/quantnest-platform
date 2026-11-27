---
title: Automated Live Trading
description: Deploy saved strategy versions through your broker in Private, manage sessions and interpret broker-confirmed results.
order: 15
---

## What Live trading does

[QuantNest Private](/docs/private/) includes automated Live strategies through
your supported broker connection. Your own saved rules generate order intents;
the broker accepts/rejects orders and establishes actual fills. Live uses real
funds and can incur losses. A displayed signal, deployment receipt or submission
acknowledgement is not a completed trade.

Public plans provide research and simulation through Paper. Terminal remains
simulated even in Private; its manual tickets do not send real broker orders.

## Prepare your first deployment

1. Complete [broker authorization](/docs/brokers/) and verify the account identity,
   readiness and latest funds observation. FYERS is currently implemented.
2. Save and validate your strategy in [Studio](/docs/builder/). Review the exact
   version, signal and traded instruments, direction, size, stops and schedule.
3. Check that the selected contracts and products are supported by the broker
   and that the deployment has the required history and live data.
4. Start with a deliberately reviewed size and verify the intended workflow.
   A successful backtest or Paper result is not proof of broker acceptance.

## Deploy from My Strategies

1. Choose the strategy's **Live** deployment action.
2. Select a saved version and an owned, ready broker account.
3. Enter a fixed rupee capital allocation. Percentage allocation is not supported.
4. Review instruments, stop conditions and settings, then confirm.
5. Open **Live Trading → Deployments** and inspect the requested/applied state,
   selected version and any preparation or application error.

The capital allocation is a local budget, not a transfer of broker funds. Other
sessions and external broker activity still share the real account's resources.

The same strategy cannot have duplicate deployments on the same broker account.
You can deploy it on a different owned account. Paper's separate-version sessions
follow a different deployment rule.

## From data to a trade

Required history is prepared before normal evaluation. Completed-candle inputs
use completed bars; LTP inputs use received live observations. A signal instrument
can differ from the traded contract, but an underlying/index price cannot serve
as the option or future's execution price.

For automatic contract selection, an eligible flat entry selects the contract
according to the saved expiry/strike policy. Pending orders and open positions
retain their exact contract when the underlying moves to another ATM strike.

Locally admitted orders reserve the account/session resources before broker
submission. Broker reports determine accepted status and cumulative fills.
Partial fills, rejections and uncertain submission can therefore produce a
different outcome from a simulation. Do not submit duplicates while investigating
an uncertain outcome.

## Running changes and controls

| Action | Behaviour |
| --- | --- |
| Save Studio | Saves a version; does not replace running rules |
| Change capital | Requests an update; capital cannot be reduced below committed exposure/orders |
| Change version | Validates compatible settings and prepares the update; check the applied version |
| Pause | Stops new strategy entries while existing exposure retains exit management |
| Resume | Requests eligible execution to resume; inspect applied state and readiness |
| Stop & close | Stops entries and requests closure; continue monitoring until pending orders/exposure settle |

Saving a version or requesting a change does not itself prove it is applied.
Inspect pending/applied information. An open position keeps its owned contract
and entry information during compatible changes.

Set **Daily square-off** in the saved strategy version to block entries, request
cancellation of working entry orders and submit a market exit for the position
that session owns. Choose a time before the broker cutoff. Use the order book
and broker reports to verify cancellation and fills. **Entry end** controls the
ordinary entry window.

## Monitor execution and results

- **Deployments:** status filters, session controls, capital and applied versions.
- **Portfolio:** source/session-specific positions, orders, history and available
  performance views. Open P&L updates with observed prices.
- **Execution Logs:** relevant session events and errors for investigation.
- **Journal and Reports:** review recorded closes without mixing Terminal,
  Paper and Live results. Optional research attachments preserve the chosen source.

**Live reporting currently excludes actual broker charges.** Do not interpret its
recorded result as independently reconciled profit after broker fees. Check the
broker's actual statement. Simulated charge profiles have a separate role in
Terminal, Paper and backtests.

## Connection interruptions and daily readiness

Keep the trading account's daily authorization current. The deployment's data
feed and broker order-update services are separate connections; functioning
charts alone do not establish order readiness.

After an interruption, inspect applied state, broker orders, account funds and
remaining exposure. Reconciliation follows owned orders. Do not assume that
disconnecting, stopping a process or signing out cancels an order at the broker.
Coordinate with Support when recovery or manual intervention is needed.

## Current boundaries

Available software does not imply every instrument/product combination has been
accepted on your account. Review support during onboarding, especially cash short
products and commodity funding ledgers. The current equity product policy uses
CNC and derivatives use MARGIN; local simulation is not broker margin approval.

Atomic multi-leg execution, automatic rollover, general external-position
attribution, actual broker-fee reconciliation and complete Live assignment,
physical-delivery and settlement accounting are not delivered capabilities.
Do not rely on them because contracts are selectable in Studio.

Private has no public-plan quotas, but ownership, funds, eligible contracts,
market sessions and technical controls continue to apply. Quotes, service periods
and renewals are handled directly; see [Private operation](/docs/private/).
