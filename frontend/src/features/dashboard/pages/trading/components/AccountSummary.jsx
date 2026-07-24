import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Banknote,
  CreditCard,
  PieChart,
  ShieldCheck,
  TrendingUp,
  Zap,
} from "lucide-react";
import { useWebSocket } from "@/shared/hooks/useWebSocket";
import { useLivePositionsPnL } from "@/shared/hooks/useLivePositionsPnL";

const StatCard = ({ icon: Icon, title, value, subtitle, variant = "default" }) => (
  <Card className="bg-slate-900/50 border-slate-800 hover:border-slate-700 transition-colors">
    <CardContent className="p-6">
      <div className="flex items-start justify-between mb-4">
        <div
          className={`p-3 rounded-2xl ${
            variant === "positive"
              ? "bg-emerald-500/10 text-emerald-400"
              : variant === "negative"
              ? "bg-rose-500/10 text-rose-400"
              : variant === "warning"
              ? "bg-amber-500/10 text-amber-400"
              : "bg-sky-500/10 text-sky-400"
          }`}
        >
          <Icon className="h-6 w-6" />
        </div>
      </div>
      <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">
        {title}
      </p>
      <p className="text-2xl font-black text-white mb-1">{value}</p>
      {subtitle && <p className="text-xs text-slate-600">{subtitle}</p>}
    </CardContent>
  </Card>
);

const formatCurrency = (value, maximumFractionDigits = 0) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 0,
    maximumFractionDigits,
  }).format(Number(value || 0));

export default function AccountSummary({ account, trades = [], positions = [], metrics }) {
  const { connectionStatus } = useWebSocket();
  const isLiveDataConnected = connectionStatus === "connected";
  const { totals } = useLivePositionsPnL(positions);
  const dynamicUnrealizedPnl = totals.totalUnrealizedPnL || 0;
  const realizedPnl = Number(metrics?.realizedPnl || 0);
  const equityValue = Number(metrics?.balance || 0) + dynamicUnrealizedPnl;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          icon={Banknote}
          title="Available Balance"
          value={formatCurrency(metrics?.balance || 0)}
          subtitle="Cash available to trade"
          variant="positive"
        />
        <StatCard
          icon={TrendingUp}
          title="Realized P&L"
          value={formatCurrency(metrics?.realizedPnl || 0)}
          subtitle="Cleared profit/loss"
          variant={metrics?.realizedPnl >= 0 ? "positive" : "negative"}
        />
        <StatCard
          icon={CreditCard}
          title="Used Margin"
          value={formatCurrency(metrics?.margin || 0)}
          subtitle="Blocked short exposure"
          variant="warning"
        />
        <StatCard
          icon={PieChart}
          title="Total Equity"
          value={formatCurrency(equityValue)}
          subtitle="Cash plus unrealized P&L"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card className="bg-slate-900/50 border-slate-800 overflow-hidden">
          <CardHeader className="border-b border-slate-800 bg-slate-900/30">
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Activity className="h-5 w-5 text-sky-400" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 max-h-[500px] overflow-y-auto custom-scrollbar">
            {trades.length > 0 ? (
              <div className="divide-y divide-slate-800">
                {trades.map((trade) => {
                  const value = Number(trade.executed_price) * Number(trade.quantity || 0);
                  return (
                    <div
                      key={trade.id}
                      className="p-4 flex items-center justify-between hover:bg-slate-800/10 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`p-2 rounded-lg ${
                            trade.transaction_type === "BUY"
                              ? "bg-rose-500/10 text-rose-400"
                              : "bg-emerald-500/10 text-emerald-400"
                          }`}
                        >
                          {trade.transaction_type === "BUY" ? (
                            <ArrowDownRight className="h-4 w-4" />
                          ) : (
                            <ArrowUpRight className="h-4 w-4" />
                          )}
                        </div>
                        <div>
                          <p className="font-bold text-white leading-none">
                            {trade.instrument.symbol}
                          </p>
                          <p className="text-[10px] text-slate-500 uppercase mt-1">
                            {trade.order_type} • {new Date(trade.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p
                          className={`font-bold ${
                            trade.transaction_type === "BUY"
                              ? "text-rose-400"
                              : "text-emerald-400"
                          }`}
                        >
                          {trade.transaction_type === "BUY" ? "-" : "+"} {formatCurrency(value)}
                        </p>
                        <p className="text-[10px] text-slate-600">
                          {trade.quantity} units @ ₹{Number(trade.executed_price).toFixed(2)}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-12 text-center">
                <Activity className="h-10 w-10 text-slate-700 mx-auto mb-3" />
                <p className="text-slate-500">No recent trades found</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="bg-slate-900/50 border-slate-800 h-fit">
          <CardHeader className="border-b border-slate-800 bg-slate-900/30">
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-emerald-400" />
              Terminal Status
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <p className="text-[10px] font-bold text-slate-500 uppercase">
                  Market Data
                </p>
                <div className="flex items-center gap-2">
                  <div
                    className={`h-2 w-2 rounded-full ${
                      isLiveDataConnected ? "bg-emerald-500 animate-pulse" : "bg-amber-500"
                    }`}
                  />
                  <span
                    className={`text-sm font-bold ${
                      isLiveDataConnected ? "text-emerald-400" : "text-amber-400"
                    }`}
                  >
                    {connectionStatus.toUpperCase()}
                  </span>
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-[10px] font-bold text-slate-500 uppercase">
                  Execution Engine
                </p>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-sm font-bold text-emerald-400">PAPER</span>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-800">
              <div className="flex items-center justify-between p-4 bg-sky-500/5 rounded-2xl border border-sky-500/20">
                <div className="flex items-center gap-3">
                  <Zap className="h-5 w-5 text-sky-400" />
                  <div>
                    <p className="text-sm font-bold text-white">Paper Trading Mode</p>
                    <p className="text-xs text-slate-500">All executions are virtual</p>
                  </div>
                </div>
                <Badge className="bg-sky-500/20 text-sky-400 border-sky-500/30">
                  ENABLED
                </Badge>
              </div>
            </div>

            <p className="text-[10px] text-center text-slate-600 italic">
              Terminal session active since{" "}
              {account?.created_at
                ? new Date(account.created_at).toLocaleDateString()
                : "initialization"}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
