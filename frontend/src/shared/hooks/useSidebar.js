import { useCallback } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  toggleSidebar,
  closeSidebar,
  openSidebar,
  initializeSidebar,
} from "../store/sidebarSlice";

export function useSidebar() {
  const dispatch = useDispatch();
  const isOpen = useSelector((state) => state.sidebar.isOpen);

  const toggle = useCallback(() => dispatch(toggleSidebar()), [dispatch]);
  const close = useCallback(() => dispatch(closeSidebar()), [dispatch]);
  const open = useCallback(() => dispatch(openSidebar()), [dispatch]);
  const initialize = useCallback(
    () => dispatch(initializeSidebar()),
    [dispatch]
  );

  return { isOpen, toggle, close, open, initialize };
}
