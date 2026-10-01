import api from "./api";

export const notificationApi = {
  getNotifications: () => api.get("/notifications/items/"),
  getSummary: () => api.get("/notifications/items/summary/"),
  markRead: (id) => api.post(`/notifications/items/${id}/mark-read/`),
  markAllRead: () => api.post("/notifications/items/mark-all-read/"),
  deleteNotification: (id) => api.delete(`/notifications/items/${id}/`),
  deleteRead: () => api.delete("/notifications/items/delete-read/"),
  getPreferences: () => api.get("/notifications/preferences/"),
  updatePreference: (id, payload) => api.patch(`/notifications/preferences/${id}/`, payload),
};

export default notificationApi;
