import PropTypes from "prop-types";
import { BarChart3, CheckCircle2, TrendingDown, TrendingUp } from "lucide-react";
import { Card, CardContent } from "@/shared/components/ui/card";
import { formatCurrency, formatNumber } from "@/shared/utils/formatters";

function Metric({ title, value, detail, tone = "text-foreground", icon: Icon = BarChart3 }) {
  return (
    <Card className="border-border bg-card/50">
      <CardContent className="p-3">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</p>
          <Icon className={`h-4 w-4 ${tone}`} />
        </div>
        <p className={`text-2xl font-semibold ${tone}`}>{value}</p>
        {detail && <p className="mt-1 text-xs text-muted-foreground">{detail}</p>}
      </CardContent>
    </Card>
  );
}

export default function LivePerformance({ summary = {} }) {
  const realizedToday = Number(summary.realized_today || 0);
  const unrealized = Number(summary.unrealized_pnl || 0);
  const todayPnl = realizedToday + unrealized;
  const closedTrades = Number(summary.closed_trades_today || 0);
  const winningTrades = Number(summary.winning_trades_today || 0);
  const winRate = closedTrades ? (winningTrades / closedTrades) * 100 : null;

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">Recorded P&amp;L from trades closed today plus current open-position P&amp;L, before broker charges.</p>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric title="Today P&L" value={`${formatCurrency(todayPnl)}`} detail="Before broker charges" tone={todayPnl >= 0 ? "text-success" : "text-loss"} icon={todayPnl >= 0 ? TrendingUp : TrendingDown} />
        <Metric title="Realized today" value={`${formatCurrency(realizedToday)}`} detail={`${closedTrades} closed trades`} tone={realizedToday >= 0 ? "text-success" : "text-loss"} icon={CheckCircle2} />
        <Metric title="Open P&L" value={`${formatCurrency(unrealized)}`} detail={`${summary.open_positions || 0} open positions`} tone={unrealized >= 0 ? "text-success" : "text-loss"} icon={unrealized >= 0 ? TrendingUp : TrendingDown} />
        <Metric title="Winning closed trades" value={winRate == null ? "—" : `${formatNumber(winRate)}%`} detail={closedTrades ? `${winningTrades} of ${closedTrades} closed today` : "No trades closed today"} icon={BarChart3} />
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <Metric title="Filled orders today" value={summary.today_fills ?? 0} detail={`${summary.today_orders ?? 0} orders placed today`} />
        <Metric title="Active sessions" value={summary.running_sessions ?? 0} detail={`${summary.paused_sessions ?? 0} paused`} />
        <Metric title="Open orders" value={summary.open_orders ?? 0} detail="Awaiting final broker status" />
      </div>
    </div>
  );
}

Metric.propTypes = {
  ...Metric.propTypes,
  detail: PropTypes.string,
  icon: PropTypes.elementType,
  title: PropTypes.string,
  tone: PropTypes.string,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
};

LivePerformance.propTypes = {
  ...LivePerformance.propTypes,
  summary: PropTypes.object,
};
