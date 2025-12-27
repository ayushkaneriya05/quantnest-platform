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

  const addNotificationAction = (notification) => {
    const id = Date.now().toString();
    dispatch(addNotification({ ...notification, id }));
    return id;
  };

  const removeNotificationAction = (id) => {
    dispatch(removeNotification(id));
  };

  const clearAll = () => {
    dispatch(clearAllNotifications());
  };

  // Convenience methods
  const notify = {
    success: (message, options = {}) =>
      addNotificationAction({ type: "success", message, ...options }),

    error: (message, options = {}) =>
      addNotificationAction({ type: "error", message, ...options }),

    info: (message, options = {}) =>
      addNotificationAction({ type: "info", message, ...options }),

    warning: (message, options = {}) =>
      addNotificationAction({ type: "warning", message, ...options }),
  };

  return {
    notifications,
    addNotification: addNotificationAction,
    removeNotification: removeNotificationAction,
    clearAll,
    notify,
  };
}
