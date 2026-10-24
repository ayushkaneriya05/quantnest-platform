---
title: Manual Simulated Terminal
description: Charts, manual practice orders, history and account settings.
order: 6
---

## Choose a workspace

The Terminal's main page header has three tabs:

- **Trade**: watchlist, chart, order ticket, positions and working orders.
- **History**: recorded orders, fills and closed positions.
- **Account**: balances, fees and simulation settings.

Your first account and watchlist are created automatically. Create or select
watchlists using the searchable dropdown. Add instruments by symbol, underlying,
contract, exchange or expiry.

Watchlists, charts and tables show instrument names with exchange/contract details,
so options sharing a symbol remain distinguishable.
Selection and subscriptions use the full exchange-qualified ticker internally.
Indices are available for analysis and cannot be traded.

## Charts

Choose a timeframe and Candlesticks or Line. The chart uses segment sessions and
IST dates. Scroll left to load older history. Available candles appear first;
missing ranges are fetched from the configured data provider and stored.

History fetching needs an authorized market-data connection. It works independently
of the live feed process. Provider entitlement determines available historical depth.
Use the chart reload button after correcting an authentication or provider error.

Live prices and matching need the market-data process. A displayed historical
candle is not a provider observation.

## Resize panels

Drag the grip above Positions/Orders up or down to change the panel height.
On desktop, drag the grip beside the watchlist left or right to change its width.
Both sizes are saved in this browser. Use the panel button to hide Positions/Orders.
Small screens use dialogs for the watchlist and
order ticket; tables scroll horizontally.

## Place an order

Choose Buy/Sell, order type and size. Cash quantities use units; derivatives use
lots, with actual order units shown. All prices follow the instrument tick size.

Orders remain pending until filled or cancelled. Execution requires an open
segment session, and expired contracts cannot fill normal orders.

| Type | Behaviour |
| --- | --- |
| Market | Fills from a fresh observed trade during the segment session. |
| Limit | Buy at/below limit; sell at/above limit. |
| Stop market | Buy triggers at/above stop; sell at/below stop. |
| Stop limit | Activates at the trigger, then respects its limit. |

For example, Buy stop-limit trigger 1240 and limit 1242 activates at 1240 or above.
If the triggering tick is 1245, it waits for a qualifying limit price. Activation
does not guarantee execution. Changing the trigger rearms it.

The ticket shows estimated funds. Optional stop loss/take profit
creates linked reduce-only exits after a fill. Pending orders remain open until
filled or cancelled. Cancellation remains available outside the session.

## Manage positions and orders

Use Manage, Protect or Close on a position. Increase, reduce and reversal actions
use the relevant position quantity and contract lot size. Reverse closes existing
exposure and opens the requested new-direction amount.

Modify or cancel working orders in the Orders panel. Cancelling selected orders
releases their reservations.

After expiry, Manage → Settle expired contract records a simulation close at an
official settlement price you enter. Zero is valid for a worthless expired option.
This is not a broker trade or physical delivery.

## Account and history

Account contains equity, available capital, cash, collateral, reservations, P&L
and recorded charges. Select an owned Charge Profile or no modeled fees. Configure
futures and short-option margin percentages there. These estimates are not broker
margin quotations.

Working orders retain their fee snapshot. Changed margin settings recalculate
collateral and reservations. Closed net P&L includes recorded charges; open P&L is
gross. Charges for both entry and exit are deducted only when you close a
position, following the same calculator as Paper and backtesting. Closing on
the same local date uses intraday treatment; holding across dates uses delivery
treatment. Saved profile rates stay attached to each accepted order. For a partial
close, only the closed quantity incurs charges; the remainder is charged at its
own exit. The ticket does not estimate charges before submission.

History filters use the platform's date pickers and searchable dropdowns. Order
intent, trigger activation, actual fills and gross/fees/net closes remain distinct.

Terminal is a simulator. It does not model exchange depth, liquidity-bounded partial
fills, portfolio margin offsets, physical delivery or all auction phases.
