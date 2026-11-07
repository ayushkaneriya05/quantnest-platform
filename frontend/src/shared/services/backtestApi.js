/**
 * Backtesting API Service
 */
import axiosInstance from './api';

const BASE_URL = '/backtest';

const normalizeRunPayload = (data) => {
  const payload = { ...data };
  if (payload.charge_profile === "") {
    payload.charge_profile = null;
  }
  return payload;
};

export const backtestApi = {
  // Backtest Runs
  getRuns: (params = {}, signal) => axiosInstance.get(`${BASE_URL}/runs/`, { params, signal }),
  getSummary: (params = {}, signal) => axiosInstance.get(`${BASE_URL}/runs/summary/`, { params, signal }),
  getRun: (id) => axiosInstance.get(`${BASE_URL}/runs/${id}/`),
  createRun: (data) => axiosInstance.post(`${BASE_URL}/runs/`, normalizeRunPayload(data)),
  // The first derivative preview can acquire uncached underlying history and
  // expired listings. Subsequent previews reuse those shared data ranges.
  estimateRun: (data) => axiosInstance.post(`${BASE_URL}/runs/estimate/`, normalizeRunPayload(data), { timeout: 180000 }),
  estimateRerun: (id) => axiosInstance.post(`${BASE_URL}/runs/${id}/estimate-rerun/`, {}, { timeout: 180000 }),
  deleteRun: (id) => axiosInstance.delete(`${BASE_URL}/runs/${id}/`),

  // Run actions
  startRun: (id) => axiosInstance.post(`${BASE_URL}/runs/${id}/start/`),
  rerunRun: (id, estimateToken, key = crypto.randomUUID()) => axiosInstance.post(`${BASE_URL}/runs/${id}/rerun/`, {estimate_token: estimateToken}, {headers:{'Idempotency-Key':key}}),
  cancelRun: (id) => axiosInstance.post(`${BASE_URL}/runs/${id}/cancel/`),

  // Run data
  getRunTrades: (id, params, signal) => axiosInstance.get(`${BASE_URL}/runs/${id}/trades/`, { params, signal }),
  getRunMetrics: (id) => axiosInstance.get(`${BASE_URL}/runs/${id}/metrics/`),
  getRunEquityCurve: (id) => axiosInstance.get(`${BASE_URL}/runs/${id}/equity_curve/`),

  // Monte Carlo
  getMonteCarloRuns: (params = {}, signal) => axiosInstance.get(`${BASE_URL}/montecarlo/`, { params, signal }),
  getMonteCarlo: (id) => axiosInstance.get(`${BASE_URL}/montecarlo/${id}/`),
  createMonteCarlo: (data) => axiosInstance.post(`${BASE_URL}/montecarlo/`, data),
  startMonteCarlo: (id) => axiosInstance.post(`${BASE_URL}/montecarlo/${id}/start/`),
  cancelMonteCarlo: (id) => axiosInstance.post(`${BASE_URL}/montecarlo/${id}/cancel/`),
  getMonteCarloResults: (id) => axiosInstance.get(`${BASE_URL}/montecarlo/${id}/results/`),
};

export default backtestApi;
