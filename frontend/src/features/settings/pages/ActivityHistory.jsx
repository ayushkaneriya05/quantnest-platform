import { useEffect, useMemo, useState } from "react";
import { Activity, ChevronDown, RefreshCw, Search, ShieldCheck } from "lucide-react";
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
  const [filters, setFilters] = useState({ search: "", action: "all", entity_type: "all", date_from: "", date_to: "" });
  const [page, setPage] = useState(1);
  const [refresh, setRefresh] = useState(0);
  const [expanded, setExpanded] = useState(null);
  const [state, setState] = useState({ loading: true, error: "", logs: null, stats: null });
  const key = JSON.stringify(filters);
  useEffect(() => {
    const controller = new AbortController();
    setState((previous) => ({ ...previous, loading: true, error: "", logs: null }));
    const params = Object.fromEntries(Object.entries(JSON.parse(key)).filter(([, value]) => value && value !== "all"));
    const timer = setTimeout(async () => {
      try {
        const [logs, stats] = await Promise.all([auditApi.getLogs({ ...params, page }, controller.signal), auditApi.getStats(params, controller.signal)]);
        if (!controller.signal.aborted) setState({ logs: logs.data, stats: stats.data, loading: false, error: "" });
      } catch (error) {
        if (!controller.signal.aborted) setState((previous) => ({ ...previous, loading: false, error: getApiErrorMessage(error, "Could not load activity history") }));
      }
    }, filters.search ? 250 : 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [key, page, refresh, filters.search]);
  const actions = useMemo(() => <Button variant="outline" disabled={state.loading} onClick={() => setRefresh((value) => value + 1)}><RefreshCw size={15} className="mr-2" />Refresh</Button>, [state.loading]);
  useSetPageActions(actions);
  function update(changes) { setFilters((previous) => ({ ...previous, ...changes })); setPage(1); setExpanded(null); }
  return <div className="container-padding space-y-5 py-5 lg:py-7">
    <div className="grid gap-3 sm:grid-cols-3"><MetricCard label="Matching events" value={state.stats?.events ?? "—"} /><MetricCard label="Today" value={state.stats?.today ?? "—"} tone="text-indigo-700 dark:text-indigo-300" /><div className="flex items-center gap-3 rounded-2xl border border-border bg-background/60 p-5"><ShieldCheck className="text-emerald-700 dark:text-emerald-400" /><div><p className="text-sm font-semibold">Read-only activity</p><p className="mt-1 text-xs text-muted-foreground">Configuration and lifecycle changes</p></div></div></div>
    <section className="grid gap-3 rounded-2xl border border-border bg-background/70 p-4 sm:grid-cols-2 xl:grid-cols-5">
      <div className="relative"><Search size={15} className="absolute left-3 top-3.5 text-muted-foreground" /><Input className="pl-9" aria-label="Search activity" placeholder="Search activity…" value={filters.search} onChange={(event) => update({ search: event.target.value })} /></div>
      <Select value={filters.action} onValueChange={(action) => update({ action })}><SelectTrigger aria-label="Action"><SelectValue placeholder="All actions" /></SelectTrigger><SelectContent><SelectItem value="all">All actions</SelectItem>{state.stats?.actions.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent></Select>
      <Select value={filters.entity_type} onValueChange={(entity_type) => update({ entity_type })}><SelectTrigger aria-label="Resource type"><SelectValue placeholder="All resources" /></SelectTrigger><SelectContent><SelectItem value="all">All resources</SelectItem>{state.stats?.entity_types.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent></Select>
      <DatePicker date={filters.date_from ? new Date(filters.date_from + "T00:00:00") : null} setDate={(date) => update({ date_from: date ? format(date, "yyyy-MM-dd") : "" })} placeholder="From date" />
      <DatePicker date={filters.date_to ? new Date(filters.date_to + "T00:00:00") : null} setDate={(date) => update({ date_to: date ? format(date, "yyyy-MM-dd") : "" })} placeholder="To date" />
    </section>
    {state.error && <p role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-700 dark:text-rose-300">{state.error}</p>}
    <section className="overflow-hidden rounded-2xl border border-border bg-background/60"><h2 className="flex items-center gap-2 border-b border-border px-5 py-4 font-semibold"><Activity size={17} className="text-indigo-700 dark:text-indigo-300" />Activity timeline</h2>
      {state.loading ? <p className="p-10 text-center text-sm text-muted-foreground">Loading activity…</p> : !state.logs?.results.length ? <p className="p-10 text-center text-sm text-muted-foreground">No activity matches these filters.</p> : state.logs.results.map((log) => <article key={log.id} className="border-b border-border/60 last:border-0">
        <button type="button" aria-expanded={expanded === log.id} onClick={() => setExpanded(expanded === log.id ? null : log.id)} className="flex w-full items-start gap-4 p-5 text-left hover:bg-card/50">
          <div className="rounded-lg bg-indigo-500/10 p-2 text-indigo-700 dark:text-indigo-300"><Activity size={16} /></div><div className="min-w-0 flex-1"><p className="text-sm font-medium">{log.action.replaceAll("_", " ").toLowerCase()} · {log.entity_name}</p><p className="mt-1 text-xs text-muted-foreground">{log.actor_name} · {log.entity_type_display} #{log.entity_id}</p>{log.reason && <p className="mt-2 text-sm text-muted-foreground">{log.reason}</p>}</div><div className="flex shrink-0 items-center gap-2"><span className="hidden text-xs text-muted-foreground sm:block">{formatDateTime(log.timestamp)}</span><ChevronDown size={15} className={expanded === log.id ? "rotate-180" : ""} /></div>
        </button>
        {expanded === log.id && <div className="space-y-3 px-5 pb-5 sm:pl-16"><p className="text-xs text-muted-foreground">{formatDateTime(log.timestamp)}{log.ip_address ? " · " + log.ip_address : ""}</p><div className="scrollbar-theme max-h-80 space-y-2 overflow-auto">{[...new Set([...Object.keys(log.old_value), ...Object.keys(log.new_value)])].map((field) => <div key={field} className="rounded-xl border border-border p-3"><p className="mb-2 text-xs font-medium text-indigo-700 dark:text-indigo-300">{field.replaceAll("_", " ")}</p><div className="grid gap-3 sm:grid-cols-2">{[["Before", log.old_value[field]], ["After", log.new_value[field]]].map(([label, value]) => <div key={label}><p className="text-xs text-muted-foreground">{label}</p><pre className="scrollbar-theme mt-1 max-h-48 overflow-auto whitespace-pre-wrap break-words text-xs text-foreground">{value == null ? "—" : typeof value === "object" ? JSON.stringify(value, null, 2) : String(value)}</pre></div>)}</div></div>)}</div></div>}
      </article>)}
      <div className="flex items-center justify-end gap-3 border-t border-border p-3"><Button size="sm" variant="outline" disabled={state.loading || page <= 1} onClick={() => setPage(page - 1)}>Previous</Button><span className="text-xs text-muted-foreground">Page {page}</span><Button size="sm" variant="outline" disabled={state.loading || !state.logs?.next} onClick={() => setPage(page + 1)}>Next</Button></div>
    </section>
  </div>;
}
