/**
 * Rules Engine API service - handles rule groups, rules, stop loss, targets
 */
import api from './api';

const RULES_URL = '/rules/';

// Time Rules
export const timeRuleApi = {
  get: async (strategyId) => {
    const response = await api.get(`${RULES_URL}time-rules/`, {
      params: { strategy: strategyId }
    });
    return response.data;
  },

  create: async (data) => {
    const response = await api.post(`${RULES_URL}time-rules/`, data);
    return response.data;
  },

  update: async (id, data) => {
    const response = await api.patch(`${RULES_URL}time-rules/${id}/`, data);
    return response.data;
  },
};

// Rule Groups
export const ruleGroupApi = {
  getByStrategy: async (strategyId, type = null) => {
    const params = { strategy_id: strategyId };
    if (type) params.type = type;
    const response = await api.get(`${RULES_URL}rule-groups/by_strategy/`, { params });
    return response.data;
  },

  create: async (data) => {
    const response = await api.post(`${RULES_URL}rule-groups/`, data);
    return response.data;
  },

  update: async (id, data) => {
    const response = await api.patch(`${RULES_URL}rule-groups/${id}/`, data);
    return response.data;
  },

  delete: async (id) => {
    await api.delete(`${RULES_URL}rule-groups/${id}/`);
  },
};

// Individual Rules
export const ruleApi = {
  create: async (data) => {
    const response = await api.post(`${RULES_URL}rules/`, data);
    return response.data;
  },

  update: async (id, data) => {
    const response = await api.patch(`${RULES_URL}rules/${id}/`, data);
    return response.data;
  },

  delete: async (id) => {
    await api.delete(`${RULES_URL}rules/${id}/`);
  },
};



// Special Event Filters
export const specialEventApi = {
  getByStrategy: async (strategyId) => {
    const response = await api.get(`${RULES_URL}event-filters/`, {
      params: { strategy: strategyId }
    });
    return response.data;
  },

  create: async (data) => {
    const response = await api.post(`${RULES_URL}event-filters/`, data);
    return response.data;
  },

  update: async (id, data) => {
    const response = await api.patch(`${RULES_URL}event-filters/${id}/`, data);
    return response.data;
  },
};

export default { timeRuleApi, ruleGroupApi, ruleApi, specialEventApi };
