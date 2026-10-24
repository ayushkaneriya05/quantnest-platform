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

  // Transactions
  getTransactions: () => axiosInstance.get(`${BASE_URL}/transactions/`),

};
