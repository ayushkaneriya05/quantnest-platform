import { useEffect, useState, useCallback } from "react";
import {
  Briefcase,
  TrendingUp,
  Activity,
  BarChart3,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { usePageActions } from "@/shared/context/PageActionsContext";
import { useLiveTradingWebSocket } from "@/shared/hooks/useLiveTradingWebSocket";
import { liveTradingApi } from "@/shared/services/liveTradingApi";
import { useMemo } from "react";

import LivePortfolioSummary from "./components/LivePortfolioSummary";
import LivePositionsAnalysis from "./components/LivePositionsAnalysis";
import LiveOrdersAnalysis from "./components/LiveOrdersAnalysis";
import LivePerformance from "./components/LivePerformance";
import LiveStrategiesOverview from "./components/LiveStrategiesOverview";

export default function LivePortfolio() {
  const { notify } = useNotifications();
  const { setPageHeader, clearPageHeader } = usePageActions();
  const [activeTab, setActiveTab] = useState("portfolio");
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [summaryRes, sessionsRes, positionsRes, ordersRes] =
        await Promise.all([
          liveTradingApi.getSummary(),
          liveTradingApi.getSessions(),
          liveTradingApi.getPositions(),
          liveTradingApi.getOrders(),
        ]);

      setSummary(summaryRes.data || {});
      setSessions(
        Array.isArray(sessionsRes.data?.results)
          ? sessionsRes.data.results
          : sessionsRes.data || [],
      );
      setPositions(positionsRes.data || []);
      setOrders(ordersRes.data?.results || ordersRes.data || []);
    } catch (error) {
      notify.error(
        error?.response?.data?.detail || "Failed to load live portfolio",
      );
    } finally {
      setLoading(false);
    }
  }, [notify]);

  const handleLiveUpdate = useCallback((payload) => {
    if (payload?.event_type === "SESSION_UPDATE" && payload?.data?.session_id) {
      setSessions((prev) =>
        prev.map((s) =>
          s.id === payload.data.session_id
            ? { ...s, status: payload.data.status }
            : s,
        ),
      );
    } else if (
      payload?.event_type === "ORDER_UPDATE" ||
      payload?.event_type === "POSITION_UPDATE"
    ) {
      // Refresh only the affected data
      liveTradingApi
        .getSummary()
        .then((res) => setSummary(res.data || {}))
        .catch(console.error);
      liveTradingApi
        .getPositions()
        .then((res) => setPositions(res.data || []))
        .catch(console.error);
      liveTradingApi
        .getOrders()
        .then((res) => setOrders(res.data?.results || res.data || []))
        .catch(console.error);
    }
  }, []);

  const { isConnected: isLiveWsConnected } =
    useLiveTradingWebSocket(handleLiveUpdate);

  // Load data only once on mount
  useEffect(() => {
    loadData();
  }, []);

  const handleRefresh = useCallback(async () => {
    await loadData();
    notify.success("Portfolio data refreshed");
  }, [loadData, notify]);

  // Inject tab navigation into MainContentHeader
  useEffect(() => {
    const HeaderTabs = () => (
      <div className="flex items-center justify-between w-full">
        <div className="flex space-x-1 bg-gray-800/30 border border-gray-700/30 rounded-lg p-1 w-full max-w-2xl mx-auto sm:mx-0 sm:ml-4">
          <button
            onClick={() => setActiveTab("portfolio")}
            className={`flex-1 flex justify-center items-center gap-2 rounded-md px-3 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm font-medium transition-all duration-200 ${
              activeTab === "portfolio"
                ? "bg-gray-700/70 text-slate-100 shadow-sm"
                : "text-slate-400 hover:text-slate-300 hover:bg-gray-800/50"
            }`}
          >
            <Briefcase className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            <span className="hidden sm:inline">Portfolio</span>
          </button>
          <button
            onClick={() => setActiveTab("positions")}
            className={`flex-1 flex justify-center items-center gap-2 rounded-md px-3 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm font-medium transition-all duration-200 ${
              activeTab === "positions"
                ? "bg-gray-700/70 text-slate-100 shadow-sm"
                : "text-slate-400 hover:text-slate-300 hover:bg-gray-800/50"
            }`}
          >
            <TrendingUp className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            <span className="hidden sm:inline">Positions</span>
          </button>
          <button
            onClick={() => setActiveTab("orders")}
            className={`flex-1 flex justify-center items-center gap-2 rounded-md px-3 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm font-medium transition-all duration-200 ${
              activeTab === "orders"
                ? "bg-gray-700/70 text-slate-100 shadow-sm"
                : "text-slate-400 hover:text-slate-300 hover:bg-gray-800/50"
            }`}
          >
            <Activity className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            <span className="hidden sm:inline">Orders</span>
          </button>
          <button
            onClick={() => setActiveTab("performance")}
            className={`flex-1 flex justify-center items-center gap-2 rounded-md px-3 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm font-medium transition-all duration-200 ${
              activeTab === "performance"
                ? "bg-gray-700/70 text-slate-100 shadow-sm"
                : "text-slate-400 hover:text-slate-300 hover:bg-gray-800/50"
            }`}
          >
            <BarChart3 className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            <span className="hidden sm:inline">Performance</span>
          </button>
        </div>

        {/* Action Bar Items */}
        <div className="hidden sm:flex items-center gap-3 ml-auto px-4">
          <div className="flex items-center gap-2 text-xs font-medium">
            <div className={`h-2 w-2 rounded-full ${isLiveWsConnected ? "bg-emerald-500" : "bg-amber-500"}`} />
            <span className={isLiveWsConnected ? "text-emerald-400" : "text-amber-400"}>
              {isLiveWsConnected ? "Live Feed" : "Offline"}
            </span>
          </div>
          <div className="w-px h-4 bg-gray-700" />
          <Button
            variant="ghost"
            onClick={handleRefresh}
            disabled={loading}
            className="h-8 px-2 text-gray-400 hover:text-gray-100 hover:bg-gray-800"
            size="sm"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            <span className="sr-only">Refresh</span>
          </Button>
        </div>
      </div>
    );

    setPageHeader(<HeaderTabs />);

    return () => {
      clearPageHeader();
    };
  }, [setPageHeader, clearPageHeader, activeTab, isLiveWsConnected, loading, handleRefresh]);

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      {/* Portfolio Tab */}
      {activeTab === "portfolio" && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {loading ? (
            <Card className="border-gray-800 bg-gray-900/60">
              <CardContent className="py-12 text-center text-gray-400">
                Loading portfolio data...
              </CardContent>
            </Card>
          ) : (
            <LivePortfolioSummary summary={summary} sessions={sessions} />
          )}
        </div>
      )}

      {/* Positions Tab */}
      {activeTab === "positions" && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {loading ? (
            <Card className="border-gray-800 bg-gray-900/60">
              <CardContent className="py-12 text-center text-gray-400">
                Loading positions...
              </CardContent>
            </Card>
          ) : (
            <LivePositionsAnalysis positions={positions} sessions={sessions} />
          )}
        </div>
      )}

      {/* Orders Tab */}
      {activeTab === "orders" && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {loading ? (
            <Card className="border-gray-800 bg-gray-900/60">
              <CardContent className="py-12 text-center text-gray-400">
                Loading orders...
              </CardContent>
            </Card>
          ) : (
            <LiveOrdersAnalysis orders={orders} sessions={sessions} />
          )}
        </div>
      )}

      {/* Performance Tab */}
      {activeTab === "performance" && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {loading ? (
            <Card className="border-gray-800 bg-gray-900/60">
              <CardContent className="py-12 text-center text-gray-400">
                Loading performance data...
              </CardContent>
            </Card>
          ) : (
            <>
              <LivePerformance summary={summary} sessions={sessions} />
              <LiveStrategiesOverview sessions={sessions} />
            </>
          )}
        </div>
      )}
    </div>
  );
}
