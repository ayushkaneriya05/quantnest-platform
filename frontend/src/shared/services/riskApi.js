import api from "./api";

export const riskApi = {
  getSizingRules: (params) => api.get("/risk/sizing/", { params }),
  createSizingRule: (data) => api.post("/risk/sizing/", data),
  updateSizingRule: (id, data) => api.patch(`/risk/sizing/${id}/`, data),
  getAutoDisableRules: (params) => api.get("/risk/auto-disable/", { params }),
  createAutoDisableRule: (data) => api.post("/risk/auto-disable/", data),
  updateAutoDisableRule: (id, data) => api.patch(`/risk/auto-disable/${id}/`, data),
  deleteAutoDisableRule: (id) => api.delete(`/risk/auto-disable/${id}/`),
};
