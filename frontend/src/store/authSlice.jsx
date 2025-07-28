import { createSlice, createAsyncThunk } from "redux";
import api from "../services/api";

export const fetchUserProfile = createAsyncThunk(
  "auth/fetchUserProfile",
  async (_, { dispatch, rejectWithValue }) => {
    try {
      const response = await api.get("/users/profile/");
      return response.data;
    } catch (err) {
      dispatch(logout()); // Log out if token is invalid
      return rejectWithValue(err.response.data);
    }
  }
);

const initialState = {
  accessToken: localStorage.getItem("accessToken") || null,
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
      state.accessToken = action.payload.access_token;
      localStorage.setItem("accessToken", action.payload.access_token);
      state.isLoading = false;
      state.error = null;
      state.is2FARequired = false;
    },
    set2FARequired: (state, action) => {
      state.is2FARequired = action.payload;
    },
    logout: (state) => {
      state.accessToken = null;
      state.user = null;
      localStorage.removeItem("accessToken");
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

export const { setLoading, loginSuccess, set2FARequired, logout } =
  authSlice.actions;
export default authSlice.reducer;
