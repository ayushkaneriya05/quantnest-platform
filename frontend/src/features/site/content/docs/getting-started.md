---
title: Getting started
description: Choose a first task, save your work and complete your first simulated trade.
order: 1
---

## What you can use

QuantNest connects research, your own strategy rules, historical testing, manual
simulation and automated Paper practice. Public plans currently support the
published NSE-stock workflow. Customer Live trading and QuantNest Private are not
offered. Additional instrument controls shown in the software do not change your
plan's published availability. Check [Billing and Usage](/docs/billing/) before
upgrading for a particular task.

You do not need to connect a personal broker account for research, backtests,
Terminal or Paper. Virtual balances and simulated profits cannot be withdrawn as
real money.

## 1. Create and protect your account

1. Register with your name, username, email and password, or use Google sign-in
   when it is configured.
2. Verify your email. Verification is required for checkout and helps associate
   earlier contact requests with your account. Ordinary password sign-in is not
   the same as email verification.
3. Open Settings → Security, enable two-factor authentication and save the backup
   codes somewhere private. See [account security](/docs/controls/).
4. Open Settings → Account for Billing, Support, record export and account-access
   controls. Use an account you own; do not share sign-in credentials.

## 2. Choose a first task

| Your starting point | Use | First useful result |
| --- | --- | --- |
| You want to understand a concept or stock | [AI Research](/docs/research/) | An answer with evidence where market calculations are needed |
| You know the filters you want | [Market Screener](/docs/screener/) | Selected stocks that pass your conditions |
| You have explicit trading rules | [Strategy Studio](/docs/builder/) | A validated saved version |
| You want to practise manual decisions | [Terminal](/docs/terminal/) | A simulated order and its recorded outcome |

Choose a liquid supported stock and a small, understandable rule set for your
first execution check. A strategy with no qualifying signal should take no trade;
do not make conditions meaningless merely to obtain a result.

## 3. Review simulation charges

Open **Charge Profiles**. Your account has a default named QuantNest unless you
have already changed it. Review the assumptions or create your own profile.
No broker connection is needed. See [charges and P&L](/docs/charges/).

## 4. Save a strategy and test it

1. Open **My Strategies → New Strategy** and enter its identity and description.
2. In Studio, choose instruments, direction and size; define Entry, Stop loss,
   Target and Exit conditions; review the schedule.
3. Validate and save a version. Saving does not start trading.
4. Open **Backtesting Lab → New Backtest**. Choose the strategy, dates, capital,
   slippage and charge profile.
5. Preview workload and credits, review the assumptions and start the test.
6. Read the trades and coverage as well as the headline result. Follow the
   [backtesting guide](/docs/backtesting/) to interpret fills and timestamps.

## 5. Move to simulated practice

For automation, add virtual funds to **Paper Trading → Wallet**, then choose
**Deploy Paper** from My Strategies. Select the saved version and a fixed rupee
allocation. Manage it in **Paper Trading → Deployments**.

For manual practice, open Terminal. Its account is separate from Paper Wallet.
Use the watchlist, chart and ticket, then inspect the resulting order and position.
Orders need an open segment session and eligible received prices to fill.

## 6. Review and improve

Use [Trade Journal and Performance Reports](/docs/journal/) to keep Terminal and
Paper outcomes separate. Add your own notes, compare realized results and inspect
current open P&L. Attach a selected report to AI Research when you want help
investigating it; sharing a strategy publicly does not share these records.

## When something does not happen immediately

- **No chart history:** the selected range may need a provider download. Read any
  history error rather than treating an empty chart as no market activity.
- **Queued research or backtest:** another computation may be using the available
  processing slot. Follow its status before submitting the same request again.
- **Accepted Paper action:** check the applied state. A request can wait for the
  execution service and is not proof that an order has already filled.
- **No Paper trade:** inspect session status, entry window, funds, history readiness
  and the exact rules. Entry conditions and capture re-entry behave differently.
- **Need help:** use [Support](/docs/support/) with the record ID and approximate
  time. Keep passwords, cookies, API keys and backup codes out of messages.
