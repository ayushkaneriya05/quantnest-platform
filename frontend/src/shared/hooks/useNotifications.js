import { useCallback, useMemo } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  addNotification,
  removeNotification,
  clearAllNotifications,
} from "../store/notificationSlice";

export function useNotifications() {
  const dispatch = useDispatch();
  const notifications = useSelector((state) => state.notification.notifications);

  const addNotificationAction = useCallback((notification) => {
    const id = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
    const newNotification = { ...notification, id };
    dispatch(addNotification(newNotification));
    return id;
  }, [dispatch]);

  const removeNotificationAction = useCallback((id) => {
    dispatch(removeNotification(id));
  }, [dispatch]);

  const clearAll = useCallback(() => {
    dispatch(clearAllNotifications());
  }, [dispatch]);

  // Convenience methods
  const notify = useMemo(() => ({
    success: (message, options = {}) =>
      addNotificationAction({ type: "INFO", variant: "success", title: "Success", message, ...options }),

    error: (message, options = {}) =>
      addNotificationAction({ type: "INFO", variant: "error", title: "Error", message, ...options }),

    info: (message, options = {}) =>
      addNotificationAction({ type: "INFO", message, ...options }),

    warning: (message, options = {}) =>
      addNotificationAction({ type: "WARNING", title: "Warning", message, ...options }),

    critical: (message, options = {}) =>
      addNotificationAction({ type: "CRITICAL", title: "Critical alert", message, ...options }),
  }), [addNotificationAction]);

  return {
    notifications,
    addNotification: addNotificationAction,
    removeNotification: removeNotificationAction,
    clearAll,
    notify,
  };
}
