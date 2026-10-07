/**
 * Portfolio API Service
 */
import axiosInstance from "./api";

const BASE_URL = "/portfolio";

export const portfolioApi = {
  // Portfolio
  getMyPortfolio: () => axiosInstance.get(`${BASE_URL}/portfolios/me/`),
  getPortfolio: (id) => axiosInstance.get(`${BASE_URL}/portfolios/${id}/`),
  updatePortfolio: (id, data) =>
    axiosInstance.patch(`${BASE_URL}/portfolios/${id}/`, data),
  deposit: (id, amount, notes = "") =>
    axiosInstance.post(`${BASE_URL}/portfolios/${id}/deposit/`, {
      amount,
      notes,
    }),
  withdraw: (id, amount, notes = "") =>
    axiosInstance.post(`${BASE_URL}/portfolios/${id}/withdraw/`, {
      amount,
      notes,
    }),

  // Allocations
  getAllocations: () => axiosInstance.get(`${BASE_URL}/allocations/`),
  getAllocationByStrategy: (strategyId) =>
    axiosInstance.get(
      `${BASE_URL}/allocations/by_strategy/?strategy_id=${strategyId}`,
    ),
  createAllocation: (data) =>
    axiosInstance.post(`${BASE_URL}/allocations/`, data),
  updateAllocation: (id, data) =>
    axiosInstance.patch(`${BASE_URL}/allocations/${id}/`, data),
  deleteAllocation: (id) =>
    axiosInstance.delete(`${BASE_URL}/allocations/${id}/`),
  confirmDeleteAllocation: (id, deletePaperAccount = false) =>
    axiosInstance.post(`${BASE_URL}/allocations/${id}/confirm_delete/`, {
      delete_paper_account: deletePaperAccount,
    }),

  // Transactions
  getTransactions: () => axiosInstance.get(`${BASE_URL}/transactions/`),

  // Performance
  getPerformanceHistory: (startDate, endDate) => {
    let url = `${BASE_URL}/performance/range/?`;
    if (startDate) url += `start=${startDate}&`;
    if (endDate) url += `end=${endDate}`;
    return axiosInstance.get(url);
  },
  getDailyPerformance: () => axiosInstance.get(`${BASE_URL}/performance/`),
  getPortfolioPerformance: () =>
    axiosInstance.get(`${BASE_URL}/portfolios/performance/`),

  // Paper account support from portfolio allocation
  createPaperAccount: (allocationId, name, executionCosts = {}) =>
    axiosInstance.post(`${BASE_URL}/portfolios/create_paper_account/`, {
      allocation_id: allocationId,
      ...(name ? { name } : {}),
      slippage_pct: executionCosts.slippage_pct ?? 0,
      charge_profile: executionCosts.charge_profile || null,
      include_charges: executionCosts.include_charges ?? true,
    }),
};

export const riskApi = {
  // Position Sizing
  getSizingRules: (params) => axiosInstance.get("/risk/sizing/", { params }),
  getSizingRule: (id) => axiosInstance.get(`/risk/sizing/${id}/`),
  createSizingRule: (data) => axiosInstance.post("/risk/sizing/", data),
  updateSizingRule: (id, data) =>
    axiosInstance.patch(`/risk/sizing/${id}/`, data),

  // Auto-disable
  getAutoDisableRules: (params) => axiosInstance.get("/risk/auto-disable/", { params }),
  createAutoDisableRule: (data) =>
    axiosInstance.post("/risk/auto-disable/", data),
  updateAutoDisableRule: (id, data) =>
    axiosInstance.patch(`/risk/auto-disable/${id}/`, data),
  deleteAutoDisableRule: (id) =>
    axiosInstance.delete(`/risk/auto-disable/${id}/`),

};

export default { portfolioApi, riskApi };
