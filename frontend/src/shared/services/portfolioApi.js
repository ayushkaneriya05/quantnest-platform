/**
 * Portfolio API Service
 */
import axiosInstance from './api';

const BASE_URL = '/portfolio';

export const portfolioApi = {
  // Portfolio
  getMyPortfolio: () => axiosInstance.get(`${BASE_URL}/portfolios/me/`),
  getPortfolio: (id) => axiosInstance.get(`${BASE_URL}/portfolios/${id}/`),
  updatePortfolio: (id, data) => axiosInstance.patch(`${BASE_URL}/portfolios/${id}/`, data),
  deposit: (id, amount, notes = '') => 
    axiosInstance.post(`${BASE_URL}/portfolios/${id}/deposit/`, { amount, notes }),
  withdraw: (id, amount, notes = '') => 
    axiosInstance.post(`${BASE_URL}/portfolios/${id}/withdraw/`, { amount, notes }),
  
  // Allocations
  getAllocations: () => axiosInstance.get(`${BASE_URL}/allocations/`),
  getAllocationByStrategy: (strategyId) => 
    axiosInstance.get(`${BASE_URL}/allocations/by_strategy/?strategy_id=${strategyId}`),
  createAllocation: (data) => axiosInstance.post(`${BASE_URL}/allocations/`, data),
  updateAllocation: (id, data) => axiosInstance.patch(`${BASE_URL}/allocations/${id}/`, data),
  deleteAllocation: (id) => axiosInstance.delete(`${BASE_URL}/allocations/${id}/`),
  
  // Transactions
  getTransactions: () => axiosInstance.get(`${BASE_URL}/transactions/`),
  
  // Exposure
  getLatestExposure: () => axiosInstance.get(`${BASE_URL}/exposure/latest/`),
  getExposureHistory: () => axiosInstance.get(`${BASE_URL}/exposure/`),
  
  // Performance
  getPerformanceHistory: (startDate, endDate) => {
    let url = `${BASE_URL}/performance/range/?`;
    if (startDate) url += `start=${startDate}&`;
    if (endDate) url += `end=${endDate}`;
    return axiosInstance.get(url);
  },
  getDailyPerformance: () => axiosInstance.get(`${BASE_URL}/performance/`),
};

export const riskApi = {
  // Risk Profile
  getMyProfile: () => axiosInstance.get('/risk/profile/me/'),
  updateProfile: (data) => axiosInstance.patch('/risk/profile/me/', data),
  
  // Position Sizing
  getSizingRules: (params) => axiosInstance.get('/risk/sizing/', { params }),
  getSizingRule: (id) => axiosInstance.get(`/risk/sizing/${id}/`),
  createSizingRule: (data) => axiosInstance.post('/risk/sizing/', data),
  updateSizingRule: (id, data) => axiosInstance.patch(`/risk/sizing/${id}/`, data),
  
  // Halt Conditions
  getHaltConditions: () => axiosInstance.get('/risk/halt/'),
  createHaltCondition: (data) => axiosInstance.post('/risk/halt/', data),
  updateHaltCondition: (id, data) => axiosInstance.patch(`/risk/halt/${id}/`, data),
  deleteHaltCondition: (id) => axiosInstance.delete(`/risk/halt/${id}/`),
  
  // Auto-disable
  getAutoDisableRules: () => axiosInstance.get('/risk/auto-disable/'),
  createAutoDisableRule: (data) => axiosInstance.post('/risk/auto-disable/', data),
  updateAutoDisableRule: (id, data) => axiosInstance.patch(`/risk/auto-disable/${id}/`, data),
  deleteAutoDisableRule: (id) => axiosInstance.delete(`/risk/auto-disable/${id}/`),
  
  // Violations
  getViolations: () => axiosInstance.get('/risk/violations/'),
  resolveViolation: (id, notes = '') => 
    axiosInstance.post(`/risk/violations/${id}/resolve/`, { notes }),
};

export default { portfolioApi, riskApi };
