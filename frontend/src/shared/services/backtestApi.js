/**
 * Backtesting API Service
 */
import axiosInstance from './api';

const BASE_URL = '/backtest';

const normalizeRunPayload = (data) => {
  const payload = { ...data };
  if (payload.charge_profile_id !== undefined && payload.charge_profile === undefined) {
    payload.charge_profile = payload.charge_profile_id;
  }
  delete payload.charge_profile_id;
  if (payload.charge_profile === "") {
    payload.charge_profile = null;
  }
  return payload;
};

export const backtestApi = {
  // Backtest Runs
  getRuns: () => axiosInstance.get(`${BASE_URL}/runs/`),
  getRun: (id) => axiosInstance.get(`${BASE_URL}/runs/${id}/`),
  createRun: (data) => axiosInstance.post(`${BASE_URL}/runs/`, normalizeRunPayload(data)),
  updateRun: (id, data) => axiosInstance.patch(`${BASE_URL}/runs/${id}/`, normalizeRunPayload(data)),
  deleteRun: (id) => axiosInstance.delete(`${BASE_URL}/runs/${id}/`),
  
  // Run actions
  startRun: (id) => axiosInstance.post(`${BASE_URL}/runs/${id}/start/`),
  rerunRun: (id) => axiosInstance.post(`${BASE_URL}/runs/${id}/rerun/`),
  cancelRun: (id) => axiosInstance.post(`${BASE_URL}/runs/${id}/cancel/`),
  
  // Run data
  getRunTrades: (id, params) => axiosInstance.get(`${BASE_URL}/runs/${id}/trades/`, { params }),
  getRunMetrics: (id) => axiosInstance.get(`${BASE_URL}/runs/${id}/metrics/`),
  getRunEquityCurve: (id) => axiosInstance.get(`${BASE_URL}/runs/${id}/equity_curve/`),
  getRunChargesTimeline: (id) => axiosInstance.get(`${BASE_URL}/runs/${id}/charges_timeline/`),
  getRunAnalytics: (id) => axiosInstance.get(`${BASE_URL}/runs/${id}/analytics/`),
  
  // Monte Carlo
  getMonteCarloRuns: () => axiosInstance.get(`${BASE_URL}/montecarlo/`),
  createMonteCarlo: (data) => axiosInstance.post(`${BASE_URL}/montecarlo/`, data),
  startMonteCarlo: (id) => axiosInstance.post(`${BASE_URL}/montecarlo/${id}/start/`),
  getMonteCarloResults: (id) => axiosInstance.get(`${BASE_URL}/montecarlo/${id}/results/`),
};

export default backtestApi;
