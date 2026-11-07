import { isObservedQuote } from './marketData';

/** Value open exposure from one quote snapshot; never mix pages or persisted P&L. */
export function valuePositions(positions, quotes, sell, connected) {
  const livePnLByPositionId = {};
  const summary = { count: 0, invested: 0, current_value: 0, unrealized_pnl: 0,
    profitable: 0, losing: 0, unpriced_positions: 0, oldest_quote_at: null, by_account: {} };

  for (const position of positions) {
    const quote = quotes[position.instrument_symbol];
    const quoteTime = Date.parse(quote?.timestamp);
    const markTime = Date.parse(position.mark_at);
    const hasQuote = isObservedQuote(quote) && Number.isFinite(Number(quote.price))
      && Number.isFinite(quoteTime) && (!Number.isFinite(markTime) || quoteTime >= markTime);
    const average = Number(position.avg_price);
    const price = hasQuote ? Number(quote.price) : Number(position.current_price) > 0 ? Number(position.current_price) : average;
    const units = Number(position.quantity) * Number(position.qty_multiplier ?? 1);
    // Futures daily MTM is already in realized cash, so subtract it exactly once.
    const pnl = (price - average) * units * (position.side === sell ? -1 : 1) - Number(position.settled_pnl ?? 0);
    const invested = average * units;
    const priced = hasQuote || position.is_priced !== false;
    const at = hasQuote ? quote.timestamp : position.mark_at;
    livePnLByPositionId[position.id] = { pnl, pnlPercent: invested > 0 ? pnl / invested * 100 : 0,
      livePrice: price, isLive: connected && hasQuote };

    const amounts = { count: 1, invested, current_value: price * units, unrealized_pnl: pnl,
      profitable: Number(pnl > 0), losing: Number(pnl < 0) };
    const account = position.account_id ?? position.allocation_id;
    const group = summary.by_account[account] ??= { count: 0, invested: 0, current_value: 0,
      unrealized_pnl: 0, profitable: 0, losing: 0 };
    for (const [key, value] of Object.entries(amounts)) {
      summary[key] += value;
      group[key] += value;
    }
    if (!priced) summary.unpriced_positions++;
    if (priced && Number.isFinite(Date.parse(at))
      && (!summary.oldest_quote_at || Date.parse(at) < Date.parse(summary.oldest_quote_at))) summary.oldest_quote_at = at;
  }
  return { livePnLByPositionId, summary };
}
