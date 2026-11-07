/**
 * Paper Trading API Service
 */
import axiosInstance from "./api";

const BASE_URL = "/paper";

export const paperApi = {
  getAccount: (id) => axiosInstance.get(`${BASE_URL}/accounts/${id}/`),
  getSessionSummary: () => axiosInstance.get(`${BASE_URL}/sessions/summary/`),
  // Deployment management
  getSessions: (params = {}, signal) => axiosInstance.get(`${BASE_URL}/sessions/`, { params, signal }),
  deleteSession: (id) => axiosInstance.delete(`${BASE_URL}/sessions/${id}/`),
  resetSession: (id) => axiosInstance.post(`${BASE_URL}/sessions/${id}/reset/`),
  updateAllocation: (id, data) => axiosInstance.post(`${BASE_URL}/sessions/${id}/update-allocation/`, data),
  pauseSession: (id) => axiosInstance.post(`${BASE_URL}/sessions/${id}/pause/`),
  stopSession: (id, data = { close_positions: true }) => axiosInstance.post(`${BASE_URL}/sessions/${id}/stop/`, data),
  resumeSession: (id) => axiosInstance.post(`${BASE_URL}/sessions/${id}/resume/`),
  configureSessionCosts: (id, data) => axiosInstance.post(`${BASE_URL}/sessions/${id}/configure-costs/`, data),

  deployVersion: (id, payload) => axiosInstance.post(`${BASE_URL}/sessions/${id}/deploy-version/`, payload),

  getPositionsSummary: (params = {}, signal) => axiosInstance.get(`${BASE_URL}/positions/summary/`, { params, signal }),
  getOrdersSummary: (params = {}, signal) => axiosInstance.get(`${BASE_URL}/orders/summary/`, { params, signal }),
  getTradeAnalytics: (params = {}, signal) => axiosInstance.get(`${BASE_URL}/trades/analytics/`, { params, signal }),
  // Positions
  getPositions: (params = {}, signal) => axiosInstance.get(`${BASE_URL}/positions/`, { params, signal }),

  // Orders
  getOrders: (params = {}, signal) => axiosInstance.get(`${BASE_URL}/orders/`, { params, signal }),

  // Trades
  getTrades: (params = {}, signal) => axiosInstance.get(`${BASE_URL}/trades/`, { params, signal }),
};

export default paperApi;
