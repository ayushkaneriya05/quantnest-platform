import RefreshButton from "@/shared/components/RefreshButton";
import WorkspaceState from "@/shared/components/WorkspaceState";
import Pagination from "@/shared/components/Pagination";
import { usePagination, useQueryState } from "@/shared/hooks/usePagination";
import PageTabs from "@/shared/components/PageTabs";
import { GlobalLoader, LoaderMark } from '@/shared/components/ui/global-loader';
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
/**
 * BacktestList — Primary backtesting dashboard.
 * Shows all backtest runs with status, live progress, and quick actions.
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card,
  CardContent,
} from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import {
  Plus,
  Search,
  TestTube,
  Activity,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Clock,
  Trash2,
  ChevronRight,
  BarChart2,
  Play,
  XCircle,
  Dices,
} from "lucide-react";
import { backtestApi } from "@/shared/services/backtestApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { customConfirm } from "@/shared/components/ui/custom-dialog";
import { useBacktestProgress } from "@/shared/hooks/useBacktestProgress";
import { formatCurrency, formatDateTime, formatNumber } from "@/shared/utils/formatters";

/* ─── Status Badge Config ─── */
const STATUS_CONFIG = {
  QUEUED:     { label: "Queued", color: "bg-warning/15 text-warning border-warning/30", icon: Clock },
  PENDING:    { label: "Pending",    color: "bg-warning/15 text-warning border-warning/30", icon: Clock },
  RUNNING:    { label: "Running",    color: "bg-brand/15 text-brand border-brand/30",     icon: RefreshCw },
  COMPLETED:  { label: "Completed",  color: "bg-success/15 text-success border-success/30", icon: CheckCircle2 },
  FAILED:     { label: "Failed",     color: "bg-loss/15 text-loss border-loss/30",        icon: AlertCircle },
  CANCELLED:  { label: "Cancelled",  color: "bg-muted/15 text-muted-foreground border-border/30",     icon: XCircle },
};

/* ─── Helpers ─── */
/* ─── Component ─── */
export default function BacktestList() {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const notifyRef = useRef(notify);
  notifyRef.current = notify;

  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useQueryState("search", "", { namespace: "", replace: true });
  const [statusFilter, setStatusFilter] = useQueryState("status", "all", { namespace: "", replace: false });
  const [deletingId, setDeletingId] = useState(null);
  const [rerunningId, setRerunningId] = useState(null);
  const { page, pageSize, setPage, setPageSize, accept } = usePagination(JSON.stringify([search, statusFilter]));
  const [metadata, setMetadata] = useState({ count: 0 });
  const [summary, setSummary] = useState({ total: 0, statuses: {} });
  const generation = useRef(0);
  const summaryKey = useRef(null);

  const fetchRuns = useCallback(async () => {
    const request = ++generation.current;
    setLoading(true);
    setError("");
    try {
      const params = { page, page_size: pageSize, search, ...(statusFilter !== 'all' ? { status: statusFilter } : {}) };
      const response = await backtestApi.getRuns(params);
      if (request !== generation.current) return;
      setRuns(response.data.results); setMetadata(response.data); accept(response.data);
      if (summaryKey.current !== search) {
        const snapshot = await backtestApi.getSummary({ search });
        if (request !== generation.current) return;
        setSummary(snapshot.data); summaryKey.current = search;
      }
    } catch (error) {
      if (request === generation.current) setError(getApiErrorMessage(error, "Failed to load backtests"));
    } finally {
      if (request === generation.current) setLoading(false);
    }
  }, [page, pageSize, search, statusFilter, accept]);

  useEffect(() => {
    const timer = setTimeout(fetchRuns, search ? 250 : 0);
    const guard = generation;
    return () => { clearTimeout(timer); guard.current++; };
  }, [fetchRuns, search]);


  // Handle WebSocket Progress
  const handleProgress = useCallback((data) => {
    setRuns((prev) =>
      prev.map((r) =>
        r.id === data.run_id
          ? { ...r, status: data.status, progress_pct: data.progress_pct }
          : r
      )
    );
  }, []);

  const handleCompleteOrError = useCallback((data) => {
    setRuns((prev) =>
      prev.map((r) =>
        r.id === data.run_id
          ? { ...r, status: data.status, progress_pct: data.progress_pct }
          : r
      )
    );
    // Fetch runs to get the updated metrics (profit, trades, etc.)
    summaryKey.current = null;
    fetchRuns();
  }, [fetchRuns]);

  // Pass null as backtestId to listen to ALL runs
  useBacktestProgress(
    null,
    handleProgress,
    handleCompleteOrError,
    handleCompleteOrError,
    fetchRuns
  );

  // Move actions to header
  useSetPageActions(
    <div className="flex items-center gap-2">

      <Button
        variant="outline"
        size="sm"
        onClick={() => navigate("/backtests/montecarlo")}
        className=""
      >
        <Dices className="h-4 w-4 mr-2" />
        Monte Carlo
      </Button>
      <RefreshButton onClick={() => { summaryKey.current = null; return fetchRuns(); }} label="Refresh backtests" loading={loading} />
    <Button variant="default"
      onClick={() => navigate("/backtests/setup")}
      className="font-semibold px-4"
    >
      <Plus className="h-4 w-4 mr-2" />
      New Backtest
    </Button>
    </div>
  );

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    const confirmed = await customConfirm("Delete this backtest run? This cannot be undone.");
    if (!confirmed) return;
    try {
      setDeletingId(id);
      await backtestApi.deleteRun(id);
      notify.success("Backtest deleted");
      summaryKey.current = null;
      await fetchRuns();
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to delete backtest"));
    } finally {
      setDeletingId(null);
    }
  };

  const handleRerun = async (e, id) => {
    e.stopPropagation();

    setRerunningId(id);
    try {
      const {data: estimate} = await backtestApi.estimateRerun(id);
      const confirmed = await customConfirm(`Rerun this saved configuration? ${formatNumber(estimate.instrument_candles, { minimumFractionDigits: 0 })} instrument-candles including warmup; ${estimate.credits === null ? 'unmetered usage' : `${estimate.credits} credits on success`}. Internal failures restore the allowance.`);
      if (!confirmed) return;
      const response = await backtestApi.rerunRun(id, estimate.token);
      notify.success("Backtest cloned and started successfully!");
      if (response.data?.run) {
        navigate(`/backtests/results/${response.data.run.id}`);
      }
    } catch (err) {
      console.error(err);
      notify.error(getApiErrorMessage(err, "Failed to rerun backtest"));
    } finally {
      setRerunningId(null);
    }
  };

  const handleRowClick = (run) => {
    navigate(`/backtests/results/${run.id}`);
  };

  /* ─── Derived Data ─── */
  const kpis = {
    total: summary.total,
    completed: summary.statuses.COMPLETED || 0,
    running: (summary.statuses.QUEUED || 0) + (summary.statuses.RUNNING || 0),
    failed: summary.statuses.FAILED || 0,
  };

  /* ─── Pagination ─── */
  const paginatedRuns = runs;

  /* ─── Render ─── */
  if (error) return <div className="page-content"><WorkspaceState error={error} onRetry={fetchRuns} /></div>;
  if (loading && !metadata.page) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="flex flex-col items-center gap-3">
          <GlobalLoader text="Loading backtests…" />
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      {/* ── KPI Cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: "Total Runs",  value: kpis.total,     icon: BarChart2,    accent: "text-foreground",       bg: "bg-muted/10" },
          { label: "Completed",   value: kpis.completed,  icon: CheckCircle2, accent: "text-success", bg: "bg-success/10" },
          { label: "Running",     value: kpis.running,    icon: Activity,     accent: "text-brand",    bg: "bg-brand/10" },
          { label: "Failed",      value: kpis.failed,     icon: AlertCircle,  accent: "text-loss",     bg: "bg-loss/10" },
        ].map((kpi) => (
          <Card key={kpi.label} className="bg-card/60 border-border hover:border-border transition-colors">
            <CardContent className="p-3 flex items-center gap-3">
              <div className={`p-2.5 rounded-xl ${kpi.bg}`}>
                <kpi.icon className={`h-5 w-5 ${kpi.accent}`} />
              </div>
              <div>
                <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">{kpi.label}</p>
                <p className={`text-2xl font-bold ${kpi.accent}`}>{kpi.value}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* ── Filters ── */}
      <div className="flex flex-col md:flex-row gap-3 justify-between items-start md:items-center">
        <div className="relative w-full md:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or strategy…"
            className="pl-9 bg-card/60 border-border text-foreground focus:ring-brand focus:border-brand"
          />
        </div>
        <PageTabs appearance="outline" label="Backtest status" value={statusFilter} onValueChange={setStatusFilter} items={[{ value: "all", label: "All" }, { value: "QUEUED", label: "Queued" }, { value: "RUNNING", label: "Running" }, { value: "COMPLETED", label: "Completed" }, { value: "FAILED", label: "Failed" }]} />
      </div>

      {/* ── Table ── */}
      {runs.length === 0 ? (
        <Card className="bg-card/40 border-border border-dashed">
          <CardContent className="py-16 flex flex-col items-center gap-3">
            <div className="p-3 rounded-2xl bg-brand/5 border border-brand/10">
              <TestTube className="h-10 w-10 text-brand" />
            </div>
            <div className="text-center">
              <h3 className="text-lg font-semibold text-foreground">
                {search || statusFilter !== "all" ? "No matching backtests" : "No backtests yet"}
              </h3>
              <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                {search || statusFilter !== "all"
                  ? "Try adjusting your search or filter criteria."
                  : "Launch your first simulation to see how your strategy performs against historical data."}
              </p>
            </div>
            {!search && statusFilter === "all" && (
              <Button variant="default"
                onClick={() => navigate("/backtests/setup")}
                className="mt-2"
              >
                <Play className="h-4 w-4 mr-2" />
                Run First Backtest
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card className="bg-card/40 border-border overflow-hidden">
          <CardContent className="p-0">
            <div className="overflow-x-auto scrollbar-thin-theme">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-secondary/40 border-b border-border">
                    <th className="px-5 py-3.5 text-[11px] text-muted-foreground font-semibold uppercase tracking-wider">Name</th>
                    <th className="px-5 py-3.5 text-[11px] text-muted-foreground font-semibold uppercase tracking-wider">Strategy</th>
                    <th className="px-5 py-3.5 text-[11px] text-muted-foreground font-semibold uppercase tracking-wider">Period</th>
                    <th className="px-5 py-3.5 text-[11px] text-muted-foreground font-semibold uppercase tracking-wider">Capital</th>
                    <th className="px-5 py-3.5 text-[11px] text-muted-foreground font-semibold uppercase tracking-wider">Status</th>
                    <th className="px-5 py-3.5 text-[11px] text-muted-foreground font-semibold uppercase tracking-wider text-right">Created</th>
                    <th className="px-5 py-3.5 text-[11px] text-muted-foreground font-semibold uppercase tracking-wider w-10"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {paginatedRuns.map((run) => {
                    const cfg = STATUS_CONFIG[run.status] || STATUS_CONFIG.PENDING;
                    const StatusIcon = cfg.icon;
                    return (
                      <tr
                        key={run.id}
                        onClick={() => handleRowClick(run)}
                        className="group hover:bg-secondary/30 cursor-pointer transition-colors"
                      >
                        {/* Name */}
                        <td className="px-5 py-3">
                          <span className="text-sm font-semibold text-foreground group-hover:text-brand transition-colors">
                            {run.name || `Backtest #${run.id}`}
                          </span>
                        </td>

                        {/* Strategy */}
                        <td className="px-5 py-3">
                          <span className="text-sm text-muted-foreground">{run.strategy_name || "—"}</span>
                        </td>

                        {/* Period */}
                        <td className="px-5 py-3">
                          <span className="text-xs text-muted-foreground font-mono">
                            {run.start_date} → {run.end_date}
                          </span>
                        </td>

                        {/* Capital */}
                        <td className="px-5 py-3">
                          <span className="text-sm text-foreground font-mono">
                            {formatCurrency(run.initial_capital)}
                          </span>
                        </td>

                        {/* Status + Progress */}
                        <td className="px-5 py-3">
                          <div className="flex flex-col gap-1.5">
                            <Badge
                              variant="outline"
                              className={`${cfg.color} text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 w-fit flex items-center gap-1`}
                            >
                              {["QUEUED", "RUNNING"].includes(run.status) ? <LoaderMark className="h-3 w-3" /> : <StatusIcon className="h-3 w-3" />}
                              {cfg.label}
                            </Badge>
                            {["QUEUED", "RUNNING"].includes(run.status) && (
                              <div className="flex items-center gap-2 w-28">
                                <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-brand rounded-full transition-all duration-700"
                                    style={{ width: `${run.progress_pct || 0}%` }}
                                  />
                                </div>
                                <span className="text-[10px] text-brand font-bold tabular-nums">
                                  {run.progress_pct || 0}%
                                </span>
                              </div>
                            )}
                          </div>
                        </td>

                        {/* Created */}
                        <td className="px-5 py-3 text-right">
                          <span className="text-xs text-muted-foreground">{formatDateTime(run.created_at)}</span>
                        </td>

                        {/* Actions */}
                        <td className="px-3 py-3">
                          <div className="flex items-center gap-1 opacity-100 transition-opacity">
                            <Button variant="ghost" type="button"
                              onClick={(e) => handleRerun(e, run.id)}
                              disabled={rerunningId === run.id}
                              className="p-1.5 rounded-md transition-colors"
                              title="Rerun Backtest"
                            >
                              {rerunningId === run.id ? <LoaderMark className="h-3.5 w-3.5" /> : <RefreshCw className="h-3.5 w-3.5" />}
                            </Button>
                            <Button variant="ghost" type="button"
                              onClick={(e) => handleDelete(e, run.id)}
                              disabled={deletingId === run.id}
                              className="p-1.5 rounded-md transition-colors"
                              title="Delete"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                            <ChevronRight className="h-4 w-4 text-foreground" />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

          </CardContent>
        </Card>
      )}
      <Pagination {...metadata} page={page} pageSize={pageSize} loading={loading} onPageChange={setPage} onPageSizeChange={setPageSize} label="Backtest pages" />
    </div>
  );
}
