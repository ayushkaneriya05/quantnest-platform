import { createSlice } from "@reduxjs/toolkit";
import { isNewerQuote } from "../utils/marketData";

const initialState = {
  isConnected: false,
  connectionStatus: "disconnected",
  manualTradingTerminalUpdate: null,
  paperLastMessage: null,
  tickData: {},
  subscriptions: [],
  reconnectAttempts: 0,
};

const websocketSlice = createSlice({
  name: "websocket",
  initialState,
  reducers: {
    clearPrivateUpdates: (state) => {
      state.manualTradingTerminalUpdate = null;
      state.paperLastMessage = null;
    },
    setConnected: (state, action) => {
      state.isConnected = action.payload;
      state.connectionStatus = action.payload ? "connected" : "disconnected";
    },
    setConnectionStatus: (state, action) => {
      state.connectionStatus = action.payload;
    },
    setManualTradingTerminalUpdate: (state, action) => {
      state.manualTradingTerminalUpdate = action.payload;
    },
    setPaperLastMessage: (state, action) => {
      state.paperLastMessage = action.payload;
    },
    updateTickData: (state, action) => {
      const { symbol, data } = action.payload;
      if (isNewerQuote(data, state.tickData[symbol])) state.tickData[symbol] = data;
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
  },
});

export const {
  setConnected,
  setConnectionStatus,
  setManualTradingTerminalUpdate,
  setPaperLastMessage,
  updateTickData,
  addSubscription,
  removeSubscription,
  incrementReconnectAttempts,
  resetReconnectAttempts,
  clearTickData,
} = websocketSlice.actions;

export default websocketSlice.reducer;
