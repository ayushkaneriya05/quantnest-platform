/**
 * Instruments API service - handles instrument and option lookups
 */
import api from './api';

const INSTRUMENTS_URL = '/instruments/';

// Instruments
export const instrumentsApi = {
  // Search instruments
  search: async (params = {}) => {
    const response = await api.get(`${INSTRUMENTS_URL}instruments/search/`, { params });
    const data = response.data;
    // Handle both direct array and paginated { results: [] } responses
    return Array.isArray(data) ? data : (data?.results || []);
  },

  // Get all instruments
  getAll: async (params = {}) => {
    const response = await api.get(`${INSTRUMENTS_URL}instruments/`, { params });
    return response.data;
  },

  // Get by ID
  getById: async (id) => {
    const response = await api.get(`${INSTRUMENTS_URL}instruments/${id}/`);
    return response.data;
  },
};



// Watchlist
export const watchlistApi = {
  getByStrategy: async (strategyId) => {
    const response = await api.get(`${INSTRUMENTS_URL}watchlist/`, {
      params: { strategy: strategyId }
    });
    return response.data;
  },

  add: async (strategyId, instrumentId) => {
    const response = await api.post(`${INSTRUMENTS_URL}watchlist/`, {
      strategy: strategyId,
      instrument: instrumentId
    });
    return response.data;
  },

  remove: async (id) => {
    await api.delete(`${INSTRUMENTS_URL}watchlist/${id}/`);
  },
};

export default instrumentsApi;
