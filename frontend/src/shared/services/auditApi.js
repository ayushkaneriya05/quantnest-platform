import api from "./api";

export const auditApi = {
  // ── Audit Logs ──
  getLogs: (params = {}) => api.get("/audit/logs/", { params }),
  getLogDetail: (id) => api.get(`/audit/logs/${id}/`),
  getStats: () => api.get("/audit/logs/stats/"),
  exportLogs: (params = {}) => api.get("/audit/logs/export/", { params }),

  // ── Strategy Approvals ──
  getApprovals: (params = {}) => api.get("/audit/approvals/", { params }),
  getApprovalDetail: (id) => api.get(`/audit/approvals/${id}/`),
  requestApproval: (payload) => api.post("/audit/approvals/", payload),
  approveRequest: (id, comments = "") =>
    api.post(`/audit/approvals/${id}/approve/`, { comments }),
  rejectRequest: (id, comments = "") =>
    api.post(`/audit/approvals/${id}/reject/`, { comments }),
  runCompliance: (id) =>
    api.post(`/audit/approvals/${id}/run-compliance/`),

  // ── Compliance Checks ──
  getComplianceChecks: (params = {}) =>
    api.get("/audit/compliance/", { params }),
  getComplianceSummary: () => api.get("/audit/compliance/summary/"),
};

export default auditApi;
