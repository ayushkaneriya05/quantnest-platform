import { useState, useEffect, useMemo } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import {
  BarChart3,
  Calendar,
  Activity,
} from "lucide-react";
import { portfolioApi } from "@/shared/services/portfolioApi";
import { paperApi } from "@/shared/services/paperApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { usePageTitle } from "@/shared/hooks/use-page-title";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { formatCurrency } from "@/shared/utils/formatters";
import { useLivePositionsPnL } from "@/shared/hooks/useLivePositionsPnL";

export default function PaperAnalytics() {
  const { notify } = useNotifications();
  const [portfolio, setPortfolio] = useState(null);
  const [trades, setTrades] = useState([]);
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const { livePnLByPositionId } = useLivePositionsPnL(positions);

  usePageTitle({
    title: "Paper Performance Analytics",
    subtitle: "Portfolio-wide performance across all paper accounts",
  });

  const fetchData = async () => {
    try {
      setLoading(true);
      const [portRes, tradesRes, positionsRes] = await Promise.all([
        portfolioApi.getMyPortfolio(),
        paperApi.getTrades(),
        paperApi.getPositions(),
      ]);
      setPortfolio(portRes.data);
      setTrades(Array.isArray(tradesRes.data) ? tradesRes.data : tradesRes.data?.results || []);
      setPositions(Array.isArray(positionsRes.data) ? positionsRes.data : positionsRes.data?.results || []);
    } catch (err) {
      notify.error("Failed to load analytics data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const perfStats = useMemo(() => {
    const today = new Date();
    const startOfDay = (date) => new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const todayStart = startOfDay(today);
    const weekStart = new Date(todayStart);
    weekStart.setDate(weekStart.getDate() - 6);
    const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
    const rolling30Start = new Date(todayStart);
    rolling30Start.setDate(rolling30Start.getDate() - 29);
    const closedTrades = trades.filter((trade) => trade.exit_time && Number.isFinite(new Date(trade.exit_time).getTime()));
    const exitedBetween = (trade, start) => {
      const exit = new Date(trade.exit_time);
      return exit >= start && exit <= today;
    };
    const sumNetPnl = (items) => items.reduce((sum, trade) => sum + Number(trade.net_pnl || 0), 0);
    const last30Trades = closedTrades.filter((trade) => exitedBetween(trade, rolling30Start));
    const dailyPnl = new Map();
    last30Trades.forEach((trade) => {
      const exit = new Date(trade.exit_time);
      const key = `${exit.getFullYear()}-${String(exit.getMonth() + 1).padStart(2, "0")}-${String(exit.getDate()).padStart(2, "0")}`;
      dailyPnl.set(key, (dailyPnl.get(key) || 0) + Number(trade.net_pnl || 0));
    });
    const dailyEntries = [...dailyPnl.entries()].map(([date, pnl]) => ({ date, pnl }));
    const bestDay = dailyEntries.length ? dailyEntries.reduce((best, day) => day.pnl > best.pnl ? day : best) : null;
    const worstDay = dailyEntries.length ? dailyEntries.reduce((worst, day) => day.pnl < worst.pnl ? day : worst) : null;
    const wins = last30Trades.filter((trade) => Number(trade.net_pnl || 0) > 0).length;
    const pnlBars = dailyEntries.sort((a, b) => a.date.localeCompare(b.date)).slice(-14);
    const maxAbs = Math.max(...pnlBars.map((day) => Math.abs(day.pnl)), 1);

    return {
      weekPnl: sumNetPnl(closedTrades.filter((trade) => exitedBetween(trade, weekStart))),
      monthPnl: sumNetPnl(closedTrades.filter((trade) => exitedBetween(trade, monthStart))),
      bestDay,
      worstDay,
      winRate: last30Trades.length ? (wins / last30Trades.length) * 100 : 0,
      closedTradeCount: last30Trades.length,
      pnlBars: pnlBars.map((day) => ({ ...day, pct: (Math.abs(day.pnl) / maxAbs) * 100 })),
    };
  }, [trades]);

  const pnlBars = perfStats.pnlBars;
  const liveUnrealizedPnl = positions.reduce(
    (sum, position) => sum + (livePnLByPositionId[position.id]?.pnl ?? Number(position.unrealized_pnl || 0)),
    0,
  );

  if (loading) {
    return (
      <GlobalLoader />
    );
  }

  return (
    <div className="container-padding py-6 lg:py-8 space-y-8 animate-in fade-in duration-500">
      <div className="grid md:grid-cols-2 gap-6">
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
              { label: "All-time realized P&L", value: parseFloat(portfolio?.realized_pnl || 0) },
              { label: "Unrealized P&L", value: liveUnrealizedPnl },
              { label: "7-day realized P&L", value: perfStats.weekPnl },
              { label: "Month-to-date realized P&L", value: perfStats.monthPnl },
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
              { label: "Win Rate", value: `${perfStats.winRate.toFixed(1)}%`, color: perfStats.winRate >= 50 ? "text-emerald-400" : "text-amber-400" },
              { label: "Closed trades", value: perfStats.closedTradeCount, color: "text-white" },
              { label: "Best realized day", value: perfStats.bestDay ? formatCurrency(perfStats.bestDay.pnl) : "—", color: "text-emerald-400" },
              { label: "Worst realized day", value: perfStats.worstDay ? formatCurrency(perfStats.worstDay.pnl) : "—", color: "text-rose-400" },
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
            Recent Daily Realized P&amp;L
          </CardTitle>
        </CardHeader>
        <CardContent>
          {pnlBars.length ? <>
            <div className="flex h-48 items-end gap-1.5 border-b border-gray-800 pt-4">
              {pnlBars.map((bar, i) => (
              <div key={i} className="group relative flex h-full min-w-0 flex-1 items-end">
                <div
                  className={`w-full rounded-t-sm transition-all duration-300 ${bar.pnl >= 0 ? "bg-emerald-500/60 group-hover:bg-emerald-500" : "bg-rose-500/60 group-hover:bg-rose-500"}`}
                  style={{ height: `${Math.max(bar.pct, 4)}%` }}
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
            <div className="flex justify-between pt-2">
              <span className="text-[10px] text-gray-500 uppercase tracking-tighter">{pnlBars[0]?.date}</span>
              <span className="text-[10px] text-gray-500 uppercase tracking-tighter">{pnlBars[pnlBars.length - 1]?.date}</span>
            </div>
          </> : <div className="py-12 text-center text-sm text-gray-500">Daily realized P&amp;L will appear after closed trades are recorded.</div>}
        </CardContent>
      </Card>
    </div>
  );
}
