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

// Execution Routes
export const executionRoutesApi = {
  createOrUpdate: async (watchlistInstrumentId, routeId, data) => {
    if (routeId) {
      const response = await api.patch(`${INSTRUMENTS_URL}execution-routes/${routeId}/`, data);
      return response.data;
    } else {
      const payload = {
        watchlist_instrument: watchlistInstrumentId,
        ...data
      };
      const response = await api.post(`${INSTRUMENTS_URL}execution-routes/`, payload);
      return response.data;
    }
  },
  
  getByWatchlistInstrument: async (watchlistInstrumentId) => {
    const response = await api.get(`${INSTRUMENTS_URL}execution-routes/`, {
      params: { watchlist_instrument: watchlistInstrumentId }
    });
    const data = response.data;
    return Array.isArray(data) ? data : (data?.results || []);
  },
  
  delete: async (id) => {
    await api.delete(`${INSTRUMENTS_URL}execution-routes/${id}/`);
  }
};

export default instrumentsApi;
