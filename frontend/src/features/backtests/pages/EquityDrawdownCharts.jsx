/**
 * Equity & Drawdown Charts — professional recharts-based visualization.
 */
import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
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
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { formatCurrency, formatDateTime } from "@/shared/utils/formatters";
import PropTypes from "prop-types";

/* ─── Helpers ─── */
const toNumber = (val) => {
  const numeric = Number(val);
  return Number.isFinite(numeric) ? numeric : 0;
};

/* ─── Custom Tooltip ─── */
function ChartTooltip({ active, payload, label, type }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-lg px-3 py-2 shadow-xl">
      <p className="text-[11px] text-muted-foreground mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="text-sm font-semibold" style={{ color: p.color }}>
          {type === "currency" ? formatCurrency(p.value) : `${toNumber(p.value).toFixed(2)}%`}
        </p>
      ))}
    </div>
  );
}

ChartTooltip.propTypes = {
  active: PropTypes.bool,
  payload: PropTypes.arrayOf(PropTypes.shape({ color: PropTypes.string, value: PropTypes.number })),
  label: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  type: PropTypes.string,
};

export default function EquityDrawdownCharts() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();

  const [run, setRun] = useState(null);
  const [equityCurve, setEquityCurve] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
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
        date: formatDateTime(point.timestamp),
        equity: toNumber(point.equity_value),
        drawdown: -Math.abs(toNumber(point.drawdown_pct)), // Negative for visual
      }));
      setEquityCurve(points);
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to load chart data"));
    } finally {
      setLoading(false);
    }
  }, [id, notify]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useSetPageActions(
    <Button
      variant="outline"
      size="sm"
      onClick={() => navigate(`/backtests/results/${id}`)}
      className="bg-card border-border hover:bg-secondary h-9"
    >
      <ChevronLeft className="h-4 w-4 mr-2" />
      Back to Results
    </Button>
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="flex flex-col items-center gap-3">
          <GlobalLoader />
          <p className="text-sm text-muted-foreground">Loading charts…</p>
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
            color: "text-foreground",
          },
          {
            label: "Final Capital",
            value: formatCurrency(metrics?.final_capital),
            color:
              toNumber(metrics?.total_return_pct) >= 0
                ? "text-emerald-700 dark:text-emerald-400"
                : "text-red-700 dark:text-red-400",
          },
          {
            label: "Total Return",
            value: `${toNumber(metrics?.total_return_pct).toFixed(2)}%`,
            color:
              toNumber(metrics?.total_return_pct) >= 0
                ? "text-emerald-700 dark:text-emerald-400"
                : "text-red-700 dark:text-red-400",
          },
          {
            label: "Max Drawdown",
            value: `${toNumber(metrics?.max_drawdown_pct).toFixed(2)}%`,
            color: "text-red-700 dark:text-red-400",
          },
        ].map((stat) => (
          <Card
            key={stat.label}
            className="bg-card/60 border-border"
          >
            <CardContent className="py-4 px-5">
              <p className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium">
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
      <Card className="bg-card/50 border-border">
        <CardHeader>
          <CardTitle className="text-foreground flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-emerald-700 dark:text-emerald-400" />
            Equity Curve
          </CardTitle>
          <CardDescription className="text-muted-foreground text-xs">
            Portfolio value over simulation period
          </CardDescription>
        </CardHeader>
        <CardContent>
          {equityCurve.length === 0 ? (
            <div className="h-72 flex items-center justify-center text-muted-foreground">
              No equity data available
            </div>
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={equityCurve}>
                  <defs>
                    <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--success))" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(var(--success))" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="hsl(var(--chart-grid))"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="date"
                    stroke="hsl(var(--muted-foreground))"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    stroke="hsl(var(--muted-foreground))"
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
                      stroke="hsl(var(--chart-line))"
                      strokeDasharray="4 4"
                      strokeOpacity={0.5}
                      label={{
                        value: "Initial",
                        position: "right",
                        fill: "hsl(var(--chart-line))",
                        fontSize: 10,
                      }}
                    />
                  )}
                  <Area
                    type="monotone"
                    dataKey="equity"
                    stroke="hsl(var(--success))"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#equityGrad)"
                    dot={false}
                    activeDot={{
                      r: 4,
                      fill: "hsl(var(--success))",
                      stroke: "hsl(var(--card))",
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
      <Card className="bg-card/50 border-border">
        <CardHeader>
          <CardTitle className="text-foreground flex items-center gap-2">
            <TrendingDown className="h-5 w-5 text-red-700 dark:text-red-400" />
            Drawdown Chart
          </CardTitle>
          <CardDescription className="text-muted-foreground text-xs">
            Percentage drawdown from equity peak
          </CardDescription>
        </CardHeader>
        <CardContent>
          {equityCurve.length === 0 ? (
            <div className="h-52 flex items-center justify-center text-muted-foreground">
              No drawdown data available
            </div>
          ) : (
            <div className="h-52 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={equityCurve}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="hsl(var(--chart-grid))"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="date"
                    stroke="hsl(var(--muted-foreground))"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    stroke="hsl(var(--muted-foreground))"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(val) => `${val.toFixed(1)}%`}
                    domain={["auto", 0]}
                  />
                  <Tooltip
                    content={<ChartTooltip type="percent" />}
                  />
                  <ReferenceLine y={0} stroke="hsl(var(--border))" />
                  <Bar
                    dataKey="drawdown"
                    fill="hsl(var(--loss))"
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
      <Card className="bg-card/50 border-border">
        <CardHeader>
          <CardTitle className="text-foreground flex items-center gap-2">
            <Activity className="h-5 w-5 text-indigo-700 dark:text-indigo-400" />
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
                className="p-4 bg-secondary/50 rounded-lg text-center border border-border/50 hover:border-border transition-colors"
              >
                <p className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium">
                  {m.label}
                </p>
                <p className="text-lg font-bold text-foreground mt-1">{m.value}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
