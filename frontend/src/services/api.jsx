import axios from "axios";
import { tokenRefreshed, logoutUser, logout } from "../store/authSlice";
import { store } from "../store/index";
import { mockApi } from "./mockApi";

// Create an Axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_REACT_APP_API_URL || "http://localhost:8000/api/v1/",
  withCredentials: true,
  timeout: 10000, // 10 second timeout
  headers: {
    "Content-Type": "application/json",
  },
});

// Track backend availability
let backendAvailable = true;
let lastBackendCheck = 0;
const BACKEND_CHECK_INTERVAL = 30000; // 30 seconds

// Function to check if response is HTML (indicating backend is not available)
const isHtmlResponse = (response) => {
  const contentType = response.headers?.['content-type'] || '';
  return contentType.includes('text/html') || 
         (typeof response.data === 'string' && response.data.includes('<!doctype html>'));
};

// Function to detect if we should use mock data
const shouldUseMockData = (error) => {
  // Check if we're getting HTML instead of JSON
  if (error.response && isHtmlResponse(error.response)) {
    return true;
  }
  
  // Check for network errors or backend unavailable
  if (!error.response || 
      error.code === 'ECONNABORTED' || 
      error.code === 'ENOTFOUND' ||
      error.code === 'ECONNREFUSED' ||
      error.response.status >= 500) {
    return true;
  }
  
  return false;
};

// Enhanced API wrapper with mock fallback
const apiWrapper = {
  // Generic method to handle API calls with fallback
  async callWithFallback(apiCall, mockCall, options = {}) {
    const { showToast = true, fallbackMessage = "Using demo data - backend unavailable" } = options;
    
    try {
      const response = await apiCall();
      
      // Check if we got HTML instead of JSON
      if (isHtmlResponse(response)) {
        throw new Error('Backend returned HTML instead of JSON');
      }
      
      backendAvailable = true;
      return response;
    } catch (error) {
      if (shouldUseMockData(error)) {
        if (backendAvailable && showToast) {
          console.warn(fallbackMessage);
          // Only show toast if this is the first time we're falling back
          if (typeof window !== 'undefined' && window.toast) {
            window.toast.error(fallbackMessage, { duration: 4000 });
          }
        }
        backendAvailable = false;
        
        // Call mock API
        const mockData = await mockCall();
        return { data: mockData };
      } else {
        throw error;
      }
    }
  },

  // Trading API methods
  async get(url, config = {}) {
    return this.callWithFallback(
      () => api.get(url, config),
      async () => {
        // Route to appropriate mock method based on URL
        if (url.includes('/trading/instruments/search/')) {
          const query = config.params?.query || '';
          return mockApi.searchInstruments(query);
        } else if (url.includes('/trading/watchlist/')) {
          return mockApi.getWatchlist();
        } else if (url.includes('/trading/account/')) {
          return mockApi.getAccount();
        } else if (url.includes('/trading/positions/')) {
          return mockApi.getPositions();
        } else if (url.includes('/trading/orders/')) {
          return mockApi.getOrders();
        } else if (url.includes('/trading/portfolio/summary/')) {
          return mockApi.getPortfolioSummary();
        } else if (url.includes('/marketdata/historical/')) {
          const { symbol, timeframe, limit } = config.params || {};
          return mockApi.getHistoricalData(symbol, timeframe, limit);
        } else if (url.includes('/marketdata/quote/')) {
          const symbol = config.params?.symbol || 'RELIANCE';
          return mockApi.getLiveQuote(symbol);
        }
        
        // Default fallback
        return {};
      }
    );
  },

  async post(url, data = {}, config = {}) {
    return this.callWithFallback(
      () => api.post(url, data, config),
      async () => {
        if (url.includes('/trading/watchlist/')) {
          return mockApi.addToWatchlist(data.instrument_id);
        } else if (url.includes('/trading/orders/')) {
          return mockApi.createOrder(data);
        }
        
        return { success: true, message: 'Mock operation completed' };
      }
    );
  },

  async put(url, data = {}, config = {}) {
    return this.callWithFallback(
      () => api.put(url, data, config),
      async () => {
        if (url.includes('/trading/orders/')) {
          const orderId = parseInt(url.split('/').slice(-2, -1)[0]);
          return mockApi.updateOrder(orderId, data);
        }
        
        return { success: true, message: 'Mock update completed' };
      }
    );
  },

  async delete(url, config = {}) {
    return this.callWithFallback(
      () => api.delete(url, config),
      async () => {
        if (url.includes('/trading/watchlist/')) {
          const instrumentId = config.data?.instrument_id;
          return mockApi.removeFromWatchlist(instrumentId);
        } else if (url.includes('/trading/orders/')) {
          const orderId = parseInt(url.split('/').slice(-2, -1)[0]);
          return mockApi.cancelOrder(orderId);
        }
        
        return { success: true, message: 'Mock deletion completed' };
      }
    );
  },

  // Method to check backend availability
  async checkBackendHealth() {
    const now = Date.now();
    if (now - lastBackendCheck < BACKEND_CHECK_INTERVAL) {
      return backendAvailable;
    }
    
    try {
      const response = await axios.get(`${api.defaults.baseURL}health/`, { 
        timeout: 5000,
        validateStatus: (status) => status < 500
      });
      
      if (isHtmlResponse(response)) {
        backendAvailable = false;
      } else {
        backendAvailable = true;
      }
    } catch (error) {
      backendAvailable = false;
    }
    
    lastBackendCheck = now;
    return backendAvailable;
  },

  // Method to get backend status
  getBackendStatus() {
    return {
      available: backendAvailable,
      lastChecked: lastBackendCheck
    };
  }
};

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
    // Check if we got HTML instead of JSON
    if (isHtmlResponse(response)) {
      const error = new Error('Backend returned HTML instead of JSON');
      error.response = response;
      throw error;
    }
    
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
    if (error.response?.status === 401 && !originalRequest._retry && backendAvailable) {
      originalRequest._retry = true; // Mark that we've tried to refresh

      try {
        const refreshToken = localStorage.getItem("refreshToken");

        if (!refreshToken) {
          throw new Error("No refresh token available");
        }

        console.log("Attempting to refresh token...");

        const response = await axios.post(
          `${api.defaults.baseURL}users/auth/token/refresh/`,
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

        // Only logout if backend is available (avoid logout on demo mode)
        if (backendAvailable) {
          store.dispatch(logoutUser());
          store.dispatch(logout());

          // Redirect to login page if not already there
          if (window.location.pathname !== "/login") {
            window.location.href = "/login";
          }
        }

        return Promise.reject(refreshError);
      }
    }

    if (
      error.response?.status === 403 &&
      error.response.data.code === "token_not_valid" &&
      backendAvailable
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

// Make toast available globally for error messages
if (typeof window !== 'undefined') {
  import('react-hot-toast').then(toastModule => {
    window.toast = toastModule.default;
  });
}

export default apiWrapper;
