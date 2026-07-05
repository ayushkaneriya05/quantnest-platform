import React, { useMemo } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { TrendingUp, BarChart3 } from "lucide-react";
import { formatNumber } from "@/shared/utils/formatters";

const StatCard = ({
  icon: Icon,
  title,
  value,
  subtitle,
  variant = "default",
}) => {
  const variantClasses = {
    default: "bg-sky-500/10 text-sky-400",
    positive: "bg-emerald-500/10 text-emerald-400",
    negative: "bg-rose-500/10 text-rose-400",
  };

  return (
    <Card className="bg-slate-900/50 border-slate-800 hover:border-slate-700 transition-colors">
      <CardContent className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className={`p-3 rounded-2xl ${variantClasses[variant]}`}>
            <Icon className="h-6 w-6" />
          </div>
        </div>
        <div>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">
            {title}
          </p>
          <p className="text-2xl font-black text-white mb-1">{value}</p>
          {subtitle && <p className="text-xs text-slate-600">{subtitle}</p>}
        </div>
      </CardContent>
    </Card>
  );
};

export default function LivePerformance({ summary = {}, sessions = [] }) {
  const performanceMetrics = useMemo(() => {
    const dayPnl = summary?.day_pnl || 0;
    const totalEquity =
      summary?.broker_accounts?.reduce(
        (sum, acc) => sum + (acc.net_equity || 0),
        0,
      ) || 0;
    const returnPct = totalEquity > 0 ? (dayPnl / totalEquity) * 100 : 0;

    // Calculate strategy-wise performance
    const strategyPerf = sessions.reduce((acc, s) => {
      const existing = acc.find((p) => p.id === s.id);
      if (!existing) {
        acc.push({
          id: s.id,
          name: s.strategy_name,
          pnl: s.pnl || 0,
          trades: s.trades_count || 0,
          positions: s.open_positions || 0,
        });
      }
      return acc;
    }, []);

    const profitableSessions = strategyPerf.filter((s) => s.pnl >= 0).length;
    const totalTrades = strategyPerf.reduce((sum, s) => sum + s.trades, 0);
    const totalSessionPnl = strategyPerf.reduce((sum, s) => sum + s.pnl, 0);

    return {
      dayPnl,
      returnPct,
      totalEquity,
      profitableSessions,
      strategyPerf,
      totalTrades,
      totalSessionPnl,
    };
  }, [summary, sessions]);

  return (
    <div className="space-y-6">
      {/* Performance Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={TrendingUp}
          title="Day P&L"
          value={`₹${formatNumber(Math.abs(performanceMetrics.dayPnl))}`}
          subtitle={performanceMetrics.dayPnl >= 0 ? "Profit" : "Loss"}
          variant={performanceMetrics.dayPnl >= 0 ? "positive" : "negative"}
        />
        <StatCard
          icon={BarChart3}
          title="Return %"
          value={`${performanceMetrics.returnPct.toFixed(2)}%`}
          subtitle="On equity"
          variant={performanceMetrics.returnPct >= 0 ? "positive" : "negative"}
        />
        <StatCard
          icon={BarChart3}
          title="Total Equity"
          value={`₹${formatNumber(performanceMetrics.totalEquity)}`}
          subtitle="All accounts"
          variant="default"
        />
        <StatCard
          icon={BarChart3}
          title="Total Trades"
          value={performanceMetrics.totalTrades}
          subtitle="Today"
          variant="default"
        />
      </div>

      {/* Session Performance */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            <span>Strategy Performance</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {performanceMetrics.strategyPerf.length === 0 ? (
            <p className="text-slate-400 text-center py-8">
              No active strategies
            </p>
          ) : (
            <div className="space-y-4">
              {performanceMetrics.strategyPerf.map((strat) => (
                <div
                  key={strat.id}
                  className="p-4 bg-slate-800/30 rounded-lg border border-slate-700 hover:border-slate-600 transition-colors"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex-1">
                      <h4 className="font-medium text-white">{strat.name}</h4>
                      <p className="text-sm text-slate-400">
                        {strat.trades} trades • {strat.positions} positions
                      </p>
                    </div>
                    <div className="text-right">
                      <p
                        className={`text-lg font-bold ${strat.pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}
                      >
                        ₹{formatNumber(strat.pnl)}
                      </p>
                      <p className="text-xs text-slate-400">
                        {(
                          (strat.pnl / performanceMetrics.totalSessionPnl) *
                          100
                        ).toFixed(1)}
                        % of total
                      </p>
                    </div>
                  </div>

                  {/* Performance bar */}
                  <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${strat.pnl >= 0 ? "bg-emerald-500" : "bg-rose-500"}`}
                      style={{
                        width: `${Math.min(100, Math.abs((strat.pnl / performanceMetrics.totalSessionPnl) * 100) || 10)}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Win Rate */}
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-emerald-400" />
              <span>Strategies in Profit</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-3xl font-bold text-emerald-400">
              {performanceMetrics.profitableSessions}/
              {performanceMetrics.strategyPerf.length}
            </p>
            <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500"
                style={{
                  width: `${performanceMetrics.strategyPerf.length > 0 ? (performanceMetrics.profitableSessions / performanceMetrics.strategyPerf.length) * 100 : 0}%`,
                }}
              />
            </div>
            <p className="text-slate-400 text-sm">
              {performanceMetrics.strategyPerf.length > 0
                ? (
                    (performanceMetrics.profitableSessions /
                      performanceMetrics.strategyPerf.length) *
                    100
                  ).toFixed(1)
                : 0}
              % win rate
            </p>
          </CardContent>
        </Card>

        {/* Avg Trade P&L */}
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-sky-400" />
              <span>Average Trade P&L</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p
              className={`text-3xl font-bold ${performanceMetrics.totalTrades > 0 ? (performanceMetrics.dayPnl / performanceMetrics.totalTrades >= 0 ? "text-emerald-400" : "text-rose-400") : "text-slate-400"}`}
            >
              ₹
              {formatNumber(
                performanceMetrics.totalTrades > 0
                  ? performanceMetrics.dayPnl / performanceMetrics.totalTrades
                  : 0,
              )}
            </p>
            <p className="text-slate-400 text-sm">
              Based on {performanceMetrics.totalTrades} total trades
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Summary Stats */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle>Daily Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
            <div className="p-3 bg-slate-800/30 rounded-lg">
              <p className="text-slate-500 uppercase text-xs font-bold mb-1">
                Active Strategies
              </p>
              <p className="text-white text-lg font-bold">
                {sessions.filter((s) => s.status === "RUNNING").length}
              </p>
            </div>
            <div className="p-3 bg-slate-800/30 rounded-lg">
              <p className="text-slate-500 uppercase text-xs font-bold mb-1">
                Total Sessions
              </p>
              <p className="text-white text-lg font-bold">{sessions.length}</p>
            </div>
            <div className="p-3 bg-slate-800/30 rounded-lg">
              <p className="text-slate-500 uppercase text-xs font-bold mb-1">
                Fills Today
              </p>
              <p className="text-white text-lg font-bold">
                {summary?.today_fills || 0}
              </p>
            </div>
            <div className="p-3 bg-slate-800/30 rounded-lg">
              <p className="text-slate-500 uppercase text-xs font-bold mb-1">
                Open Positions
              </p>
              <p className="text-white text-lg font-bold">
                {summary?.open_positions || 0}
              </p>
            </div>
            <div className="p-3 bg-slate-800/30 rounded-lg">
              <p className="text-slate-500 uppercase text-xs font-bold mb-1">
                Open Orders
              </p>
              <p className="text-white text-lg font-bold">
                {summary?.open_orders || 0}
              </p>
            </div>
            <div className="p-3 bg-slate-800/30 rounded-lg">
              <p className="text-slate-500 uppercase text-xs font-bold mb-1">
                Session P&L
              </p>
              <p
                className={`text-lg font-bold ${performanceMetrics.totalSessionPnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}
              >
                ₹{formatNumber(performanceMetrics.totalSessionPnl)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
