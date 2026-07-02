import { useEffect, useMemo, useState, useCallback } from "react";
import { Clock3, RefreshCw, ShieldAlert, XCircle } from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { useLiveTradingWebSocket } from "@/shared/hooks/useLiveTradingWebSocket";
import { liveTradingApi } from "@/shared/services/liveTradingApi";

import { formatNumber, formatDateTime } from "@/shared/utils/formatters";

export default function ExecutionLogs() {
  const { notify } = useNotifications();
  const [logs, setLogs] = useState([]);
  const [orders, setOrders] = useState([]);
  const [slippage, setSlippage] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyOrder, setBusyOrder] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [logsRes, ordersRes, slippageRes] = await Promise.all([
        liveTradingApi.getLogs(),
        liveTradingApi.getOrders(),
        liveTradingApi.getSlippage(),
      ]);
      setLogs(Array.isArray(logsRes.data?.results) ? logsRes.data.results : logsRes.data || []);
      setOrders(Array.isArray(ordersRes.data?.results) ? ordersRes.data.results : ordersRes.data || []);
      setSlippage(Array.isArray(slippageRes.data?.results) ? slippageRes.data.results : slippageRes.data || []);
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load execution data");
    } finally {
      setLoading(false);
    }
  };

  const handleLiveUpdate = useCallback((payload) => {
    if (payload?.event_type === "ORDER_UPDATE") {
      liveTradingApi.getOrders().then(res => setOrders(Array.isArray(res.data?.results) ? res.data.results : res.data || [])).catch(console.error);
      liveTradingApi.getLogs().then(res => setLogs(Array.isArray(res.data?.results) ? res.data.results : res.data || [])).catch(console.error);
    }
  }, []);

  useLiveTradingWebSocket(handleLiveUpdate);

  useEffect(() => {
    loadData();
  }, []);

  useSetPageActions(
    <Button variant="outline" onClick={loadData} className="border-gray-700 text-gray-100">
      <RefreshCw className="mr-2 h-4 w-4" />
      Refresh
    </Button>,
  );

  const summary = useMemo(() => {
    const pending = orders.filter((order) => order.can_cancel).length;
    const rejected = orders.filter((order) => order.status === "REJECTED").length;
    const avgLatency = logs.length ? logs.reduce((sum, log) => sum + Number(log.latency_ms || 0), 0) / logs.length : 0;
    const avgSlippage = slippage.length
      ? slippage.reduce((sum, row) => sum + Number(row.slippage_pct || 0), 0) / slippage.length
      : 0;
    return { pending, rejected, avgLatency, avgSlippage };
  }, [logs, orders, slippage]);

  const cancelOrder = async (orderId) => {
    try {
      setBusyOrder(String(orderId));
      await liveTradingApi.cancelOrder(orderId);
      notify.success("Order cancellation requested");
      await loadData();
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to cancel live order");
    } finally {
      setBusyOrder("");
    }
  };

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="border-gray-800 bg-gray-900/60"><CardContent className="p-5"><p className="text-xs uppercase tracking-[0.16em] text-gray-500">Pending Orders</p><p className="mt-2 text-2xl font-semibold text-amber-300">{summary.pending}</p></CardContent></Card>
        <Card className="border-gray-800 bg-gray-900/60"><CardContent className="p-5"><p className="text-xs uppercase tracking-[0.16em] text-gray-500">Rejected</p><p className="mt-2 text-2xl font-semibold text-red-300">{summary.rejected}</p></CardContent></Card>
        <Card className="border-gray-800 bg-gray-900/60"><CardContent className="p-5"><p className="text-xs uppercase tracking-[0.16em] text-gray-500">Avg Latency</p><p className="mt-2 text-2xl font-semibold text-cyan-300">{formatNumber(summary.avgLatency)} ms</p></CardContent></Card>
        <Card className="border-gray-800 bg-gray-900/60"><CardContent className="p-5"><p className="text-xs uppercase tracking-[0.16em] text-gray-500">Avg Slippage</p><p className="mt-2 text-2xl font-semibold text-white">{formatNumber(summary.avgSlippage)}%</p></CardContent></Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Card className="border-gray-800 bg-gray-900/60">
          <CardHeader><CardTitle className="text-white">Recent Execution Events</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <div className="py-8 text-center text-gray-400">Loading execution logs...</div>
            ) : logs.length === 0 ? (
              <div className="py-8 text-center text-gray-400">No execution logs yet.</div>
            ) : logs.slice(0, 12).map((log) => (
              <div key={log.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-white">{log.order_symbol}</p>
                    <p className="mt-1 text-sm text-gray-400">{log.message || log.event_type}</p>
                  </div>
                  <Badge className="bg-cyan-500/10 text-cyan-300 border-cyan-500/20">{log.event_type}</Badge>
                </div>
                <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-500">
                  <span className="flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" /> {log.latency_ms || 0} ms</span>
                  <span>Fill: {log.fill_quantity || 0} @ {log.fill_price || "-"}</span>
                  <span>{formatDateTime(log.created_at)}</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader><CardTitle className="text-white">Actionable Orders</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {orders.filter((order) => order.can_cancel).slice(0, 8).map((order) => (
                <div key={order.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">{order.instrument_symbol}</p>
                      <p className="mt-1 text-xs text-gray-400">{order.strategy_name || "Manual"} • {order.side} {order.quantity}</p>
                    </div>
                    <Badge className="bg-amber-500/10 text-amber-300 border-amber-500/20">{order.status}</Badge>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3 text-xs text-gray-500">
                    <span>Broker ID: {order.broker_order_id || "-"}</span>
                    <Button
                      size="sm"
                      className="bg-red-600 hover:bg-red-500"
                      onClick={() => cancelOrder(order.id)}
                      disabled={busyOrder === String(order.id)}
                    >
                      <XCircle className="mr-2 h-4 w-4" />
                      Cancel
                    </Button>
                  </div>
                </div>
              ))}
              {!orders.some((order) => order.can_cancel) && !loading ? (
                <div className="py-6 text-center text-sm text-gray-400">No pending live orders to cancel.</div>
              ) : null}
            </CardContent>
          </Card>

          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader><CardTitle className="text-white">Execution Quality</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {slippage.slice(0, 6).map((row) => (
                <div key={row.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">{row.order_symbol}</p>
                      <p className="mt-1 text-xs text-gray-400">Expected {row.expected_price} • Actual {row.actual_price}</p>
                    </div>
                    <Badge className="bg-gray-500/10 text-gray-200 border-gray-500/20">{formatNumber(row.slippage_pct)}%</Badge>
                  </div>
                </div>
              ))}
              {!slippage.length && !loading ? (
                <div className="flex items-center gap-2 py-6 text-sm text-gray-400">
                  <ShieldAlert className="h-4 w-4 text-cyan-300" />
                  No slippage records yet.
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
