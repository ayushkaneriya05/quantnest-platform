---
title: Broker Integration
description: Authorize your supported trading account in Private and check connection readiness, funds and order updates.
order: 14
---

## Availability and purpose

Broker Integration is included with [QuantNest Private](/docs/private/).
FYERS is currently implemented. Public research, backtesting, Terminal simulation
and Paper do not require you to connect a personal trading account.

A connection belongs to its account owner. Authorizing it does not deploy a
strategy or place an order. Real execution begins only after you explicitly
configure and start an eligible [Live strategy deployment](/docs/live/).

## Before connecting

Have your own supported broker account and its trading app configuration ready.
Use the account and app details intended for this Private deployment, including
the callback and network settings supplied during onboarding.

The trading account's app is separate from the deployment's market-data app.
QuantNest manages the shared data connection; trading authorization alone does
not establish that every required history/tick subscription is ready.

Keep app secrets and authentication codes out of support messages, AI research,
screenshots and shared strategy links. Enter the app settings in the connection
dialog; complete authentication on the broker's own sign-in page.

## Connect step by step

1. Open **Broker Integration → Connections** in your Private workspace.
2. Choose the available broker and configure its app settings. For FYERS these
   are its App ID and App Secret. Existing secrets are not displayed back to you.
3. Start authorization and complete the broker's sign-in/verification flow.
4. Return to the workspace and check the connected account's identity and status.
5. Inspect the latest funds snapshot and its observation time. Confirm that this
   is the account you intend to use before choosing it for Live deployment.

If authorization fails, review the app, callback and account settings and begin
a new sign-in. Do not repeatedly submit an expired authentication code.

## Authorization and daily operation

Broker authorization expires independently of your QuantNest login. Complete
reauthorization when required; FYERS trading sessions require daily sign-in.
Changing a QuantNest password or renewing a Private agreement does not renew
the broker's authorization.

Connection and funds information are observations with timestamps. Refresh when
checking readiness, especially before starting new exposure. A capital allocation
does not deposit money into a separate broker subaccount.

Broker Integration is the place to review connection and funds details. Live
Portfolio focuses on strategy/session execution and does not duplicate detailed
broker-account balance cards.

## How orders and positions are synchronized

QuantNest correlates its owned orders with broker order reports. Reports can
arrive through the broker stream or reconciliation; cumulative fills update the
owned orders and derive strategy/session positions and recorded trades.

The broker's aggregate positions can include activity outside QuantNest.
They do not overwrite an individual strategy session's positions. Do not assume
that a trade placed in the broker app will automatically appear as a QuantNest
strategy trade, or that external activity is fully attributed in its reports.

## Changing or disconnecting an account

Review active deployments, pending orders and open exposure first. Unsafe
disconnect/reconfiguration can be rejected while related work still needs the
connection. Settle or explicitly manage that work before removing access.

If an order's outcome is uncertain, inspect its broker order ID and account
records and allow reconciliation. Avoid issuing a duplicate order merely because
the local response was delayed.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Authorization failed | Correct app/account, callback and a newly started sign-in |
| Connection expired | Reauthorize the trading account; workspace login is separate |
| Funds unavailable or old | Connection readiness and the latest funds observation |
| Live menu unavailable | The workspace must have Live execution scope enabled |
| Orders rejected | Broker message, supported product, funds, whole lots, price increments and market session |
| Local and broker records differ | Owned order IDs, pending reconciliation and any external activity |

Contact Support with the affected account/session/order identifier and error
message. Never include broker credentials or one-time authentication codes.
