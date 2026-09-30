import { BarChart3, CheckCircle2, TrendingDown, TrendingUp } from "lucide-react";
import { Card, CardContent } from "@/shared/components/ui/card";
import { formatNumber } from "@/shared/utils/formatters";
import { useLivePositionsPnL } from "@/shared/hooks/useLivePositionsPnL";

function Metric({ title, value, detail, tone = "text-white", icon: Icon = BarChart3 }) {
  return (
    <Card className="border-slate-800 bg-slate-900/50">
      <CardContent className="p-5">
        <div className="mb-4 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</p>
          <Icon className={`h-4 w-4 ${tone}`} />
        </div>
        <p className={`text-2xl font-semibold ${tone}`}>{value}</p>
        {detail && <p className="mt-1 text-xs text-slate-500">{detail}</p>}
      </CardContent>
    </Card>
  );
}

export default function LivePerformance({ summary = {}, positions = [] }) {
  const realizedToday = Number(summary.realized_today || 0);
  const { totals } = useLivePositionsPnL(positions);
  const unrealized = positions.length ? totals.totalUnrealizedPnL : Number(summary.unrealized_pnl || 0);
  const todayPnl = realizedToday + unrealized;
  const closedTrades = Number(summary.closed_trades_today || 0);
  const winningTrades = Number(summary.winning_trades_today || 0);
  const winRate = closedTrades ? (winningTrades / closedTrades) * 100 : null;

  return (
    <div className="space-y-5">
      <p className="text-sm text-slate-500">Realized P&amp;L from trades closed today plus current open-position P&amp;L.</p>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric title="Today P&L" value={`₹${formatNumber(todayPnl)}`} detail={todayPnl >= 0 ? "Net gain" : "Net loss"} tone={todayPnl >= 0 ? "text-emerald-400" : "text-rose-400"} icon={todayPnl >= 0 ? TrendingUp : TrendingDown} />
        <Metric title="Realized today" value={`₹${formatNumber(realizedToday)}`} detail={`${closedTrades} closed trades`} tone={realizedToday >= 0 ? "text-emerald-400" : "text-rose-400"} icon={CheckCircle2} />
        <Metric title="Open P&L" value={`₹${formatNumber(unrealized)}`} detail={`${summary.open_positions || 0} open positions`} tone={unrealized >= 0 ? "text-emerald-400" : "text-rose-400"} icon={unrealized >= 0 ? TrendingUp : TrendingDown} />
        <Metric title="Winning closed trades" value={winRate == null ? "—" : `${winRate.toFixed(1)}%`} detail={closedTrades ? `${winningTrades} of ${closedTrades} closed today` : "No trades closed today"} icon={BarChart3} />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Metric title="Filled orders today" value={summary.today_fills ?? 0} detail={`${summary.today_orders ?? 0} orders placed today`} />
        <Metric title="Active sessions" value={summary.running_sessions ?? 0} detail={`${summary.paused_sessions ?? 0} paused`} />
        <Metric title="Open orders" value={summary.open_orders ?? 0} detail="Awaiting final broker status" />
      </div>
    </div>
  );
}
