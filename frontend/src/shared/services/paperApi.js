/**
 * Paper Trading API Service
 */
import axiosInstance from "./api";

const BASE_URL = "/paper";

export const paperApi = {
  // Read-only session ledgers
  getAccounts: () => axiosInstance.get(`${BASE_URL}/accounts/`),

  // Deployment management
  getSessions: () => axiosInstance.get(`${BASE_URL}/sessions/`),
  deleteSession: (id) => axiosInstance.delete(`${BASE_URL}/sessions/${id}/`),
  resetSession: (id) => axiosInstance.post(`${BASE_URL}/sessions/${id}/reset/`),
  updateAllocation: (id, data) => axiosInstance.post(`${BASE_URL}/sessions/${id}/update-allocation/`, data),
  pauseSession: (id) => axiosInstance.post(`${BASE_URL}/sessions/${id}/pause/`),
  stopSession: (id, data = { close_positions: true }) => axiosInstance.post(`${BASE_URL}/sessions/${id}/stop/`, data),
  resumeSession: (id) => axiosInstance.post(`${BASE_URL}/sessions/${id}/resume/`),
  configureSessionCosts: (id, data) => axiosInstance.post(`${BASE_URL}/sessions/${id}/configure-costs/`, data),

  deployVersion: (id, payload) => axiosInstance.post(`${BASE_URL}/sessions/${id}/deploy-version/`, payload),

  // Positions
  getPositions: () => axiosInstance.get(`${BASE_URL}/positions/`),

  // Orders
  getOrders: () => axiosInstance.get(`${BASE_URL}/orders/`),

  // Trades
  getTrades: () => axiosInstance.get(`${BASE_URL}/trades/`),
};

export default paperApi;
