import { useEffect, useMemo, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  Pause,
  Play,
  RefreshCw,
  RotateCw,
  Power,
  Zap,
  Settings,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardContent,
} from "@/shared/components/ui/card";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { useWebSocket } from "@/shared/hooks/useWebSocket";
import { useLiveTradingWebSocket } from "@/shared/hooks/useLiveTradingWebSocket";
import { liveTradingApi } from "@/shared/services/liveTradingApi";
import LivePositionsTable from "./LivePositionsTable";
import LiveOrdersTable from "./LiveOrdersTable";
import LiveAllocationUpdateModal from "./components/LiveAllocationUpdateModal";
import LiveHotSwapModal from "./components/LiveHotSwapModal";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/shared/components/ui/tabs";
import { formatNumber, formatDateTime } from "@/shared/utils/formatters";
import { statusTone } from "@/shared/constants/statusColors";

export default function LiveStrategies() {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { connectionStatus } = useWebSocket();
  const [sessions, setSessions] = useState([]);
  const [expandedSession, setExpandedSession] = useState(null);
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState("");
  const [allocationModal, setAllocationModal] = useState({ open: false, session: null });
  const [hotSwapModal, setHotSwapModal] = useState({ open: false, session: null });

  const loadData = async () => {
    try {
      setLoading(true);
      const [sessionsRes, positionsRes, ordersRes] = await Promise.all([
        liveTradingApi.getSessions(),
        liveTradingApi.getPositions(),
        liveTradingApi.getOrders(),
      ]);
      setSessions(
        Array.isArray(sessionsRes.data?.results)
          ? sessionsRes.data.results
          : sessionsRes.data || [],
      );
      setPositions(positionsRes.data || []);
      setOrders(ordersRes.data?.results || ordersRes.data || []);
    } catch (error) {
      notify.error(
        error?.response?.data?.detail || "Failed to load live strategies",
      );
    } finally {
      setLoading(false);
    }
  };

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

  useEffect(() => {
    loadData();
  }, []);

  const runAction = async (key, action, successMessage) => {
    try {
      setBusyAction(key);
      await action();
      if (successMessage) notify.success(successMessage);
      await loadData();
    } catch (error) {
      notify.error(
        error?.response?.data?.detail || "Live trading action failed",
      );
    } finally {
      setBusyAction("");
    }
  };

  const pageActions = useMemo(
    () => (
      <>
        <div className="hidden lg:flex items-center gap-4 mr-2 text-xs font-medium border-r border-gray-700 pr-4">
          <div className="flex items-center gap-1.5">
            <div className={`h-2 w-2 rounded-full ${connectionStatus === "connected" ? "bg-emerald-500" : "bg-amber-500"}`} />
            <span className={connectionStatus === "connected" ? "text-emerald-400" : "text-amber-400"}>
              {connectionStatus === "connected" ? "Market Data" : "Market Data Offline"}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className={`h-2 w-2 rounded-full ${isLiveWsConnected ? "bg-emerald-500" : "bg-amber-500"}`} />
            <span className={isLiveWsConnected ? "text-emerald-400" : "text-amber-400"}>
              {isLiveWsConnected ? "Live Feed" : "Feed Offline"}
            </span>
          </div>
        </div>
        <Button
          onClick={() => navigate("/dashboard/strategy/list")}
          className="bg-indigo-600 hover:bg-indigo-500 text-white"
        >
          <Zap className="mr-2 h-4 w-4" />
          Deploy Strategy
        </Button>
        <Button
          variant="outline"
          onClick={loadData}
          className="border-gray-700 text-gray-100"
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
        <Button
          className="bg-red-600 hover:bg-red-500"
          onClick={() =>
            runAction(
              "stop-all",
              () => liveTradingApi.stopAllSessions({ close_positions: false }),
              "All live sessions stopped",
            )
          }
          disabled={busyAction === "stop-all"}
        >
          <Power className="mr-2 h-4 w-4" />
          Stop All
        </Button>
      </>
    ),
    [busyAction, connectionStatus, isLiveWsConnected, navigate, loadData],
  );

  useSetPageActions(pageActions);

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      {(!isLiveWsConnected || connectionStatus !== "connected") && (
        <div className="rounded-xl border border-red-900/50 bg-red-500/10 p-4 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-medium text-red-200">API Outage / Connection Lost</h4>
            <p className="text-xs text-red-300/80 mt-1">
              Live market feed or broker API connection is currently down. Order execution and status updates may be delayed.
            </p>
          </div>
        </div>
      )}

      {loading ? (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-400">
            Loading live sessions...
          </CardContent>
        </Card>
      ) : sessions.length === 0 ? (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-400">
            No live strategies deployed yet. Deploy from the strategy list into
            a connected broker account.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {sessions.map((session) => (
            <div
              key={session.id}
              className="border border-gray-800 bg-gray-900/60 rounded-xl overflow-hidden shadow-lg transition-all"
            >
              {/* Compact Header Row */}
              <div className="flex flex-col lg:flex-row lg:items-center justify-between p-4 gap-4 hover:bg-gray-800/30 transition-colors">
                {/* Identity & Status */}
                <div className="flex items-center gap-4 flex-1">
                  <div className="flex-shrink-0 min-w-[80px] flex justify-center">
                    <Badge
                      className={`px-3 py-1.5 text-xs font-semibold text-center flex flex-col items-center leading-tight gap-0.5 ${
                        statusTone[session.status] || statusTone.STOPPED
                      }`}
                    >
                      {session.status === "PAUSED" ? (
                        <>
                          <span>Paused</span>
                          <span className="text-[10px] opacity-80 font-medium">(Exits Active)</span>
                        </>
                      ) : (
                        session.status
                      )}
                    </Badge>
                  </div>
                  <div>
                    <h3 className="font-medium text-white flex items-center gap-2">
                      {session.strategy_name}
                      {session.allocation?.version_number && (
                        <Badge className="bg-indigo-500/20 text-indigo-300 border-indigo-500/30 text-[10px] px-1.5 py-0.5 font-mono">
                          v{session.allocation.version_number}
                        </Badge>
                      )}
                    </h3>
                    <p className="text-xs text-gray-500">
                      {session.broker_label ||
                        session.broker_name ||
                        "No broker"}
                    </p>
                  </div>
                </div>

                {/* Key Metrics */}
                <div className="flex items-center gap-6 lg:gap-8 flex-1 justify-between lg:justify-center text-sm">
                  <div className="text-center">
                    <p className="text-gray-500 text-xs uppercase tracking-wider mb-1">
                      P&L
                    </p>
                    <p
                      className={`font-medium ${Number(session.pnl || 0) >= 0 ? "text-emerald-400" : "text-rose-400"}`}
                    >
                      Rs {formatNumber(session.pnl)}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-gray-500 text-xs uppercase tracking-wider mb-1">
                      Trades
                    </p>
                    <p className="text-gray-200 font-medium">
                      {session.trades_count}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-gray-500 text-xs uppercase tracking-wider mb-1">
                      Positions
                    </p>
                    <p className="text-gray-200 font-medium">
                      {session.open_positions}
                    </p>
                  </div>
                </div>

                {session.allocation && (
                  <div className="flex items-center gap-6 text-xs text-gray-400 flex-wrap">
                    <span>
                      Allocated:{" "}
                      <span className="text-gray-200">
                        Rs {formatNumber(session.allocation.allocated_capital)}
                      </span>
                    </span>
                    <span>
                      Used:{" "}
                      <span className="text-gray-200">
                        Rs {formatNumber(session.allocation.used_capital)}
                      </span>
                    </span>
                    <span>
                      Available:{" "}
                      <span className="text-gray-200">
                        Rs {formatNumber(session.allocation.available_capital)}
                      </span>
                    </span>
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-1 justify-end flex-shrink-0 mt-4 lg:mt-0">
                  {session.status === "RUNNING" ? (
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8 text-amber-500 hover:text-amber-400 hover:bg-amber-500/10"
                      onClick={() =>
                        runAction(
                          `pause-${session.id}`,
                          () => liveTradingApi.pauseSession(session.id),
                          "Session paused",
                        )
                      }
                      disabled={busyAction === `pause-${session.id}`}
                      title="Pause Strategy"
                    >
                      <Pause className="h-4 w-4" />
                    </Button>
                  ) : (
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8 text-emerald-500 hover:text-emerald-400 hover:bg-emerald-500/10"
                      onClick={() =>
                        runAction(
                          `resume-${session.id}`,
                          () => liveTradingApi.resumeSession(session.id),
                          "Session resumed",
                        )
                      }
                      disabled={busyAction === `resume-${session.id}`}
                      title="Resume Strategy"
                    >
                      <Play className="h-4 w-4" />
                    </Button>
                  )}
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8 text-rose-500 hover:text-rose-400 hover:bg-rose-500/10"
                    onClick={() =>
                      runAction(
                        `stop-${session.id}`,
                        () =>
                          liveTradingApi.stopSession(session.id, {
                            close_positions: false,
                          }),
                        "Session stopped",
                      )
                    }
                    disabled={busyAction === `stop-${session.id}`}
                    title="Stop Strategy"
                  >
                    <Power className="h-4 w-4" />
                  </Button>
                  
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8 text-slate-400 hover:text-slate-100 hover:bg-slate-700/50"
                    onClick={() => setAllocationModal({ open: true, session })}
                    title="Edit Allocation"
                  >
                    <Settings className="h-4 w-4" />
                  </Button>

                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8 text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10"
                    title="Hot-Swap Version"
                    onClick={() => setHotSwapModal({ open: true, session })}
                  >
                    <RefreshCw className="h-4 w-4" />
                  </Button>

                  <div className="w-px h-6 bg-gray-800 mx-2 hidden sm:block"></div>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setExpandedSession(
                        expandedSession === session.id ? null : session.id,
                      )
                    }
                    className="border-gray-700 text-gray-300 h-8 text-xs bg-gray-950/40 hover:bg-gray-800"
                  >
                    {expandedSession === session.id ? "Close" : "Details"}
                    {expandedSession === session.id ? (
                      <ChevronUp className="ml-1 h-3 w-3" />
                    ) : (
                      <ChevronDown className="ml-1 h-3 w-3" />
                    )}
                  </Button>
                </div>
              </div>

              {/* Expanded Details */}
              {expandedSession === session.id && (
                <div className="border-t border-gray-800 bg-black/30 p-4 sm:p-5 animate-in slide-in-from-top-2 duration-200">
                  {/* Quick Actions & Health */}
                  <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between mb-5">
                    <div className="flex gap-6 text-sm">
                      <span className="text-gray-400 flex items-center gap-2">
                        <Activity className="h-4 w-4 text-gray-500" />
                        Health:
                        <span
                          className={
                            session.broker_session_valid
                              ? "text-emerald-400"
                              : "text-rose-400"
                          }
                        >
                          {session.broker_session_valid
                            ? "Ready"
                            : "Reconnect Required"}
                        </span>
                      </span>
                      <span className="text-gray-400">
                        Started:{" "}
                        <span className="text-gray-200">
                          {formatDateTime(session.started_at)}
                        </span>
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="border-gray-700 text-gray-200 h-8 bg-gray-900/50 hover:bg-gray-800"
                        onClick={() =>
                          runAction(
                            `sync-${session.id}`,
                            () => liveTradingApi.syncSession(session.id),
                            "Session synced",
                          )
                        }
                        disabled={busyAction === `sync-${session.id}`}
                      >
                        <RotateCw className="mr-2 h-3 w-3" /> Sync Orders
                      </Button>

                    </div>
                  </div>

                  {session.error_message && (
                    <div className="rounded-xl border border-red-900/50 bg-red-500/5 p-3 text-sm text-red-200 mb-5">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                        <span>{session.error_message}</span>
                      </div>
                    </div>
                  )}

                  {session.phantom_positions > 0 && (
                    <div className="rounded-xl border border-amber-900/50 bg-amber-500/5 p-3 text-sm text-amber-200 mb-5">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                        <span>Phantom Position Alert: Strategy holds {session.phantom_positions} virtual positions not matching broker side.</span>
                      </div>
                    </div>
                  )}

                  <Tabs defaultValue="positions" className="w-full">
                    <div className="flex items-center justify-between mb-3 border-b border-gray-800 pb-2">
                      <TabsList className="bg-transparent border-0 p-0 h-auto space-x-4">
                        <TabsTrigger
                          value="positions"
                          className="text-sm data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:text-indigo-400 p-0 pb-2 border-b-2 border-transparent data-[state=active]:border-indigo-400 rounded-none"
                        >
                          Open Positions{" "}
                          <span className="ml-2 bg-gray-800 text-gray-300 py-0.5 px-2 rounded-full text-xs">
                            {session.open_positions}
                          </span>
                        </TabsTrigger>
                        <TabsTrigger
                          value="orders"
                          className="text-sm data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:text-indigo-400 p-0 pb-2 border-b-2 border-transparent data-[state=active]:border-indigo-400 rounded-none"
                        >
                          Recent Orders{" "}
                          <span className="ml-2 bg-gray-800 text-gray-300 py-0.5 px-2 rounded-full text-xs">
                            {session.active_orders}
                          </span>
                        </TabsTrigger>
                      </TabsList>
                    </div>
                    <TabsContent
                      value="positions"
                      className="mt-0 outline-none"
                    >
                      <LivePositionsTable
                        positions={positions.filter(
                          (p) => p.strategy === session.strategy,
                        )}
                      />
                    </TabsContent>
                    <TabsContent value="orders" className="mt-0 outline-none">
                      <LiveOrdersTable
                        orders={orders.filter((o) => o.session === session.id)}
                      />
                    </TabsContent>
                  </Tabs>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <LiveAllocationUpdateModal
        open={allocationModal.open}
        session={allocationModal.session}
        onOpenChange={(open) => setAllocationModal({ ...allocationModal, open })}
        onSuccess={loadData}
      />
      <LiveHotSwapModal
        open={hotSwapModal.open}
        session={hotSwapModal.session}
        onOpenChange={(open) => setHotSwapModal({ ...hotSwapModal, open })}
        onSuccess={loadData}
      />
    </div>
  );
}
