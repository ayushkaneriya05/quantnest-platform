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
  // A candle's synthetic close time must not hide an actual provider LTP.
  if (isObservedQuote(next) !== isObservedQuote(current)) return isObservedQuote(next);
  if (isObservedQuote(next) && next.source !== current.source) {
    return Date.parse(next.updated_at) >= Date.parse(current.updated_at);
  }
  return !Number.isFinite(currentTime) || nextTime > currentTime
    || (nextTime === currentTime && Date.parse(next.updated_at) >= Date.parse(current.updated_at));
}
