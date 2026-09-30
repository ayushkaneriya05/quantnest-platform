import api from "./api";

const BASE_URL = "/live";

export const liveTradingApi = {
  getSessions: () => api.get(`${BASE_URL}/sessions/`),
  getSummary: () => api.get(`${BASE_URL}/sessions/summary/`),
  deployVersion: (id, payload) => api.post(`${BASE_URL}/allocations/${id}/deploy-version/`, payload),
  pauseSession: (id) => api.post(`${BASE_URL}/sessions/${id}/pause/`),
  resumeSession: (id) => api.post(`${BASE_URL}/sessions/${id}/resume/`),
  startSession: (id) => api.post(`${BASE_URL}/sessions/${id}/start/`),
  stopSession: (id, payload = {}) => api.post(`${BASE_URL}/sessions/${id}/stop/`, payload),
  syncSession: (id, payload = {}) => api.post(`${BASE_URL}/sessions/${id}/sync/`, payload),
  updateAllocation: (id, payload) => api.post(`${BASE_URL}/allocations/${id}/update-allocation/`, payload),
  getOrders: (params = {}) => api.get(`${BASE_URL}/orders/`, { params }),
  getOrdersSummary: (params = {}) => api.get(`${BASE_URL}/orders/summary/`, { params }),
  getPositions: (params = {}) => api.get(`${BASE_URL}/positions/`, { params }),
  getPositionsSummary: (params = {}) => api.get(`${BASE_URL}/positions/summary/`, { params }),
  getTrades: (params = {}) => api.get(`${BASE_URL}/trades/`, { params }),
  getTradesSummary: (params = {}) => api.get(`${BASE_URL}/trades/summary/`, { params }),
  getAllocations: (params = {}) => api.get(`${BASE_URL}/allocations/`, { params }),
  getLogs: (params = {}) => api.get(`${BASE_URL}/execution-logs/`, { params }),
  getSlippage: (params = {}) => api.get(`${BASE_URL}/slippage/`, { params }),
};

export default liveTradingApi;
