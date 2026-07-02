import api from "@/shared/services/api";

export const reputationApi = {
  getMyReputation: () => api.get("/reputation/profiles/me/"),
  refreshMyReputation: () => api.post("/reputation/profiles/me/"),
  getProfiles: (params = {}) => api.get("/reputation/profiles/", { params }),
  getScores: () => api.get("/reputation/scores/"),
  getMentors: () => api.get("/reputation/mentors/"),
  getMyMentorProfile: () => api.get("/reputation/mentors/me/"),
  updateMyMentorProfile: (payload) => api.patch("/reputation/mentors/me/", payload),
};

