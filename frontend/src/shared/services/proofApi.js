import api from "@/shared/services/api";

export const proofApi = {
  getTradingProofs: () => api.get("/proofs/trading/"),
  createTradingProof: (payload) => api.post("/proofs/trading/", payload),
  getBacktestProofs: () => api.get("/proofs/backtests/"),
  createBacktestProof: (payload) => api.post("/proofs/backtests/", payload),
  getStrategyVerifications: () => api.get("/proofs/strategies/"),
  createStrategyVerification: (payload) => api.post("/proofs/strategies/", payload),
};

