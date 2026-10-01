import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Clock3, RefreshCw, ShieldAlert } from "lucide-react";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader } from "@/shared/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/components/ui/tabs";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { useLiveTradingWebSocket } from "@/shared/hooks/useLiveTradingWebSocket";
import { liveTradingApi } from "@/shared/services/liveTradingApi";
import { formatNumber } from "@/shared/utils/formatters";
import LiveTablePagination from "./components/LiveTablePagination";
import LiveSyncStatus from "./components/LiveSyncStatus";
import { formatBrokerAccount, formatDateTime as formatLiveDateTime } from "@/shared/utils/formatters";

const PAGE_SIZE = 25;
const emptyPage = { count: 0, next: null, previous: null, results: [] };
const responsePage = (response) => response.data?.results ? response.data : { ...emptyPage, results: Array.isArray(response.data) ? response.data : [] };
const eventTone = (event) => {
  if (["FILLED", "PLACED"].includes(event)) return "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";
  if (["REJECTED", "CANCELLED"].includes(event)) return "border-rose-500/30 bg-rose-500/10 text-rose-300";
  if (event === "PARTIAL_FILL") return "border-amber-500/30 bg-amber-500/10 text-amber-300";
  return "border-slate-700 bg-slate-800/50 text-slate-300";
};

function Metric({ title, value, note, color = "text-white" }) {
  return <Card className="border-slate-800 bg-slate-900/50"><CardContent className="p-5"><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</p><p className={`mt-2 text-2xl font-semibold ${color}`}>{value}</p>{note && <p className="mt-1 text-xs text-slate-500">{note}</p>}</CardContent></Card>;
}

export default function ExecutionLogs() {
  const { notify } = useNotifications();
  const [summary, setSummary] = useState({});
  const [logs, setLogs] = useState(emptyPage);
  const [slippage, setSlippage] = useState(emptyPage);
  const [logPage, setLogPage] = useState(1);
  const [slippagePage, setSlippagePage] = useState(1);
  const [eventType, setEventType] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const timer = useRef(null);
  const loadDataRef = useRef(null);

  const fetchLogs = useCallback(async (page = logPage, filter = eventType) => {
    const response = await liveTradingApi.getLogs({ page, page_size: PAGE_SIZE, ...(filter ? { event_type: filter } : {}) });
    setLogs(responsePage(response));
    setLogPage(page);
  }, [eventType, logPage]);
  const fetchSlippage = useCallback(async (page = slippagePage) => {
    const response = await liveTradingApi.getSlippage({ page, page_size: PAGE_SIZE });
    setSlippage(responsePage(response));
    setSlippagePage(page);
  }, [slippagePage]);

  const loadData = useCallback(async (spinner = true) => {
    if (spinner) setLoading(true);
    try {
      const [summaryResponse] = await Promise.all([
        liveTradingApi.getSummary(), fetchLogs(logPage), fetchSlippage(slippagePage),
      ]);
      setSummary(summaryResponse.data || {});
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to load execution history"));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [fetchLogs, fetchSlippage, logPage, notify, slippagePage]);
  loadDataRef.current = loadData;

  const handleLiveUpdate = useCallback((payload) => {
    if (!["ORDER_UPDATE", "POSITION_UPDATE"].includes(payload?.event_type)) return;
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      Promise.all([liveTradingApi.getSummary(), fetchLogs(logPage), fetchSlippage(slippagePage)])
        .then(([response]) => setSummary(response.data || {}))
        .catch((error) => console.error("Execution history refresh failed", error));
    }, 200);
  }, [fetchLogs, fetchSlippage, logPage, slippagePage]);

  const { isConnected } = useLiveTradingWebSocket(handleLiveUpdate);
  useEffect(() => {
    loadDataRef.current?.();
    const pollTimer = setInterval(() => loadDataRef.current?.(false), 30000);
    return () => { if (timer.current) clearTimeout(timer.current); clearInterval(pollTimer); };
  }, []);

  const refresh = useCallback(() => {
    setRefreshing(true);
    return loadData(false);
  }, [loadData]);
  const actions = useMemo(() => <div className="flex items-center gap-3"><div className="hidden sm:block"><LiveSyncStatus isConnected={isConnected} /></div><Button variant="outline" onClick={refresh} disabled={refreshing} className="border-gray-700 text-gray-100"><RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />Refresh</Button></div>, [isConnected, refresh, refreshing]);
  useSetPageActions(actions);

  const metrics = useMemo(() => ({
    open: Number(summary.open_orders || 0),
    rejected: Number(summary.rejected_orders || 0),
    latency: summary.avg_execution_latency_ms == null ? null : Number(summary.avg_execution_latency_ms),
    slippage: summary.avg_slippage_pct == null ? null : Number(summary.avg_slippage_pct),
  }), [summary]);

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric title="Active orders" value={metrics.open} note="Awaiting a terminal broker status" color="text-amber-300" />
        <Metric title="Rejected orders" value={metrics.rejected} note="All recorded live orders" color="text-rose-300" />
        <Metric title="Average event latency" value={metrics.latency == null ? "—" : `${formatNumber(metrics.latency)} ms`} note="Average of events with a measured latency" color="text-cyan-300" />
        <Metric title="Average slippage" value={metrics.slippage == null ? "—" : `${formatNumber(metrics.slippage)}%`} note="Average across completed records" />
      </div>

      <Tabs defaultValue="events" className="space-y-4">
        <TabsList className="h-auto w-full justify-start gap-1 overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/60 p-1 sm:w-auto">
          <TabsTrigger value="events" className="text-slate-300 data-[state=active]:bg-slate-700 data-[state=active]:text-white">Order lifecycle</TabsTrigger>
          <TabsTrigger value="slippage" className="text-slate-300 data-[state=active]:bg-slate-700 data-[state=active]:text-white">Slippage</TabsTrigger>
        </TabsList>
        <TabsContent value="events" className="mt-0">
          <Card className="overflow-hidden border-slate-800 bg-slate-900/50">
            <CardHeader className="flex flex-col gap-2 space-y-0 border-b border-slate-800 px-4 py-2 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xl text-slate-300 font-semibold">Order Updates</p>
              <Select value={eventType || "ALL"} onValueChange={(value) => { const next = value === "ALL" ? "" : value; setEventType(next); fetchLogs(1, next).catch((error) => notify.error(getApiErrorMessage(error, "Could not filter execution events"))); }}>
                <SelectTrigger className="h-9 w-full border-slate-700 bg-slate-950 text-slate-200 sm:w-48" aria-label="Filter event type"><SelectValue placeholder="All events" /></SelectTrigger>
                <SelectContent><SelectItem value="ALL">All events</SelectItem><SelectItem value="CREATED">Created</SelectItem><SelectItem value="PLACED">Placed</SelectItem><SelectItem value="PARTIAL_FILL">Partial fill</SelectItem><SelectItem value="FILLED">Filled</SelectItem><SelectItem value="REJECTED">Rejected</SelectItem><SelectItem value="CANCELLED">Cancelled</SelectItem><SelectItem value="UNKNOWN">Unknown</SelectItem></SelectContent>
              </Select>
            </CardHeader>
            {loading ? <CardContent className="py-10 text-center text-slate-400">Loading order events…</CardContent> : logs.results.length === 0 ? <CardContent className="py-12 text-center text-slate-400">No matching execution events.</CardContent> : <>
              <CardContent className="divide-y divide-slate-800 p-0">{logs.results.map((log) => <div key={log.id} className="flex flex-wrap items-start justify-between gap-4 p-4"><div className="min-w-[220px]"><div className="flex items-center gap-2"><span className="font-semibold text-white">{log.order_symbol || "Order"}</span><Badge variant="outline" className={eventTone(log.event_type)}>{log.event_type}</Badge></div><p className="mt-1 text-xs text-slate-500">{formatBrokerAccount(log.broker_name, log.broker_label)}</p><p className="mt-1 text-sm text-slate-400">{log.message || "No additional broker message"}</p></div><div className="flex items-center gap-4 text-xs text-slate-500"><span className="inline-flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" />{Number(log.latency_ms || 0)} ms</span><span>{formatLiveDateTime(log.created_at)}</span><span className="font-mono">Order #{log.order}</span></div></div>)}</CardContent>
              <LiveTablePagination page={logPage} count={logs.count} onPageChange={(page) => fetchLogs(page).catch((error) => notify.error(getApiErrorMessage(error, "Could not load execution events")))} />
            </>}
          </Card>
        </TabsContent>
        <TabsContent value="slippage" className="mt-0">
          <Card className="overflow-hidden border-slate-800 bg-slate-900/50">
            <CardHeader className="space-y-0 border-b border-slate-800 px-4 py-2"><p className="text-xl text-slate-300 font-semibold">Slippage</p></CardHeader>
            {loading ? <CardContent className="py-10 text-center text-slate-400">Loading execution quality…</CardContent> : slippage.results.length === 0 ? <CardContent className="flex items-center justify-center gap-2 py-12 text-slate-400"><ShieldAlert className="h-4 w-4 text-cyan-300" />No completed slippage records.</CardContent> : <>
              <CardContent className="divide-y divide-slate-800 p-0">{slippage.results.map((row) => <div key={row.id} className="flex flex-wrap items-center justify-between gap-4 p-4"><div><p className="font-medium text-white">{row.order_symbol || "Order"}</p><p className="mt-1 text-xs text-slate-500">{formatBrokerAccount(row.broker_name, row.broker_label)}</p><p className="mt-1 text-xs text-slate-400">Expected ₹{formatNumber(Number(row.expected_price))} · Actual ₹{formatNumber(Number(row.actual_price))} · {formatLiveDateTime(row.created_at)}</p></div><div className="text-right"><p className="font-semibold text-slate-100">{formatNumber(Number(row.slippage_pct))}%</p><p className="text-xs text-slate-500">Total impact ₹{formatNumber(Number(row.slippage_amount))}</p></div></div>)}</CardContent>
              <LiveTablePagination page={slippagePage} count={slippage.count} onPageChange={(page) => fetchSlippage(page).catch((error) => notify.error(getApiErrorMessage(error, "Could not load slippage records")))} />
            </>}
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
