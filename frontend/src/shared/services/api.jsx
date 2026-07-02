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

    // Check if the error is a 401 and we haven't already tried to refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true; // Mark that we've tried to refresh

      try {
        const refreshToken = localStorage.getItem("refreshToken");

        if (!refreshToken) {
          throw new Error("No refresh token available");
        }

        const baseUrl = (import.meta.env.VITE_REACT_APP_API_URL || "").replace(
          /\/$/,
          ""
        );
        const response = await axios.post(
          `${baseUrl}/users/auth/token/refresh/`,
          { refresh: refreshToken },
          {
            withCredentials: true,
            timeout: 10000,
          }
        );

        const { access } = response.data;

        // Update the Redux store and localStorage with the new token
        store.dispatch(tokenRefreshed({ access }));

        // Update the header of the original request and retry it
        originalRequest.headers["Authorization"] = `Bearer ${access}`;
        return api(originalRequest);
      } catch (refreshError) {
        store.dispatch(logoutUser());
        store.dispatch(logout());

        // Redirect to login page if not already there
        if (window.location.pathname !== "/login") {
          window.location.href = "/login";
        }

        return Promise.reject(refreshError);
      }
    }

    if (
      error.response?.status === 403 &&
      error.response.data.code === "token_not_valid"
    ) {
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      store.dispatch(logoutUser());
      store.dispatch(logout());
      window.location.href = "/login";
    }

    return Promise.reject(error);
  }
);

export default api;
