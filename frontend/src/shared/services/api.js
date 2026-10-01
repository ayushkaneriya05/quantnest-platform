import axios from "axios";
import { tokenRefreshed, logout } from "../store/authSlice";
import { store } from "../store/index";

const api = axios.create({
  baseURL: import.meta.env.VITE_REACT_APP_API_URL,
  withCredentials: true,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("accessToken");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    if (config.data instanceof FormData) {
      delete config.headers["Content-Type"];
    }

    return config;
  },
  (error) => Promise.reject(error)
);

const AUTH_ENDPOINTS = [
  "/users/auth/login/",
  "/users/auth/logout/",
  "/users/auth/token/refresh/",
];

let refreshPromise = null;

function refreshAccessToken() {
  if (!refreshPromise) {
    const refreshToken = localStorage.getItem("refreshToken");
    const baseUrl = (api.defaults.baseURL || "").replace(/\/$/, "");

    refreshPromise = axios
      .post(
        `${baseUrl}/users/auth/token/refresh/`,
        refreshToken ? { refresh: refreshToken } : {},
        { withCredentials: true, timeout: 10000 },
      )
      .then(({ data }) => {
        if (!data?.access) {
          throw new Error("Token refresh did not return an access token.");
        }
        store.dispatch(tokenRefreshed(data));
        return data.access;
      })
      .catch((error) => {
        store.dispatch(logout());
        throw error;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const isAuthEndpoint = AUTH_ENDPOINTS.some((endpoint) =>
      originalRequest?.url?.includes(endpoint),
    );

    if (
      originalRequest &&
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !isAuthEndpoint
    ) {
      originalRequest._retry = true;
      try {
        const access = await refreshAccessToken();
        originalRequest.headers = originalRequest.headers || {};
        originalRequest.headers.Authorization = `Bearer ${access}`;
        return api(originalRequest);
      } catch (refreshError) {
        return Promise.reject(refreshError);
      }
    }

    if (error.response?.status === 403 && error.response?.data?.code === "token_not_valid") {
      store.dispatch(logout());
    }

    return Promise.reject(error);
  }
);

export default api;
