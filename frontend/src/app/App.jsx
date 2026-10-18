import AppRoutes from "./AppRoutes";
import { useEffect } from "react";
import { useAuthSession } from "@/shared/hooks/useAuthSession";
import { useViewportHeight } from "@/shared/hooks/useViewportHeight";
import ErrorBoundary from "@/shared/components/ErrorBoundary";
import { EnumsProvider } from "@/shared/context/EnumsContext";
import PlatformProvider from '@/shared/context/PlatformProvider';

import { NotificationContainer } from "@/shared/components/ui/notification";

import { useNotifications } from "@/shared/hooks/useNotifications";
import {reportClientError} from "@/shared/services/clientErrors";

function AppContent() {
  useViewportHeight();
  useAuthSession();
  const notifications = useNotifications();

  // Global error handler for unhandled promise rejections
  useEffect(() => {
    const handleUnhandledRejection = (event) => {
      if ((import.meta.env || {}).DEV) console.error("Unhandled promise rejection:", event.reason);
      reportClientError("app_failure");
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
      <PlatformProvider>
      <SystemNotificationsProvider>
        <EnumsProvider>
          <AppContent />
        </EnumsProvider>
      </SystemNotificationsProvider>
      </PlatformProvider>
    </ErrorBoundary>
  );
}

export default App;
