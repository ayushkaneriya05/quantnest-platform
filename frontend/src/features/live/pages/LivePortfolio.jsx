import { useQueryState } from "@/shared/hooks/usePagination";
import RefreshButton from "@/shared/components/RefreshButton";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import PageTabs from "@/shared/components/PageTabs";
import { useEffect } from "react";
import { Activity, BarChart3, Briefcase, TrendingUp, Receipt } from "lucide-react";

import { Card, CardContent } from "@/shared/components/ui/card";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { usePageActions } from "@/shared/context/pageActions";
import { useLiveTradingData } from "@/features/live/hooks/useLiveTradingData.js";
import LivePortfolioSummary from "@/features/live/components/LivePortfolioSummary.jsx";
import LivePositionsAnalysis from "@/features/live/components/LivePositionsAnalysis.jsx";
import LiveOrdersAnalysis from "@/features/live/components/LiveOrdersAnalysis.jsx";
import LivePerformance from "@/features/live/components/LivePerformance.jsx";
import LiveTradesAnalysis from "@/features/live/components/LiveTradesAnalysis.jsx";
import LiveSyncStatus from "@/features/live/components/LiveSyncStatus.jsx";

const tabs = [
  { id: "portfolio", label: "Overview", icon: Briefcase },
  { id: "positions", label: "Positions", icon: TrendingUp },
  { id: "orders", label: "Orders", icon: Activity },
  { id: "trades", label: "Trades", icon: Receipt },
  { id: "performance", label: "Performance", icon: BarChart3 },
];

export default function LivePortfolio() {
  const { notify } = useNotifications();
  const { setPageHeader, clearPageHeader } = usePageActions();
  const [activeTab, setActiveTab] = useQueryState("section", "portfolio", { resetPage: false });
  const data = useLiveTradingData({ includePortfolio: true, activeTab, notify });
  const { refresh: handleRefresh } = data;

  useEffect(() => {
    const HeaderTabs = () => (
      <div className="flex min-w-0 w-full items-center gap-2">
        <PageTabs className="flex-1" label="Live portfolio sections" value={activeTab} onValueChange={setActiveTab} items={tabs.map(({ id, label, icon }) => ({ value: id, label, icon }))} />
        <div className="ml-auto hidden sm:block"><LiveSyncStatus isConnected={data.isConnected} /></div>
        <RefreshButton onClick={handleRefresh} label="Refresh live trading data" disabled={data.refreshing} loading={data.refreshing} />
      </div>
    );
    setPageHeader(<HeaderTabs />);
    return clearPageHeader;
  }, [activeTab, setActiveTab, clearPageHeader, data.isConnected, data.refreshing, handleRefresh, setPageHeader]);

  const content = data.error ? <WorkspaceState error={data.error} onRetry={data.refresh} /> : data.loading ? (
    <Card className="border-border bg-card/60">
      <CardContent className="py-12 text-center text-muted-foreground"><GlobalLoader inline text="Loading live trading data…" /></CardContent>
    </Card>
  ) : (
    <>
      {activeTab === "portfolio" && <LivePortfolioSummary summary={data.summary} />}
      {activeTab === "positions" && (
        <LivePositionsAnalysis
          positions={data.positions.results}
          summary={data.positionsSummary}
          allocationFilter={data.positionAllocation}
          onAllocationChange={data.filterPositions}
          pagination={data.positions} loading={data.listLoading} onPageSizeChange={data.positionPages.setPageSize}
          onPageChange={data.positionPages.setPage}
        />
      )}
      {activeTab === "orders" && (
        <LiveOrdersAnalysis
          orders={data.orders.results}
          summary={data.ordersSummary}
          allocationFilter={data.orderAllocation}
          onAllocationChange={data.filterOrderAllocation}
          statusFilter={data.orderStatus}
          onStatusChange={data.filterOrders}
          pagination={data.orders} loading={data.listLoading} onPageSizeChange={data.orderPages.setPageSize}
          onPageChange={data.orderPages.setPage}
        />
      )}
      {activeTab === "performance" && <LivePerformance summary={data.summary || {}} />}
      {activeTab === "trades" && <LiveTradesAnalysis
        trades={data.trades.results}
        pagination={data.trades} loading={data.listLoading} onPageSizeChange={data.tradePages.setPageSize}
        summary={data.tradesSummary}
        allocationFilter={data.tradeAllocation}
        onAllocationChange={data.filterTrades}
        onPageChange={data.tradePages.setPage}
      />}
    </>
  );

  return <div className="page-content">{content}</div>;
}
