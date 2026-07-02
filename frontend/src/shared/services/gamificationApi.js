import api from "@/shared/services/api";

export const gamificationApi = {
  getMe: () => api.get("/gamification/me/"),
  getXPEvents: () => api.get("/gamification/xp-events/"),
  getAchievements: () => api.get("/gamification/achievements/"),
  getMyAchievements: () => api.get("/gamification/achievements/mine/"),
  getStreaks: () => api.get("/gamification/streaks/"),
  getChallenges: (params = {}) => api.get("/gamification/challenges/", { params }),
  joinChallenge: (id) => api.post(`/gamification/challenges/${id}/join/`),
  getMyChallenges: () => api.get("/gamification/challenges/mine/"),
  getLeaderboards: (params = {}) => api.get("/gamification/leaderboards/", { params }),
};

