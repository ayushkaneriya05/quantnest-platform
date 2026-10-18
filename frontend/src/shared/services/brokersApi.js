import api from "./api";

const BASE_URL = "/brokers";

export const brokersApi = {
  getCatalog: () => api.get(`${BASE_URL}/credentials/catalog/`),
  connectBroker: (brokerName) =>
    api.post(`${BASE_URL}/credentials/connect/`, { broker_name: brokerName }),
  disconnectCredential: (id) => api.post(`${BASE_URL}/credentials/${id}/disconnect/`),
  createSession: (id, payload = {}) => api.post(`${BASE_URL}/credentials/${id}/create-session/`, payload),
  getProfile: (id) => api.get(`${BASE_URL}/credentials/${id}/profile/`),
  getFunds: (id) => api.get(`${BASE_URL}/credentials/${id}/funds/`),
  getSessions: () => api.get(`${BASE_URL}/sessions/`),
  getLogs: (params) => api.get(`${BASE_URL}/logs/`, { params }),

  // Charge Profiles
  getChargeProfiles: () => api.get(`${BASE_URL}/charge-profiles/`),
  createChargeProfile: (payload) => api.post(`${BASE_URL}/charge-profiles/`, payload),
  updateChargeProfile: (id, payload) => api.patch(`${BASE_URL}/charge-profiles/${id}/`, payload),
  deleteChargeProfile: (id) => api.delete(`${BASE_URL}/charge-profiles/${id}/`),
  setDefaultChargeProfile: (id) => api.post(`${BASE_URL}/charge-profiles/${id}/set-default/`),
};

export default brokersApi;
