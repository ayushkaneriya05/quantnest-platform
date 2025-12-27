import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  isOpen: false,
};

const sidebarSlice = createSlice({
  name: "sidebar",
  initialState,
  reducers: {
    setSidebarOpen: (state, action) => {
      state.isOpen = action.payload;
    },
    toggleSidebar: (state) => {
      state.isOpen = !state.isOpen;
    },
    closeSidebar: (state) => {
      state.isOpen = false;
    },
    openSidebar: (state) => {
      state.isOpen = true;
    },
    initializeSidebar: (state) => {
      // Set default state based on screen size
      if (typeof window !== "undefined") {
        state.isOpen = window.innerWidth >= 1024; // Open on desktop (lg breakpoint)
      }
    },
  },
});

export const {
  setSidebarOpen,
  toggleSidebar,
  closeSidebar,
  openSidebar,
  initializeSidebar,
} = sidebarSlice.actions;

export default sidebarSlice.reducer;
