import { configureStore } from "@reduxjs/toolkit";
import authReducer from "./authSlice"; // Assuming you have this from before
import paperTradingReducer from "./paperTradingSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    paperTrading: paperTradingReducer,
  },
});
