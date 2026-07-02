import api from "./api";

const BASE_URL = "/brokers";

export const brokersApi = {
  getCatalog: () => api.get(`${BASE_URL}/credentials/catalog/`),
  getCredentials: () => api.get(`${BASE_URL}/credentials/`),
  connectBroker: (brokerName) =>
    api.post(`${BASE_URL}/credentials/connect/`, { broker_name: brokerName }),
  createCredential: (payload) => api.post(`${BASE_URL}/credentials/`, payload),
  updateCredential: (id, payload) => api.patch(`${BASE_URL}/credentials/${id}/`, payload),
  verifyCredential: (id) => api.post(`${BASE_URL}/credentials/${id}/verify/`),
  activateCredential: (id) => api.post(`${BASE_URL}/credentials/${id}/activate/`),
  disconnectCredential: (id) => api.post(`${BASE_URL}/credentials/${id}/disconnect/`),
  createSession: (id, payload = {}) => api.post(`${BASE_URL}/credentials/${id}/create-session/`, payload),
  getAuthUrl: (id) => api.get(`${BASE_URL}/credentials/${id}/auth-url/`),
  exchangeAuthCode: (id, authCode) =>
    api.post(`${BASE_URL}/credentials/${id}/exchange-auth-code/`, {
      auth_code: authCode,
    }),
  getProfile: (id) => api.get(`${BASE_URL}/credentials/${id}/profile/`),
  getFunds: (id) => api.get(`${BASE_URL}/credentials/${id}/funds/`),
  getFundsSummary: (id) => api.get(`${BASE_URL}/credentials/${id}/funds-summary/`),
  getOrderbook: (id) => api.get(`${BASE_URL}/credentials/${id}/orderbook/`),
  getSessions: () => api.get(`${BASE_URL}/sessions/`),
  getSettings: () => api.get(`${BASE_URL}/settings/`),
  updateSettings: (id, payload) => api.patch(`${BASE_URL}/settings/${id}/`, payload),
  getLogs: (params) => api.get(`${BASE_URL}/logs/`, { params }),
};

export default brokersApi;
