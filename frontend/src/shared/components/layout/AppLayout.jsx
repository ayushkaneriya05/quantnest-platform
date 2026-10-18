import { Suspense, useEffect, useRef } from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import { usePlatform } from '@/shared/context/platform';
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
  const { executionScopes, loading, error } = usePlatform();
  const { isOpen, isDesktop, closeMobile } = useSidebar();
  const { title, subtitle } = usePageTitle();
  const { actions, headerContent } = usePageActionState();
  const { pathname } = useLocation();
  const privatePath = pathname.startsWith('/live/') || (pathname.startsWith('/brokers') && !pathname.startsWith('/brokers/charge-profiles'));
  const privateOnly = !executionScopes.includes('live') && privatePath;
  const mainRef = useRef(null);
  useWebSocket();
  useEffect(() => {
    closeMobile();
    mainRef.current?.scrollTo({ top: 0 });
  }, [pathname, closeMobile]);
  useEffect(() => { if (isDesktop) closeMobile(); }, [isDesktop, closeMobile]);
  useEffect(() => { document.title = `${title} | QuantNest`; }, [title]);
  if (loading && privatePath) return <RouteLoading />;
  if (error && privatePath) return <section className="container-padding space-y-4 py-10"><h1 className="text-2xl font-semibold">Unable to load execution settings</h1><p className="text-muted-foreground">Check your connection and reload the workspace.</p><button type="button" className="rounded-lg border border-border px-5 py-3" onClick={() => window.location.reload()}>Reload workspace</button></section>;
  return <div className="flex h-[var(--viewport-height)] min-h-0 overflow-hidden bg-background text-foreground">
    <a href="#main-content" className="sr-only z-[100] rounded-md bg-primary p-3 text-primary-foreground focus:not-sr-only focus:absolute focus:left-4 focus:top-4">Skip to content</a>
    <Sidebar />
    <div className={`flex min-h-0 min-w-0 flex-1 flex-col ${isDesktop && isOpen ? "lg:ml-64" : ""}`}>
      <MainContentHeader title={title} subtitle={subtitle} actions={actions} customContent={headerContent} />
      <main id="main-content" tabIndex={-1} ref={mainRef} className="scrollbar-theme flex min-h-0 min-w-0 flex-1 flex-col overflow-auto outline-none">
        <ErrorBoundary><Suspense fallback={<RouteLoading />}>{privateOnly ? <section className="container-padding py-10 max-w-3xl space-y-5"><h1 className="text-2xl font-semibold">Broker execution belongs to QuantNest Private</h1><p className="text-muted-foreground">Workspace covers your research, strategy rules, historical tests and simulated Paper execution. A customer-owned Private deployment can support broker execution after its separate setup, broker qualification and Live activation.</p><div className="flex flex-wrap gap-4"><Link className="rounded-lg bg-primary px-5 py-3 text-primary-foreground" to="/support?request=private">Request a Private assessment</Link><Link className="rounded-lg border border-border px-5 py-3" to="/paper">Open Paper trading</Link></div></section> : <Outlet />}</Suspense></ErrorBoundary>
      </main>
    </div>
  </div>;
}
export default function AppLayout() {
  return <PageActionsProvider><AppContent /></PageActionsProvider>;
}
