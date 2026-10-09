import { Suspense, useEffect, useRef } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useSidebar } from "@/shared/hooks/useSidebar";
import { useWebSocket } from "@/shared/hooks/useWebSocket";
import { usePageTitle } from "@/shared/hooks/use-page-title";
import { PageActionsProvider } from "@/shared/context/PageActionsContext";
import { usePageActionState } from "@/shared/context/pageActions";
import ErrorBoundary from "@/shared/components/ErrorBoundary";
import RouteLoading from "@/shared/components/RouteLoading";
import Sidebar from "./sidebar";
import MainContentHeader from "./main-content-header";

function AppContent() {
  const { isOpen, isDesktop, closeMobile } = useSidebar();
  const { title, subtitle } = usePageTitle();
  const { actions, headerContent } = usePageActionState();
  const { pathname } = useLocation();
  const mainRef = useRef(null);
  useWebSocket();
  useEffect(() => {
    closeMobile();
    mainRef.current?.scrollTo({ top: 0 });
  }, [pathname, closeMobile]);
  useEffect(() => { if (isDesktop) closeMobile(); }, [isDesktop, closeMobile]);
  useEffect(() => { document.title = `${title} | QuantNest`; }, [title]);
  return <div className="flex h-[var(--viewport-height)] min-h-0 overflow-hidden bg-background text-foreground">
    <a href="#main-content" className="sr-only z-[100] rounded-md bg-primary p-3 text-primary-foreground focus:not-sr-only focus:absolute focus:left-4 focus:top-4">Skip to content</a>
    <Sidebar />
    <div className={`flex min-h-0 min-w-0 flex-1 flex-col ${isDesktop && isOpen ? "lg:ml-64" : ""}`}>
      <MainContentHeader title={title} subtitle={subtitle} actions={actions} customContent={headerContent} />
      <main id="main-content" tabIndex={-1} ref={mainRef} className="scrollbar-theme flex min-h-0 min-w-0 flex-1 flex-col overflow-auto outline-none">
        <ErrorBoundary><Suspense fallback={<RouteLoading />}><Outlet /></Suspense></ErrorBoundary>
      </main>
    </div>
  </div>;
}
export default function AppLayout() {
  return <PageActionsProvider><AppContent /></PageActionsProvider>;
}
