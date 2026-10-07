import api from "./api";

export const journalApi = {
  summary: (params, signal) => api.get("/journal/entries/summary/", { params, signal }),
  create: (payload) => api.post("/journal/entries/", payload),
  update: (id, payload) => api.patch(`/journal/entries/${id}/`, payload),
  delete: (id) => api.delete(`/journal/entries/${id}/`),
};
