import { usePagination, useQueryState } from "@/shared/hooks/usePagination";
import { useStableCallback } from "@/shared/hooks/useStableCallback";
import RefreshButton from "@/shared/components/RefreshButton";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import PropTypes from "prop-types";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Clock3, ShieldAlert } from "lucide-react";
import { Badge } from "@/shared/components/ui/badge";

import { Card, CardContent, CardHeader } from "@/shared/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/components/ui/tabs";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { useLiveTradingWebSocket } from "@/shared/hooks/useLiveTradingWebSocket";
import { liveTradingApi } from "@/shared/services/liveTradingApi";
import { formatNumber, formatCurrency } from "@/shared/utils/formatters";
import Pagination from "@/shared/components/Pagination";
import WorkspaceState from "@/shared/components/WorkspaceState";
import LiveSyncStatus from "@/features/live/components/LiveSyncStatus.jsx";
import { formatBrokerAccount, formatDateTime as formatLiveDateTime } from "@/shared/utils/formatters";

const emptyPage = { count: 0, next: null, previous: null, results: [] };
const eventTone = (event) => {
  if (["FILLED", "PLACED"].includes(event)) return "border-success/30 bg-success/10 text-success";
  if (["REJECTED", "CANCELLED"].includes(event)) return "border-loss/30 bg-loss/10 text-loss";
  if (event === "PARTIAL_FILL") return "border-warning/30 bg-warning/10 text-warning";
  return "border-border bg-secondary/50 text-foreground";
};

function Metric({ title, value, note, color = "text-foreground" }) {
  return <Card className="border-border bg-card/50"><CardContent className="p-3"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</p><p className={`mt-2 text-2xl font-semibold ${color}`}>{value}</p>{note && <p className="mt-1 text-xs text-muted-foreground">{note}</p>}</CardContent></Card>;
}

export default function ExecutionLogs() {
  const { notify } = useNotifications();
  const [summary, setSummary] = useState({});
  const [logs, setLogs] = useState(emptyPage);
  const [slippage, setSlippage] = useState(emptyPage);
  const [eventType, setEventType] = useQueryState("event_type", "", { namespace: "events", replace: false });
  const [tab, setTab] = useQueryState("tab", "events", { namespace: "", replace: false });
  const logPages = usePagination(eventType, 'events');
  const slipPages = usePagination('', 'slippage');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const request = useRef(null);
  const timer = useRef(null);
  const fetchVisible = useStableCallback(async () => {
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    setLoading(true); setError("");
    const paging = tab === 'events' ? logPages : slipPages;
    try {
      const response = tab === 'events'
        ? await liveTradingApi.getLogs({ page: paging.page, page_size: paging.pageSize, ...(eventType ? { event_type: eventType } : {}) }, controller.signal)
        : await liveTradingApi.getSlippage({ page: paging.page, page_size: paging.pageSize }, controller.signal);
      if (!controller.signal.aborted) { (tab === 'events' ? setLogs : setSlippage)(response.data); paging.accept(response.data); }
    } catch (error) { if (!controller.signal.aborted) setError(getApiErrorMessage(error)); }
    finally { if (!controller.signal.aborted) setLoading(false); }
  });
  const loadData = useStableCallback(async () => {
    try { const [response] = await Promise.all([liveTradingApi.getSummary(), fetchVisible()]); setSummary(response.data); }
    catch (error) { notify.error(getApiErrorMessage(error)); }
    finally { setRefreshing(false); }
  });
  useEffect(() => { fetchVisible(); }, [fetchVisible, tab, eventType, logPages.page, logPages.pageSize, slipPages.page, slipPages.pageSize]);
  useEffect(() => {
    liveTradingApi.getSummary().then(response => setSummary(response.data)).catch(error => notify.error(getApiErrorMessage(error)));
    const poll = setInterval(loadData, 30000); const pending = request; const timers = timer;
    return () => { clearInterval(poll); clearTimeout(timers.current); pending.current?.abort(); };
  }, [loadData, notify]);
  const handleLiveUpdate = useCallback(() => { clearTimeout(timer.current); timer.current = setTimeout(loadData, 200); }, [loadData]);
  const { isConnected } = useLiveTradingWebSocket(handleLiveUpdate);
  const refresh = useCallback(() => { setRefreshing(true); return loadData(); }, [loadData]);
  const actions = useMemo(() => <div className="flex items-center gap-3"><div className="hidden sm:block"><LiveSyncStatus isConnected={isConnected} /></div><RefreshButton onClick={refresh} label="Refresh execution logs" disabled={refreshing} loading={refreshing} /></div>, [isConnected, refresh, refreshing]);
  useSetPageActions(actions);

  const metrics = useMemo(() => ({
    open: Number(summary.open_orders || 0),
    rejected: Number(summary.rejected_orders || 0),
    latency: summary.avg_execution_latency_ms == null ? null : Number(summary.avg_execution_latency_ms),
    slippage: summary.avg_slippage_pct == null ? null : Number(summary.avg_slippage_pct),
  }), [summary]);

  if (error) return <div className="page-content"><WorkspaceState error={error} onRetry={fetchVisible} /></div>;
  return (
    <div className="page-content">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric title="Active orders" value={metrics.open} note="Awaiting a terminal broker status" color="text-warning" />
        <Metric title="Rejected orders" value={metrics.rejected} note="All recorded live orders" color="text-loss" />
        <Metric title="Average event latency" value={metrics.latency == null ? "—" : `${formatNumber(metrics.latency)} ms`} note="Average of events with a measured latency" color="text-brand" />
        <Metric title="Average slippage" value={metrics.slippage == null ? "—" : `${formatNumber(metrics.slippage)}%`} note="Average across completed records" />
      </div>

      <Tabs value={tab} onValueChange={setTab} className="space-y-3">
        <TabsList >
          <TabsTrigger value="events" >Order lifecycle</TabsTrigger>
          <TabsTrigger value="slippage" >Slippage</TabsTrigger>
        </TabsList>
        <TabsContent value="events" className="mt-0">
          <Card className="overflow-hidden border-border bg-card/50">
            <CardHeader className="flex flex-col gap-2 space-y-0 border-b border-border px-4 py-2 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xl text-foreground font-semibold">Order Updates</p>
              <Select value={eventType || "ALL"} onValueChange={(value) => setEventType(value === "ALL" ? "" : value)}>
                <SelectTrigger className="w-full border-border bg-background text-foreground sm:w-48" aria-label="Filter event type"><SelectValue placeholder="All events" /></SelectTrigger>
                <SelectContent><SelectItem value="ALL">All events</SelectItem><SelectItem value="CREATED">Created</SelectItem><SelectItem value="PLACED">Placed</SelectItem><SelectItem value="PARTIAL_FILL">Partial fill</SelectItem><SelectItem value="FILLED">Filled</SelectItem><SelectItem value="REJECTED">Rejected</SelectItem><SelectItem value="CANCELLED">Cancelled</SelectItem><SelectItem value="UNKNOWN">Unknown</SelectItem></SelectContent>
              </Select>
            </CardHeader>
            {loading ? <CardContent className="py-10 text-center text-muted-foreground"><GlobalLoader inline text="Loading order events…" /></CardContent> : logs.results.length === 0 ? <CardContent className="py-12 text-center text-muted-foreground">No matching execution events.</CardContent> : <>
              <CardContent className="divide-y divide-border p-0">{logs.results.map((log) => <div key={log.id} className="flex flex-wrap items-start justify-between gap-3 p-3"><div className="min-w-[220px]"><div className="flex items-center gap-2"><span className="font-semibold text-foreground">{log.order_symbol || "Order"}</span><Badge variant="outline" className={eventTone(log.event_type)}>{log.event_type}</Badge></div><p className="mt-1 text-xs text-muted-foreground">{formatBrokerAccount(log.broker_name, log.broker_label)}</p><p className="mt-1 text-sm text-muted-foreground">{log.message || "No additional broker message"}</p></div><div className="flex items-center gap-3 text-xs text-muted-foreground"><span className="inline-flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" />{Number(log.latency_ms || 0)} ms</span><span>{formatLiveDateTime(log.created_at)}</span><span className="font-mono">Order #{log.order}</span></div></div>)}</CardContent>
            </>}

              <Pagination {...logs} page={logPages.page} pageSize={logPages.pageSize} loading={loading} onPageChange={logPages.setPage} onPageSizeChange={logPages.setPageSize} label="Order lifecycle pages" />
          </Card>
        </TabsContent>
        <TabsContent value="slippage" className="mt-0">
          <Card className="overflow-hidden border-border bg-card/50">
            <CardHeader className="space-y-0 border-b border-border px-4 py-2"><p className="text-xl text-foreground font-semibold">Slippage</p></CardHeader>
            {loading ? <CardContent className="py-10 text-center text-muted-foreground"><GlobalLoader inline text="Loading execution quality…" /></CardContent> : slippage.results.length === 0 ? <CardContent className="flex items-center justify-center gap-2 py-12 text-muted-foreground"><ShieldAlert className="h-4 w-4 text-brand" />No completed slippage records.</CardContent> : <>
              <CardContent className="divide-y divide-border p-0">{slippage.results.map((row) => <div key={row.id} className="flex flex-wrap items-center justify-between gap-3 p-3"><div><p className="font-medium text-foreground">{row.order_symbol || "Order"}</p><p className="mt-1 text-xs text-muted-foreground">{formatBrokerAccount(row.broker_name, row.broker_label)}</p><p className="mt-1 text-xs text-muted-foreground">Expected {formatCurrency(Number(row.expected_price))} · Actual {formatCurrency(Number(row.actual_price))} · {formatLiveDateTime(row.created_at)}</p></div><div className="text-right"><p className="font-semibold text-foreground">{formatNumber(Number(row.slippage_pct))}%</p><p className="text-xs text-muted-foreground">Total impact {formatCurrency(Number(row.slippage_amount))}</p></div></div>)}</CardContent>
            </>}

              <Pagination {...slippage} page={slipPages.page} pageSize={slipPages.pageSize} loading={loading} onPageChange={slipPages.setPage} onPageSizeChange={slipPages.setPageSize} label="Slippage pages" />
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

Metric.propTypes = {
  ...Metric.propTypes,
  color: PropTypes.string,
  note: PropTypes.string,
  title: PropTypes.string,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
};
