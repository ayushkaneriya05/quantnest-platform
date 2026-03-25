import React, { useEffect } from "react";
import { Outlet } from "react-router-dom";
import { useSidebar } from "@/shared/hooks/useSidebar";
import { useWebSocket } from "@/shared/hooks/useWebSocket";
import { usePageTitle } from "@/shared/hooks/use-page-title";
import { PageActionsProvider, usePageActions } from "@/shared/context/PageActionsContext";
import Sidebar from "@/features/dashboard/components/layout/sidebar";
import MainContentHeader from "@/features/dashboard/components/layout/main-content-header";

function DashboardContent() {
  const { isOpen, initialize } = useSidebar();
  const { title, subtitle } = usePageTitle();
  const { actions, headerContent } = usePageActions();

  // Initialize WebSocket connection - this should be stable
  useWebSocket();

  useEffect(() => {
    // Initialize sidebar state based on screen size
    initialize();

    // Handle window resize
    const handleResize = () => {
      initialize();
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [initialize]);

  return (
    <div className="flex h-screen bg-black overflow-hidden">
      <Sidebar />
      <div
        className={`flex-1 flex flex-col transition-all duration-300 min-w-0 ${
          isOpen ? "ml-64 sm:ml-72 lg:ml-64" : "ml-0"
        }`}
      >
        <MainContentHeader 
          title={title} 
          subtitle={subtitle} 
          actions={actions}
          customContent={headerContent} 
        />
        <main className="flex-1 overflow-auto scrollbar-theme flex flex-col">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default function DashboardLayout() {
  return (
    <PageActionsProvider>
      <DashboardContent />
    </PageActionsProvider>
  );
}

