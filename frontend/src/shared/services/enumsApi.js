/**
 * Enums API service - fetches all enum choices from the backend
 */
import api from './api';

const COMMON_URL = '/common/';

export const enumsApi = {
  /**
   * Fetch all enum choices from backend.
   * Returns { EnumName: [{value, label}, ...], ... }
   */
  getAll: async () => {
    const response = await api.get(`${COMMON_URL}enums/`);
    return response.data;
  },
};

export default enumsApi;
