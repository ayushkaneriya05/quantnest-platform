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
  ChevronLeft,
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
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { formatCurrency, formatDateTime } from "@/shared/utils/formatters";

/* ─── Status Badge Config ─── */
const STATUS_CONFIG = {
  PENDING:    { label: "Pending",    color: "bg-yellow-500/15 text-yellow-700 dark:text-yellow-400 border-yellow-500/30", icon: Clock },
  RUNNING:    { label: "Running",    color: "bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/30",     icon: RefreshCw },
  COMPLETED:  { label: "Completed",  color: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30", icon: CheckCircle2 },
  FAILED:     { label: "Failed",     color: "bg-red-500/15 text-red-700 dark:text-red-400 border-red-500/30",        icon: AlertCircle },
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
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [deletingId, setDeletingId] = useState(null);
  const [rerunningId, setRerunningId] = useState(null);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [search, statusFilter]);

  const fetchRuns = useCallback(async () => {
    try {
      const response = await backtestApi.getRuns();
      setRuns(Array.isArray(response.data) ? response.data : response.data?.results || []);
    } catch (error) {
      notifyRef.current.error(getApiErrorMessage(error, "Failed to load backtests"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

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
        className="bg-card border-border hover:bg-secondary text-amber-700 dark:text-amber-400 h-9"
      >
        <Dices className="h-4 w-4 mr-2" />
        Monte Carlo
      </Button>
      <div className="h-6 w-px bg-secondary mx-1" />
    <Button
      onClick={() => navigate("/backtests/setup")}
      className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold h-9 px-4 shadow-lg shadow-indigo-500/20"
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
      setRuns((prev) => prev.filter((r) => r.id !== id));
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to delete backtest"));
    } finally {
      setDeletingId(null);
    }
  };

  const handleRerun = async (e, id) => {
    e.stopPropagation();
    const confirmed = await customConfirm("Are you sure you want to clone and rerun this backtest?");
    if (!confirmed) return;
    
    setRerunningId(id);
    try {
      const response = await backtestApi.rerunRun(id);
      notify.success("Backtest cloned and started successfully!");
      if (response.data?.run) {
        setRuns((prev) => [response.data.run, ...prev]);
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
  const filtered = runs.filter((r) => {
    if (statusFilter !== "all" && r.status !== statusFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        (r.name || "").toLowerCase().includes(q) ||
        (r.strategy_name || "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  const kpis = {
    total: runs.length,
    completed: runs.filter((r) => r.status === "COMPLETED").length,
    running: runs.filter((r) => r.status === "RUNNING").length,
    failed: runs.filter((r) => r.status === "FAILED").length,
  };

  /* ─── Pagination ─── */
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginatedRuns = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  /* ─── Render ─── */
  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="flex flex-col items-center gap-3">
          <GlobalLoader />
          <p className="text-sm text-muted-foreground">Loading backtests…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-6 lg:py-8 space-y-6">
      {/* ── KPI Cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Runs",  value: kpis.total,     icon: BarChart2,    accent: "text-foreground",       bg: "bg-muted/10" },
          { label: "Completed",   value: kpis.completed,  icon: CheckCircle2, accent: "text-emerald-700 dark:text-emerald-400", bg: "bg-emerald-500/10" },
          { label: "Running",     value: kpis.running,    icon: Activity,     accent: "text-blue-700 dark:text-blue-400",    bg: "bg-blue-500/10" },
          { label: "Failed",      value: kpis.failed,     icon: AlertCircle,  accent: "text-red-700 dark:text-red-400",     bg: "bg-red-500/10" },
        ].map((kpi) => (
          <Card key={kpi.label} className="bg-card/60 border-border hover:border-border transition-colors">
            <CardContent className="p-4 flex items-center gap-4">
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
            className="pl-9 bg-card/60 border-border text-foreground h-10 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        <div className="flex bg-card/60 border border-border p-1 rounded-lg">
          {[
            { key: "all",       label: "All" },
            { key: "RUNNING",   label: "Running" },
            { key: "COMPLETED", label: "Completed" },
            { key: "FAILED",    label: "Failed" },
          ].map((f) => (
            <button
              key={f.key}
              onClick={() => setStatusFilter(f.key)}
              className={`px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all ${
                statusFilter === f.key
                  ? "bg-indigo-600 text-white shadow-lg"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Table ── */}
      {filtered.length === 0 ? (
        <Card className="bg-card/40 border-border border-dashed">
          <CardContent className="py-16 flex flex-col items-center gap-4">
            <div className="p-4 rounded-2xl bg-indigo-500/5 border border-indigo-500/10">
              <TestTube className="h-10 w-10 text-indigo-700 dark:text-indigo-400" />
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
              <Button
                onClick={() => navigate("/backtests/setup")}
                className="text-white bg-indigo-600 hover:bg-indigo-700 mt-2"
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
                        <td className="px-5 py-4">
                          <span className="text-sm font-semibold text-foreground group-hover:text-indigo-800 dark:group-hover:text-indigo-300 transition-colors">
                            {run.name || `Backtest #${run.id}`}
                          </span>
                        </td>

                        {/* Strategy */}
                        <td className="px-5 py-4">
                          <span className="text-sm text-muted-foreground">{run.strategy_name || "—"}</span>
                        </td>

                        {/* Period */}
                        <td className="px-5 py-4">
                          <span className="text-xs text-muted-foreground font-mono">
                            {run.start_date} → {run.end_date}
                          </span>
                        </td>

                        {/* Capital */}
                        <td className="px-5 py-4">
                          <span className="text-sm text-foreground font-mono">
                            {formatCurrency(run.initial_capital)}
                          </span>
                        </td>

                        {/* Status + Progress */}
                        <td className="px-5 py-4">
                          <div className="flex flex-col gap-1.5">
                            <Badge
                              variant="outline"
                              className={`${cfg.color} text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 w-fit flex items-center gap-1`}
                            >
                              <StatusIcon className={`h-3 w-3 ${run.status === "RUNNING" ? "animate-spin" : ""}`} />
                              {cfg.label}
                            </Badge>
                            {run.status === "RUNNING" && (
                              <div className="flex items-center gap-2 w-28">
                                <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-blue-500 rounded-full transition-all duration-700 shadow-[0_0_8px_rgba(59,130,246,0.5)]"
                                    style={{ width: `${run.progress_pct || 0}%` }}
                                  />
                                </div>
                                <span className="text-[10px] text-blue-700 dark:text-blue-400 font-bold tabular-nums">
                                  {run.progress_pct || 0}%
                                </span>
                              </div>
                            )}
                          </div>
                        </td>

                        {/* Created */}
                        <td className="px-5 py-4 text-right">
                          <span className="text-xs text-muted-foreground">{formatDateTime(run.created_at)}</span>
                        </td>

                        {/* Actions */}
                        <td className="px-3 py-4">
                          <div className="flex items-center gap-1 opacity-100 transition-opacity">
                            <button
                              onClick={(e) => handleRerun(e, run.id)}
                              disabled={rerunningId === run.id}
                              className="p-1.5 rounded-md hover:bg-blue-500/10 text-muted-foreground hover:text-blue-800 dark:hover:text-blue-400 transition-colors"
                              title="Rerun Backtest"
                            >
                              <RefreshCw className={`h-3.5 w-3.5 ${rerunningId === run.id ? "animate-spin" : ""}`} />
                            </button>
                            <button
                              onClick={(e) => handleDelete(e, run.id)}
                              disabled={deletingId === run.id}
                              className="p-1.5 rounded-md hover:bg-red-500/10 text-muted-foreground hover:text-red-800 dark:hover:text-red-400 transition-colors"
                              title="Delete"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                            <ChevronRight className="h-4 w-4 text-foreground" />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-6 py-4 border-t border-border">
                <span className="text-xs text-muted-foreground">
                  Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length} runs
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                    className="border-border bg-card hover:bg-secondary h-8 px-3"
                  >
                    <ChevronLeft className="h-3.5 w-3.5 mr-1" />
                    Prev
                  </Button>
                  <span className="text-xs text-muted-foreground font-medium tabular-nums">
                    {page} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                    className="border-border bg-card hover:bg-secondary h-8 px-3"
                  >
                    Next
                    <ChevronRight className="h-3.5 w-3.5 ml-1" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
