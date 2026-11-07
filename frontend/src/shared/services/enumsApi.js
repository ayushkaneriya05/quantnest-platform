/**
 * Enums API service - fetches all enum choices from the backend
 */
import api from './api';

const COMMON_URL = '/common/';
let pendingRequest;

export const enumsApi = {
  /**
   * Fetch all enum choices from backend.
   * Returns { EnumName: [{value, label}, ...], ... }
   */
  getAll: () => {
    // Share overlapping loads (including provider remounts). EnumsProvider owns
    // the resolved cache; clearing this promise allows an explicit refresh.
    pendingRequest ??= api.get(`${COMMON_URL}enums/`, { publicRequest: true })
      .then((response) => response.data)
      .finally(() => { pendingRequest = undefined; });
    return pendingRequest;
  },
};

export default enumsApi;
