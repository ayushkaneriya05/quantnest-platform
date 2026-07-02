import api from "./api";

export const analyticsSuiteApi = {
  refreshSnapshots: (payload = {}) => api.post("/analytics/snapshots/refresh/", payload),
  getSnapshots: () => api.get("/analytics/snapshots/"),
  getDailyReports: () => api.get("/analytics/daily-reports/"),
  getAnalyticsDashboard: () => api.get("/analytics/daily-reports/dashboard/"),
  createComparison: (payload) => api.post("/analytics/comparisons/", payload),
  getComparisons: () => api.get("/analytics/comparisons/"),
  getJournalEntries: () => api.get("/journal/entries/"),
  getJournalSummary: () => api.get("/journal/entries/summary/"),
  bootstrapJournalEntries: () => api.post("/journal/entries/bootstrap/"),
  createJournalEntry: (payload) => api.post("/journal/entries/", payload),
  updateJournalEntry: (id, payload) => api.patch(`/journal/entries/${id}/`, payload),
  getMistakeTags: () => api.get("/journal/mistake-tags/"),
  getInsights: () => api.get("/journal/insights/"),
  generateInsights: () => api.post("/journal/insights/generate/"),
  createInsight: (payload) => api.post("/journal/insights/", payload),
  getNotifications: () => api.get("/notifications/items/"),
  getNotificationSummary: () => api.get("/notifications/items/summary/"),
  markNotificationRead: (id) => api.post(`/notifications/items/${id}/mark-read/`),
  markAllNotificationsRead: () => api.post("/notifications/items/mark-all-read/"),
  deleteNotification: (id) => api.delete(`/notifications/items/${id}/`),
  deleteReadNotifications: () => api.delete("/notifications/items/delete-read/"),
  getNotificationPrefs: () => api.get("/notifications/preferences/"),
  updateNotificationPref: (id, payload) => api.patch(`/notifications/preferences/${id}/`, payload),
  getSummarySchedule: () => api.get("/notifications/summary-schedule/"),
  updateSummarySchedule: (payload, id = 1) => api.patch(`/notifications/summary-schedule/${id}/`, payload),
};

export default analyticsSuiteApi;
