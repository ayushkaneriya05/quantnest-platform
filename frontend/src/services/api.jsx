import axios from "axios";
import { tokenRefreshed, logoutUser, logout } from "../store/authSlice";
import { store } from "../store/index";

// Create an Axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_REACT_APP_API_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add a request interceptor to include the token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("accessToken");
    console.log("API Request - token : ", token);
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
    console.log(
      `API Success - ${response.config.method?.toUpperCase()} ${
        response.config.url
      }:`,
      response.status
    );
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    console.error(
      `API Error - ${originalRequest?.method?.toUpperCase()} ${
        originalRequest?.url
      }:`,
      error.response?.status,
      error.response?.data
    );

    // Check if the error is a 401 and we haven't already tried to refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true; // Mark that we've tried to refresh

      try {
        const refreshToken = localStorage.getItem("refreshToken");

        if (!refreshToken) {
          throw new Error("No refresh token available");
        }

        console.log("Attempting to refresh token...");

        const response = await axios.post(
          `${import.meta.env.VITE_REACT_APP_API_URL}users/auth/token/refresh/`,
          { refresh: refreshToken },
          {
            withCredentials: true,
            timeout: 10000,
          }
        );

        const { access } = response.data;

        // Update the Redux store and localStorage with the new token
        store.dispatch(tokenRefreshed({ access }));

        console.log("Token refreshed successfully");

        // Update the header of the original request and retry it
        originalRequest.headers["Authorization"] = `Bearer ${access}`;
        return api(originalRequest);
      } catch (refreshError) {
        console.error("Token refresh failed:", refreshError);

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
      console.error("Access forbidden - insufficient permissions");
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      store.dispatch(logoutUser());
      store.dispatch(logout());
      window.location.href = "/login";
    } else if (error.response?.status === 403) {
      console.error("Access forbidden - insufficient permissions");
    } else if (error.response?.status === 404) {
      console.error("Resource not found");
    } else if (error.response?.status >= 500) {
      console.error("Server error - please try again later");
    } else if (error.code === "ECONNABORTED") {
      console.error("Request timeout - please check your connection");
    } else if (!error.response) {
      console.error("Network error - please check your connection");
    }

    return Promise.reject(error);
  }
);

export default api;
