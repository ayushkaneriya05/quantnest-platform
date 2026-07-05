/**
 * BacktestList — Primary backtesting dashboard.
 * Shows all backtest runs with status, live progress, and quick actions.
 */
import React, { useState, useEffect, useCallback, useRef } from "react";
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
  TrendingUp,
  TrendingDown,
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

/* ─── Status Badge Config ─── */
const STATUS_CONFIG = {
  PENDING:    { label: "Pending",    color: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30", icon: Clock },
  RUNNING:    { label: "Running",    color: "bg-blue-500/15 text-blue-400 border-blue-500/30",     icon: RefreshCw },
  COMPLETED:  { label: "Completed",  color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30", icon: CheckCircle2 },
  FAILED:     { label: "Failed",     color: "bg-red-500/15 text-red-400 border-red-500/30",        icon: AlertCircle },
  CANCELLED:  { label: "Cancelled",  color: "bg-gray-500/15 text-gray-400 border-gray-500/30",     icon: XCircle },
};

/* ─── Helpers ─── */
function timeAgo(dateString) {
  if (!dateString) return "—";
  const seconds = Math.floor((Date.now() - new Date(dateString).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateString).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

function formatCurrency(val) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(val) || 0);
}

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
    } catch {
      notifyRef.current.error("Failed to load backtests");
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
    handleCompleteOrError
  );

  // Move actions to header
  useSetPageActions(
    <div className="flex items-center gap-2">

      <Button
        variant="outline"
        size="sm"
        onClick={() => navigate("/dashboard/backtest/montecarlo")}
        className="bg-gray-900 border-gray-800 hover:bg-gray-800 text-amber-400 h-9"
      >
        <Dices className="h-4 w-4 mr-2" />
        Monte Carlo
      </Button>
      <div className="h-6 w-px bg-gray-800 mx-1" />
    <Button
      onClick={() => navigate("/dashboard/backtest/setup")}
      className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold h-9 px-4 shadow-lg shadow-indigo-500/20"
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
    } catch {
      notify.error("Failed to delete backtest");
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
        navigate(`/dashboard/backtest/results/${response.data.run.id}`);
      }
    } catch (err) {
      console.error(err);
      notify.error(err.response?.data?.error || "Failed to rerun backtest");
    } finally {
      setRerunningId(null);
    }
  };

  const handleRowClick = (run) => {
    navigate(`/dashboard/backtest/results/${run.id}`);
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
          <p className="text-sm text-gray-500">Loading backtests…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-6 lg:py-8 space-y-6">
      {/* ── KPI Cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Runs",  value: kpis.total,     icon: BarChart2,    accent: "text-white",       bg: "bg-gray-500/10" },
          { label: "Completed",   value: kpis.completed,  icon: CheckCircle2, accent: "text-emerald-400", bg: "bg-emerald-500/10" },
          { label: "Running",     value: kpis.running,    icon: Activity,     accent: "text-blue-400",    bg: "bg-blue-500/10" },
          { label: "Failed",      value: kpis.failed,     icon: AlertCircle,  accent: "text-red-400",     bg: "bg-red-500/10" },
        ].map((kpi) => (
          <Card key={kpi.label} className="bg-gray-900/60 border-gray-800 hover:border-gray-700 transition-colors">
            <CardContent className="p-4 flex items-center gap-4">
              <div className={`p-2.5 rounded-xl ${kpi.bg}`}>
                <kpi.icon className={`h-5 w-5 ${kpi.accent}`} />
              </div>
              <div>
                <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wider">{kpi.label}</p>
                <p className={`text-2xl font-bold ${kpi.accent}`}>{kpi.value}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* ── Filters ── */}
      <div className="flex flex-col md:flex-row gap-3 justify-between items-start md:items-center">
        <div className="relative w-full md:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or strategy…"
            className="pl-9 bg-gray-900/60 border-gray-800 text-white h-10 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        <div className="flex bg-gray-900/60 border border-gray-800 p-1 rounded-lg">
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
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Table ── */}
      {filtered.length === 0 ? (
        <Card className="bg-gray-900/40 border-gray-800 border-dashed">
          <CardContent className="py-16 flex flex-col items-center gap-4">
            <div className="p-4 rounded-2xl bg-indigo-500/5 border border-indigo-500/10">
              <TestTube className="h-10 w-10 text-indigo-400/60" />
            </div>
            <div className="text-center">
              <h3 className="text-lg font-semibold text-white">
                {search || statusFilter !== "all" ? "No matching backtests" : "No backtests yet"}
              </h3>
              <p className="text-sm text-gray-500 mt-1 max-w-sm">
                {search || statusFilter !== "all"
                  ? "Try adjusting your search or filter criteria."
                  : "Launch your first simulation to see how your strategy performs against historical data."}
              </p>
            </div>
            {!search && statusFilter === "all" && (
              <Button
                onClick={() => navigate("/dashboard/backtest/setup")}
                className="bg-indigo-600 hover:bg-indigo-500 mt-2"
              >
                <Play className="h-4 w-4 mr-2" />
                Run First Backtest
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card className="bg-gray-900/40 border-gray-800 overflow-hidden">
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-gray-800/40 border-b border-gray-800">
                    <th className="px-5 py-3.5 text-[11px] text-gray-500 font-semibold uppercase tracking-wider">Name</th>
                    <th className="px-5 py-3.5 text-[11px] text-gray-500 font-semibold uppercase tracking-wider">Strategy</th>
                    <th className="px-5 py-3.5 text-[11px] text-gray-500 font-semibold uppercase tracking-wider">Period</th>
                    <th className="px-5 py-3.5 text-[11px] text-gray-500 font-semibold uppercase tracking-wider">Capital</th>
                    <th className="px-5 py-3.5 text-[11px] text-gray-500 font-semibold uppercase tracking-wider">Status</th>
                    <th className="px-5 py-3.5 text-[11px] text-gray-500 font-semibold uppercase tracking-wider text-right">Created</th>
                    <th className="px-5 py-3.5 text-[11px] text-gray-500 font-semibold uppercase tracking-wider w-10"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/50">
                  {paginatedRuns.map((run) => {
                    const cfg = STATUS_CONFIG[run.status] || STATUS_CONFIG.PENDING;
                    const StatusIcon = cfg.icon;
                    return (
                      <tr
                        key={run.id}
                        onClick={() => handleRowClick(run)}
                        className="group hover:bg-gray-800/30 cursor-pointer transition-colors"
                      >
                        {/* Name */}
                        <td className="px-5 py-4">
                          <span className="text-sm font-semibold text-white group-hover:text-indigo-300 transition-colors">
                            {run.name || `Backtest #${run.id}`}
                          </span>
                        </td>

                        {/* Strategy */}
                        <td className="px-5 py-4">
                          <span className="text-sm text-gray-400">{run.strategy_name || "—"}</span>
                        </td>

                        {/* Period */}
                        <td className="px-5 py-4">
                          <span className="text-xs text-gray-500 font-mono">
                            {run.start_date} → {run.end_date}
                          </span>
                        </td>

                        {/* Capital */}
                        <td className="px-5 py-4">
                          <span className="text-sm text-gray-300 font-mono">
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
                                <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-blue-500 rounded-full transition-all duration-700 shadow-[0_0_8px_rgba(59,130,246,0.5)]"
                                    style={{ width: `${run.progress_pct || 0}%` }}
                                  />
                                </div>
                                <span className="text-[10px] text-blue-400 font-bold tabular-nums">
                                  {run.progress_pct || 0}%
                                </span>
                              </div>
                            )}
                          </div>
                        </td>

                        {/* Created */}
                        <td className="px-5 py-4 text-right">
                          <span className="text-xs text-gray-500">{timeAgo(run.created_at)}</span>
                        </td>

                        {/* Actions */}
                        <td className="px-3 py-4">
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={(e) => handleRerun(e, run.id)}
                              disabled={rerunningId === run.id}
                              className="p-1.5 rounded-md hover:bg-blue-500/10 text-gray-600 hover:text-blue-400 transition-colors"
                              title="Rerun Backtest"
                            >
                              <RefreshCw className={`h-3.5 w-3.5 ${rerunningId === run.id ? "animate-spin" : ""}`} />
                            </button>
                            <button
                              onClick={(e) => handleDelete(e, run.id)}
                              disabled={deletingId === run.id}
                              className="p-1.5 rounded-md hover:bg-red-500/10 text-gray-600 hover:text-red-400 transition-colors"
                              title="Delete"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                            <ChevronRight className="h-4 w-4 text-gray-700" />
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
              <div className="flex items-center justify-between px-6 py-4 border-t border-gray-800">
                <span className="text-xs text-gray-500">
                  Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length} runs
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                    className="border-gray-700 bg-gray-900 hover:bg-gray-800 h-8 px-3"
                  >
                    <ChevronLeft className="h-3.5 w-3.5 mr-1" />
                    Prev
                  </Button>
                  <span className="text-xs text-gray-400 font-medium tabular-nums">
                    {page} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                    className="border-gray-700 bg-gray-900 hover:bg-gray-800 h-8 px-3"
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
