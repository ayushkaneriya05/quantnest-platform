import { useState, useEffect, useMemo } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Calendar,
  Loader2,
  AlertTriangle,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import { portfolioApi } from "@/shared/services/portfolioApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { usePageTitle } from "@/shared/hooks/use-page-title";

export default function PaperAnalytics() {
  const { notify } = useNotifications();
  const [portfolio, setPortfolio] = useState(null);
  const [performance, setPerformance] = useState([]);
  const [loading, setLoading] = useState(true);

  usePageTitle({
    title: "Paper Performance Analytics",
    subtitle: "Deep dive into your virtual trading results and drawdown metrics",
  });

  const fetchData = async () => {
    try {
      setLoading(true);
      const [portRes, perfRes] = await Promise.all([
        portfolioApi.getMyPortfolio(),
        portfolioApi.getPortfolioPerformance(),
      ]);
      setPortfolio(portRes.data);
      setPerformance(
        Array.isArray(perfRes.data)
          ? perfRes.data
          : perfRes.data?.results || [],
      );
    } catch (err) {
      notify.error("Failed to load analytics data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const formatCurrency = (val) => {
    if (val == null) return "₹0";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(val);
  };

  const perfStats = useMemo(() => {
    if (!performance.length)
      return {
        weekPnl: 0,
        monthPnl: 0,
        bestDay: null,
        worstDay: null,
        avgWinRate: 0,
        totalFees: 0,
        totalTradesToday: 0,
        avgPnlPct: 0,
      };

    const sorted = [...performance].sort(
      (a, b) => new Date(b.date) - new Date(a.date),
    );
    const last7 = sorted.slice(0, 7);
    const last30 = sorted.slice(0, 30);

    const weekPnl = last7.reduce((s, d) => s + parseFloat(d.total_pnl || 0), 0);
    const monthPnl = last30.reduce((s, d) => s + parseFloat(d.total_pnl || 0), 0);

    let bestDay = sorted[0], worstDay = sorted[0];
    sorted.forEach((d) => {
      if (parseFloat(d.total_pnl) > parseFloat(bestDay.total_pnl)) bestDay = d;
      if (parseFloat(d.total_pnl) < parseFloat(worstDay.total_pnl)) worstDay = d;
    });

    const totalTrades = last30.reduce((s, d) => s + (d.winning_trades || 0) + (d.losing_trades || 0), 0);
    const totalWins = last30.reduce((s, d) => s + (d.winning_trades || 0), 0);
    const avgWinRate = totalTrades > 0 ? (totalWins / totalTrades) * 100 : 0;

    const totalFees = last30.reduce((s, d) => s + parseFloat(d.brokerage_paid || 0) + parseFloat(d.taxes_paid || 0), 0);
    const totalTradesToday = last30.reduce((s, d) => s + (d.trades_count || 0), 0);
    const avgPnlPct = last30.length > 0 ? last30.reduce((s, d) => s + parseFloat(d.pnl_percentage || 0), 0) / last30.length : 0;

    return { weekPnl, monthPnl, bestDay, worstDay, avgWinRate, totalFees, totalTradesToday, avgPnlPct };
  }, [performance]);

  const pnlBars = useMemo(() => {
    if (!performance.length) return [];
    const sorted = [...performance].sort((a, b) => new Date(a.date) - new Date(b.date));
    const last14 = sorted.slice(-14);
    const maxAbs = Math.max(...last14.map((d) => Math.abs(parseFloat(d.total_pnl || 0))), 1);
    return last14.map((d) => ({
      date: d.date,
      pnl: parseFloat(d.total_pnl || 0),
      pct: (Math.abs(parseFloat(d.total_pnl || 0)) / maxAbs) * 100,
    }));
  }, [performance]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  const drawdown = parseFloat(portfolio?.current_drawdown || 0);

  return (
    <div className="container-padding py-6 lg:py-8 space-y-8 animate-in fade-in duration-500">
      <div className="grid md:grid-cols-3 gap-6">
        {/* P&L Breakdown */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader className="pb-3 border-b border-gray-800/50">
            <CardTitle className="text-white text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-indigo-400" />
              P&L Performance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {[
              { label: "Realized P&L", value: parseFloat(portfolio?.realized_pnl || 0) },
              { label: "Unrealized P&L", value: parseFloat(portfolio?.unrealized_pnl || 0) },
              { label: "Week P&L", value: perfStats.weekPnl },
              { label: "Month P&L", value: perfStats.monthPnl },
            ].map((item, i) => (
              <div key={i} className="flex justify-between items-center">
                <span className="text-sm text-gray-400">{item.label}</span>
                <span className={`text-sm font-bold ${item.value >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                  {item.value >= 0 ? "+" : ""}{formatCurrency(item.value)}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Drawdown Gauge */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader className="pb-3 border-b border-gray-800/50">
            <CardTitle className="text-white text-sm flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-rose-400" />
              Drawdown Analysis
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center py-6">
            <div className="relative w-32 h-32">
              <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="50" stroke="#1f2937" strokeWidth="8" fill="none" />
                <circle
                  cx="60" cy="60" r="50"
                  stroke={drawdown > 10 ? "#ef4444" : drawdown > 5 ? "#f59e0b" : "#10b981"}
                  strokeWidth="8" fill="none"
                  strokeDasharray={`${Math.min(drawdown, 100) * 3.14} 314.16`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className={`text-2xl font-bold ${drawdown > 10 ? "text-red-400" : drawdown > 5 ? "text-amber-400" : "text-emerald-400"}`}>
                  {drawdown.toFixed(1)}%
                </span>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-4">Current Peak to Trough Drawdown</p>
          </CardContent>
        </Card>

        {/* 30-Day Stats */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader className="pb-3 border-b border-gray-800/50">
            <CardTitle className="text-white text-sm flex items-center gap-2">
              <Calendar className="h-4 w-4 text-purple-400" />
              Rolling 30-Day Metrics
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {[
              { label: "Win Rate", value: `${perfStats.avgWinRate.toFixed(1)}%`, color: perfStats.avgWinRate >= 50 ? "text-emerald-400" : "text-amber-400" },
              { label: "Avg Daily P&L %", value: `${perfStats.avgPnlPct >= 0 ? "+" : ""}${perfStats.avgPnlPct.toFixed(2)}%`, color: perfStats.avgPnlPct >= 0 ? "text-emerald-400" : "text-rose-400" },
              { label: "Best Day", value: perfStats.bestDay ? formatCurrency(perfStats.bestDay.total_pnl) : "—", color: "text-emerald-400" },
              { label: "Worst Day", value: perfStats.worstDay ? formatCurrency(perfStats.worstDay.total_pnl) : "—", color: "text-rose-400" },
            ].map((item, i) => (
              <div key={i} className="flex justify-between items-center">
                <span className="text-sm text-gray-400">{item.label}</span>
                <span className={`text-sm font-bold ${item.color}`}>{item.value}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Daily P&L Chart */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white text-base flex items-center gap-2">
            <Activity className="h-4 w-4 text-indigo-400" />
            Equity Curve History (Last 14 Days)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-1.5 h-48 pt-4">
            {pnlBars.map((bar, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-2 group relative">
                <div
                  className={`w-full rounded-t-sm transition-all duration-300 ${bar.pnl >= 0 ? "bg-emerald-500/60 group-hover:bg-emerald-500" : "bg-rose-500/60 group-hover:bg-rose-500"}`}
                  style={{ height: `${Math.max(bar.pct, 5)}%` }}
                />
                <div className="absolute bottom-full mb-2 hidden group-hover:block bg-gray-800 text-[10px] text-white px-2 py-1 rounded shadow-2xl z-20 whitespace-nowrap border border-gray-700">
                  <p className="font-bold">{bar.date}</p>
                  <p className={bar.pnl >= 0 ? "text-emerald-400" : "text-rose-400"}>
                    {bar.pnl >= 0 ? "+" : ""}{formatCurrency(bar.pnl)}
                  </p>
                </div>
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-4 border-t border-gray-800 pt-2">
            <span className="text-[10px] text-gray-500 uppercase tracking-tighter">{pnlBars[0]?.date}</span>
            <span className="text-[10px] text-gray-500 uppercase tracking-tighter">{pnlBars[pnlBars.length - 1]?.date}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
