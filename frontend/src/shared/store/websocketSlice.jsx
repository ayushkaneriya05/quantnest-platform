import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import toast from "react-hot-toast";
import api from "../services/api";

const initialState = {
  isConnected: false,
  connectionStatus: "disconnected",
  lastMessage: null,
  tickData: {},
  orderUpdates: [],
  positionUpdates: [],
  subscriptions: [],
  reconnectAttempts: 0,
  maxReconnectAttempts: 5,
};

// Async thunks for WebSocket operations
export const connectWebSocket = createAsyncThunk(
  "websocket/connect",
  async (_, { dispatch, getState }) => {
    const state = getState().websocket;
    if (state.isConnected) return;

    // This will be handled by middleware or component
    // For now, just return success
    return true;
  }
);

export const disconnectWebSocket = createAsyncThunk(
  "websocket/disconnect",
  async (_, { dispatch }) => {
    // This will be handled by middleware or component
    return true;
  }
);

export const subscribeToSymbol = createAsyncThunk(
  "websocket/subscribe",
  async (symbol, { getState }) => {
    // This will be handled by middleware or component
    return symbol;
  }
);

export const unsubscribeFromSymbol = createAsyncThunk(
  "websocket/unsubscribe",
  async (symbol, { getState }) => {
    // This will be handled by middleware or component
    return symbol;
  }
);

export const fetchLatestPrice = createAsyncThunk(
  "websocket/fetchLatestPrice",
  async (symbol, { rejectWithValue }) => {
    try {
      const response = await api.get(
        `/market/latest-tick/?instrument=${symbol}`
      );
      return { symbol, data: response.data };
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

const websocketSlice = createSlice({
  name: "websocket",
  initialState,
  reducers: {
    setConnected: (state, action) => {
      state.isConnected = action.payload;
      state.connectionStatus = action.payload ? "connected" : "disconnected";
    },
    setConnectionStatus: (state, action) => {
      state.connectionStatus = action.payload;
    },
    setLastMessage: (state, action) => {
      state.lastMessage = action.payload;
    },
    updateTickData: (state, action) => {
      const { symbol, data } = action.payload;
      state.tickData[symbol] = { ...data, timestamp: Date.now() };
    },
    addOrderUpdate: (state, action) => {
      state.orderUpdates = [action.payload, ...state.orderUpdates.slice(0, 99)];
      const instrumentSymbol = action.payload.instrument?.symbol || "N/A";
      // Toast will be handled by component
    },
    addPositionUpdate: (state, action) => {
      state.positionUpdates = [
        action.payload,
        ...state.positionUpdates.slice(0, 99),
      ];
    },
    addSubscription: (state, action) => {
      if (!state.subscriptions.includes(action.payload)) {
        state.subscriptions.push(action.payload);
      }
    },
    removeSubscription: (state, action) => {
      state.subscriptions = state.subscriptions.filter(
        (sub) => sub !== action.payload
      );
    },
    incrementReconnectAttempts: (state) => {
      state.reconnectAttempts += 1;
    },
    resetReconnectAttempts: (state) => {
      state.reconnectAttempts = 0;
    },
    clearTickData: (state) => {
      state.tickData = {};
    },
    clearOrderUpdates: (state) => {
      state.orderUpdates = [];
    },
    clearPositionUpdates: (state) => {
      state.positionUpdates = [];
    },
  },
  extraReducers: (builder) => {
    builder.addCase(fetchLatestPrice.fulfilled, (state, action) => {
      const { symbol, data } = action.payload;
      if (!state.tickData[symbol]) {
        state.tickData[symbol] = data;
      }
    });
  },
});

export const {
  setConnected,
  setConnectionStatus,
  setLastMessage,
  updateTickData,
  addOrderUpdate,
  addPositionUpdate,
  addSubscription,
  removeSubscription,
  incrementReconnectAttempts,
  resetReconnectAttempts,
  clearTickData,
  clearOrderUpdates,
  clearPositionUpdates,
} = websocketSlice.actions;

export default websocketSlice.reducer;
