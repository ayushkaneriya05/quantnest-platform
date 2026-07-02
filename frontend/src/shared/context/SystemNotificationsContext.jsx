import React, { createContext, useContext, useEffect } from "react";
import { useSystemNotifications } from "../hooks/useSystemNotifications";
import { analyticsSuiteApi } from "../services/analyticsSuiteApi";

const SystemNotificationsContext = createContext(null);

export function SystemNotificationsProvider({ children }) {
  const notificationsHook = useSystemNotifications();

  // On mount, fetch the initial unread count from the backend API
  useEffect(() => {
    const fetchInitialCount = async () => {
      try {
        const res = await analyticsSuiteApi.getNotificationSummary();
        const unread = res.data?.unread || 0;
        notificationsHook.initializeUnreadCount(unread);
      } catch (err) {
        console.error("Failed to fetch initial unread notification count", err);
      }
    };
    fetchInitialCount();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <SystemNotificationsContext.Provider value={notificationsHook}>
      {children}
    </SystemNotificationsContext.Provider>
  );
}

export function useSystemNotificationsContext() {
  const context = useContext(SystemNotificationsContext);
  if (!context) {
    throw new Error("useSystemNotificationsContext must be used within a SystemNotificationsProvider");
  }
  return context;
}
