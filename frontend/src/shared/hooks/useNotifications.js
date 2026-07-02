import { useCallback, useMemo } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  addNotification,
  removeNotification,
  clearAllNotifications,
} from "../store/notificationSlice";

export function useNotifications() {
  const dispatch = useDispatch();
  const notifications = useSelector(
    (state) => state.notification.notifications
  );

  const addNotificationAction = useCallback((notification) => {
    const id = Date.now().toString();
    const newNotification = { ...notification, id };
    console.info("Dispatching Notification to Redux:", newNotification);
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
      addNotificationAction({ type: "success", message, ...options }),

    error: (message, options = {}) =>
      addNotificationAction({ type: "error", message, ...options }),

    info: (message, options = {}) =>
      addNotificationAction({ type: "info", message, ...options }),

    warning: (message, options = {}) =>
      addNotificationAction({ type: "warning", message, ...options }),
  }), [addNotificationAction]);

  return {
    notifications,
    addNotification: addNotificationAction,
    removeNotification: removeNotificationAction,
    clearAll,
    notify,
  };
}
