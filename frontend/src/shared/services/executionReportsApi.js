import api from "./api";

export const executionReportsApi = {
  report: (params, signal) => api.get("/analytics/reports/", { params, signal }),
  trades: (params, signal) => api.get("/analytics/reports/trades/", { params, signal }),
  export: (params) => api.get("/analytics/reports/export/", { params }),
  researchContext: (payload) => api.post("/analytics/reports/research-context/", payload),
};
