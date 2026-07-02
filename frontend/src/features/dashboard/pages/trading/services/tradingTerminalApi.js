import api from "@/shared/services/api";

export const tradingTerminalApi = {
  getSnapshot: () => api.get("/trading/terminal/"),
  getCandles: ({
    symbol,
    interval = "1m",
    limit = 200,
    before,
    signal,
  } = {}) =>
    api.get("/market/candles/", {
      params: { symbol, interval, limit, before },
      signal,
    }),
  getLatestQuote: (symbol) =>
    api.get("/market/latest-tick/", {
      params: { instrument: symbol },
    }),
  addToWatchlist: (instrumentId) =>
    api.post("/trading/watchlist/", { instrument_id: instrumentId }),
  removeFromWatchlist: (instrumentId) =>
    api.delete("/trading/watchlist/", {
      data: { instrument_id: instrumentId },
    }),
  placeOrder: (payload) => api.post("/trading/orders/", payload),
};

export default tradingTerminalApi;
