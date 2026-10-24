import PropTypes from "prop-types";
import { Card, CardContent } from "@/shared/components/ui/card";
import {
  Wallet,
  TrendingUp,
  Activity,
} from "lucide-react";
import { formatCurrency } from "@/shared/utils/formatters";

const StatCard = ({
  icon: Icon,
  title,
  value,
  subtitle,
  variant = "default",
}) => {
  const variantClasses = {
    default: "bg-sky-500/10 text-sky-700 dark:text-sky-400",
    positive: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
    negative: "bg-rose-500/10 text-rose-700 dark:text-rose-400",
    warning: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
  };

  return (
    <Card className="bg-card/50 border-border hover:border-border transition-colors">
      <CardContent className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className={`p-3 rounded-2xl ${variantClasses[variant]}`}>
            <Icon className="h-6 w-6" />
          </div>
        </div>
        <div>
          <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-1">
            {title}
          </p>
          <p className="text-2xl font-black text-foreground mb-1">{value}</p>
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
        </div>
      </CardContent>
    </Card>
  );
};

export default function LivePortfolioSummary({ summary = {}, sessions = [] }) {
  const runningSessionsCount = sessions.filter(
    (s) => s.status === "RUNNING",
  ).length;
  const totalOpenPositions = summary?.open_positions || 0;
  const totalOpenOrders = summary?.open_orders || 0;
  const dayPnl = Number(summary?.day_pnl || 0);

  const pnlVariant = dayPnl >= 0 ? "positive" : "negative";

  return (
    <div className="space-y-8">
      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          icon={Activity}
          title="Active Sessions"
          value={runningSessionsCount}
          subtitle={`of ${sessions.length} total`}
          variant="default"
        />
        <StatCard
          icon={TrendingUp}
          title="Open Positions"
          value={totalOpenPositions}
          subtitle="Active trades"
          variant="default"
        />
        <StatCard
          icon={Wallet}
          title="Open Orders"
          value={totalOpenOrders}
          subtitle="Awaiting terminal status"
          variant="default"
        />
        <StatCard
          icon={TrendingUp}
          title="Today P&L"
          value={`${formatCurrency(dayPnl)}`}
          subtitle="Realized today + open P&L · before broker charges"
          variant={pnlVariant}
        />
      </div>

    </div>
  );
}

StatCard.propTypes = {
  ...StatCard.propTypes,
  icon: PropTypes.elementType,
  subtitle: PropTypes.string,
  title: PropTypes.string,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  variant: PropTypes.string,
};

LivePortfolioSummary.propTypes = {
  ...LivePortfolioSummary.propTypes,
  sessions: PropTypes.array,
  summary: PropTypes.object,
};
