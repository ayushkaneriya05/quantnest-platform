/**
 * Monte Carlo Simulation - statistical analysis of backtest results
 * B12: Auto-refresh when RUNNING
 * B13: Display worst/best case + equity distribution chart
 */
import { useState, useEffect, useMemo, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { Badge } from "@/shared/components/ui/badge";
import {
  Play,
  Plus,
  ChevronLeft,
  ChevronRight,
  BarChart2,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  X,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { backtestApi } from "@/shared/services/backtestApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { formatCurrency, formatNumber } from "@/shared/utils/formatters";

const formatMetricValue = (value, metricName) => {
  if (value == null) return "N/A";
  if (["Terminal Capital", "Expectancy"].includes(metricName)) return formatCurrency(value);
  if (["Total Return", "Max Drawdown", "Win Rate"].includes(metricName)) return `${formatNumber(value)}%`;
  return formatNumber(value);
};

export default function MonteCarloSim() {
  const location = useLocation();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const [backtestRuns, setBacktestRuns] = useState([]);
  const [monteCarloRuns, setMonteCarloRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  const [results, setResults] = useState([]);
  const selectedRunId = selectedRun?.id;
  const selectedRunStatus = selectedRun?.status;
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [startingRunId, setStartingRunId] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 10;

  const [formData, setFormData] = useState({
    backtest_run: "",
    num_simulations: 1000,
    confidence_level: 0.95,
  });

  const backtestFilterId = location.state?.backtestId ? String(location.state.backtestId) : null;

  const fetchData = useCallback(async () => {
    try {
      const [runsData, mcData] = await Promise.all([
        backtestApi.getRuns({ status: "COMPLETED" }),
        backtestApi.getMonteCarloRuns(),
      ]);
      setBacktestRuns(runsData.data || []);
      const runs = mcData.data || [];
      setMonteCarloRuns(runs);
      setSelectedRun((current) => current ? runs.find((run) => run.id === current.id) || current : current);
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to load Monte Carlo data"));
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (backtestFilterId) {
      setFormData((current) => ({
        ...current,
        backtest_run: backtestFilterId,
      }));
    }
  }, [backtestFilterId]);

  // B12: Auto-refresh when any simulation is RUNNING
  const hasRunning = monteCarloRuns.some((mc) => mc.status === "RUNNING");
  useEffect(() => {
    if (!hasRunning) return undefined;
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [hasRunning, fetchData]);

  // Newer results should appear first + optionally filter by active backtest ID
  const filteredAndSortedRuns = useMemo(() => {
    let runs = [...monteCarloRuns];
    if (backtestFilterId) {
      runs = runs.filter((run) => String(run.backtest_run) === backtestFilterId);
    }
    // Newer first (descending by ID)
    runs.sort((a, b) => b.id - a.id);
    return runs;
  }, [monteCarloRuns, backtestFilterId]);

  /* ─── Pagination ─── */
  const totalPages = Math.max(1, Math.ceil(filteredAndSortedRuns.length / PAGE_SIZE));
  const paginatedRuns = filteredAndSortedRuns.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE,
  );

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.backtest_run) {
      notify.error("Please select a backtest run");
      return;
    }

    try {
      setSubmitting(true);
      const response = await backtestApi.createMonteCarlo(formData);
      await backtestApi.startMonteCarlo(response.data.id);
      setIsModalOpen(false);
      notify.success("Monte Carlo simulation started.");
      await fetchData();
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to start simulation"));
      await fetchData();
    } finally {
      setSubmitting(false);
    }
  };

  const handleStart = useCallback(async (mcRun) => {
    try {
      setStartingRunId(mcRun.id);
      await backtestApi.startMonteCarlo(mcRun.id);
      notify.success("Monte Carlo simulation started.");
      await fetchData();
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to start simulation"));
      await fetchData();
    } finally {
      setStartingRunId(null);
    }
  }, [fetchData, notify]);

  const viewResults = useCallback((mcRun) => setSelectedRun(mcRun), []);

  useEffect(() => {
    if (!selectedRunId || selectedRunStatus !== "COMPLETED") {
      setResults([]);
      setResultsLoading(false);
      return undefined;
    }

    let active = true;
    setResultsLoading(true);
    backtestApi.getMonteCarloResults(selectedRunId)
      .then((response) => {
        if (active) setResults(response.data || []);
      })
      .catch((error) => {
        if (active) notify.error(getApiErrorMessage(error, "Failed to load simulation results"));
      })
      .finally(() => {
        if (active) setResultsLoading(false);
      });

    return () => { active = false; };
  }, [selectedRunId, selectedRunStatus, notify]);

  // Auto-select latest completed run on load
  useEffect(() => {
    if (filteredAndSortedRuns.length > 0 && !selectedRun) {
      const latestCompleted = filteredAndSortedRuns.find((run) => run.status === "COMPLETED");
      if (latestCompleted) {
        setSelectedRun(latestCompleted);
      }
    }
  }, [filteredAndSortedRuns, selectedRun]);

  // Build histogram data from equity_distribution_json
  const histogramData = useMemo(() => {
    if (!selectedRun?.equity_distribution_json?.histogram) return [];
    const { counts, bin_edges } = selectedRun.equity_distribution_json.histogram;
    if (!counts || !bin_edges) return [];
    return counts.map((count, i) => ({
      range: `${formatCurrency(bin_edges[i])}`,
      count,
      from: bin_edges[i],
      to: bin_edges[i + 1],
    }));
  }, [selectedRun]);

  const confidenceLevel = Number(selectedRun?.confidence_level ?? 0.95);
  const lowerBoundPercentile = ((1 - confidenceLevel) / 2) * 100;
  const upperBoundPercentile = 100 - lowerBoundPercentile;
  const formatPercentile = (value) => Number(value.toFixed(2));
  const selectedRunMessage = selectedRun?.error_message || ({
    FAILED: "The simulation failed.",
    RUNNING: "Simulation is running. Results will appear here when it completes.",
    PENDING: "This simulation is waiting to start. Use Start simulation in the history list.",
    COMPLETED: resultsLoading
      ? "Loading simulation results..."
      : "No result metrics are available for this simulation.",
  }[selectedRun?.status] || "Select a completed simulation from the history log to view its detailed metrics and charts.");

  const handleBack = () => {
    if (backtestFilterId) {
      navigate(`/dashboard/backtest/results/${backtestFilterId}`);
    } else {
      navigate("/dashboard/backtest");
    }
  };

  useSetPageActions(
    <div className="flex items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        onClick={handleBack}
        className="bg-gray-900 border-gray-800 hover:bg-gray-800 h-9 px-3"
      >
        <ChevronLeft className="h-4 w-4 mr-1" />
        Back
      </Button>
      <Button
        size="sm"
        onClick={() => setIsModalOpen(true)}
        className="bg-indigo-600 hover:bg-indigo-700 text-white h-9 px-3"
      >
        <Plus className="h-4 w-4 mr-2" />
        New Simulation
      </Button>
    </div>,
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <GlobalLoader />
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-6 lg:py-8 space-y-6">
      {/* Simulation Form Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="bg-gray-900 border border-gray-800 rounded-xl max-w-lg w-full p-6 shadow-2xl relative">
            <button
              onClick={() => setIsModalOpen(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-white"
            >
              <X className="h-5 w-5" />
            </button>
            <h3 className="text-white text-lg font-bold mb-4">Configure Simulation</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label className="text-gray-400">Backtest Run *</Label>
                {backtestFilterId ? (
                  <div className="p-3 bg-gray-800 border border-gray-700 rounded-md text-white font-medium text-sm">
                    {backtestRuns.find((run) => String(run.id) === backtestFilterId)?.name || `Backtest Run #${backtestFilterId}`}
                  </div>
                ) : (
                  <Select resource="backtests" filters={{ status: "COMPLETED" }}
                    value={formData.backtest_run}
                    onValueChange={(value) =>
                      setFormData({ ...formData, backtest_run: value })
                    }
                  >
                    <SelectTrigger className="bg-gray-800 border-gray-700">
                      <SelectValue placeholder="Select completed backtest" />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-900 border-gray-800 text-white">
                      {backtestRuns.map((run) => (
                        <SelectItem key={run.id} value={run.id.toString()}>
                          {run.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-gray-400">Simulations</Label>
                  <Input
                    type="number"
                    min={100}
                    max={10000}
                    step={100}
                    value={formData.num_simulations}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        num_simulations: parseInt(e.target.value, 10) || 0,
                      })
                    }
                    className="bg-gray-800 border-gray-700 text-white"
                  />
                </div>
                <div className="space-y-2">
                    <Label className="text-gray-400">Central Outcome Range</Label>
                  <Select
                    value={formData.confidence_level.toString()}
                    onValueChange={(value) =>
                      setFormData({
                        ...formData,
                        confidence_level: parseFloat(value),
                      })
                    }
                  >
                    <SelectTrigger className="bg-gray-800 border-gray-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-900 border-gray-800 text-white">
                      <SelectItem value="0.9">90% of outcomes</SelectItem>
                      <SelectItem value="0.95">95% of outcomes</SelectItem>
                      <SelectItem value="0.99">99% of outcomes</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsModalOpen(false)}
                  className="border-gray-700"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="bg-indigo-600"
                  disabled={submitting}
                >
                  {submitting ? (
                    <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4 mr-1" />
                  )}
                  {submitting ? "Starting…" : "Run Simulation"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Side-by-Side (Split Panel Layout) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Side: History List (1/3 Width) */}
        <div className="lg:col-span-1 space-y-4">
          <Card className="bg-gray-900/50 border-gray-800">
            <CardHeader className="pb-3">
              <CardTitle className="text-white text-base">
                {backtestFilterId ? "Simulation Log" : "Simulation History"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {filteredAndSortedRuns.length === 0 ? (
                <div className="py-8 text-center text-gray-500 text-sm">
                  No simulations available. Click &quot;New Simulation&quot; to start.
                </div>
              ) : (
                <div className="space-y-2">
                  {paginatedRuns.map((mc) => (
                    <div
                      key={mc.id}
                      className={`p-3 bg-gray-800/40 rounded-lg cursor-pointer hover:bg-gray-800/80 border transition-all duration-150 ${
                        selectedRun?.id === mc.id
                          ? "border-indigo-500 bg-indigo-500/5"
                          : "border-transparent"
                      }`}
                      onClick={() => viewResults(mc)}
                    >
                      <div className="flex justify-between items-start">
                        <div className="space-y-0.5">
                          <p className="text-white text-sm font-semibold truncate max-w-[150px] xl:max-w-[180px]">
                            {backtestRuns.find((run) => run.id === mc.backtest_run)
                              ?.name || `Backtest #${mc.backtest_run}`}
                          </p>
                          <p className="text-xs text-gray-400">
                            {mc.num_simulations} sims • {(mc.confidence_level * 100).toFixed(0)}% outcome range
                          </p>
                        </div>
                        <Badge
                          className={`text-[10px] py-0.5 px-1.5 ${
                            mc.status === "COMPLETED"
                              ? "bg-green-600/15 text-green-400 border-green-500/10"
                              : mc.status === "RUNNING"
                                ? "bg-blue-600/15 text-blue-400 border-blue-500/10 animate-pulse"
                                : mc.status === "FAILED"
                                  ? "bg-red-600/15 text-red-400 border-red-500/10"
                                  : "bg-yellow-600/15 text-yellow-400 border-yellow-500/10"
                          }`}
                        >
                          {mc.status}
                        </Badge>
                      </div>
                      {mc.status === "PENDING" && (
                        <div className="flex justify-end mt-2">
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={startingRunId === mc.id}
                            onClick={(event) => {
                              event.stopPropagation();
                              handleStart(mc);
                            }}
                            className="h-7 border-gray-700 text-xs"
                          >
                            {startingRunId === mc.id ? "Starting..." : "Start simulation"}
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Compact Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between pt-3 border-t border-gray-800 mt-3 text-xs">
                      <span className="text-gray-500 font-mono">
                        {page}/{totalPages}
                      </span>
                      <div className="flex gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={page <= 1}
                          onClick={() => setPage((p) => p - 1)}
                          className="h-7 px-2 border-gray-800 text-gray-400"
                        >
                          <ChevronLeft className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={page >= totalPages}
                          onClick={() => setPage((p) => p + 1)}
                          className="h-7 px-2 border-gray-800 text-gray-400"
                        >
                          <ChevronRight className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Side: Selected Results Details (2/3 Width) */}
        <div className="lg:col-span-2 space-y-6">
          {selectedRun && results.length > 0 ? (
            <div className="space-y-6">
              {/* Performance Cards Grid */}
              <Card className="bg-gray-900/50 border-gray-800">
                <CardHeader className="pb-3 border-b border-gray-800/40">
                  <CardTitle className="text-white text-base">
                    Metrics Summary:{" "}
                    {backtestRuns.find((run) => run.id === selectedRun.backtest_run)
                      ?.name || `Backtest #${selectedRun.backtest_run}`}
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Estimated central {(selectedRun.confidence_level * 100).toFixed(0)}% outcome range across {selectedRun.num_simulations} resampled trade sequences
                  </CardDescription>
                  <p className="text-[11px] text-gray-500 mt-1">
                    Resamples closed-trade net P&amp;L with replacement; drawdown uses realized trade closes.
                  </p>
                </CardHeader>
                <CardContent className="pt-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                    {results.map((result) => (
                      <div
                        key={result.id}
                        className="p-4 bg-gray-800/30 rounded-lg border border-gray-800 text-xs space-y-2"
                      >
                        <div className="text-white font-bold text-xs uppercase tracking-wider border-b border-gray-800 pb-1.5 mb-1 text-indigo-400">
                          {result.metric_name}
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Mean (Expected)</span>
                          <span className="text-white font-semibold">
                            {formatMetricValue(result.mean_value, result.metric_name)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Median</span>
                          <span className="text-gray-300">
                            {formatMetricValue(result.median_value, result.metric_name)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Std Deviation</span>
                          <span className="text-gray-400">
                            {formatMetricValue(result.std_dev, result.metric_name)}
                          </span>
                        </div>
                        <div className={`flex justify-between border-t border-gray-800/50 pt-1 ${result.metric_name === "Max Drawdown" ? "text-green-400" : "text-red-400"}`}>
                          <span className="flex items-center gap-1 font-medium">
                            <TrendingDown className="h-3 w-3" />
                            Lower outcome bound ({formatPercentile(lowerBoundPercentile)}th percentile)
                          </span>
                          <span className="font-bold">
                            {formatMetricValue(result.lower_outcome_bound, result.metric_name)}
                          </span>
                        </div>
                        <div className={`flex justify-between ${result.metric_name === "Max Drawdown" ? "text-red-400" : "text-green-400"}`}>
                          <span className="flex items-center gap-1 font-medium">
                            <TrendingUp className="h-3 w-3" />
                            Upper outcome bound ({formatPercentile(upperBoundPercentile)}th percentile)
                          </span>
                          <span className="font-bold">
                            {formatMetricValue(result.upper_outcome_bound, result.metric_name)}
                          </span>
                        </div>
                        {result.valid_simulations != null && result.valid_simulations < selectedRun.num_simulations && (
                          <p className="text-[10px] text-amber-400">
                            Valid outcomes: {result.valid_simulations} of {selectedRun.num_simulations} simulations
                          </p>
                        )}
                        <div className="h-px bg-gray-800/50 my-1" />
                        <div className="flex justify-between text-red-500">
                          <span className="font-semibold">Worst observed</span>
                          <span className="font-bold">
                            {formatMetricValue(result.worst_case, result.metric_name)}
                          </span>
                        </div>
                        <div className="flex justify-between text-green-500">
                          <span className="font-semibold">Best observed</span>
                          <span className="font-bold">
                            {formatMetricValue(result.best_case, result.metric_name)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Equity Distribution Chart Card */}
              {histogramData.length > 0 && (
                <Card className="bg-gray-900/50 border-gray-800">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-white text-base flex items-center gap-2">
                      <BarChart2 className="h-4 w-4 text-indigo-400" />
                      Equity Distribution Density
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="h-[250px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={histogramData}>
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="#374151"
                            vertical={false}
                          />
                          <XAxis
                            dataKey="range"
                            stroke="#9ca3af"
                            fontSize={9}
                            tickLine={false}
                            axisLine={false}
                            angle={-25}
                            textAnchor="end"
                            height={50}
                          />
                          <YAxis
                            stroke="#9ca3af"
                            fontSize={10}
                            tickLine={false}
                            axisLine={false}
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: "#111827",
                              border: "1px solid #374151",
                              borderRadius: "8px",
                            }}
                            formatter={(value) => [value, "Simulations"]}
                            labelFormatter={(label) => `Equity: ${label}`}
                          />
                          <Bar
                            dataKey="count"
                            fill="#6366f1"
                            radius={[3, 3, 0, 0]}
                            fillOpacity={0.85}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Compact distribution percentile markers */}
                    {selectedRun.equity_distribution_json && (
                      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 border-t border-gray-800 pt-4 text-center">
                        {[
                          { label: "Min", value: selectedRun.equity_distribution_json.min, color: "text-red-400" },
                          { label: "P25", value: selectedRun.equity_distribution_json.p25, color: "text-amber-400" },
                          { label: "Median", value: selectedRun.equity_distribution_json.p50, color: "text-white" },
                          { label: "P75", value: selectedRun.equity_distribution_json.p75, color: "text-indigo-400" },
                          { label: "Max", value: selectedRun.equity_distribution_json.max, color: "text-green-400" },
                        ].map((item) => (
                          <div key={item.label} className="bg-gray-800/20 p-2 rounded border border-gray-800/40">
                            <div className="text-[10px] text-gray-500 uppercase font-bold">{item.label}</div>
                            <div className={`text-xs font-bold font-mono ${item.color} mt-0.5`}>
                              {item.value != null ? formatCurrency(item.value) : "—"}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <Card className="bg-gray-900/50 border-gray-800 h-96 flex flex-col items-center justify-center text-gray-500">
              <BarChart2 className="h-10 w-10 mb-2 text-gray-700" />
              <p className="text-sm text-center px-6">
                {selectedRunMessage}
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
