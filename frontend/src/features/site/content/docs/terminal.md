---
title: Manual Simulated Terminal
description: Organize watchlists, read charts and practise manual orders, protection and position management.
order: 7
---

## Your Terminal workspace

Terminal is manual simulation and does not send real broker orders. Its account
is separate from Paper Wallet and automated Paper sessions. Public instrument
availability follows the published plan; contract controls below apply where
those instruments are enabled.

| Tab | Use |
| --- | --- |
| Trade | Watchlist, chart, ticket, open positions and working orders |
| History | Settlements, recorded orders, fills and closed positions |
| Account | Balances, modeled charges and simulation configuration |

Your first account/watchlist is created automatically. Use Account to inspect
available funds and the selected Charge Profile. Do not look for a separate
Paper-wallet transfer or a real-money top-up in Terminal.

## Named watchlists and prices

Create, rename and select watchlists from the list control. Add instruments by
name, ticker, underlying or contract text, and use the offered exchange/type/expiry
filters. Read full option names and contract details rather than only the shared
underlying symbol. Indices can be charted but cannot receive orders.

Watchlist prices update for the subscribed visible list without opening each
chart. Selecting a row changes the chart and ticket. All named lists remain
separately available for [AI context](/docs/research/) and [screening](/docs/screener/),
subject to those tools' stock restrictions.

## Read charts and resize the workspace

Choose a chart timeframe and Candlesticks or Line. Available stored candles load
first; missing requested history is fetched when the source permits it. Scroll
left for older data and use chart reload after resolving a reported history error.
Provider access and historical depth affect what can be retrieved.

Received market prices update the current chart candle and displayed price.
Completed-candle Close used by Studio is a different input from that forming
chart candle. A historical close or cached display price does not prove that a
new price is available to fill an order.

Dates display in IST, with candle intervals aligned to segment sessions/holidays.
A connected page outside market hours does not imply an open trading session.

On desktop drag the divider beside the watchlist to resize it and the grip above
Positions/Orders to resize the bottom panel. Use the panel controls to hide or
expand it. Browser preferences retain these sizes. Small screens use compact
watchlist/ticket dialogs; wide tables can scroll horizontally.

## Submit a simulated order

Select Buy or Sell, order type and size. Cash quantities use Units. Derivative
tickets use Lots and show the resulting order units; one lot uses that contract's
lot size. Enter prices on its allowed tick increment.

The ticket shows estimated funds, not an advance charge estimate. Check the
instrument, side, units and all required price fields before submission. A
successful request can appear as a working order before an eligible observation
fills it. Do not submit a duplicate simply because no fill has appeared yet.

Orders can be submitted for the segment's supported open session. Normal fills
also require an open session, an eligible received price and a non-expired
tradeable contract. Cancellation remains available outside the session.

## The four order types

| Type | Buy | Sell |
| --- | --- | --- |
| Market | Fill on a later eligible received price | Fill on a later eligible received price |
| Limit | Fill at or below the limit | Fill at or above the limit |
| Stop market | Activate at or above trigger, then market matching | Activate at or below trigger, then market matching |
| Stop limit | Activate at or above trigger, then require the buy limit | Activate at or below trigger, then require the sell limit |

For a Buy limit of 1240.00, a later eligible price of 1238.00 qualifies; a Buy
limit of 1237.00 does not qualify at that same price.

For a Buy stop-limit with trigger 1240.00 and limit 1242.00, price must first
activate the trigger. If it gaps to 1245.00, the activated limit waits for
1242.00 or lower. Falling below the trigger afterward does not undo activation.
Changing the trigger rearms the order. Activation is not a guaranteed fill.

Pending orders remain until filled or cancelled; there is no customer-selectable
Validity control. This simulation does not reproduce exchange depth, queue
position, liquidity-bounded partial fills or every auction phase.

## Manage positions and protection

Use **Manage**, **Protect** or **Close** on a position. Increase/reduce quantities
must respect its lot size and available funds. Reverse closes existing exposure
and requests the chosen amount in the opposite direction; it is not merely a
relabel of the original trade.

Optional Stop loss/Take profit on a ticket creates linked reduce-only protection
after the fill. Position protection and close actions still depend on execution
and eligible observations. Removing or changing a protection level changes its
future behavior; inspect the resulting working orders.

Modify or cancel eligible working orders from Orders. A completed or already
cancelled order is not editable. Cancellation requests must finish applying;
check final status and released reservation before assuming funds are available.

## Balances, charges and P&L

Account separates equity, cash, collateral, reservations and available capital.
Open positions and working orders can reduce spendable funds. Unrealized profit
is a current valuation, not a cash deposit.

Choose an owned Charge Profile or no modeled fees. Futures and short-option
margin percentages, where offered, are estimates; they are not broker portfolio
margin quotations. Changing those settings recalculates commitments rather than
rewriting closed trades.

Charges for entry and exit are applied when quantity closes. Open P&L is gross;
closed gross P&L, Charges and Net P&L are separate. Same-local-date equity closes
use the modeled intraday treatment even with CNC product mapping. Partial closes
charge their closed quantity; the remainder is charged at its own exit. Accepted
orders keep their profile snapshot. See [charges](/docs/charges/).

## History and settlement

Use History's tabs, search, date filters and page controls. Order placement time,
trigger activation, fill time and closing time describe different events.
Closed positions show gross P&L, charges and net P&L separately.

Reviewed futures MTM and qualified index expiry postings, where enabled, appear
in Settlements with their source, charges and cash changes. They are accounting
events rather than invented market fills. Physical delivery is not supported.

Use [Journal/Reports](/docs/journal/) for notes and source-specific summaries.
Refreshing a table reloads recorded state; it does not create a new trade or
change the market's trading hours.

## If an order does not fill

Check whether it is still pending, the side/limit/trigger, activation state,
whole-lot size, available funds, segment session and received prices. The last
visible chart price may be historical. A market order waiting for a later
observation is different from a limit that never qualified.
Report the order ID, instrument, type, prices and approximate time through
[Support](/docs/support/) if the recorded behavior still disagrees.
