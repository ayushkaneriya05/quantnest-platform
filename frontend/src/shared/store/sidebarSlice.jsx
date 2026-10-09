import { createSlice } from "@reduxjs/toolkit";

const sidebarSlice = createSlice({
  name: "sidebar",
  initialState: { desktopOpen: true, mobileOpen: false },
  reducers: {
    setSidebarOpen(state, { payload: { desktop, open } }) {
      const key = desktop ? "desktopOpen" : "mobileOpen";
      state[key] = open ?? !state[key];
    },
    closeMobileSidebar(state) { state.mobileOpen = false; },
  },
});
export const { setSidebarOpen, closeMobileSidebar } = sidebarSlice.actions;
export default sidebarSlice.reducer;
