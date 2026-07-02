// src/services/orderService.js
import api from "@/services/api";

/**
 * Lightweight wrapper around the backend paper trading endpoints.
 * - placeOrder(payload)
 * - placeBracket(payload)
 * - placeCover(payload)
 * - cancel(orderId)
 * - modify(orderId, body)
 * - fetchAudit(params)
 */

export default {
  placeOrder: (payload) => api.post("/paper/orders/", payload),
  placeBracket: (payload) => api.post("/paper/bracket/", payload),
  placeCover: (payload) => api.post("/paper/cover/", payload),
  cancel: (orderId) => api.post(`/paper/orders/${orderId}/cancel/`, {}),
  modify: (orderId, body) => api.post(`/paper/orders/${orderId}/modify/`, body),
  listOrders: () => api.get("/paper/orders/list/"),
  listTrades: () => api.get("/paper/orders/trades/"),
  listPositions: () => api.get("/paper/positions/"),
  fetchOrderbook: (symbol, depth = 12) =>
    api.get(`/paper/orderbook/${encodeURIComponent(symbol)}/?depth=${depth}`),
  fetchAudit: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/paper/orders/audit-logs/?${qs}`);
  },
};
