import PageTabs from "@/shared/components/PageTabs";
import { useEffect, useState, useCallback } from "react";
import { Activity, BarChart3, Briefcase, RefreshCw, TrendingUp, Receipt } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
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
  const [activeTab, setActiveTab] = useState("portfolio");
  const data = useLiveTradingData({ includePortfolio: true, notify });

  const handleRefresh = useCallback(async () => {
    await data.refresh();
    notify.success("Live trading data refreshed");
  }, [data.refresh, notify]);

  useEffect(() => {
    const HeaderTabs = () => (
      <div className="flex min-w-0 w-full items-center gap-2">
        <PageTabs className="flex-1" label="Live portfolio sections" value={activeTab} onValueChange={setActiveTab} items={tabs.map(({ id, label, icon }) => ({ value: id, label, icon }))} />
        <div className="ml-auto hidden sm:block"><LiveSyncStatus isConnected={data.isConnected} /></div>
        <Button variant="ghost" size="sm" onClick={handleRefresh} disabled={data.refreshing} aria-label="Refresh live trading data">
          <RefreshCw className={`h-4 w-4 ${data.refreshing ? "animate-spin" : ""}`} />
        </Button>
      </div>
    );
    setPageHeader(<HeaderTabs />);
    return clearPageHeader;
  }, [activeTab, clearPageHeader, data.isConnected, data.refreshing, handleRefresh, setPageHeader]);

  const content = data.loading ? (
    <Card className="border-border bg-card/60">
      <CardContent className="py-12 text-center text-muted-foreground">Loading live trading data…</CardContent>
    </Card>
  ) : (
    <>
      {activeTab === "portfolio" && <LivePortfolioSummary summary={data.summary || {}} sessions={data.sessions} />}
      {activeTab === "positions" && (
        <LivePositionsAnalysis
          positions={data.positions.results}
          positionsForPnL={data.pnlPositions}
          summary={data.positionsSummary}
          allocationFilter={data.positionAllocation}
          onAllocationChange={(value) => data.filterPositions(value).catch((error) => notify.error(getApiErrorMessage(error, "Could not filter positions")))}
          pagination={{ page: data.positionsPage, count: data.positions.count }}
          onPageChange={data.changePositionsPage}
        />
      )}
      {activeTab === "orders" && (
        <LiveOrdersAnalysis
          orders={data.orders.results}
          summary={data.ordersSummary}
          allocationFilter={data.orderAllocation}
          onAllocationChange={(value) => data.filterOrderAllocation(value).catch((error) => notify.error(getApiErrorMessage(error, "Could not filter orders")))}
          statusFilter={data.orderStatus}
          onStatusChange={(value) => data.filterOrders(value).catch((error) => notify.error(getApiErrorMessage(error, "Could not filter orders")))}
          pagination={{ page: data.ordersPage, count: data.orders.count }}
          onPageChange={data.changeOrdersPage}
        />
      )}
      {activeTab === "performance" && <LivePerformance summary={data.summary || {}} positions={data.pnlPositions} />}
      {activeTab === "trades" && <LiveTradesAnalysis
        trades={data.trades.results}
        pagination={{ page: data.tradesPage, count: data.trades.count }}
        summary={data.tradesSummary}
        allocationFilter={data.tradeAllocation}
        onAllocationChange={(value) => data.filterTrades(value).catch((error) => notify.error(getApiErrorMessage(error, "Could not filter trades")))}
        onPageChange={data.changeTradesPage}
      />}
    </>
  );

  return <div className="container-padding space-y-6 py-6 lg:py-8">{content}</div>;
}
