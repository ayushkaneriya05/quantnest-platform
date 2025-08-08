import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import api from "../services/api";

export const fetchUserProfile = createAsyncThunk(
  "auth/fetchUserProfile",
  async (_, { dispatch, rejectWithValue }) => {
    try {
      const response = await api.get("/users/profile/");
      console.log("fetch user profile : ", response);
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response.data);
    }
  }
);
export const logoutUser = createAsyncThunk(
  "auth/logout",
  async (_, { getState, rejectWithValue }) => {
    const { refreshToken } = getState().auth;
    try {
      // Tell the backend to blacklist the refresh token
      console.log("Logging out with refresh token:", refreshToken);
      await api.post("users/auth/logout/", { refresh: refreshToken });
    } catch (error) {
      console.error(
        "Server-side logout failed, proceeding with client-side logout.",
        error
      );
    }
    return;
  }
);
const initialState = {
  accessToken: localStorage.getItem("accessToken") || null,
  refreshToken: localStorage.getItem("refreshToken") || null,
  user: null,
  isLoading: false,
  error: null,
  is2FARequired: false,
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setLoading: (state, action) => {
      state.isLoading = action.payload;
    },
    loginSuccess: (state, action) => {
      console.log("Login successfull :", action.payload);
      state.accessToken = action.payload.access;
      state.refreshToken = action.payload.refresh;
      localStorage.setItem("accessToken", action.payload.access);
      localStorage.setItem("refreshToken", action.payload.refresh);
      state.isLoading = false;
      state.error = null;
      state.is2FARequired = false;
    },
    tokenRefreshed: (state, action) => {
      state.accessToken = action.payload.access;
      localStorage.setItem("accessToken", action.payload.access);
    },
    set2FARequired: (state, action) => {
      state.is2FARequired = action.payload;
    },
    logout: (state) => {
      console.log("Logging out user");
      state.accessToken = null;
      state.user = null;
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchUserProfile.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(fetchUserProfile.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
      })
      .addCase(fetchUserProfile.rejected, (state) => {
        state.isLoading = false;
      });
  },
});

export const {
  setLoading,
  loginSuccess,
  tokenRefreshed,
  set2FARequired,
  logout,
} = authSlice.actions;
export default authSlice.reducer;
