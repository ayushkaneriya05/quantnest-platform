import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { Suspense, useEffect, useRef } from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import { usePlatform } from '@/shared/context/platform';
import { useSidebar } from "@/shared/hooks/useSidebar";
import { useWebSocket } from "@/shared/hooks/useWebSocket";
import { usePageTitle } from "@/shared/hooks/use-page-title";
import { PageActionsProvider } from "@/shared/context/PageActionsContext";
import { usePageActionState } from "@/shared/context/pageActions";
import ErrorBoundary from "@/shared/components/ErrorBoundary";
import Sidebar from "./sidebar";
import MainContentHeader from "./main-content-header";

function AppContent() {
  const { executionScopes, loading, error } = usePlatform();
  const { isOpen, isDesktop, closeMobile } = useSidebar();
  const { title, subtitle } = usePageTitle();
  const { actions, headerContent } = usePageActionState();
  const { pathname } = useLocation();
  const requiredScope = /^\/(paper|terminal)(\/|$)/.test(pathname) ? 'paper'
    : /^\/(live|brokers)(\/|$)/.test(pathname) && !pathname.startsWith('/brokers/charge-profiles') ? 'live' : null;
  const mainRef = useRef(null);
  useWebSocket();
  useEffect(() => {
    closeMobile();
    mainRef.current?.scrollTo({ top: 0 });
  }, [pathname, closeMobile]);
  useEffect(() => { if (isDesktop) closeMobile(); }, [isDesktop, closeMobile]);
  useEffect(() => { document.title = `${title} | QuantNest`; }, [title]);
  if (loading && requiredScope) return <GlobalLoader text="Loading page…" />;
  if (error && requiredScope) return <section className="container-padding space-y-4 py-10"><h1 className="text-2xl font-semibold">Unable to load execution settings</h1><p className="text-muted-foreground">Check your connection and reload the workspace.</p><button type="button" className="rounded-lg border border-border px-5 py-3" onClick={() => window.location.reload()}>Reload workspace</button></section>;
  return <div className="flex h-[var(--viewport-height)] min-h-0 overflow-hidden bg-background text-foreground">
    <a href="#main-content" className="sr-only z-[100] rounded-md bg-primary p-3 text-primary-foreground focus:not-sr-only focus:absolute focus:left-4 focus:top-4">Skip to content</a>
    <Sidebar />
    <div className={`flex min-h-0 min-w-0 flex-1 flex-col ${isDesktop && isOpen ? "lg:ml-64" : ""}`}>
      <MainContentHeader title={title} subtitle={subtitle} actions={actions} customContent={headerContent} />
      <main id="main-content" tabIndex={-1} ref={mainRef} className="scrollbar-theme flex min-h-0 min-w-0 flex-1 flex-col overflow-auto outline-none">
        <ErrorBoundary><Suspense fallback={<GlobalLoader text="Loading page…" />}>{requiredScope && !executionScopes.includes(requiredScope) ? <section className="container-padding py-10 max-w-3xl space-y-5"><h1 className="text-2xl font-semibold">Execution scope is not enabled</h1><p className="text-muted-foreground">This page requires the {requiredScope === 'paper' ? 'Paper' : 'Live'} execution scope in this workspace.</p><Link className="inline-block rounded-lg border border-border px-5 py-3" to="/overview">Open overview</Link></section> : <Outlet />}</Suspense></ErrorBoundary>
      </main>
    </div>
  </div>;
}
export default function AppLayout() {
  return <PageActionsProvider><AppContent /></PageActionsProvider>;
}
