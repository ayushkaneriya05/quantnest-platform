/**
 * Backtesting API Service
 */
import axiosInstance from './api';

const BASE_URL = '/backtest';

export const backtestApi = {
  // Backtest Runs
  getRuns: () => axiosInstance.get(`${BASE_URL}/runs/`),
  getRun: (id) => axiosInstance.get(`${BASE_URL}/runs/${id}/`),
  createRun: (data) => axiosInstance.post(`${BASE_URL}/runs/`, data),
  updateRun: (id, data) => axiosInstance.patch(`${BASE_URL}/runs/${id}/`, data),
  deleteRun: (id) => axiosInstance.delete(`${BASE_URL}/runs/${id}/`),
  
  // Run actions
  startRun: (id) => axiosInstance.post(`${BASE_URL}/runs/${id}/start/`),
  rerunRun: (id) => axiosInstance.post(`${BASE_URL}/runs/${id}/rerun/`),
  cancelRun: (id) => axiosInstance.post(`${BASE_URL}/runs/${id}/cancel/`),
  
  // Run data
  getRunTrades: (id) => axiosInstance.get(`${BASE_URL}/runs/${id}/trades/`),
  getRunMetrics: (id) => axiosInstance.get(`${BASE_URL}/runs/${id}/metrics/`),
  getRunEquityCurve: (id) => axiosInstance.get(`${BASE_URL}/runs/${id}/equity_curve/`),
  getRunAnalytics: (id) => axiosInstance.get(`${BASE_URL}/runs/${id}/analytics/`),
  
  // Monte Carlo
  getMonteCarloRuns: () => axiosInstance.get(`${BASE_URL}/montecarlo/`),
  createMonteCarlo: (data) => axiosInstance.post(`${BASE_URL}/montecarlo/`, data),
  startMonteCarlo: (id) => axiosInstance.post(`${BASE_URL}/montecarlo/${id}/start/`),
  getMonteCarloResults: (id) => axiosInstance.get(`${BASE_URL}/montecarlo/${id}/results/`),
};

export default backtestApi;
