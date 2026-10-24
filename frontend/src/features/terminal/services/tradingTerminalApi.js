import api from "@/shared/services/api";

export const tradingTerminalApi = {
  getSnapshot: (watchlistId) => api.get("/trading/terminal/", { params: { watchlist_id: watchlistId } }),
  updateAccount: (payload) => api.patch('/trading/account/', payload),
  previewOrder: (payload, signal) => api.post('/trading/orders/preview/', payload, { signal }),
  cancelOrders: (ids) => api.post('/trading/orders/cancel/', { ids }),
  positionAction: (id, payload) => api.post('/trading/positions/' + id + '/action/', payload),
  getCandles: ({
    symbol,
    interval = "1m",
    limit = 200,
    before,
    signal,
    fetchMissing = false,
  } = {}) =>
    api.get("/market/candles/", {
      params: { symbol, interval, limit, before, fetch_missing: fetchMissing },
      signal,
    }),
  addToWatchlist: (symTicker, watchlistId) =>
    api.post("/trading/watchlist/", { sym_ticker: symTicker }, { params: { watchlist_id: watchlistId } }),
  removeFromWatchlist: (symTicker, watchlistId) =>
    api.delete("/trading/watchlist/", {
      params: { watchlist_id: watchlistId },
      data: { sym_ticker: symTicker },
    }),
  placeOrder: (payload) => api.post("/trading/orders/", payload),
};

export default tradingTerminalApi;
