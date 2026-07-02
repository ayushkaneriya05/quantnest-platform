import axios from "axios";
import { tokenRefreshed, logoutUser, logout } from "../store/authSlice";
import { store } from "../store/index";

// Create an Axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_REACT_APP_API_URL,
  withCredentials: true,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add a request interceptor to include the token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("accessToken");
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }

    // Let Axios handle the Content-Type and boundary for FormData automatically
    if (config.data instanceof FormData) {
      delete config.headers["Content-Type"];
    }

    return config;
  },
  (error) => {
    console.error("API Request Error:", error);
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Skip refresh logic if the request is already trying to login, logout, or refresh
    const skipAuthRefresh = ["/users/auth/login/", "/users/auth/logout/", "/users/auth/token/refresh/"];
    const isAuthEndpoint = skipAuthRefresh.some(endpoint => originalRequest.url?.includes(endpoint));

    // Check if the error is a 401 and we haven't already tried to refresh
    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true; // Mark that we've tried to refresh

      try {
        const refreshToken = localStorage.getItem("refreshToken");
        
        // If refreshToken is present, send it in body (legacy support), otherwise let the server use the HttpOnly cookie.
        const payload = refreshToken ? { refresh: refreshToken } : {};

        const baseUrl = (import.meta.env.VITE_REACT_APP_API_URL || "").replace(
          /\/$/,
          ""
        );
        const response = await axios.post(
          `${baseUrl}/users/auth/token/refresh/`,
          payload,
          {
            withCredentials: true,
            timeout: 10000,
          }
        );

        const { access } = response.data;
        if (access) {
            // Update the Redux store and localStorage with the new token
            store.dispatch(tokenRefreshed({ access }));
            // Update the header of the original request and retry it
            originalRequest.headers["Authorization"] = `Bearer ${access}`;
        }
        return api(originalRequest);
      } catch (refreshError) {
        store.dispatch(logout());

        // We rely on ProtectedRoute to redirect to login if the route requires auth.
        // This allows public routes (like password reset) to stay on their page.

        return Promise.reject(refreshError);
      }
    }

    if (
      error.response?.status === 403 &&
      error.response.data.code === "token_not_valid"
    ) {
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      store.dispatch(logout());
    }

    return Promise.reject(error);
  }
);

export default api;
