import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../services/api';

// Async thunk for fetching user profile
export const fetchUserProfile = createAsyncThunk(
  'auth/fetchUserProfile',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/users/profile/');
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response.data);
    }
  }
);

const initialState = {
  accessToken: localStorage.getItem('accessToken') || null,
  user: null,
  isLoading: false,
  error: null,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    loginSuccess: (state, action) => {
      state.accessToken = action.payload.access;
      localStorage.setItem('accessToken', action.payload.access);
      state.isLoading = false;
      state.error = null;
    },
    logout: (state) => {
      state.accessToken = null;
      state.user = null;
      localStorage.removeItem('accessToken');
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
      .addCase(fetchUserProfile.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
        // If profile fetch fails, the token is likely invalid, so log out
        state.accessToken = null;
        state.user = null;
        localStorage.removeItem('accessToken');
      });
  },
});

export const { loginSuccess, logout } = authSlice.actions;
export default authSlice.reducer;