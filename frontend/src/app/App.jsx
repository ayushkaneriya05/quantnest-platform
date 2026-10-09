import AppRoutes from "./AppRoutes";
import { useEffect } from "react";
import { useAuthSession } from "@/shared/hooks/useAuthSession";
import { useViewportHeight } from "@/shared/hooks/useViewportHeight";
import ErrorBoundary from "@/shared/components/ErrorBoundary";
import { EnumsProvider } from "@/shared/context/EnumsContext";

import { NotificationContainer } from "@/shared/components/ui/notification";

import { useNotifications } from "@/shared/hooks/useNotifications";

function AppContent() {
  useViewportHeight();
  useAuthSession();
  const notifications = useNotifications();

  // Global error handler for unhandled promise rejections
  useEffect(() => {
    const handleUnhandledRejection = (event) => {
      console.error("Unhandled promise rejection:", event.reason);
      notifications.notify.error("An unexpected error occurred");
    };

    window.addEventListener("unhandledrejection", handleUnhandledRejection);

    return () => {
      window.removeEventListener(
        "unhandledrejection",
        handleUnhandledRejection,
      );
    };
  }, [notifications.notify]);

  return (
    <div className="min-h-[var(--viewport-height)] bg-background text-foreground">
      <AppRoutes />

      {/* Global Notification System */}
      <NotificationContainer
        notifications={notifications.notifications}
        onClose={notifications.removeNotification}
      />
    </div>
  );
}

import { SystemNotificationsProvider } from "@/shared/context/SystemNotificationsContext";

function App() {
  return (
    <ErrorBoundary>
      <SystemNotificationsProvider>
        <EnumsProvider>
          <AppContent />
        </EnumsProvider>
      </SystemNotificationsProvider>
    </ErrorBoundary>
  );
}

export default App;
