/**
 * Strategy API service - handles all strategy-related API calls
 */
import api from './api';

const STRATEGIES_URL = '/strategies/';

// Strategy CRUD
export const strategyApi = {
  // Get all strategies
  getAll: async () => {
    const response = await api.get(`${STRATEGIES_URL}strategies/`);
    return response.data;
  },

  // Get single strategy
  getById: async (id) => {
    const response = await api.get(`${STRATEGIES_URL}strategies/${id}/`);
    return response.data;
  },

  // Create new strategy
  create: async (data) => {
    const response = await api.post(`${STRATEGIES_URL}strategies/`, data);
    return response.data;
  },

  // Update strategy
  update: async (id, data) => {
    const response = await api.patch(`${STRATEGIES_URL}strategies/${id}/`, data);
    return response.data;
  },

  // Delete strategy
  delete: async (id) => {
    await api.delete(`${STRATEGIES_URL}strategies/${id}/`);
  },

  // Clone strategy
  clone: async (id) => {
    const response = await api.post(`${STRATEGIES_URL}strategies/${id}/clone/`);
    return response.data;
  },

  // Activate strategy
  activate: async (id) => {
    const response = await api.post(`${STRATEGIES_URL}strategies/${id}/activate/`);
    return response.data;
  },

  // Archive strategy
  archive: async (id) => {
    const response = await api.post(`${STRATEGIES_URL}strategies/${id}/archive/`);
    return response.data;
  },

  // Halt and Archive strategy
  haltAndArchive: async (id) => {
    const response = await api.post(`${STRATEGIES_URL}strategies/${id}/halt-and-archive/`);
    return response.data;
  },

  // Pause active strategy
  pause: async (id) => {
    const response = await api.post(`${STRATEGIES_URL}strategies/${id}/pause/`);
    return response.data;
  },

  // Unarchive strategy back to draft
  unarchive: async (id) => {
    const response = await api.post(`${STRATEGIES_URL}strategies/${id}/unarchive/`);
    return response.data;
  },

  // Get versions
  getVersions: async (id) => {
    const response = await api.get(`${STRATEGIES_URL}strategies/${id}/versions/`);
    return response.data;
  },

  // Create version snapshot
  createVersion: async (id, notes) => {
    const response = await api.post(`${STRATEGIES_URL}strategies/${id}/create-version/`, { notes });
    return response.data;
  },

  // Rollback to version
  rollback: async (id, versionId) => {
    const response = await api.post(`${STRATEGIES_URL}strategies/${id}/rollback/`, { version_id: versionId });
    return response.data;
  },

  // Deployment
  deployPaper: async (id, options = {}) => {
    const payload = {};
    if (options?.versionId) payload.version_id = options.versionId;
    if (options?.allocationId) payload.allocation_id = options.allocationId;
    if (options?.allocationAmount) payload.allocation_amount = options.allocationAmount;
    const response = await api.post(`${STRATEGIES_URL}strategies/${id}/deploy-paper/`, payload);
    return response.data;
  },

  deployLive: async (id, options = {}) => {
    const payload = {};
    if (options?.versionId) payload.version_id = options.versionId;
    if (options?.allocationAmount) payload.allocation_amount = options.allocationAmount;
    if (options?.allocationPercentage) payload.allocation_percentage = options.allocationPercentage;
    if (options?.brokerCredential) payload.broker_credential = options.brokerCredential;
    const response = await api.post(`${STRATEGIES_URL}strategies/${id}/deploy-live/`, payload);
    return response.data;
  },

  // Get tunable parameters for optimization
  getTunableParameters: async (id) => {
    const response = await api.get(`${STRATEGIES_URL}strategies/${id}/tunable-parameters/`);
    return response.data;
  },
};

// Strategy Tags
export const tagsApi = {
  getAll: async () => {
    const response = await api.get(`${STRATEGIES_URL}tags/`);
    return response.data;
  },
};

// Entry Order Config
export const entryConfigApi = {
  get: async (id) => {
    const response = await api.get(`${STRATEGIES_URL}entry-configs/${id}/`);
    return response.data;
  },

  create: async (data) => {
    const response = await api.post(`${STRATEGIES_URL}entry-configs/`, data);
    return response.data;
  },

  update: async (id, data) => {
    const response = await api.patch(`${STRATEGIES_URL}entry-configs/${id}/`, data);
    return response.data;
  },
};

// Exit Order Config
export const exitConfigApi = {
  get: async (id) => {
    const response = await api.get(`${STRATEGIES_URL}exit-configs/${id}/`);
    return response.data;
  },

  update: async (id, data) => {
    const response = await api.patch(`${STRATEGIES_URL}exit-configs/${id}/`, data);
    return response.data;
  },
};



// Tags logic attached to strategyApi
strategyApi.getTags = async () => {
  const response = await api.get(`${STRATEGIES_URL}tags/`);
  return response.data;
};

strategyApi.createTag = async (data) => {
  const response = await api.post(`${STRATEGIES_URL}tags/`, data);
  return response.data;
};

export default strategyApi;
