import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import {
  TrendingUp,
  TrendingDown,
  BarChart2,
  Activity,
  RefreshCw,
  ListIcon,
  LineChart,
  Dices,

  AlertCircle,
  CheckCircle2,
  Info,
  Power,
  ChevronLeft,
  DollarSign,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { backtestApi } from "@/shared/services/backtestApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { useBacktestProgress } from "@/shared/hooks/useBacktestProgress";
import { GlobalLoader } from '@/shared/components/ui/global-loader';

const STATUS_STYLES = {
  PENDING: { bg: "bg-yellow-600", text: "Pending", icon: RefreshCw },
  RUNNING: { bg: "bg-blue-600", text: "Running", icon: RefreshCw },
  COMPLETED: { bg: "bg-green-600", text: "Completed", icon: CheckCircle2 },
  FAILED: { bg: "bg-red-600", text: "Failed", icon: AlertCircle },
  CANCELLED: { bg: "bg-gray-600", text: "Cancelled", icon: Activity },
};

/* ─── Helpers ─── */
const toNumber = (val) => {
  const numeric = Number(val);
  return Number.isFinite(numeric) ? numeric : 0;
};

const formatCurrency = (val) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(toNumber(val));

const formatPercent = (val) => `${toNumber(val).toFixed(2)}%`;
const formatRatio = (val) => toNumber(val).toFixed(2);

export default function BacktestResults() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();

  const [run, setRun] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [equityData, setEquityData] = useState([]);
  const [chargesTimeline, setChargesTimeline] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pnlMode, setPnlMode] = useState("net"); // "net" or "gross"

  const fetchData = useCallback(async (isSilent = true) => {
    if (!isSilent) setIsRefreshing(true);
    try {
      const [runData, metricsData, equityCurveData, chargesTimelineData] = await Promise.all([
        backtestApi.getRun(id),
        backtestApi.getRunMetrics(id),
        backtestApi.getRunEquityCurve(id),
        backtestApi.getRunChargesTimeline(id),
      ]);
      setRun(runData.data);
      setMetrics(metricsData.data);
      setEquityData(
        (equityCurveData.data || []).map((point) => ({
          ...point,
          rawTimestamp: new Date(point.timestamp).getTime(),
          timestamp: new Date(point.timestamp).toLocaleDateString(),
          equity: parseFloat(point.equity_value),
        })),
      );
      setChargesTimeline(chargesTimelineData.data || []);
      
      // Lazy load analytics in background without blocking
      backtestApi.getRunAnalytics(id)
        .then(res => setAnalytics(res.data))
        .catch(() => setAnalytics(null));

    } catch (error) {
      notify.error("Failed to load backtest");
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [id, notify]);

  const chartEquityData = useMemo(() => {
    if (pnlMode === "net") return equityData;
    const sortedCharges = chargesTimeline;
    let chargeIndex = 0;
    let cumulativeCharges = 0;
    return equityData.map((point) => {
      while (chargeIndex < sortedCharges.length && sortedCharges[chargeIndex].exitTime <= point.rawTimestamp) {
        cumulativeCharges += sortedCharges[chargeIndex].charges;
        chargeIndex += 1;
      }
      return {
        ...point,
        equity: point.equity + cumulativeCharges,
      };
    });
  }, [equityData, pnlMode, chargesTimeline]);

  useEffect(() => {
    fetchData(true);
  }, [fetchData]);

  const handleProgress = useCallback((data) => {
    setRun((prev) => prev ? { ...prev, progress_pct: data.progress_pct, status: data.status, message: data.message || prev.message } : prev);
  }, []);

  const handleCompleteOrError = useCallback((data) => {
    setRun((prev) => prev ? { ...prev, progress_pct: data.progress_pct, status: data.status, message: data.error || data.message || prev.message } : prev);
    fetchData(); // Fetch the full results when done
  }, [fetchData]);

  useBacktestProgress(
    Number(id), // Convert id to number just in case
    handleProgress,
    handleCompleteOrError,
    handleCompleteOrError
  );

  const handleCancel = async () => {
    try {
      setCancelling(true);
      await backtestApi.cancelRun(id);
      notify.success("Backtest cancelled");
      fetchData();
    } catch (error) {
      notify.error("Failed to cancel backtest");
    } finally {
      setCancelling(false);
    }
  };

  const consolidatedActions = useMemo(() => (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-2 mr-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate("/dashboard/backtest")}
          className="bg-gray-900 border-gray-800 hover:bg-gray-800 h-9 px-3"
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <Badge
          className={`${STATUS_STYLES[run?.status]?.bg || "bg-yellow-600"} text-white border-none px-3 h-9 flex items-center gap-1.5 rounded-md`}
        >
          {React.createElement(STATUS_STYLES[run?.status]?.icon || RefreshCw, { className: "h-4 w-4" })}
          <span className="text-xs font-bold uppercase tracking-wider">
            {STATUS_STYLES[run?.status]?.text || "Pending"}
          </span>
        </Badge>
      </div>

      <div className="flex items-center gap-2">
        {run?.status === "RUNNING" && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleCancel}
            disabled={cancelling}
            className="border-red-500/30 bg-red-500/5 text-red-300 hover:bg-red-500 hover:text-white h-9"
          >
            <Power className="h-4 w-4 mr-2" />
            {cancelling ? "..." : "Cancel"}
          </Button>
        )}

        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            navigate("/dashboard/backtest/montecarlo", {
              state: { backtestId: id },
            })
          }
          className="border-amber-500/30 bg-amber-500/5 text-amber-300 hover:bg-amber-500 hover:text-white h-9"
        >
          <Dices className="h-4 w-4 mr-2" />
          Analysis
        </Button>
      </div>

      <div className="h-4 w-px bg-gray-800 mx-2" />

      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchData(false)}
          className="border-gray-700 hover:bg-gray-800 text-gray-300 h-9 w-9 p-0"
        >
          <RefreshCw
            className={`h-4 w-4 ${isRefreshing || run?.status === "RUNNING" ? "animate-spin" : ""}`}
          />
        </Button>
        <Link to={`/dashboard/backtest/trades/${id}`}>
          <Button
            variant="outline"
            size="sm"
            className="border-gray-700 hover:bg-gray-800 text-gray-300 h-9"
          >
            <ListIcon className="h-4 w-4 mr-1" />
            Trades
          </Button>
        </Link>
        <Link to={`/dashboard/backtest/charts/${id}`}>
          <Button
            variant="outline"
            size="sm"
            className="border-gray-700 hover:bg-gray-800 text-gray-300 h-9"
          >
            <LineChart className="h-4 w-4 mr-1" />
            Charts
          </Button>
        </Link>
        <div className="ml-2 flex bg-gray-800 rounded-lg p-1">
          <button
            onClick={() => setPnlMode("net")}
            className={`px-3 py-1 rounded text-xs font-medium transition-all ${pnlMode === "net" ? "bg-indigo-600 text-white" : "text-gray-400 hover:text-white"}`}
          >
            Net
          </button>
          <button
            onClick={() => setPnlMode("gross")}
            className={`px-3 py-1 rounded text-xs font-medium transition-all ${pnlMode === "gross" ? "bg-indigo-600 text-white" : "text-gray-400 hover:text-white"}`}
          >
            Gross
          </button>
        </div>
      </div>
    </div>
  ), [id, run?.status, cancelling, isRefreshing, pnlMode, navigate, fetchData]);

  useSetPageActions(consolidatedActions);

  const instrumentBreakdown = Object.entries(
    analytics?.trade_distribution?.instrument_breakdown || {},
  );
  const monthlyReturns = Object.entries(analytics?.monthly_returns || {});
  const drawdownPeriods = analytics?.drawdown_periods || [];

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <GlobalLoader />
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-6 lg:py-8 space-y-6">
      {run?.status === "FAILED" && (
        <div className="bg-red-900/20 border border-red-800/50 rounded-xl p-4 flex gap-3">
          <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />
          <div className="text-red-300 text-sm">{run.error_message}</div>
        </div>
      )}

      {run?.config?.instrument_type && ["FUTURES", "OPTIONS"].includes(run.config.instrument_type) && (
        <div className="bg-amber-900/20 border border-amber-800/50 rounded-xl p-4 flex gap-3 mb-6">
          <AlertCircle className="h-5 w-5 text-amber-400 shrink-0" />
          <div className="text-amber-300 text-sm">
            <strong>F&O Instrument Detected:</strong> This backtest uses underlying spot prices (continuous data) to simulate fills. Real-world derivatives may trade at a premium or discount (contango/backwardation) to the spot price. Please interpret these PnL results with caution.
          </div>
        </div>
      )}

      {run?.status === "RUNNING" && (
        <Card className="bg-indigo-900/10 border-indigo-800/30 overflow-hidden">
          <CardContent className="py-5 px-6">
            <div className="flex items-center gap-5">
              <div className="relative flex items-center justify-center h-12 w-12 rounded-full bg-indigo-900/40 border border-indigo-500/30">
                <RefreshCw className="h-5 w-5 text-indigo-400 animate-spin" />
                <div className="absolute inset-0 rounded-full animate-ping bg-indigo-500/20" />
              </div>
              <div className="flex-1">
                <div className="flex justify-between items-end mb-2">
                  <div>
                    <p className="text-indigo-200 text-sm font-semibold">
                      Simulation in progress
                    </p>
                    <p className="text-indigo-400/60 text-xs mt-0.5">
                      {(run.progress_pct || 0) < 10
                        ? "Fetching market data…"
                        : (run.progress_pct || 0) < 40
                        ? "Computing entry/exit signals…"
                        : (run.progress_pct || 0) < 80
                        ? "Simulating trades…"
                        : "Calculating metrics…"}
                    </p>
                  </div>
                  <span className="text-indigo-300 text-lg font-bold tabular-nums">
                    {run.progress_pct || 0}%
                  </span>
                </div>
                <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-indigo-600 to-indigo-400 rounded-full transition-all duration-700 shadow-[0_0_12px_rgba(99,102,241,0.5)]"
                    style={{ width: `${run.progress_pct || 0}%` }}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: pnlMode === "net" ? "Net Profit" : "Gross Profit",
            value: formatCurrency(
              Number(metrics?.final_capital || 0) - Number(run?.initial_capital || 0) + (pnlMode === "gross" ? Number(metrics?.total_charges || 0) : 0)
            ),
            positive:
              Number(metrics?.final_capital || 0) - Number(run?.initial_capital || 0) + (pnlMode === "gross" ? Number(metrics?.total_charges || 0) : 0) >= 0,
            icon: TrendingUp,
          },
          {
            label: "Total Return",
            value: formatPercent(metrics?.total_return_pct),
            positive: (metrics?.total_return_pct || 0) >= 0,
            icon: Activity,
          },
          {
            label: "Sharpe Ratio",
            value: formatRatio(metrics?.sharpe_ratio),
            icon: BarChart2,
          },
          {
            label: "Max Drawdown",
            value: formatPercent(metrics?.max_drawdown_pct),
            negative: true,
            icon: TrendingDown,
          },
        ].map((kpi, idx) => (
          <Card
            key={idx}
            className="bg-gray-900/50 border-gray-800 hover:border-gray-700 transition-colors"
          >
            <CardContent className="p-5">
              <div className="flex justify-between items-start mb-2">
                <p className="text-sm text-gray-400 font-medium">{kpi.label}</p>
                <div
                  className={`p-1.5 rounded-lg ${kpi.positive ? "bg-green-500/10 text-green-400" : kpi.negative ? "bg-red-500/10 text-red-400" : "bg-indigo-500/10 text-indigo-400"}`}
                >
                  <kpi.icon className="h-4 w-4" />
                </div>
              </div>
              <div
                className={`text-2xl font-bold tracking-tight ${kpi.positive ? "text-green-400" : kpi.negative ? "text-red-400" : "text-white"}`}
              >
                {kpi.value}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Full-width Equity Curve */}
      <Card className="bg-gray-900/50 border-gray-800 backdrop-blur-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg text-white font-semibold flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-indigo-400" />
              Equity Curve
            </CardTitle>
            <CardDescription className="text-xs text-gray-500">
              Portfolio value over simulation time
            </CardDescription>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <div className="flex flex-col items-end">
              <span className="text-gray-500 uppercase tracking-tighter font-bold">Initial Capital</span>
              <span className="text-white font-mono font-bold">{formatCurrency(run?.initial_capital)}</span>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartEquityData}>
                <defs>
                  <linearGradient
                    id="colorEquity"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#374151"
                  vertical={false}
                />
                <XAxis
                  dataKey="timestamp"
                  stroke="#9ca3af"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke="#9ca3af"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(val) => `INR ${Math.round(val / 1000)}k`}
                  domain={["auto", "auto"]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#111827",
                    border: "1px solid #374151",
                  }}
                  itemStyle={{ color: "#818cf8" }}
                  formatter={(val) => formatCurrency(val)}
                />
                <Area
                  type="monotone"
                  dataKey="equity"
                  stroke="#6366f1"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorEquity)"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Masonry stats grid */}
      <div className="grid lg:grid-cols-3 gap-6 items-start">

        {/* Column 1 */}
        <div className="space-y-6">
          <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader className="pb-3 border-b border-gray-800/50">
            <CardTitle className="text-md text-white font-semibold flex items-center gap-2">
              <ListIcon className="h-4 w-4 text-indigo-400" />
              Performance Summary
            </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-gray-800/50">
                {[
                  { label: "Total Trades", value: metrics?.total_trades || 0 },
                  {
                    label: "Win Rate",
                    value: formatPercent(metrics?.win_rate),
                    color: "text-indigo-400",
                  },
                  {
                    label: "Winning Trades",
                    value: metrics?.winning_trades || 0,
                    color: "text-green-400",
                  },
                  {
                    label: "Losing Trades",
                    value: metrics?.losing_trades || 0,
                    color: "text-red-400",
                  },
                  {
                    label: "Profit Factor",
                    value: formatRatio(metrics?.profit_factor),
                    color: "text-white",
                  },
                  {
                    label: "Avg Trade P&L",
                    value: formatCurrency(metrics?.avg_trade_pnl),
                    color:
                      (metrics?.avg_trade_pnl || 0) >= 0
                        ? "text-green-400"
                        : "text-red-400",
                  },
                  {
                    label: "Avg Holding Time",
                    value: `${Math.round(metrics?.avg_holding_time_minutes || 0)} min`,
                    color: "text-gray-400",
                  },
                  {
                    label: "Avg Win Hold",
                    value: `${Math.round(metrics?.avg_winning_hold_time || 0)} min`,
                    color: "text-green-400",
                  },
                  {
                    label: "Avg Loss Hold",
                    value: `${Math.round(metrics?.avg_losing_hold_time || 0)} min`,
                    color: "text-red-400",
                  },
                  {
                    label: "Expectancy (Pts)",
                    value: formatRatio(metrics?.expectancy),
                    color: "text-indigo-400",
                  },
                  {
                    label: "Payoff Ratio",
                    value: formatRatio(metrics?.payoff_ratio),
                    color: "text-white",
                  },
                ].map((stat, i) => (
                  <div
                    key={i}
                    className="flex justify-between items-center p-4"
                  >
                    <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">
                      {stat.label}
                    </span>
                    <span className={`font-bold ${stat.color || "text-white"}`}>
                      {stat.value}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gray-900/50 border-gray-800">
              <CardHeader className="pb-3 border-b border-gray-800/50">
                <CardTitle className="text-md text-white font-semibold">
                  Run Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y divide-gray-800/50">
                  <div className="flex justify-between items-center p-4">
                    <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">Initial Capital</span>
                    <span className="font-bold text-white">{formatCurrency(run?.initial_capital)}</span>
                  </div>
                  <div className="flex justify-between items-center p-4">
                    <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">Slippage</span>
                    <span className="font-bold text-white">{formatPercent(run?.slippage_pct)}</span>
                  </div>
                  <div className="flex justify-between items-center p-4">
                    <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">Fill Model</span>
                    <span className="font-bold text-white">{run?.fill_model || "NEXT_OPEN"}</span>
                  </div>
                  <div className="flex justify-between items-center p-4">
                    <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">Charge Profile</span>
                    <span className="font-bold text-white">{run?.charge_profile_detail?.name || "No Charges"}</span>
                  </div>
                  <div className="flex justify-between items-center p-4">
                    <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">Include Charges</span>
                    <span className="font-bold text-white">{run?.include_charges ? "Yes" : "No"}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
        </div>
        {/* Column 2 */}
        <div className="space-y-6">
          <Card className="bg-gray-900/50 border-gray-800">
            <CardHeader className="pb-3 border-b border-gray-800/50">
              <CardTitle className="text-md text-white font-semibold">
                Risk and Returns
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-gray-800/50">
                {[
                  {
                    label: "Final Capital",
                    value: formatCurrency(metrics?.final_capital),
                    color: "text-white",
                  },
                  {
                    label: "CAGR",
                    value: formatPercent(metrics?.cagr),
                    color: "text-green-400",
                  },
                  {
                    label: "Sharpe Ratio",
                    value: formatRatio(metrics?.sharpe_ratio),
                    color: "text-white",
                  },
                  {
                    label: "Volatility",
                    value: formatPercent(metrics?.volatility_pct),
                    color: "text-white",
                  },
                  {
                    label: "Sortino Ratio",
                    value: formatRatio(metrics?.sortino_ratio),
                    color: "text-white",
                  },
                  {
                    label: "Calmar Ratio",
                    value: formatRatio(metrics?.calmar_ratio),
                    color: "text-white",
                  },
                  {
                    label: "Recovery Factor",
                    value: formatRatio(metrics?.recovery_factor),
                    color: "text-indigo-400",
                  },
                  {
                    label: "Max DD Amount",
                    value: formatCurrency(metrics?.max_drawdown_amount),
                    color: "text-red-400",
                  },
                  {
                    label: "DD Duration",
                    value: `${metrics?.max_drawdown_duration_days || 0} days`,
                    color: "text-gray-400",
                  },
                  {
                    label: "Charges Paid",
                    value: formatCurrency(metrics?.total_charges),
                    color: "text-white",
                  },
                  {
                    label: "Slippage Paid",
                    value: formatCurrency(metrics?.total_slippage),
                    color: "text-white",
                  },
                ].map((stat, i) => (
                  <div key={i} className="flex justify-between items-center p-4">
                    <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">
                      {stat.label}
                    </span>
                    <span className={`font-bold ${stat.color || "text-white"}`}>
                      {stat.value}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gray-900/50 border-gray-800">
              <CardHeader className="pb-3 border-b border-gray-800/50">
              <CardTitle className="text-md text-white font-semibold flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-amber-400" /> Charges Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-gray-800/50">
                <div className="flex justify-between items-center p-4">
                  <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">Total Brokerage</span>
                  <span className="font-bold text-white">{formatCurrency(metrics?.charges_breakdown?.brokerage || 0)}</span>
                </div>
                <div className="flex justify-between items-center p-4">
                  <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">STT / CTT</span>
                  <span className="font-bold text-white">{formatCurrency(metrics?.charges_breakdown?.stt || 0)}</span>
                </div>
                <div className="flex justify-between items-center p-4">
                  <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">Exchange Txn</span>
                  <span className="font-bold text-white">{formatCurrency(metrics?.charges_breakdown?.exchange_txn || 0)}</span>
                </div>
                <div className="flex justify-between items-center p-4">
                  <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">SEBI / Stamp Duty</span>
                  <span className="font-bold text-white">{formatCurrency((metrics?.charges_breakdown?.sebi || 0) + (metrics?.charges_breakdown?.stamp_duty || 0))}</span>
                </div>
                <div className="flex justify-between items-center p-4">
                  <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">GST</span>
                  <span className="font-bold text-white">{formatCurrency(metrics?.charges_breakdown?.gst || 0)}</span>
                </div>
                <div className="flex justify-between items-center p-4 bg-gray-800/30">
                  <span className="text-xs text-white uppercase tracking-wider font-bold">Total Charges</span>
                  <span className="font-bold text-red-400">{formatCurrency(metrics?.total_charges || 0)}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
        {/* Column 3 */}
        <div className="space-y-6">
          <Card className="bg-gray-900/50 border-gray-800">
            <CardHeader className="pb-3 border-b border-gray-800/50">
              <CardTitle className="text-md text-white font-semibold">
                Trade Distribution
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-gray-800/50">
                {[
                  {
                    label: "Avg Win",
                    value: formatCurrency(metrics?.avg_win),
                    color: "text-green-400",
                  },
                  {
                    label: "Avg Loss",
                    value: formatCurrency(metrics?.avg_loss),
                    color: "text-red-400",
                  },
                  {
                    label: "Largest Win",
                    value: formatCurrency(metrics?.largest_win),
                    color: "text-green-400",
                  },
                  {
                    label: "Largest Loss",
                    value: formatCurrency(metrics?.largest_loss),
                    color: "text-red-400",
                  },
                  {
                    label: "Breakeven Trades",
                    value: metrics?.breakeven_trades || 0,
                    color: "text-gray-400",
                  },
                ].map((stat, i) => (
                  <div key={i} className="flex justify-between items-center p-4">
                    <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">
                      {stat.label}
                    </span>
                    <span className={`font-bold ${stat.color || "text-white"}`}>
                      {stat.value}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gray-900/50 border-gray-800 border-l-4 border-l-indigo-500">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <Info className="h-5 w-5 text-indigo-400 mt-0.5" />
                <div>
                  <h4 className="text-sm font-bold text-white uppercase italic tracking-tighter">
                    Consistency Note
                  </h4>
                  <p className="text-xs text-gray-400 mt-1">
                    Max consecutive wins:{" "}
                    <span className="text-green-400 font-bold">
                      {metrics?.max_consecutive_wins || 0}
                    </span>
                    . Max consecutive losses:{" "}
                    <span className="text-red-400 font-bold">
                      {metrics?.max_consecutive_losses || 0}
                    </span>
                    .
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
  </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="bg-gray-900/50 border-gray-800 lg:col-span-2">
          <CardHeader className="pb-3 border-b border-gray-800/50">
            <CardTitle className="text-md text-white font-semibold">
              Instrument Breakdown
            </CardTitle>
            <CardDescription className="text-xs text-gray-500">
              Phase 5 multi-instrument results summary
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-800/50">
              {instrumentBreakdown.length === 0 && (
                <div className="p-4 text-sm text-gray-500">
                  Instrument-level analytics will appear once trades are available.
                </div>
              )}
              {instrumentBreakdown.map(([symbol, info]) => (
                <div key={symbol} className="grid grid-cols-4 gap-4 p-4 text-sm">
                  <div>
                    <div className="text-white font-semibold">{symbol}</div>
                    <div className="text-xs text-gray-500">Instrument</div>
                  </div>
                  <div>
                    <div className="text-white font-semibold">{info.trades}</div>
                    <div className="text-xs text-gray-500">Trades</div>
                  </div>
                  <div>
                    <div className={info.pnl >= 0 ? "text-green-400 font-semibold" : "text-red-400 font-semibold"}>
                      {formatCurrency(info.pnl)}
                    </div>
                    <div className="text-xs text-gray-500">Net P&amp;L</div>
                  </div>
                  <div>
                    <div className="text-indigo-300 font-semibold">{formatPercent(info.win_rate)}</div>
                    <div className="text-xs text-gray-500">Win Rate</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader className="pb-3 border-b border-gray-800/50">
            <CardTitle className="text-md text-white font-semibold">
              Advanced Analytics
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-800/50 rounded-lg p-3">
                <div className="text-xs text-gray-500 uppercase">Avg MAE</div>
                <div className="text-red-400 font-semibold">{formatCurrency(metrics?.avg_mae)}</div>
              </div>
              <div className="bg-gray-800/50 rounded-lg p-3">
                <div className="text-xs text-gray-500 uppercase">Avg MFE</div>
                <div className="text-green-400 font-semibold">{formatCurrency(metrics?.avg_mfe)}</div>
              </div>
              <div className="bg-gray-800/50 rounded-lg p-3">
                <div className="text-xs text-gray-500 uppercase">Efficiency</div>
                <div className="text-indigo-300 font-semibold">{formatRatio(metrics?.trade_efficiency)}</div>
              </div>
              <div className="bg-gray-800/50 rounded-lg p-3">
                <div className="text-xs text-gray-500 uppercase">Drawdowns</div>
                <div className="text-white font-semibold">{drawdownPeriods.length}</div>
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase mb-2">Monthly Returns</div>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {monthlyReturns.length === 0 && (
                  <div className="text-sm text-gray-500">No monthly return data available.</div>
                )}
                {monthlyReturns.map(([month, value]) => (
                  <div key={month} className="flex items-center justify-between text-sm bg-gray-800/40 rounded-lg px-3 py-2">
                    <span className="text-gray-300">{month}</span>
                    <span className={value >= 0 ? "text-green-400 font-semibold" : "text-red-400 font-semibold"}>
                      {formatPercent(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
