---
title: Automated Paper Execution
description: Deploy saved strategy versions, fund sessions and manage simulated execution.
order: 7
---
## 1. Fund your Paper wallet

Open **Paper Trading → Wallet**, enter a positive amount and add virtual funds.
These are simulated funds, separate from broker balances and the manual Terminal.
The Transactions tab records deposits, withdrawals, deployment funding and capital returns.

## 2. Prepare and deploy a strategy

1. Open **My Strategies** and activate your strategy with Paper trading enabled.
2. Choose **Deploy Paper** on that strategy.
3. Select a saved version. That version supplies the instruments, routes, rules, entry times and risk settings.
4. Enter the capital amount in rupees. There is no percentage allocation or automatic rebalancing.
5. Review slippage and the charge profile. Enable transaction charges if desired.
6. Confirm deployment. The system creates the session, its allocation and its internal ledger together.

There is no separate account or allocation creation step. The deployment page's
**Deploy strategy** button takes you to My Strategies.

Each strategy version can have one Paper deployment. Deploy another version of
the same strategy to compare versions in separate sessions. To run an existing
deployment again, use **Start** or **Resume** instead of creating a duplicate.

The ledger is named **Strategy name · S123**, where S123 identifies that session.
It keeps a separate cash balance, positions, orders and trade history.

## 3. Use the Deployments page

Open **Paper Trading → Deployments**. Sessions appear as list rows, with:

- Strategy, pinned version, session ID and status.
- Allocated capital, margin used, available capital and lifetime P&L.
- Trade/open-position counts, execution costs and the last session error.

Filter by Running, Paused, Stopping, Stopped or Error. **All statuses** shows every
deployment. Use **Portfolio** on a row to open that session's positions, orders and
trades. Live quotes update open-position P&L; recorded Paper fills are simulated.

## 4. Change capital or version while running

**Capital** updates the rupee amount assigned to that session. Increasing capital
transfers the difference from the wallet; reducing it returns the difference.
A reduction cannot withdraw margin already committed to positions. Realized gains
and losses remain in the session balance. No stop/restart is needed: a funds
publication updates the running worker's background inputs.

**Version** applies a saved version of the same strategy. The new version must
retain instruments with open positions, and pending orders must settle first.
It cannot duplicate another Paper deployment of that strategy/version.
The running worker receives the version change automatically; existing positions
remain open. Saving a version in the builder alone does not deploy it.

## 5. Pause, stop and restart

- **Pause** prevents new entries while exit management remains active.
- **Stop & close** stops new entries and requests closure of open positions.
  Stopping completes after positions and orders settle. Inspect errors or use
  Retry close if settlement remains incomplete.
- **Start / Resume** explicitly restarts the same session and balance. Current
  capacity, strategy enablement, enabled execution scope still apply.
- Strategy end time is an entry cutoff. It does not square off Intraday positions;
  stop-loss, target and exit rules continue to manage them.

Missing history or incomplete market readiness can block entries. Every tick does
not necessarily produce a signal or order.

## 6. Manage a stopped session

- **Costs** changes slippage and charge settings only while stopped and without
  open positions. Existing trades retain their recorded charges.
- **Reset balance** restores the currently allocated capital using a wallet transfer.
  It preserves trade history and fails if the wallet cannot cover the difference.
- **Remove** deletes the stopped deployment and its Paper execution history, and
  returns its remaining cash to the wallet. Close all positions/orders first.

Use Journal and Reports before removing a deployment if you need its records.

## Capacity and renewal

Running, Paused, Stopping and Error sessions count towards public deployment and
instrument capacity; stopped sessions release it. A new deployment, restart or
active version change checks the applicable plan allowance. Development records
usage without enforcing plan quotas. Private installations have no numeric plan
quota. Customer Private deployments are not currently available.

Running execution has no background subscription-expiry gate. Session state,
market readiness and trading risk controls still apply. Renewal never silently
restarts a stopped deployment.
