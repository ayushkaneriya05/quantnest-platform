import Pagination from "@/shared/components/Pagination";
import { usePagination, useQueryState } from "@/shared/hooks/usePagination";
import RefreshButton from "@/shared/components/RefreshButton";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, ChevronDown, Search, ShieldCheck } from "lucide-react";
import { format } from "date-fns";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { DatePicker } from "@/shared/components/ui/date-picker";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { auditApi } from "@/shared/services/auditApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { formatDateTime } from "@/shared/utils/formatters";
import { MetricCard } from "@/features/journal/components/ReviewWorkspace.jsx";

export default function ActivityHistory() {
  const [search, setSearch] = useQueryState('search', '', { replace: true });
  const [action, setAction] = useQueryState('action', 'all');
  const [entityType, setEntityType] = useQueryState('entity_type', 'all');
  const [dateFrom, setDateFrom] = useQueryState('date_from');
  const [dateTo, setDateTo] = useQueryState('date_to');
  const filters = useMemo(() => ({ search, action, entity_type: entityType, date_from: dateFrom, date_to: dateTo }), [search, action, entityType, dateFrom, dateTo]);
  const { page, pageSize, setPage, setPageSize, accept } = usePagination(JSON.stringify(filters));
  const [refresh, setRefresh] = useState(0);
  const [expanded, setExpanded] = useState(null);
  const [state, setState] = useState({ loading: true, error: "", logs: null, stats: null });
  const key = JSON.stringify(filters);
  const snapshot = useRef({ key: null, stats: null });
  useEffect(() => {
    const controller = new AbortController();
    setState((previous) => ({ ...previous, loading: true, error: "", logs: previous.key === key ? previous.logs : null, key }));
    const params = Object.fromEntries(Object.entries(JSON.parse(key)).filter(([, value]) => value && value !== "all"));
    const timer = setTimeout(async () => {
      try {
        const [logs, stats] = await Promise.all([auditApi.getLogs({ ...params, page, page_size: pageSize }, controller.signal), snapshot.current.key === key + refresh ? Promise.resolve({ data: snapshot.current.stats }) : auditApi.getStats(params, controller.signal)]);
        if (!controller.signal.aborted) { snapshot.current = { key: key + refresh, stats: stats.data }; accept(logs.data); setState({ key, logs: logs.data, stats: stats.data, loading: false, error: "" }); }
      } catch (error) {
        if (!controller.signal.aborted) setState((previous) => ({ ...previous, loading: false, error: getApiErrorMessage(error, "Could not load activity history") }));
      }
    }, filters.search ? 250 : 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [key, page, pageSize, accept, refresh, filters.search]);
  const actions = useMemo(() => <RefreshButton onClick={() => setRefresh((value) => value + 1)} label="Refresh activity history" disabled={state.loading} loading={state.loading} />, [state.loading]);
  useSetPageActions(actions);
  function update(changes) { const [key, value] = Object.entries(changes)[0]; ({ search: setSearch, action: setAction, entity_type: setEntityType, date_from: setDateFrom, date_to: setDateTo })[key](value); setExpanded(null); }
  return <div className="page-content">
    <div className="grid gap-3 sm:grid-cols-3"><MetricCard label="Matching events" value={state.stats?.events ?? "—"} /><MetricCard label="Today" value={state.stats?.today ?? "—"} tone="text-brand" /><div className="flex items-center gap-3 rounded-2xl border border-border bg-background/60 p-3"><ShieldCheck className="text-success" /><div><p className="text-sm font-semibold">Read-only activity</p><p className="mt-1 text-xs text-muted-foreground">Configuration and lifecycle changes</p></div></div></div>
    <section className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
      <div className="relative"><Search size={15} className="absolute left-3 top-3.5 text-muted-foreground" /><Input className="pl-9" aria-label="Search activity" placeholder="Search activity…" value={filters.search} onChange={(event) => update({ search: event.target.value })} /></div>
      <Select value={filters.action} onValueChange={(action) => update({ action })}><SelectTrigger aria-label="Action"><SelectValue placeholder="All actions" /></SelectTrigger><SelectContent><SelectItem value="all">All actions</SelectItem>{state.stats?.actions.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent></Select>
      <Select value={filters.entity_type} onValueChange={(entity_type) => update({ entity_type })}><SelectTrigger aria-label="Resource type"><SelectValue placeholder="All resources" /></SelectTrigger><SelectContent><SelectItem value="all">All resources</SelectItem>{state.stats?.entity_types.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent></Select>
      <DatePicker date={filters.date_from ? new Date(filters.date_from + "T00:00:00") : null} setDate={(date) => update({ date_from: date ? format(date, "yyyy-MM-dd") : "" })} placeholder="From date" />
      <DatePicker date={filters.date_to ? new Date(filters.date_to + "T00:00:00") : null} setDate={(date) => update({ date_to: date ? format(date, "yyyy-MM-dd") : "" })} placeholder="To date" />
    </section>
    {state.error && <p role="alert" className="rounded-xl border border-loss/30 bg-loss/10 p-3 text-sm text-loss">{state.error}</p>}
    <section className="overflow-hidden rounded-2xl border border-border bg-background/60"><h2 className="flex items-center gap-2 border-b border-border px-5 py-3 font-semibold"><Activity size={17} className="text-brand" />Activity timeline</h2>
      {state.loading && !state.logs ? <p className="p-10 text-center text-sm text-muted-foreground"><GlobalLoader inline text="Loading activity…" /></p> : !state.logs?.results.length ? <p className="p-10 text-center text-sm text-muted-foreground">No activity matches these filters.</p> : state.logs.results.map((log) => <article key={log.id} className="border-b border-border/60 last:border-0">
        <Button variant="ghost" type="button" aria-expanded={expanded === log.id} onClick={() => setExpanded(expanded === log.id ? null : log.id)} className="block h-auto justify-start whitespace-normal p-0 flex w-full items-start gap-3 p-3 text-left">
          <div className="rounded-lg bg-brand/10 p-2 text-brand"><Activity size={16} /></div><div className="min-w-0 flex-1"><p className="text-sm font-medium">{log.action.replaceAll("_", " ").toLowerCase()} · {log.entity_name}</p><p className="mt-1 text-xs text-muted-foreground">{log.actor_name} · {log.entity_type_display} #{log.entity_id}</p>{log.reason && <p className="mt-2 text-sm text-muted-foreground">{log.reason}</p>}</div><div className="flex shrink-0 items-center gap-2"><span className="hidden text-xs text-muted-foreground sm:block">{formatDateTime(log.timestamp)}</span><ChevronDown size={15} className={expanded === log.id ? "rotate-180" : ""} /></div>
        </Button>
        {expanded === log.id && <div className="space-y-3 px-5 pb-5 sm:pl-16"><p className="text-xs text-muted-foreground">{formatDateTime(log.timestamp)}{log.ip_address ? " · " + log.ip_address : ""}</p><div className="scrollbar-theme max-h-80 space-y-2 overflow-auto">{[...new Set([...Object.keys(log.old_value), ...Object.keys(log.new_value)])].map((field) => <div key={field} className="rounded-xl border border-border p-3"><p className="mb-2 text-xs font-medium text-brand">{field.replaceAll("_", " ")}</p><div className="grid gap-3 sm:grid-cols-2">{[["Before", log.old_value[field]], ["After", log.new_value[field]]].map(([label, value]) => <div key={label}><p className="text-xs text-muted-foreground">{label}</p><pre className="scrollbar-theme mt-1 max-h-48 overflow-auto whitespace-pre-wrap break-words text-xs text-foreground">{value == null ? "—" : typeof value === "object" ? JSON.stringify(value, null, 2) : String(value)}</pre></div>)}</div></div>)}</div></div>}
      </article>)}
      <Pagination {...state.logs} page={page} pageSize={pageSize} loading={state.loading} onPageChange={setPage} onPageSizeChange={setPageSize} label="Activity pages" />
    </section>
  </div>;
}
