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
  activateAccount: (id) =>
    axiosInstance.post(`${BASE_URL}/accounts/${id}/activate/`),
  deactivateAccount: (id) =>
    axiosInstance.post(`${BASE_URL}/accounts/${id}/deactivate/`),
  createAccount: (data) => axiosInstance.post(`${BASE_URL}/accounts/`, data),
  updateAccount: (id, data) =>
    axiosInstance.patch(`${BASE_URL}/accounts/${id}/`, data),
  deleteAccount: (id) => axiosInstance.delete(`${BASE_URL}/accounts/${id}/`),
  validateDeleteAccount: (id) =>
    axiosInstance.post(`${BASE_URL}/accounts/${id}/validate_delete/`),
  resetAccount: (id) => axiosInstance.post(`${BASE_URL}/accounts/${id}/reset/`),
  getAccountSummary: (id) =>
    axiosInstance.get(`${BASE_URL}/accounts/${id}/summary/`),

  // Positions
  getPositions: () => axiosInstance.get(`${BASE_URL}/positions/`),
  // closePosition: (id) => axiosInstance.post(`${BASE_URL}/positions/${id}/close/`), // Handled via trading app endpoints for manual trading

  // Orders
  getOrders: () => axiosInstance.get(`${BASE_URL}/orders/`),
  // placeOrder: (data) => axiosInstance.post(`${BASE_URL}/orders/place/`, data), // Handled via trading app endpoints for manual trading
  // cancelOrder: (id) => axiosInstance.post(`${BASE_URL}/orders/${id}/cancel/`), // Handled via trading app endpoints for manual trading

  // Trades
  getTrades: () => axiosInstance.get(`${BASE_URL}/trades/`),
  getTradeAnalytics: () => axiosInstance.get(`${BASE_URL}/trades/analytics/`),
};

export default paperApi;
