import api from "./api";

export const researchApi = {
  schema: () => api.get("/research/schema/"),
  sessions: (params) => api.get("/research/sessions/", { params }),
  createSession: (payload) => api.post("/research/sessions/", payload),
  session: (id, config) => api.get(`/research/sessions/${id}/`, config),
  updateSession: (id, payload) => api.patch(`/research/sessions/${id}/`, payload),
  deleteSession: (id) => api.delete(`/research/sessions/${id}/`),
  runs: (session, params = {}) => api.get("/research/runs/", { params: { ...(session ? { session } : {}), ...params } }),
  run: (id) => api.get(`/research/runs/${id}/`),
  start: (data) => api.post("/research/runs/", data),
  cancel: (id) => api.post(`/research/runs/${id}/cancel/`),
  proposeAction: (id, action_type, payload = {}) => api.post(`/research/runs/${id}/propose-action/`, { action_type, payload }),
  confirmAction: (id) => api.post(`/research/actions/${id}/confirm/`),
};
