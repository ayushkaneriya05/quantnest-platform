import axios from "axios";
import { tokenRefreshed, logoutUser, logout } from "../store/authSlice";
import { store } from "../store/index";
// Create an Axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_REACT_APP_API_URL,
  withCredentials: true,
});

// Add a request interceptor to include the token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("accessToken");
    console.log("token : ", token);
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refreshing
api.interceptors.response.use(
  (response) => response, // Simply return the response if it's successful
  async (error) => {
    const originalRequest = error.config;

    // Check if the error is a 401 and we haven't already tried to refresh
    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true; // Mark that we've tried to refresh

      try {
        const refreshToken = localStorage.getItem("refreshToken");
        // Make the call to the refresh endpoint
        const response = await api.post("users/auth/token/refresh/", {
          refresh: refreshToken,
        });

        const { access } = response.data;

        // Update the Redux store and localStorage with the new token
        store.dispatch(tokenRefreshed({ access }));

        // Update the header of the original request and retry it
        originalRequest.headers["Authorization"] = `Bearer ${access}`;
        return api(originalRequest);
      } catch (refreshError) {
        // If the refresh token is also invalid, log the user out
        store.dispatch(logoutUser());
        store.dispatch(logout());
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
