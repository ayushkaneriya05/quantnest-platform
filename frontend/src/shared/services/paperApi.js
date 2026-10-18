/**
 * Paper Trading API Service
 */
import axiosInstance from "./api";

const BASE_URL = "/paper";

export const paperApi = {
  // Accounts
  getAccounts: () => axiosInstance.get(`${BASE_URL}/accounts/`),
  getActiveAccount: () => axiosInstance.get(`${BASE_URL}/accounts/active/`),
  deleteAccount: (id) => axiosInstance.delete(`${BASE_URL}/accounts/${id}/`),
  resetAccount: (id) => axiosInstance.post(`${BASE_URL}/accounts/${id}/reset/`),

  // Sessions
  pauseSession: (id) => axiosInstance.post(`${BASE_URL}/sessions/${id}/pause/`),
  stopSession: (id, data = { close_positions: true }) => axiosInstance.post(`${BASE_URL}/sessions/${id}/stop/`, data),
  resumeSession: (id) => axiosInstance.post(`${BASE_URL}/sessions/${id}/resume/`),
  configureSessionCosts: (id, data) => axiosInstance.post(`${BASE_URL}/sessions/${id}/configure-costs/`, data),

  // Allocations & Hot Swapping
  getAllocations: (params = {}) => axiosInstance.get(`${BASE_URL}/allocations/`, { params }),
  deployVersion: (id, payload) => axiosInstance.post(`${BASE_URL}/allocations/${id}/deploy-version/`, payload),

  // Positions
  getPositions: () => axiosInstance.get(`${BASE_URL}/positions/`),

  // Orders
  getOrders: () => axiosInstance.get(`${BASE_URL}/orders/`),

  // Trades
  getTrades: () => axiosInstance.get(`${BASE_URL}/trades/`),
};

export default paperApi;
