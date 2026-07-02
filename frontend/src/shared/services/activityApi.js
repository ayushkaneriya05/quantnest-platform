import api from "@/shared/services/api";

export const activityApi = {
  getEvents: () => api.get("/events/"),
  getActivity: (params = {}) => api.get("/activity/", { params }),
};

