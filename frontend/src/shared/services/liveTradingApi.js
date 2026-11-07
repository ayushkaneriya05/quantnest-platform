import api from "./api";

const BASE_URL = "/live";

export const liveTradingApi = {
  getSessions: (params = {}, signal) => api.get(`${BASE_URL}/sessions/`, { params, signal }),
  getSummary: (signal) => api.get(`${BASE_URL}/sessions/summary/`, { signal }),
  deployVersion: (id, payload) => api.post(`${BASE_URL}/allocations/${id}/deploy-version/`, payload),
  pauseSession: (id) => api.post(`${BASE_URL}/sessions/${id}/pause/`),
  resumeSession: (id) => api.post(`${BASE_URL}/sessions/${id}/resume/`),
  stopSession: (id, payload = {}) => api.post(`${BASE_URL}/sessions/${id}/stop/`, payload),
  syncSession: (id, payload = {}) => api.post(`${BASE_URL}/sessions/${id}/sync/`, payload),
  updateAllocation: (id, payload) => api.post(`${BASE_URL}/allocations/${id}/update-allocation/`, payload),
  getOrders: (params = {}, signal) => api.get(`${BASE_URL}/orders/`, { params, signal }),
  getOrdersSummary: (params = {}, signal) => api.get(`${BASE_URL}/orders/summary/`, { params, signal }),
  getPositions: (params = {}, signal) => api.get(`${BASE_URL}/positions/`, { params, signal }),
  getPositionsSummary: (params = {}, signal) => api.get(`${BASE_URL}/positions/summary/`, { params, signal }),
  getTrades: (params = {}, signal) => api.get(`${BASE_URL}/trades/`, { params, signal }),
  getTradesSummary: (params = {}, signal) => api.get(`${BASE_URL}/trades/summary/`, { params, signal }),
  getLogs: (params = {}, signal) => api.get(`${BASE_URL}/execution-logs/`, { params, signal }),
  getSlippage: (params = {}, signal) => api.get(`${BASE_URL}/slippage/`, { params, signal }),
};

export default liveTradingApi;
