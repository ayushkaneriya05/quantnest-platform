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
    default: "bg-brand/10 text-brand",
    positive: "bg-success/10 text-success",
    negative: "bg-loss/10 text-loss",
    warning: "bg-warning/10 text-warning",
  };

  return (
    <Card className="bg-card/50 border-border hover:border-border transition-colors">
      <CardContent className="p-3">
        <div className="flex items-start justify-between mb-3">
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

export default function LivePortfolioSummary({ summary = {} }) {
  const runningSessionsCount = summary.running_sessions || 0;
  const totalOpenPositions = summary?.open_positions || 0;
  const totalOpenOrders = summary?.open_orders || 0;
  const dayPnl = Number(summary?.day_pnl || 0);

  const pnlVariant = dayPnl >= 0 ? "positive" : "negative";

  return (
    <div className="space-y-4">
      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        <StatCard
          icon={Activity}
          title="Active Sessions"
          value={runningSessionsCount}
          subtitle={`of ${summary.total_sessions || 0} total`}
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
  summary: PropTypes.object,
};
