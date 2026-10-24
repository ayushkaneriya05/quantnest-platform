import api from "./api";

const BASE_URL = "/brokers";

export const brokersApi = {
  getCatalog: () => api.get(`${BASE_URL}/credentials/catalog/`),
  configureBroker: (payload) => api.post(`${BASE_URL}/credentials/configure/`, payload),
  connectBroker: (id) => api.post(`${BASE_URL}/credentials/${id}/connect/`),
  disconnectCredential: (id) => api.post(`${BASE_URL}/credentials/${id}/disconnect/`),
  getProfile: (id) => api.get(`${BASE_URL}/credentials/${id}/profile/`),
  getFunds: (id) => api.get(`${BASE_URL}/credentials/${id}/funds/`),
  getLogs: (params) => api.get(`${BASE_URL}/logs/`, { params }),

  // Charge Profiles
  getChargeProfiles: () => api.get(`${BASE_URL}/charge-profiles/`),
  createChargeProfile: (payload) => api.post(`${BASE_URL}/charge-profiles/`, payload),
  updateChargeProfile: (id, payload) => api.patch(`${BASE_URL}/charge-profiles/${id}/`, payload),
  deleteChargeProfile: (id) => api.delete(`${BASE_URL}/charge-profiles/${id}/`),
  setDefaultChargeProfile: (id) => api.post(`${BASE_URL}/charge-profiles/${id}/set-default/`),
};

export default brokersApi;
