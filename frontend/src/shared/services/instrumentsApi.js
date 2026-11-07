/**
 * Instruments API service - handles instrument and option lookups
 */
import api from './api';

const INSTRUMENTS_URL = '/instruments/';

// Instruments
export const instrumentsApi = {
  selectionPreview: async (underlyingId, policy) => {
    const response = await api.post(`${INSTRUMENTS_URL}instruments/selection-preview/`, { underlying_id: underlyingId, policy });
    return response.data;
  },
  // Search instruments
  search: async (params = {}, config = {}) => {
    const response = await api.get(`${INSTRUMENTS_URL}instruments/search/`, { ...config, params });
    return response.data;
  },


};

export async function searchTerminalInstruments(params, config = {}) {
  const response = await api.get("/trading/instruments/search/", { ...config, params });
  return response.data;
}



export default instrumentsApi;
