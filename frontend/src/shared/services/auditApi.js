import api from "./api";

export const auditApi = {
  getLogs: (params, signal) => api.get("/audit/logs/", { params, signal }),
  getStats: (params, signal) => api.get("/audit/logs/stats/", { params, signal }),
};
