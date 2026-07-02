import api from "./api";

export const aiApi = {
  getRecommendations: () => api.get("/ai/recommendations/"),
  getOverview: () => api.get("/ai/recommendations/overview/"),
  generateRecommendation: (strategy) => api.post("/ai/recommendations/generate/", { strategy }),
  refreshSuite: (strategy = null) =>
    api.post("/ai/recommendations/refresh/", strategy ? { strategy } : {}),
  dismissRecommendation: (id) => api.post(`/ai/recommendations/${id}/dismiss/`),
  applyRecommendation: (id) => api.post(`/ai/recommendations/${id}/apply/`),
  getHealthScores: () => api.get("/ai/health-scores/"),
  refreshHealthScore: (strategy) => api.post("/ai/health-scores/refresh/", { strategy }),
  getMarketRegimes: () => api.get("/ai/market-regimes/"),
  refreshMarketRegimes: (strategy) => api.post("/ai/market-regimes/refresh/", { strategy }),
  getOverfitDetections: () => api.get("/ai/overfit/"),
  refreshOverfitDetection: (strategy) => api.post("/ai/overfit/refresh/", { strategy }),
};

export default aiApi;
