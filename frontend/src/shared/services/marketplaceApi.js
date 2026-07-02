import api from "./api";

export const marketplaceApi = {
  getListings: (params = {}) => api.get("/marketplace/listings/", { params }),
  getListingDetail: (id) => api.get(`/marketplace/listings/${id}/`),
  createListing: (payload) => api.post("/marketplace/listings/", payload),
  updateListing: (id, payload) => api.patch(`/marketplace/listings/${id}/`, payload),
  getMyListings: () => api.get("/marketplace/listings/my-listings/"),
  getCreatorDashboard: () => api.get("/marketplace/listings/creator-dashboard/"),

  getSubscriptions: () => api.get("/marketplace/subscriptions/"),
  getSubscriptionSummary: () => api.get("/marketplace/subscriptions/summary/"),
  subscribe: (listing, autoRenew = false) =>
    api.post("/marketplace/subscriptions/subscribe/", {
      listing,
      auto_renew: autoRenew,
    }),
  cancelSubscription: (id) => api.post(`/marketplace/subscriptions/${id}/cancel/`),

  getReviews: (params = {}) => api.get("/marketplace/reviews/", { params }),
  createReview: (payload) => api.post("/marketplace/reviews/", payload),
  updateReview: (id, payload) => api.patch(`/marketplace/reviews/${id}/`, payload),
  markReviewHelpful: (id) => api.post(`/marketplace/reviews/${id}/helpful/`),

  getEarnings: () => api.get("/marketplace/earnings/"),
};

export default marketplaceApi;
