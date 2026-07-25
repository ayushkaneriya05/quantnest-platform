import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import api from "../services/api";

export const fetchUserProfile = createAsyncThunk(
  "auth/fetchUserProfile",
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get("/users/profile/");
      console.log("fetch user profile : ", response);
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

export const logoutUser = createAsyncThunk(
  "auth/logout",
  async (_, { getState }) => {
    const { refreshToken } = getState().auth;
    try {
      console.log("Logging out with refresh token:", refreshToken);
      await api.post("/users/auth/logout/", { refresh: refreshToken });
    } catch (error) {
      console.error(
        "Server-side logout failed, proceeding with client-side logout.",
        error
      );
    }
    return;
  }
);

export const refreshAccessToken = createAsyncThunk(
  "auth/refreshToken",
  async (_, { getState, rejectWithValue }) => {
    const { refreshToken } = getState().auth;
    try {
      const response = await api.post("/users/auth/token/refresh/", {
        refresh: refreshToken,
      });
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

const initialState = {
  accessToken: localStorage.getItem("accessToken") || null,
  refreshToken: localStorage.getItem("refreshToken") || null,
  user: null,
  isLoading: false,
  error: null,
  is2FARequired: false,
  isAuthenticated: false,
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setLoading: (state, action) => {
      state.isLoading = action.payload;
    },
    setError: (state, action) => {
      state.error = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
    loginSuccess: (state, action) => {
      console.log("Login successful :", action.payload);
      if (action.payload.access) {
        state.accessToken = action.payload.access;
        localStorage.setItem("accessToken", action.payload.access);
      }
      if (action.payload.refresh) {
        state.refreshToken = action.payload.refresh;
        localStorage.setItem("refreshToken", action.payload.refresh);
      }
      localStorage.setItem("isAuthenticated", "true");
      
      state.user = action.payload.user || null;
      state.isLoading = false;
      state.error = null;
      state.is2FARequired = false;
      state.isAuthenticated = true;
    },
    tokenRefreshed: (state, action) => {
      state.accessToken = action.payload.access;
      localStorage.setItem("accessToken", action.payload.access);
      if (action.payload.refresh) {
        state.refreshToken = action.payload.refresh;
        localStorage.setItem("refreshToken", action.payload.refresh);
      }
    },
    set2FARequired: (state, action) => {
      state.is2FARequired = action.payload;
    },
    logout: (state) => {
      console.log("Logging out user");
      state.accessToken = null;
      state.refreshToken = null;
      state.user = null;
      state.isAuthenticated = false;
      state.is2FARequired = false;
      state.error = null;
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      localStorage.removeItem("isAuthenticated");
    },
    updateUser: (state, action) => {
      state.user = { ...state.user, ...action.payload };
    },
    initializeAuth: (state) => {
      const isAuth = localStorage.getItem("isAuthenticated");
      const token = localStorage.getItem("accessToken");
      if (isAuth === "true" || token) {
        state.isAuthenticated = true;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch User Profile
      .addCase(fetchUserProfile.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchUserProfile.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
        state.isAuthenticated = true;
      })
      .addCase(fetchUserProfile.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload?.detail || "Failed to fetch user profile";
      })
      // Logout User
      .addCase(logoutUser.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(logoutUser.fulfilled, (state) => {
        state.isLoading = false;
        state.accessToken = null;
        state.refreshToken = null;
        state.user = null;
        state.isAuthenticated = false;
        state.is2FARequired = false;
        state.error = null;
        localStorage.removeItem("accessToken");
        localStorage.removeItem("refreshToken");
        localStorage.removeItem("isAuthenticated");
      })
      .addCase(logoutUser.rejected, (state) => {
        state.isLoading = false;
        // Even if server logout fails, we clear local state
        state.accessToken = null;
        state.refreshToken = null;
        state.user = null;
        state.isAuthenticated = false;
        state.is2FARequired = false;
        localStorage.removeItem("accessToken");
        localStorage.removeItem("refreshToken");
        localStorage.removeItem("isAuthenticated");
      })
      // Refresh Access Token
      .addCase(refreshAccessToken.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(refreshAccessToken.fulfilled, (state, action) => {
        state.isLoading = false;
        state.accessToken = action.payload.access;
        localStorage.setItem("accessToken", action.payload.access);
      })
      .addCase(refreshAccessToken.rejected, (state) => {
        state.isLoading = false;
        // Token refresh failed, user needs to login again
        state.accessToken = null;
        state.refreshToken = null;
        state.user = null;
        state.isAuthenticated = false;
        localStorage.removeItem("accessToken");
        localStorage.removeItem("refreshToken");
        localStorage.removeItem("isAuthenticated");
      });
  },
});

export const {
  setLoading,
  setError,
  clearError,
  loginSuccess,
  tokenRefreshed,
  set2FARequired,
  logout,
  updateUser,
  initializeAuth,
} = authSlice.actions;

export default authSlice.reducer;
