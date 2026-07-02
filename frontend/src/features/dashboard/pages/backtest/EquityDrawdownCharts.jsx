/**
 * Equity & Drawdown Charts — professional recharts-based visualization.
 */
import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  ChevronLeft,
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { backtestApi } from "@/shared/services/backtestApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";

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

/* ─── Custom Tooltip ─── */
function ChartTooltip({ active, payload, label, type }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 shadow-xl">
      <p className="text-[11px] text-gray-400 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="text-sm font-semibold" style={{ color: p.color }}>
          {type === "currency" ? formatCurrency(p.value) : `${toNumber(p.value).toFixed(2)}%`}
        </p>
      ))}
    </div>
  );
}

export default function EquityDrawdownCharts() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();

  const [run, setRun] = useState(null);
  const [equityCurve, setEquityCurve] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    try {
      const [runData, curveData, metricsData] = await Promise.all([
        backtestApi.getRun(id),
        backtestApi.getRunEquityCurve(id),
        backtestApi.getRunMetrics(id),
      ]);
      setRun(runData.data);
      setMetrics(metricsData.data);

      // Process curve data for recharts
      const points = (curveData.data || []).map((point) => ({
        date: new Date(point.timestamp).toLocaleDateString("en-IN", {
          day: "numeric",
          month: "short",
        }),
        equity: toNumber(point.equity_value),
        drawdown: -Math.abs(toNumber(point.drawdown_pct)), // Negative for visual
      }));
      setEquityCurve(points);
    } catch {
      notify.error("Failed to load chart data");
    } finally {
      setLoading(false);
    }
  };

  useSetPageActions(
    <Button
      variant="outline"
      size="sm"
      onClick={() => navigate(`/dashboard/backtest/results/${id}`)}
      className="bg-gray-900 border-gray-800 hover:bg-gray-800 h-9"
    >
      <ChevronLeft className="h-4 w-4 mr-2" />
      Back to Results
    </Button>
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-10 w-10 border-2 border-indigo-500 border-t-transparent" />
          <p className="text-sm text-gray-500">Loading charts…</p>
        </div>
      </div>
    );
  }

  const initialCapital = toNumber(run?.initial_capital);

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-6 lg:py-8 space-y-6">
      {/* ── Summary Stats ── */}

      {/* ── Summary Stats ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: "Starting Capital",
            value: formatCurrency(run?.initial_capital),
            color: "text-white",
          },
          {
            label: "Final Capital",
            value: formatCurrency(metrics?.final_capital),
            color:
              toNumber(metrics?.total_return_pct) >= 0
                ? "text-emerald-400"
                : "text-red-400",
          },
          {
            label: "Total Return",
            value: `${toNumber(metrics?.total_return_pct).toFixed(2)}%`,
            color:
              toNumber(metrics?.total_return_pct) >= 0
                ? "text-emerald-400"
                : "text-red-400",
          },
          {
            label: "Max Drawdown",
            value: `${toNumber(metrics?.max_drawdown_pct).toFixed(2)}%`,
            color: "text-red-400",
          },
        ].map((stat) => (
          <Card
            key={stat.label}
            className="bg-gray-900/60 border-gray-800"
          >
            <CardContent className="py-4 px-5">
              <p className="text-[11px] text-gray-500 uppercase tracking-wider font-medium">
                {stat.label}
              </p>
              <p className={`text-xl font-bold mt-1 ${stat.color}`}>
                {stat.value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* ── Equity Curve (AreaChart) ── */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-emerald-400" />
            Equity Curve
          </CardTitle>
          <CardDescription className="text-gray-500 text-xs">
            Portfolio value over simulation period
          </CardDescription>
        </CardHeader>
        <CardContent>
          {equityCurve.length === 0 ? (
            <div className="h-72 flex items-center justify-center text-gray-500">
              No equity data available
            </div>
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={equityCurve}>
                  <defs>
                    <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#1f2937"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="date"
                    stroke="#6b7280"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    stroke="#6b7280"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(val) => `₹${Math.round(val / 1000)}k`}
                    domain={["auto", "auto"]}
                  />
                  <Tooltip
                    content={<ChartTooltip type="currency" />}
                  />
                  {initialCapital > 0 && (
                    <ReferenceLine
                      y={initialCapital}
                      stroke="#6366f1"
                      strokeDasharray="4 4"
                      strokeOpacity={0.5}
                      label={{
                        value: "Initial",
                        position: "right",
                        fill: "#6366f1",
                        fontSize: 10,
                      }}
                    />
                  )}
                  <Area
                    type="monotone"
                    dataKey="equity"
                    stroke="#10b981"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#equityGrad)"
                    dot={false}
                    activeDot={{
                      r: 4,
                      fill: "#10b981",
                      stroke: "#064e3b",
                      strokeWidth: 2,
                    }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Drawdown Chart (BarChart) ── */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <TrendingDown className="h-5 w-5 text-red-400" />
            Drawdown Chart
          </CardTitle>
          <CardDescription className="text-gray-500 text-xs">
            Percentage drawdown from equity peak
          </CardDescription>
        </CardHeader>
        <CardContent>
          {equityCurve.length === 0 ? (
            <div className="h-52 flex items-center justify-center text-gray-500">
              No drawdown data available
            </div>
          ) : (
            <div className="h-52 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={equityCurve}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#1f2937"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="date"
                    stroke="#6b7280"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    stroke="#6b7280"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(val) => `${val.toFixed(1)}%`}
                    domain={["auto", 0]}
                  />
                  <Tooltip
                    content={<ChartTooltip type="percent" />}
                  />
                  <ReferenceLine y={0} stroke="#374151" />
                  <Bar
                    dataKey="drawdown"
                    fill="#ef4444"
                    fillOpacity={0.6}
                    radius={[2, 2, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Risk Metrics Grid ── */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Activity className="h-5 w-5 text-indigo-400" />
            Risk-Adjusted Metrics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              { label: "CAGR", value: `${toNumber(metrics?.cagr).toFixed(2)}%` },
              { label: "Volatility", value: `${toNumber(metrics?.volatility_pct).toFixed(2)}%` },
              { label: "Sharpe", value: toNumber(metrics?.sharpe_ratio).toFixed(2) },
              { label: "Sortino", value: toNumber(metrics?.sortino_ratio).toFixed(2) },
              { label: "Calmar", value: toNumber(metrics?.calmar_ratio).toFixed(2) },
            ].map((m) => (
              <div
                key={m.label}
                className="p-4 bg-gray-800/50 rounded-lg text-center border border-gray-700/50 hover:border-gray-600 transition-colors"
              >
                <p className="text-[11px] text-gray-500 uppercase tracking-wider font-medium">
                  {m.label}
                </p>
                <p className="text-lg font-bold text-white mt-1">{m.value}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
