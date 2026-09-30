import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import {
  Wallet,
  TrendingUp,
  DollarSign,
  Activity,
  RefreshCw,
} from "lucide-react";
import { formatNumber } from "@/shared/utils/formatters";
import { formatBrokerAccount, formatDateTime as formatLiveDateTime } from "@/shared/utils/formatters";

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
    warning: "bg-amber-500/10 text-amber-400",
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

export default function LivePortfolioSummary({ summary = {}, sessions = [] }) {
  const runningSessionsCount = sessions.filter(
    (s) => s.status === "RUNNING",
  ).length;
  const totalOpenPositions = summary?.open_positions || 0;
  const totalOpenOrders = summary?.open_orders || 0;
  const dayPnl = Number(summary?.day_pnl || 0);

  const pnlVariant = dayPnl >= 0 ? "positive" : "negative";

  const brokerAccounts = summary?.broker_accounts || [];

  const totalEquity = useMemo(() => {
    return brokerAccounts.reduce((sum, acc) => sum + Number(acc.net_equity || 0), 0);
  }, [brokerAccounts]);
  const equityComplete = brokerAccounts.length > 0 && brokerAccounts.every((account) => account.net_equity != null);

  return (
    <div className="space-y-8">
      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
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
          icon={DollarSign}
          title="Total Equity"
          value={equityComplete ? `₹${formatNumber(totalEquity)}` : "—"}
          subtitle={equityComplete ? "All broker accounts" : "Broker snapshots incomplete"}
          variant="default"
        />
        <StatCard
          icon={TrendingUp}
          title="Today P&L"
          value={`₹${formatNumber(dayPnl)}`}
          subtitle="Realized today + open P&L"
          variant={pnlVariant}
        />
      </div>

      {/* Broker Accounts Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {brokerAccounts.map((account) => (
          <Card
            key={account.credential_id ?? account.broker_label}
            className="bg-slate-900/50 border-slate-800"
          >
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <CardTitle className="text-lg text-white">{formatBrokerAccount(account.broker_name, account.broker_label)}</CardTitle>
              <div className="flex items-center gap-3">
                {!account.broker_session_valid && (
                  <Button
                    asChild
                    variant="ghost"
                    size="sm"
                    className="h-8 text-amber-400 hover:text-amber-300 hover:bg-amber-400/10 gap-2"
                  >
                    <Link to="/dashboard/brokers">
                      <RefreshCw className="h-3.5 w-3.5" />
                      Reconnect
                    </Link>
                  </Button>
                )}
                <Badge
                  className={
                    account.is_healthy
                      ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                      : "bg-rose-500/15 text-rose-300 border-rose-500/30"
                  }
                >
                  {account.is_healthy ? "Account ready" : "Action required"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Account Metrics */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                    Net Equity
                  </p>
                  <p className="text-white font-bold text-lg">
                    {account.net_equity == null ? "—" : `₹${formatNumber(Number(account.net_equity))}`}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                    Cash Balance
                  </p>
                  <p className="text-cyan-400 font-bold text-lg">
                    {account.cash_balance == null ? "—" : `₹${formatNumber(Number(account.cash_balance))}`}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                    Available Margin
                  </p>
                  <p className="text-emerald-400 font-bold text-lg">
                    {account.available_margin == null ? "—" : `₹${formatNumber(Number(account.available_margin))}`}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                    Used Margin
                  </p>
                  <p className="text-amber-400 font-bold text-lg">
                    {account.used_margin == null ? "—" : `₹${formatNumber(Number(account.used_margin))}`}
                  </p>
                </div>
              </div>

              <div className="border-t border-slate-800 pt-3 text-xs text-slate-500">
                <div>Funds snapshot: {account.funds_as_of ? formatLiveDateTime(account.funds_as_of) : "Not synced yet"}</div>
                <div className="mt-1">Broker order updates: <span className={account.order_websocket_status === "connected" ? "text-emerald-300" : account.order_websocket_status === "reconciliation" ? "text-amber-300" : "text-rose-300"}>{account.order_websocket_status || "unknown"}</span></div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

    </div>
  );
}
