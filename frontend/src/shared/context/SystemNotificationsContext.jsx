import { createContext, useContext, useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import { useSystemNotifications } from "../hooks/useSystemNotifications";
import { notificationApi } from "../services/notificationApi";

const SystemNotificationsContext = createContext(null);

export function SystemNotificationsProvider({ children }) {
  const notificationsHook = useSystemNotifications();
  const { syncUnreadCount } = notificationsHook;
  const accessToken = useSelector((state) => state.auth.accessToken);

  // On mount, fetch the initial unread count from the backend API
  useEffect(() => {
    if (!accessToken) {
      syncUnreadCount(0);
      return undefined;
    }
    const fetchInitialCount = async () => {
      try {
        const res = await notificationApi.getSummary();
        const unread = res.data?.unread || 0;
        syncUnreadCount(unread);
      } catch (err) {
        console.error("Failed to fetch initial unread notification count", err);
      }
    };
    fetchInitialCount();
    return undefined;
  }, [accessToken, syncUnreadCount]);

  return (
    <SystemNotificationsContext.Provider value={notificationsHook}>
      {children}
    </SystemNotificationsContext.Provider>
  );
}

SystemNotificationsProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export function useSystemNotificationsContext() {
  const context = useContext(SystemNotificationsContext);
  if (!context) {
    throw new Error("useSystemNotificationsContext must be used within a SystemNotificationsProvider");
  }
  return context;
}
