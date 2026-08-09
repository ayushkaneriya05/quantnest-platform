/**
 * Paper Trading API Service
 */
import axiosInstance from "./api";

const BASE_URL = "/paper";

export const paperApi = {
  // Accounts
  getAccounts: () => axiosInstance.get(`${BASE_URL}/accounts/`),
  getAccount: (id) => axiosInstance.get(`${BASE_URL}/accounts/${id}/`),
  getActiveAccount: () => axiosInstance.get(`${BASE_URL}/accounts/active/`),
  createAccount: (data) => axiosInstance.post(`${BASE_URL}/accounts/`, data),
  updateAccount: (id, data) =>
    axiosInstance.patch(`${BASE_URL}/accounts/${id}/`, data),
  deleteAccount: (id) => axiosInstance.delete(`${BASE_URL}/accounts/${id}/`),
  validateDeleteAccount: (id) =>
    axiosInstance.post(`${BASE_URL}/accounts/${id}/validate_delete/`),
  resetAccount: (id) => axiosInstance.post(`${BASE_URL}/accounts/${id}/reset/`),
  getAccountSummary: (id) =>
    axiosInstance.get(`${BASE_URL}/accounts/${id}/summary/`),

  // Sessions
  listSessions: () => axiosInstance.get(`${BASE_URL}/sessions/`),
  pauseSession: (id) => axiosInstance.post(`${BASE_URL}/sessions/${id}/pause/`),
  stopSession: (id, data = { close_positions: true }) => axiosInstance.post(`${BASE_URL}/sessions/${id}/stop/`, data),
  resumeSession: (id) => axiosInstance.post(`${BASE_URL}/sessions/${id}/resume/`),

  // Allocations & Hot Swapping
  getAllocations: (params = {}) => axiosInstance.get(`${BASE_URL}/allocations/`, { params }),
  deployVersion: (id, payload) => axiosInstance.post(`${BASE_URL}/allocations/${id}/deploy-version/`, payload),

  // Positions
  getPositions: () => axiosInstance.get(`${BASE_URL}/positions/`),
  // closePosition: (id) => axiosInstance.post(`${BASE_URL}/positions/${id}/close/`), // Handled via trading app endpoints for manual trading

  // Orders
  getOrders: () => axiosInstance.get(`${BASE_URL}/orders/`),
  // placeOrder: (data) => axiosInstance.post(`${BASE_URL}/orders/place/`, data), // Handled via trading app endpoints for manual trading
  cancelOrder: (id) => axiosInstance.post(`${BASE_URL}/orders/${id}/cancel/`),

  // Trades
  getTrades: () => axiosInstance.get(`${BASE_URL}/trades/`),
  getTradeAnalytics: () => axiosInstance.get(`${BASE_URL}/trades/analytics/`),
};

export default paperApi;
