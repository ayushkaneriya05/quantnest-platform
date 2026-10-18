/**
 * Portfolio API Service
 */
import axiosInstance from "./api";

const BASE_URL = "/paper";

export const portfolioApi = {
  // Portfolio
  getMyPortfolio: () => axiosInstance.get(`${BASE_URL}/portfolios/me/`),
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
