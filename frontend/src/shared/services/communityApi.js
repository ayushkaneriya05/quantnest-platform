import api from "@/shared/services/api";

export const communityApi = {
  getProfiles: (params = {}) => api.get("/community/profiles/", { params }),
  getMyProfile: () => api.get("/community/profiles/me/"),
  updateMyProfile: (payload) => api.patch("/community/profiles/me/", payload),
  getTopics: () => api.get("/community/topics/"),
  getPosts: (params = {}) => api.get("/community/posts/", { params }),
  createPost: (payload) => api.post("/community/posts/", payload),
  reactToPost: (id, reaction_type = "LIKE") => api.post(`/community/posts/${id}/react/`, { reaction_type }),
  bookmarkPost: (id) => api.post(`/community/posts/${id}/bookmark/`),
  getComments: (post) => api.get("/community/comments/", { params: { post } }),
  createComment: (payload) => api.post("/community/comments/", payload),
  getBookmarks: () => api.get("/community/bookmarks/"),
  followUser: (following) => api.post("/community/follows/", { following }),
  reportPost: (payload) => api.post("/community/reports/", payload),
  getStrategyRooms: (params = {}) => api.get("/community/strategy-rooms/", { params }),
  getStrategyRoomByStrategy: (strategyId) => api.get(`/community/strategies/${strategyId}/rooms/`),
};

