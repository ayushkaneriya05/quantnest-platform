import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import {
  TrendingUp,
  BarChart3,
  Target,
  Zap,
  ArrowRight,
  DollarSign,
  Activity,
  BrainCircuit,
} from "lucide-react";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { analyticsSuiteApi } from "@/shared/services/analyticsSuiteApi";
import { portfolioApi } from "@/shared/services/portfolioApi";
import { liveTradingApi } from "@/shared/services/liveTradingApi";
import { GlobalLoader } from "@/shared/components/ui/global-loader";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function Dashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [paperPortfolio, setPaperPortfolio] = useState(null);
  const [liveSummary, setLiveSummary] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Execute all API requests concurrently
        const [dashRes, paperRes, liveRes] = await Promise.allSettled([
          analyticsSuiteApi.getAnalyticsDashboard(),
          portfolioApi.getMyPortfolio(),
          liveTradingApi.getSummary(),
        ]);

        if (dashRes.status === "fulfilled")
          setDashboardData(dashRes.value.data);
        if (paperRes.status === "fulfilled")
          setPaperPortfolio(paperRes.value.data);
        if (liveRes.status === "fulfilled") setLiveSummary(liveRes.value.data);
      } catch (err) {
        console.error("Failed to load dashboard data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return <GlobalLoader text="Loading your intelligence dashboard..." />;
  }

  const report = dashboardData?.latest_report || {};
  const snapshots = dashboardData?.snapshots || [];
  const insights = dashboardData?.insights || [];

  // Calculate Paper & Live Values
  const paperValue = parseFloat(paperPortfolio?.total_value || 0);
  const liveValue =
    parseFloat(liveSummary?.total_allocated || 0) +
    parseFloat(liveSummary?.unrealized_pnl || 0);

  // Formatter for currency
  const formatCurrency = (val) =>
    new Intl.NumberFormat("hi-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 2,
    }).format(val || 0);

  // Process chart data from snapshots (grouping by date)
  const chartDataMap = {};
  snapshots.forEach((snap) => {
    const date = snap.date;
    if (!chartDataMap[date]) chartDataMap[date] = { date, pnl: 0 };
    chartDataMap[date].pnl += parseFloat(snap.daily_pnl || 0);
  });
  const chartData = Object.values(chartDataMap).sort(
    (a, b) => new Date(a.date) - new Date(b.date),
  );

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6 lg:space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Quick Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {/* Paper Portfolio */}
        <Card className="bg-gray-900/40 backdrop-blur-md border-gray-800/60 shadow-lg hover:shadow-indigo-500/10 transition-all duration-300 hover:-translate-y-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">
              Paper Portfolio
            </CardTitle>
            <DollarSign className="h-4 w-4 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-slate-100">
              {formatCurrency(paperValue)}
            </div>
            <p
              className={`text-xs mt-1 ${parseFloat(paperPortfolio?.unrealized_pnl || 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}
            >
              {parseFloat(paperPortfolio?.unrealized_pnl || 0) >= 0 ? "+" : ""}
              {formatCurrency(paperPortfolio?.unrealized_pnl || 0)} Open PnL
            </p>
          </CardContent>
        </Card>

        {/* Live Portfolio */}
        <Card className="bg-gray-900/40 backdrop-blur-md border-gray-800/60 shadow-lg hover:shadow-purple-500/10 transition-all duration-300 hover:-translate-y-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">
              Live Capital
            </CardTitle>
            <Activity className="h-4 w-4 text-purple-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-slate-100">
              {formatCurrency(liveValue)}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Active in {liveSummary?.active_sessions_count || 0} strategies
            </p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/40 backdrop-blur-md border-gray-800/60 shadow-lg hover:shadow-indigo-500/10 transition-all duration-300 hover:-translate-y-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">
              Win Rate
            </CardTitle>
            <Target className="h-4 w-4 text-indigo-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-slate-100">
              {report.total_trades
                ? ((report.winning_trades / report.total_trades) * 100).toFixed(
                    1,
                  )
                : "0.0"}
              %
            </div>
            <p className="text-xs text-slate-400 mt-1">
              {report.winning_trades || 0}W / {report.losing_trades || 0}L
            </p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/40 backdrop-blur-md border-gray-800/60 shadow-lg hover:shadow-cyan-500/10 transition-all duration-300 hover:-translate-y-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">
              Daily Realized P&L
            </CardTitle>
            <Zap
              className={`h-4 w-4 ${parseFloat(report.realized_pnl) >= 0 ? "text-emerald-400" : "text-red-400"}`}
            />
          </CardHeader>
          <CardContent>
            <div
              className={`text-2xl font-bold ${parseFloat(report.realized_pnl) >= 0 ? "text-emerald-400" : "text-red-400"}`}
            >
              {parseFloat(report.realized_pnl) > 0 ? "+" : ""}
              {formatCurrency(report.realized_pnl || 0)}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Across {report.total_trades || 0} trades today
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Performance Chart Section */}
      <Card className="bg-gray-900/40 backdrop-blur-md border-gray-800/60 shadow-lg">
        <CardHeader>
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-indigo-400" />
            Performance History
          </CardTitle>
          <CardDescription className="text-slate-400">
            Aggregate Daily PnL across your strategies
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] w-full mt-4">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={chartData}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#334155"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="date"
                    stroke="#94a3b8"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    stroke="#94a3b8"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value) => `₹${value}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#1e293b",
                      borderRadius: "8px",
                    }}
                    itemStyle={{ color: "#e2e8f0" }}
                    formatter={(value) => [
                      `₹${parseFloat(value).toFixed(2)}`,
                      "Daily PnL",
                    ]}
                  />
                  <Area
                    type="monotone"
                    dataKey="pnl"
                    stroke="#8b5cf6"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#colorPnl)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-slate-500 border border-dashed border-gray-800 rounded-lg">
                Not enough historical data to display chart.
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Recent AI Insights */}
        <Card className="bg-gray-900/40 backdrop-blur-md border-gray-800/60 shadow-lg hover:shadow-card-hover transition-all duration-300">
          <CardHeader>
            <CardTitle className="text-slate-100 flex items-center gap-2">
              <BrainCircuit className="h-5 w-5 text-orange-400" />
              AI Trading Insights
            </CardTitle>
            <CardDescription className="text-slate-400">
              Latest pattern recognitions and journal insights
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {insights.length > 0 ? (
                insights.map((insight) => (
                  <div
                    key={insight.id}
                    className="flex flex-col p-4 rounded-lg bg-gray-800/40 border border-gray-700/30 hover:bg-gray-800/60 transition-all"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-slate-200 font-medium">
                        {insight.title}
                      </span>
                      <span className="text-xs bg-orange-500/20 text-orange-300 px-2 py-1 rounded-full capitalize">
                        {insight.insight_type}
                      </span>
                    </div>
                    <p className="text-sm text-slate-400 line-clamp-2">
                      {insight.description}
                    </p>
                  </div>
                ))
              ) : (
                <div className="p-4 text-center text-slate-500">
                  No recent insights generated. Check your Trade Journal.
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Active Strategies Performance */}
        <Card className="bg-gray-900/40 backdrop-blur-md border-gray-800/60 shadow-lg hover:shadow-card-hover transition-all duration-300">
          <CardHeader>
            <CardTitle className="text-slate-100 flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-emerald-400" />
              Active Strategies
            </CardTitle>
            <CardDescription className="text-slate-400">
              Performance overview of your deployed algorithms
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {snapshots.length > 0 ? (
                [
                  ...new Map(
                    snapshots.map((item) => [item.strategy?.id, item]),
                  ).values(),
                ]
                  .slice(0, 4)
                  .map((snap) => (
                    <div
                      key={snap.id}
                      className="flex justify-between items-center p-3 rounded-lg bg-gray-800/40 border border-gray-700/30 hover:bg-gray-800/60 transition-all"
                    >
                      <div>
                        <p className="text-slate-200 font-medium">
                          {snap.strategy?.name || "Unnamed Strategy"}
                        </p>
                        <p className="text-xs text-slate-400">
                          Win Rate: {parseFloat(snap.win_rate || 0).toFixed(1)}%
                        </p>
                      </div>
                      <div className="text-right">
                        <p
                          className={`text-sm font-bold ${parseFloat(snap.daily_pnl) >= 0 ? "text-emerald-400" : "text-red-400"}`}
                        >
                          {parseFloat(snap.daily_pnl) > 0 ? "+" : ""}
                          {formatCurrency(snap.daily_pnl)}
                        </p>
                        <p className="text-xs text-slate-400">
                          {snap.trades_count} trades today
                        </p>
                      </div>
                    </div>
                  ))
              ) : (
                <div className="p-4 text-center text-slate-500">
                  No active strategies running today.
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mt-4">
        <Card className="bg-gradient-to-br from-indigo-500/10 to-purple-600/10 border-indigo-500/30 hover:border-indigo-400/50 transition-all duration-300 hover:-translate-y-1">
          <CardHeader>
            <CardTitle className="text-slate-100">Strategy Builder</CardTitle>
            <CardDescription className="text-slate-300">
              Create, configure, and backtest technical trading strategies using
              our intuitive rule builder.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => navigate("/dashboard/strategy/create")}
              className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 border-0"
            >
              Build Strategy
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-emerald-500/10 to-teal-600/10 border-emerald-500/30 hover:border-emerald-400/50 transition-all duration-300 hover:-translate-y-1">
          <CardHeader>
            <CardTitle className="text-slate-100">Paper Trading</CardTitle>
            <CardDescription className="text-slate-300">
              Execute your strategies in a simulated environment using real-time
              market data.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => navigate("/dashboard/paper")}
              className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 border-0"
            >
              Start Trading
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-orange-500/10 to-red-600/10 border-orange-500/30 hover:border-orange-400/50 transition-all duration-300 hover:-translate-y-1">
          <CardHeader>
            <CardTitle className="text-slate-100">Strategy Advisor</CardTitle>
            <CardDescription className="text-slate-300">
              Automated recommendations based on strategy health scoring, market
              regime detection, and overfit analysis.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => navigate("/dashboard/ai/advisor")}
              className="w-full bg-gradient-to-r from-orange-500 to-red-600 hover:from-orange-600 hover:to-red-700 border-0"
            >
              View Advisor
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
