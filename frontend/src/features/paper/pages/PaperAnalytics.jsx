import { GlobalLoader } from '@/shared/components/ui/global-loader';
import {useStableCallback} from "@/shared/hooks/useStableCallback";
import { useState, useEffect, useRef } from "react";
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
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { usePageTitle } from "@/shared/hooks/use-page-title";
import { formatCurrency, formatNumber } from "@/shared/utils/formatters";
import { TooltipHint } from "@/shared/components/ui/tooltip";
import { useLivePositionSummary } from "@/shared/hooks/useLivePositionsPnL";
import { usePaperTradingUpdate, usePaperTradingWebSocket } from "@/shared/hooks/usePaperTradingWebSocket";

export default function PaperAnalytics() {
  const fetchData = useStableCallback(async (showLoading = true) => {
    const generation = ++request.current;
    try {
      if (showLoading) setLoading(true);
      const [portRes, tradesRes, positionsRes] = await Promise.all([
        portfolioApi.getMyPortfolio(),
        paperApi.getTradeAnalytics(),
        paperApi.getPositionsSummary(),
      ]);
      if (generation !== request.current) return;
      setPortfolio(portRes.data);
      setAnalytics(tradesRes.data);
      setValuation(positionsRes.data);
    } catch (error) {
      if (generation === request.current) notify.error(getApiErrorMessage(error, "Failed to load analytics data"));
    } finally {
      if (generation === request.current) setLoading(false);
    }
  });

  const { notify } = useNotifications();
  const [portfolio, setPortfolio] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [snapshot, setValuation] = useState({});
  const valuation = useLivePositionSummary(snapshot);
  usePaperTradingWebSocket();
  const lastMessage = usePaperTradingUpdate();
  const [loading, setLoading] = useState(true);
  const request = useRef(0);

  usePageTitle({
    title: "Paper Performance Analytics",
    subtitle: "Portfolio-wide performance across all Paper sessions",
  });



  useEffect(() => {
    fetchData();
    const guard = request;
    return () => { guard.current++; };
  }, [fetchData]);

  useEffect(() => {
    if (!lastMessage) return undefined;
    const timer = setTimeout(() => fetchData(false), 150);
    return () => clearTimeout(timer);
  }, [lastMessage, fetchData]);

  const perfStats = analytics?.performance || { pnlBars: [], weekPnl: 0, monthPnl: 0, winRate: 0, closedTradeCount: 0 };
  const maxAbs = Math.max(...perfStats.pnlBars.map(day => Math.abs(Number(day.pnl))), 1);
  const pnlBars = perfStats.pnlBars.map(day => ({ ...day, pnl: Number(day.pnl), pct: Math.abs(Number(day.pnl)) / maxAbs * 100 }));
  const liveUnrealizedPnl = Number(valuation.unrealized_pnl || 0);

  if (loading) {
    return (
      <GlobalLoader />
    );
  }

  return (
    <div className="page-content animate-in fade-in duration-500">
      <div className="grid md:grid-cols-2 gap-3">
        {/* P&L Breakdown */}
        <Card className="bg-card/50 border-border">
          <CardHeader className="pb-3 border-b border-border/50">
            <CardTitle className="text-foreground text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-brand" />
              P&L Performance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            {[
              { label: "All-time realized P&L", value: parseFloat(portfolio?.realized_pnl || 0) },
              { label: "Unrealized P&L", value: liveUnrealizedPnl },
              { label: "7-day realized P&L", value: perfStats.weekPnl },
              { label: "Month-to-date realized P&L", value: perfStats.monthPnl },
            ].map((item, i) => (
              <div key={i} className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">{item.label}</span>
                <span className={`text-sm font-bold ${item.value >= 0 ? "text-success" : "text-loss"}`}>
                  {item.value >= 0 ? "+" : ""}{formatCurrency(item.value)}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* 30-Day Stats */}
        <Card className="bg-card/50 border-border">
          <CardHeader className="pb-3 border-b border-border/50">
            <CardTitle className="text-foreground text-sm flex items-center gap-2">
              <Calendar className="h-4 w-4 text-brand" />
              Rolling 30-Day Metrics
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-4">
            {[
              { label: "Win Rate", value: `${formatNumber(perfStats.winRate)}%`, color: perfStats.winRate >= 50 ? "text-success" : "text-warning" },
              { label: "Closed trades", value: perfStats.closedTradeCount, color: "text-foreground" },
              { label: "Best realized day", value: perfStats.bestDay ? formatCurrency(perfStats.bestDay.pnl) : "—", color: "text-success" },
              { label: "Worst realized day", value: perfStats.worstDay ? formatCurrency(perfStats.worstDay.pnl) : "—", color: "text-loss" },
            ].map((item, i) => (
              <div key={i} className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">{item.label}</span>
                <span className={`text-sm font-bold ${item.color}`}>{item.value}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Daily P&L Chart */}
      <Card className="bg-card/50 border-border">
        <CardHeader>
          <CardTitle className="text-foreground text-base flex items-center gap-2">
            <Activity className="h-4 w-4 text-brand" />
            Recent Daily Realized P&amp;L
          </CardTitle>
        </CardHeader>
        <CardContent>
          {pnlBars.length ? <>
            <div className="flex h-48 items-end gap-1.5 border-b border-border pt-4">
              {pnlBars.map((bar, i) => (
              <TooltipHint key={i} content={<><p className="font-bold">{bar.date}</p><p className={bar.pnl >= 0 ? "text-success" : "text-loss"}>{bar.pnl >= 0 ? "+" : ""}{formatCurrency(bar.pnl)}</p></>}>
              <div tabIndex={0} aria-label={`Realized P&L on ${bar.date}: ${formatCurrency(bar.pnl)}`} className="group relative flex h-full min-w-0 flex-1 items-end">
                <div
                  className={`w-full rounded-t-sm transition-all duration-300 ${bar.pnl >= 0 ? "bg-success/60 group-hover:bg-success" : "bg-loss/60 group-hover:bg-loss"}`}
                  style={{ height: `${Math.max(bar.pct, 4)}%` }}
                />
              </div>
              </TooltipHint>
              ))}
            </div>
            <div className="flex justify-between pt-2">
              <span className="text-[10px] text-muted-foreground uppercase tracking-tighter">{pnlBars[0]?.date}</span>
              <span className="text-[10px] text-muted-foreground uppercase tracking-tighter">{pnlBars[pnlBars.length - 1]?.date}</span>
            </div>
          </> : <div className="py-12 text-center text-sm text-muted-foreground">Daily realized P&amp;L will appear after closed trades are recorded.</div>}
        </CardContent>
      </Card>
    </div>
  );
}
