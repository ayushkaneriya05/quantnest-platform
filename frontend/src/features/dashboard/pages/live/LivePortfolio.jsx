import { useEffect, useState, useCallback } from "react";
import { Activity, BarChart3, Briefcase, RefreshCw, TrendingUp, Receipt } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/shared/components/ui/tabs";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { usePageActions } from "@/shared/context/PageActionsContext";
import { useLiveTradingData } from "./hooks/useLiveTradingData";
import LivePortfolioSummary from "./components/LivePortfolioSummary";
import LivePositionsAnalysis from "./components/LivePositionsAnalysis";
import LiveOrdersAnalysis from "./components/LiveOrdersAnalysis";
import LivePerformance from "./components/LivePerformance";
import LiveTradesAnalysis from "./components/LiveTradesAnalysis";
import LiveSyncStatus from "./components/LiveSyncStatus";

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
      <div className="flex w-full items-center gap-3">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full max-w-2xl">
        <TabsList className="h-auto w-full justify-start gap-1 rounded-lg border border-gray-700/40 bg-gray-800/30 p-1">
          {tabs.map(({ id, label, icon: Icon }) => (
            <TabsTrigger
              key={id}
              value={id}
              className="flex flex-1 items-center gap-2 rounded-md px-3 py-2 text-xs text-slate-400 transition hover:bg-gray-800/60 hover:text-slate-200 data-[state=active]:bg-gray-700/80 data-[state=active]:text-white sm:text-sm"
            >
              <Icon className="h-4 w-4" />
              <span>{label}</span>
            </TabsTrigger>
          ))}
        </TabsList>
        </Tabs>
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
    <Card className="border-gray-800 bg-gray-900/60">
      <CardContent className="py-12 text-center text-gray-400">Loading live trading data…</CardContent>
    </Card>
  ) : (
    <>
      {activeTab === "portfolio" && <LivePortfolioSummary summary={data.summary || {}} sessions={data.sessions} />}
      {activeTab === "positions" && (
        <LivePositionsAnalysis
          positions={data.positions.results}
          positionsForPnL={data.pnlPositions}
          summary={data.positionsSummary}
          sessions={data.sessions}
          allocationFilter={data.positionAllocation}
          onAllocationChange={(value) => data.filterPositions(value).catch(() => notify.error("Could not filter positions"))}
          pagination={{ page: data.positionsPage, count: data.positions.count }}
          onPageChange={data.changePositionsPage}
        />
      )}
      {activeTab === "orders" && (
        <LiveOrdersAnalysis
          orders={data.orders.results}
          summary={data.ordersSummary}
          sessions={data.sessions}
          allocationFilter={data.orderAllocation}
          onAllocationChange={(value) => data.filterOrderAllocation(value).catch(() => notify.error("Could not filter orders"))}
          statusFilter={data.orderStatus}
          onStatusChange={(value) => data.filterOrders(value).catch(() => notify.error("Could not filter orders"))}
          pagination={{ page: data.ordersPage, count: data.orders.count }}
          onPageChange={data.changeOrdersPage}
        />
      )}
      {activeTab === "performance" && <LivePerformance summary={data.summary || {}} positions={data.pnlPositions} />}
      {activeTab === "trades" && <LiveTradesAnalysis
        trades={data.trades.results}
        pagination={{ page: data.tradesPage, count: data.trades.count }}
        summary={data.tradesSummary}
        sessions={data.sessions}
        allocationFilter={data.tradeAllocation}
        onAllocationChange={(value) => data.filterTrades(value).catch(() => notify.error("Could not filter trades"))}
        onPageChange={data.changeTradesPage}
      />}
    </>
  );

  return <div className="container-padding space-y-6 py-6 lg:py-8">{content}</div>;
}
