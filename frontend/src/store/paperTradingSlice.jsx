import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import api from "../services/api";
import { toast } from "react-hot-toast";

// --- Async Thunks for API interactions ---

export const createOrder = createAsyncThunk(
  "paperTrading/createOrder",
  async (orderData, { rejectWithValue }) => {
    try {
      const response = await api.post("/paper-trading/orders/", orderData);
      toast.success("Order placed successfully!");
      return response.data;
    } catch (err) {
      const error = err.response?.data?.detail || "Failed to place order.";
      toast.error(error);
      return rejectWithValue(error);
    }
  }
);

export const cancelOrder = createAsyncThunk(
  "paperTrading/cancelOrder",
  async (orderId, { rejectWithValue }) => {
    try {
      await api.delete(`/paper-trading/orders/${orderId}/`);
      toast.success("Order cancelled.");
      return orderId;
    } catch (err) {
      toast.error("Failed to cancel order.");
      return rejectWithValue(err.response.data);
    }
  }
);

// Add other thunks for modifying orders, positions, watchlist etc.

const initialState = {
  // This state will be populated by the WebSocket
  account: null,
  positions: [],
  orders: [],
  watchlist: [],
  unrealized_pnl: "0.00",
  // --- Local state ---
  isSocketConnected: false,
  isLoading: true, // For initial load
  error: null,
};

const paperTradingSlice = createSlice({
  name: "paperTrading",
  initialState,
  reducers: {
    setSocketConnected: (state, action) => {
      state.isSocketConnected = action.payload;
    },
    // Action to handle the initial state pushed by the WebSocket on connect
    setInitialState: (state, action) => {
      const { account, positions, orders, watchlist, unrealized_pnl } =
        action.payload;
      state.account = account;
      state.positions = positions;
      state.orders = orders;
      state.watchlist = watchlist;
      state.unrealized_pnl = unrealized_pnl;
      state.isLoading = false;
    },
    // Action to handle real-time portfolio updates from the WebSocket
    updatePortfolio: (state, action) => {
      const { account, positions, orders, watchlist, unrealized_pnl } =
        action.payload;
      state.account = account;
      state.positions = positions;
      state.orders = orders;
      state.watchlist = watchlist;
      state.unrealized_pnl = unrealized_pnl;
    },
  },
});

export const { setSocketConnected, setInitialState, updatePortfolio } =
  paperTradingSlice.actions;
export default paperTradingSlice.reducer;
