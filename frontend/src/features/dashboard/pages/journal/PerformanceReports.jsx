import { useCallback, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Download, RefreshCw, Sparkles, BookOpen, Loader2 } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import { Button } from "@/shared/components/ui/button";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/shared/components/ui/dialog";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { executionReportsApi } from "@/shared/services/executionReportsApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { formatDateTime } from "@/shared/utils/formatters";
import { SourceTabs, ReviewFilters, MetricCard } from "./components/ReviewWorkspace";
import { useReviewWorkspace, displayMoney, displayNumber, pnlTone, modes } from "./components/useReviewWorkspace";

export default function PerformanceReports() {
  const { filters, details: report, loading, error, update, reload } = useReviewWorkspace("report");
  const [researchOpen, setResearchOpen] = useState(false);
  const [includeNotes, setIncludeNotes] = useState(false);
  const [busy, setBusy] = useState(false);
  const { notify } = useNotifications();
  const navigate = useNavigate();
  const summary = report?.summary;
  const positions = report?.current_positions;
  const source = modes.find((mode) => mode.value === filters.source);
  const journalUrl = `/dashboard/journal?${new URLSearchParams(filters)}`;

  const exportCsv = useCallback(async () => {
    setBusy(true);
    try {
      const { data } = await executionReportsApi.export(filters);
      const url = URL.createObjectURL(new Blob([data], { type: "text/csv;charset=utf-8" }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filters.source.toLowerCase() + "-closes.csv";
      anchor.click();
      URL.revokeObjectURL(url);
      notify.success("Execution report exported");
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Could not export the report"));
    } finally { setBusy(false); }
  }, [filters, notify]);

  async function research() {
    setBusy(true);
    try {
      const { data } = await executionReportsApi.researchContext({ filters, include_notes: includeNotes });
      navigate(`/dashboard/analysis/ai-research-assistant?session=${data.id}&review=1`);
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Could not attach this report"));
    } finally { setBusy(false); }
  }

  const actions = useMemo(() => <>
    <div className="hidden xl:block"><SourceTabs source={filters.source} onChange={(source) => update({ source })} /></div>
    <Button size="sm" disabled={busy || loading || !!error || !summary?.closes} onClick={() => { setIncludeNotes(false); setResearchOpen(true); }} aria-label="Ask AI about these results">
      <Sparkles size={15} /><span className="ml-2 hidden sm:inline">Ask AI</span>
    </Button>
    <Button variant="outline" size="sm" disabled={busy || loading || !!error} onClick={exportCsv} aria-label="Export report CSV"><Download size={15} /><span className="ml-2 hidden 2xl:inline">Export CSV</span></Button>
    <Button variant="outline" size="sm" disabled={loading} onClick={reload} aria-label="Refresh report"><RefreshCw size={15} /><span className="ml-2 hidden 2xl:inline">Refresh</span></Button>
  </>, [filters, update, busy, loading, error, summary?.closes, exportCsv, reload]);
  useSetPageActions(actions);

  const chart = (report?.daily || []).map((row) => ({ ...row, realized_pnl: Number(row.realized_pnl) }));
  return <div className="container-padding space-y-4 py-4">
    <div className="xl:hidden"><SourceTabs source={filters.source} onChange={(source) => update({ source })} /></div>
    <ReviewFilters filters={filters} onChange={update} />
    {error && <div role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">
      {error}<Button variant="ghost" size="sm" onClick={reload}>Retry</Button>
    </div>}
    <div className="grid grid-cols-2 gap-2 xl:grid-cols-4">
      <MetricCard label="Realized P&L" value={loading ? "—" : displayMoney(summary?.realized_pnl)} tone={pnlTone(summary?.realized_pnl)} hint={report?.pnl_basis} />
      <MetricCard label="Recorded closes" value={summary?.closes ?? "—"} hint={summary ? `${summary.wins} winning · ${summary.losses} losing · ${summary.breakeven} flat` : ""} />
      <MetricCard label="Win rate" value={loading ? "—" : summary?.win_rate == null ? "N/A" : displayNumber(summary.win_rate) + "%"} hint="Winning closes / all closes" />
      <MetricCard label="Profit factor" value={loading ? "—" : displayNumber(summary?.profit_factor)} hint="Winning P&L / absolute losing P&L" />
    </div>
    <section aria-label="Additional report metrics" className="grid gap-4 rounded-xl border border-slate-800 bg-slate-950/60 p-4 sm:grid-cols-3">
      <div><p className="text-xs text-slate-400">Average P&L per close</p><p className="mt-1 font-semibold tabular-nums">{loading ? "—" : displayMoney(summary?.average_pnl)}</p></div>
      <div><p className="text-xs text-slate-400">Recorded charges</p><p className="mt-1 font-semibold tabular-nums">{loading ? "—" : displayMoney(summary?.recorded_charges)}</p><p className="mt-1 text-[11px] text-slate-500">{filters.source === "PAPER" ? "Simulated brokerage and taxes" : "Unavailable for this execution source"}</p></div>
      <div><p className="text-xs text-slate-400">Current unrealized P&L</p><p className={`mt-1 font-semibold tabular-nums ${pnlTone(positions?.unrealized_pnl)}`}>{loading ? "—" : displayMoney(positions?.unrealized_pnl)}</p>
        {positions && <p className="mt-1 text-[11px] leading-4 text-slate-500">{positions.positions} open positions · before exit costs · {positions.unpriced_positions ? `${positions.unpriced_positions} awaiting fresh quotes` : positions.oldest_quote_at ? `oldest quote ${formatDateTime(positions.oldest_quote_at)}` : "no open exposure"}. Separate from the selected close-date period.</p>}
      </div>
    </section>
    <section className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div><h2 className="font-semibold">Daily realized P&L</h2><p className="mt-1 text-xs text-slate-500">Grouped by close date · excludes open positions and cash transfers</p></div>
        <Link to={journalUrl} className="flex items-center gap-1.5 text-xs text-slate-300 hover:text-white"><BookOpen size={14} />Review closes in journal</Link>
      </div>
      <div className="mt-4 h-64">{chart.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={chart}>
        <CartesianGrid vertical={false} stroke="#1e293b" strokeDasharray="3 3" />
        <XAxis dataKey="date" stroke="#64748b" fontSize={11} minTickGap={40} />
        <YAxis stroke="#64748b" fontSize={11} tickFormatter={displayNumber} />
        <Tooltip formatter={(value) => [displayMoney(value), "Realized P&L"]} contentStyle={{ background: "#020617", border: "1px solid #334155", borderRadius: 12 }} />
        <Bar dataKey="realized_pnl" radius={[3, 3, 0, 0]}>{chart.map((row) => <Cell key={row.date} fill={row.realized_pnl < 0 ? "#fb7185" : "#34d399"} />)}</Bar>
      </BarChart></ResponsiveContainer> : <div className="flex h-full items-center justify-center text-sm text-slate-500">{loading ? "Calculating report…" : "No closes in this period."}</div>}</div>
    </section>
    <div className={`grid gap-4 ${filters.source !== "TERMINAL" ? "lg:grid-cols-2" : ""}`}>
      {[
        ["Instrument breakdown", report?.instruments, "symbol"],
        ...(filters.source !== "TERMINAL" ? [["Strategy comparison", report?.strategies, "strategy_name"]] : []),
      ].map(([title, rows, name]) => <section key={title} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
        <h2 className="mb-3 font-semibold">{title}</h2>
        <div className="scrollbar-theme max-h-80 space-y-2 overflow-y-auto">
          {!rows?.length && <p className="text-sm text-slate-500">No results for these filters.</p>}
          {rows?.map((row) => <div key={row.instrument_id ?? row.strategy_key ?? "unavailable"} className="flex items-center justify-between gap-3 rounded-lg bg-slate-900/50 p-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{row[name] || "Strategy unavailable"}</p>
              <p className="mt-1 text-xs text-slate-500">{row.closes} closes · {displayNumber(row.win_rate)}% wins</p>
            </div>
            <span className={`whitespace-nowrap text-sm font-semibold ${pnlTone(row.realized_pnl)}`}>{displayMoney(row.realized_pnl)}</span>
          </div>)}
        </div>
      </section>)}
    </div>
    <div className="flex flex-wrap justify-between gap-2 text-xs leading-5 text-slate-500">
      <p>Historical equity returns, Sharpe, and account drawdown are unavailable without a verified equity series.</p>
      {report && <span>{source.description} · Observed {formatDateTime(report.observed_at)}</span>}
    </div>
    <Dialog open={researchOpen} onOpenChange={(open) => { if (!busy) setResearchOpen(open); }}>
      <DialogContent className="flex max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] flex-col gap-0 overflow-hidden rounded-xl p-0">
        <div className="shrink-0 border-b border-slate-800 p-5 pr-12">
          <DialogTitle className="flex items-center gap-2"><Sparkles size={18} />Investigate these results</DialogTitle>
          <DialogDescription className="mt-2">Open a conversation with the recorded evidence from this report.</DialogDescription>
        </div>
        <div className="scrollbar-theme min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 text-sm">
            <p className="font-medium">{source.label} · {filters.date_from} to {filters.date_to}</p>
            <p className="mt-1 text-slate-400">{summary?.closes} recorded closes · {displayMoney(summary?.realized_pnl)} realized P&L</p>
            <p className="mt-2 text-xs text-slate-500">{report?.pnl_basis}. Account, strategy, and instrument filters are retained.</p>
          </div>
          <label className="flex items-start gap-3 text-sm text-slate-300">
            <Checkbox className="mt-0.5" checked={includeNotes} onCheckedChange={(value) => setIncludeNotes(Boolean(value))} disabled={busy} />
            <span>Include saved journal notes<span className="mt-1 block text-xs text-slate-500">Optional. Notes and ratings are your own assessments.</span></span>
          </label>
          <p className="text-xs leading-5 text-slate-400">You can edit the question before sending. Sending starts AI research.</p>
        </div>
        <div className="flex shrink-0 justify-end gap-2 border-t border-slate-800 p-4">
          <Button variant="outline" disabled={busy} onClick={() => setResearchOpen(false)}>Cancel</Button>
          <Button disabled={busy || loading || !!error || !summary?.closes} onClick={research}>{busy && <Loader2 size={15} className="mr-2 animate-spin" />}Open research</Button>
        </div>
      </DialogContent>
    </Dialog>
  </div>;
}
