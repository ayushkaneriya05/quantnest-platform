import { configureStore } from "@reduxjs/toolkit";
import authReducer from "./authSlice";
import notificationReducer from "./notificationSlice";
import sidebarReducer from "./sidebarSlice";
import websocketReducer from "./websocketSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    notification: notificationReducer,
    sidebar: sidebarReducer,
    websocket: websocketReducer,
  },
});
