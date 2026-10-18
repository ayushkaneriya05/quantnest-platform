---
title: Automated Paper Execution
description: Deploy a saved strategy, allocate simulated capital and monitor it.
order: 7
---
## Prepare your strategy

- Activate your strategy and enable Paper execution.
- Create or choose a simulated capital allocation/account.
- Select the saved version and review instruments, slippage and charge settings before confirming.

## Start and monitor

- Paper runs separately from manual Terminal practice.
- Inspect session state, orders, positions, costs and recorded trades.
- Missing history or incomplete readiness can block entries; check the reported reason rather than assuming every tick produces an order.

## Pause, stop and resume

- Pause prevents new entries; protective behaviour remains distinct.
- Stop explicitly and inspect remaining exposure. Settlement of positions/orders may be required before completion.
- Resume explicitly within your current limits. Resumption does not override independent strategy restrictions.

## Capacity and renewal

- Paused deployments count toward active deployment and instrument limits.
- Capacity is released after stop and settlement.
- Expiry restricts new/increased exposure while preserving protective reductions, monitoring and records. It does not force liquidation for payment reasons.
- Renewal does not silently resume a deployment.

## Review the results

- Use Paper in Journal and Reports to inspect this environment only.
- Recorded fills are simulated and cannot establish how a broker would fill the same instructions.
