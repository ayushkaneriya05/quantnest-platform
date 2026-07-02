import api from "@/shared/services/api";

export const replayApi = {
  getReplays: () => api.get("/replays/"),
  createReplay: (payload) => api.post("/replays/", payload),
  publishReplay: (id, visibility = "PUBLIC") => api.post(`/replays/${id}/publish/`, { visibility }),
};
