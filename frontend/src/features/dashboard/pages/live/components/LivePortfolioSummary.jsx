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
  const dayPnl = summary?.day_pnl || 0;

  const pnlVariant = dayPnl >= 0 ? "positive" : "negative";

  const brokerAccounts = summary?.broker_accounts || [];
  const hasHealthIssues = brokerAccounts.some((acc) => !acc.is_healthy);

  const totalEquity = useMemo(() => {
    return brokerAccounts.reduce((sum, acc) => sum + (acc.net_equity || 0), 0);
  }, [brokerAccounts]);

  const totalMargin = useMemo(() => {
    return brokerAccounts.reduce(
      (sum, acc) => sum + (acc.available_margin || 0),
      0,
    );
  }, [brokerAccounts]);

  return (
    <div className="space-y-8">
      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
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
          subtitle="Pending fills"
          variant="default"
        />
        <StatCard
          icon={DollarSign}
          title="Total Equity"
          value={`₹${formatNumber(totalEquity)}`}
          subtitle="All broker accounts"
          variant="default"
        />
        <StatCard
          icon={TrendingUp}
          title="Day P&L"
          value={`₹${formatNumber(Math.abs(dayPnl))}`}
          subtitle={dayPnl >= 0 ? "Profit" : "Loss"}
          variant={pnlVariant}
        />
      </div>

      {/* Broker Accounts Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {brokerAccounts.map((account) => (
          <Card
            key={account.credential_id}
            className="bg-slate-900/50 border-slate-800"
          >
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <CardTitle className="text-lg text-white">
                {account.broker_label || account.broker_name}
              </CardTitle>
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
                  {account.is_healthy ? "Healthy" : "Action Required"}
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
                    ₹{formatNumber(account.net_equity)}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                    Cash Balance
                  </p>
                  <p className="text-cyan-400 font-bold text-lg">
                    ₹{formatNumber(account.cash_balance)}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                    Available Margin
                  </p>
                  <p className="text-emerald-400 font-bold text-lg">
                    ₹{formatNumber(account.available_margin)}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                    Used Margin
                  </p>
                  <p className="text-amber-400 font-bold text-lg">
                    ₹{formatNumber(account.used_margin)}
                  </p>
                </div>
              </div>

              {/* Allocations */}
              {(account.allocations || []).length > 0 && (
                <div className="border-t border-slate-700 pt-4">
                  <p className="text-xs uppercase tracking-wider font-bold text-slate-500 mb-3">
                    Strategy Wallets
                  </p>
                  <div className="space-y-2">
                    {account.allocations.map((allocation) => (
                      <div
                        key={allocation.id}
                        className="rounded-lg border border-slate-700 bg-slate-800/20 p-3"
                      >
                        <div className="flex items-center justify-between gap-3 mb-2">
                          <span className="text-slate-200 font-medium">
                            {allocation.strategy_name ||
                              `Strategy #${allocation.strategy_id}`}
                          </span>
                          {allocation.is_over_allocated ? (
                            <Badge className="bg-rose-500/15 text-rose-300 border-rose-500/30 text-xs">
                              Over allocated
                            </Badge>
                          ) : (
                            <Badge className="bg-emerald-500/15 text-emerald-300 border-emerald-500/30 text-xs">
                              Healthy
                            </Badge>
                          )}
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-xs text-slate-400">
                          <div>
                            <p className="text-slate-500">Allocated</p>
                            <p className="text-white font-semibold">
                              ₹{formatNumber(allocation.allocated_capital)}
                            </p>
                          </div>
                          <div>
                            <p className="text-slate-500">Used</p>
                            <p className="text-white font-semibold">
                              ₹{formatNumber(allocation.used_capital)}
                            </p>
                          </div>
                          <div>
                            <p className="text-slate-500">Available</p>
                            <p className="text-white font-semibold">
                              ₹{formatNumber(allocation.available_capital)}
                            </p>
                          </div>
                        </div>
                        {allocation.breach_reason && (
                          <p className="text-xs text-rose-400 mt-2">
                            {allocation.breach_reason}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Summary Stats Bar */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-6 text-sm">
          <div>
            <p className="text-slate-500 uppercase tracking-wider text-xs font-bold mb-1">
              Total Fills Today
            </p>
            <p className="text-2xl font-bold text-white">
              {summary?.today_fills || 0}
            </p>
          </div>
          <div className="h-12 w-px bg-slate-700 hidden sm:block" />
          <div>
            <p className="text-slate-500 uppercase tracking-wider text-xs font-bold mb-1">
              Last Updated
            </p>
            <p className="text-slate-300">{new Date().toLocaleTimeString()}</p>
          </div>
          <div className="h-12 w-px bg-slate-700 hidden sm:block" />
          <div>
            <p className="text-slate-500 uppercase tracking-wider text-xs font-bold mb-1">
              System Status
            </p>
            <div className="flex items-center gap-2">
              <div
                className={`h-2 w-2 rounded-full ${hasHealthIssues ? "bg-amber-500" : "bg-emerald-500"}`}
              />
              <span className="text-slate-300">
                {hasHealthIssues ? "Requires attention" : "Operational"}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
