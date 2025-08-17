import { configureStore } from "@reduxjs/toolkit";
import authReducer from "./authSlice"; // Assuming you have this from before

export const store = configureStore({
  reducer: {
    auth: authReducer,
  },
});
