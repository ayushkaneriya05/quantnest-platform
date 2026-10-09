import { useCallback } from "react";
import { useDispatch, useSelector } from "react-redux";
import { setSidebarOpen, closeMobileSidebar } from "../store/sidebarSlice";
import { useMediaQuery } from "./useMediaQuery";

export function useSidebar() {
  const dispatch = useDispatch();
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const isOpen = useSelector((state) => isDesktop ? state.sidebar.desktopOpen : state.sidebar.mobileOpen);
  const toggle = useCallback(() => dispatch(setSidebarOpen({ desktop: isDesktop })), [dispatch, isDesktop]);
  const close = useCallback(() => dispatch(setSidebarOpen({ desktop: isDesktop, open: false })), [dispatch, isDesktop]);
  const open = useCallback(() => dispatch(setSidebarOpen({ desktop: isDesktop, open: true })), [dispatch, isDesktop]);
  const closeMobile = useCallback(() => dispatch(closeMobileSidebar()), [dispatch]);
  return { isOpen, isDesktop, toggle, close, open, closeMobile };
}
