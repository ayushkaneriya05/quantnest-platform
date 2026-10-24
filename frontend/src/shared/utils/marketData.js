// Quotes use ISO event/receipt timestamps supplied by the market-data API.
export function isObservedQuote(quote) {
  return ['observed', 'provider'].includes(quote?.source) && Number(quote?.price) > 0;
}

export function normalizeMarketSymbol(symbol) {
  const value = symbol.trim().toUpperCase();
  if (!/^[^:]+:[^:]+$/.test(value)) throw new Error('Use the instrument sym_ticker.');
  return value;
}

export function isNewerQuote(next, current) {
  const nextTime = Date.parse(next?.timestamp), currentTime = Date.parse(current?.timestamp);
  if (!(Number(next?.price) > 0) || !Number.isFinite(nextTime) || nextTime > Date.now() + 1000) return false;
  return !Number.isFinite(currentTime) || nextTime > currentTime
    || (nextTime === currentTime && Date.parse(next.updated_at) >= Date.parse(current.updated_at));
}
