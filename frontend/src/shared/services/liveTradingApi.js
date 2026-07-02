import api from "./api";

const BASE_URL = "/live";

export const liveTradingApi = {
  getSessions: () => api.get(`${BASE_URL}/sessions/`),
  getSummary: () => api.get(`${BASE_URL}/sessions/summary/`),
  deployStrategy: (payload) => api.post(`${BASE_URL}/sessions/deploy/`, payload),
  pauseSession: (id) => api.post(`${BASE_URL}/sessions/${id}/pause/`),
  resumeSession: (id) => api.post(`${BASE_URL}/sessions/${id}/resume/`),
  stopSession: (id, payload = {}) => api.post(`${BASE_URL}/sessions/${id}/stop/`, payload),
  stopAllSessions: (payload = {}) => api.post(`${BASE_URL}/sessions/stop-all/`, payload),
  runSessionOnce: (id, payload = {}) => api.post(`${BASE_URL}/sessions/${id}/run-once/`, payload),
  syncSession: (id, payload = {}) => api.post(`${BASE_URL}/sessions/${id}/sync/`, payload),
  updateAllocation: (id, payload) => api.post(`${BASE_URL}/sessions/${id}/update-allocation/`, payload),
  getOrders: () => api.get(`${BASE_URL}/orders/`),
  cancelOrder: (id) => api.post(`${BASE_URL}/orders/${id}/cancel/`),
  getPositions: () => api.get(`${BASE_URL}/positions/`),
  getAllocations: (params = {}) => api.get(`${BASE_URL}/allocations/`, { params }),
  getLogs: () => api.get(`${BASE_URL}/execution-logs/`),
  getSlippage: () => api.get(`${BASE_URL}/slippage/`),
};

export default liveTradingApi;
