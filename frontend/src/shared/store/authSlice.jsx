import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import api, { isAuthFailure, refreshAccessToken } from "../services/api";
import { getApiErrorMessage } from "../utils/apiErrors";
import { AuthChangedError, getAuthGeneration } from "../services/authSession";

// Remove tokens persisted by the previous implementation; do not reuse them.
["accessToken", "refreshToken", "isAuthenticated"].forEach((key) => localStorage.removeItem(key));

export const fetchUserProfile = createAsyncThunk(
  "auth/fetchUserProfile",
  async (_, { rejectWithValue }) => {
    const generation = getAuthGeneration();
    try {
      const { data } = await api.get("/users/profile/");
      return generation === getAuthGeneration() ? data : null;
    } catch (error) {
      return rejectWithValue(getApiErrorMessage(error, "Could not load your profile."));
    }
  },
);

export const initializeAuth = createAsyncThunk(
  "auth/initialize",
  async (_, { getState, rejectWithValue }) => {
    const generation = getAuthGeneration();
    try {
      const access = await refreshAccessToken();
      const { data: user } = await api.get("/users/profile/");
      return generation === getAuthGeneration() ? { access: getState().auth.accessToken || access, user } : null;
    } catch (error) {
      if (isAuthFailure(error) || error instanceof AuthChangedError) return null;
      return rejectWithValue(getApiErrorMessage(error, "Could not verify your session. Please retry."));
    }
  },
  { condition: (options, { getState }) => options?.force || !getState().auth.isInitializing },
);

export const logoutUser = createAsyncThunk(
  "auth/signOut",
  async (_, { dispatch, rejectWithValue }) => {
    try {
      await api.post("/users/auth/logout/", {});
      dispatch(logout());
    } catch (error) {
      return rejectWithValue(getApiErrorMessage(error, "Could not end the server session."));
    }
  },
);

const initialState = {
  accessToken: null, user: null,
  isLoading: false, isInitializing: false, initialized: false,
  error: null, isAuthenticated: false,
  initializationRequestId: null,
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setLoading: (state, action) => { state.isLoading = action.payload; },
    setError: (state, action) => { state.error = action.payload; },
    clearError: (state) => { state.error = null; },
    loginSuccess: (state, { payload }) => {
      if (!payload.access || !payload.user) return;
      state.accessToken = payload.access;
      state.user = payload.user;
      state.isAuthenticated = true;
      state.initialized = true;
      state.isLoading = false;
      state.isInitializing = false;
      state.initializationRequestId = null;
      state.error = null;
    },
    tokenRefreshed: (state, { payload }) => {
      state.accessToken = payload.access;
    },
    logout: (state) => {
      Object.assign(state, initialState, { initialized: true });
    },
    updateUser: (state, action) => { state.user = { ...state.user, ...action.payload }; },
  },
  extraReducers: (builder) => {
    builder
      .addCase(initializeAuth.pending, (state, action) => {
        state.isInitializing = true;
        state.error = null;
        state.initializationRequestId = action.meta.requestId;
      })
      .addCase(initializeAuth.fulfilled, (state, { payload, meta }) => {
        if (meta.requestId !== state.initializationRequestId) return;
        state.initializationRequestId = null;
        state.isInitializing = false;
        state.initialized = true;
        if (payload) {
          state.accessToken = payload.access;
          state.user = payload.user;
          state.isAuthenticated = true;
        }
      })
      .addCase(initializeAuth.rejected, (state, { payload, meta }) => {
        if (meta.requestId !== state.initializationRequestId) return;
        state.initializationRequestId = null;
        state.isInitializing = false;
        state.initialized = true;
        state.error = payload;
      })
      .addCase(fetchUserProfile.fulfilled, (state, { payload }) => {
        if (payload && state.accessToken) state.user = payload;
      })
      .addCase(fetchUserProfile.rejected, (state, { payload }) => { state.error = payload; });
  },
});

export const {
  setLoading, setError, clearError, loginSuccess, tokenRefreshed,
  logout, updateUser,
} = authSlice.actions;
export default authSlice.reducer;
