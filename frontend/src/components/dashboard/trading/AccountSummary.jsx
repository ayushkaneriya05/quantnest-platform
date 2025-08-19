import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Wallet, 
  TrendingUp, 
  TrendingDown, 
  DollarSign,
  BarChart3,
  Target,
  Activity,
  CreditCard,
  Banknote,
  PieChart,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw
} from "lucide-react";
import api from "@/services/api";

const StatCard = ({ icon: Icon, title, value, subtitle, change, variant = "default" }) => (
  <Card className="bg-[#161b22] border-gray-700/50 hover:border-gray-600/60 transition-all duration-300 hover:shadow-lg group">
    <CardContent className="p-3 sm:p-4 lg:p-6">
      <div className="flex items-start justify-between mb-3 sm:mb-4">
        <div className={`p-2 sm:p-3 rounded-xl group-hover:scale-110 transition-transform duration-300 ${
          variant === 'positive' ? 'bg-emerald-500/20' :
          variant === 'negative' ? 'bg-red-500/20' :
          variant === 'warning' ? 'bg-orange-500/20' :
          'bg-[#0969da]/20'
        }`}>
          <Icon className={`h-4 w-4 sm:h-5 sm:w-5 lg:h-6 lg:w-6 ${
            variant === 'positive' ? 'text-emerald-400' :
            variant === 'negative' ? 'text-red-400' :
            variant === 'warning' ? 'text-orange-400' :
            'text-[#58a6ff]'
          }`} />
        </div>
        {change && (
          <div className="flex items-center gap-1">
            {change.includes('+') ? (
              <ArrowUpRight className="h-3 w-3 sm:h-4 sm:w-4 text-emerald-400" />
            ) : (
              <ArrowDownRight className="h-3 w-3 sm:h-4 sm:w-4 text-red-400" />
            )}
            <span className={`text-xs sm:text-sm font-medium ${
              change.includes('+') ? 'text-emerald-400' : 'text-red-400'
            }`}>
              {change}
            </span>
          </div>
        )}
      </div>
      <div>
        <p className="text-xs sm:text-sm font-medium text-gray-400 uppercase tracking-wider mb-1">
          {title}
        </p>
        <p className="text-lg sm:text-xl lg:text-2xl font-bold text-white mb-1 truncate">{value}</p>
        {subtitle && (
          <p className="text-xs sm:text-sm text-gray-500 truncate">{subtitle}</p>
        )}
      </div>
    </CardContent>
  </Card>
);

const MetricCard = ({ title, metrics }) => (
  <Card className="bg-[#161b22] border-gray-700/50">
    <CardHeader className="pb-3 sm:pb-4">
      <CardTitle className="text-base sm:text-lg text-white flex items-center gap-2">
        <BarChart3 className="h-4 w-4 sm:h-5 sm:w-5 text-[#58a6ff]" />
        <span className="truncate">{title}</span>
      </CardTitle>
    </CardHeader>
    <CardContent className="pt-0">
      <div className="space-y-3 sm:space-y-4">
        {metrics.map((metric, index) => (
          <div key={index} className="flex items-center justify-between py-1 sm:py-2">
            <span className="text-xs sm:text-sm text-gray-400 truncate pr-2">{metric.label}</span>
            <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
              <span className="text-xs sm:text-sm font-semibold text-gray-200">
                {metric.value}
              </span>
              {metric.trend && (
                <Badge 
                  className={`text-xs ${
                    metric.trend === 'up' 
                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' 
                      : 'bg-red-500/20 text-red-400 border-red-500/30'
                  }`}
                >
                  {metric.trend === 'up' ? '↗' : '↘'}
                </Badge>
              )}
            </div>
          </div>
        ))}
      </div>
    </CardContent>
  </Card>
);

const AccountLimits = () => (
  <Card className="bg-[#161b22] border-gray-700/50">
    <CardHeader className="pb-3 sm:pb-4">
      <CardTitle className="text-base sm:text-lg text-white flex items-center gap-2">
        <Target className="h-4 w-4 sm:h-5 sm:w-5 text-[#58a6ff]" />
        <span className="truncate">Account Limits</span>
      </CardTitle>
    </CardHeader>
    <CardContent className="pt-0">
      <div className="space-y-3 sm:space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between text-xs sm:text-sm">
            <span className="text-gray-400">Daily Trading Limit</span>
            <span className="text-gray-200">₹5,00,000</span>
          </div>
          <div className="w-full bg-[#0d1117] rounded-full h-2">
            <div className="bg-gradient-to-r from-[#58a6ff] to-[#0969da] h-2 rounded-full" style={{width: '35%'}}></div>
          </div>
          <div className="flex justify-between text-xs text-gray-500">
            <span>Used: ₹1,75,000</span>
            <span>Available: ₹3,25,000</span>
          </div>
        </div>
        
        <div className="space-y-2">
          <div className="flex justify-between text-xs sm:text-sm">
            <span className="text-gray-400">Margin Utilization</span>
            <span className="text-gray-200">₹75,000</span>
          </div>
          <div className="w-full bg-[#0d1117] rounded-full h-2">
            <div className="bg-gradient-to-r from-orange-500 to-red-500 h-2 rounded-full" style={{width: '60%'}}></div>
          </div>
          <div className="flex justify-between text-xs text-gray-500">
            <span>Used: ₹45,000</span>
            <span>Available: ₹30,000</span>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
);

export default function AccountSummary() {
  const [account, setAccount] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchAccountData = async () => {
    try {
      setRefreshing(true);
      const response = await api.get("/trading/account/");
      if (response.data) {
        setAccount(response.data);
      } else {
        console.error("Invalid account response:", response.data);
      }
    } catch (error) {
      console.error("Failed to fetch account data:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAccountData();
  }, []);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  if (loading) {
    return (
      <div className="space-y-4 sm:space-y-6">
        <div className="flex items-center justify-between mb-4 sm:mb-6">
          <div className="h-6 sm:h-8 bg-[#161b22] rounded w-32 sm:w-48 animate-pulse" />
          <div className="h-8 sm:h-10 bg-[#161b22] rounded w-16 sm:w-24 animate-pulse" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 lg:gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 sm:h-32 bg-[#161b22] rounded-lg animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4 lg:gap-6">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="h-48 sm:h-64 bg-[#161b22] rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!account) {
    return (
      <Card className="bg-[#161b22] border-gray-700/50">
        <CardContent className="p-8 sm:p-12 text-center">
          <div className="p-3 sm:p-4 rounded-full bg-red-500/20 w-fit mx-auto mb-4">
            <Wallet className="h-6 w-6 sm:h-8 sm:w-8 text-red-400" />
          </div>
          <h3 className="text-base sm:text-lg font-medium text-gray-300 mb-2">
            Account Data Unavailable
          </h3>
          <p className="text-xs sm:text-sm text-gray-500 mb-4">
            Could not load account details. Please try refreshing.
          </p>
          <Button 
            onClick={fetchAccountData}
            variant="outline"
            className="border-red-500/30 text-red-400 hover:bg-red-500/10 text-xs sm:text-sm"
          >
            <RefreshCw className="h-3 w-3 sm:h-4 sm:w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  const tradingMetrics = [
    { label: "Total Trades", value: "47", trend: "up" },
    { label: "Win Rate", value: "68%", trend: "up" },
    { label: "Avg Trade Size", value: "₹12,500" },
    { label: "Max Drawdown", value: "₹3,250", trend: "down" },
  ];

  const riskMetrics = [
    { label: "Portfolio Beta", value: "1.24" },
    { label: "Sharpe Ratio", value: "1.89", trend: "up" },
    { label: "VaR (1 day)", value: "₹8,500" },
    { label: "Risk Score", value: "Medium" },
  ];

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="p-2 sm:p-3 rounded-xl bg-[#0969da]/20">
            <Wallet className="h-5 w-5 sm:h-6 sm:w-6 text-[#58a6ff]" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-white">Account Overview</h1>
            <p className="text-xs sm:text-sm lg:text-base text-gray-400">Virtual trading account status</p>
          </div>
        </div>
        <Button
          onClick={fetchAccountData}
          variant="outline"
          className="border-[#0969da]/30 text-[#58a6ff] hover:bg-[#0969da]/10 text-xs sm:text-sm w-fit"
          disabled={refreshing}
        >
          <RefreshCw className={`h-3 w-3 sm:h-4 sm:w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 lg:gap-6">
        <StatCard
          icon={Banknote}
          title="Available Balance"
          value={formatCurrency(account.balance || 100000)}
          subtitle="Ready for trading"
          change="+2.5%"
          variant="positive"
        />
        <StatCard
          icon={TrendingUp}
          title="Unrealized P&L"
          value={formatCurrency(2450)}
          subtitle="Open positions"
          change="+₹1,250 today"
          variant="positive"
        />
        <StatCard
          icon={CreditCard}
          title="Margin Used"
          value={formatCurrency(account.margin || 45000)}
          subtitle="60% of available"
          variant="warning"
        />
        <StatCard
          icon={PieChart}
          title="Portfolio Value"
          value={formatCurrency(125000)}
          subtitle="Total equity"
          change="+8.2%"
          variant="positive"
        />
      </div>

      {/* Detailed Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 sm:gap-4 lg:gap-6">
        <MetricCard title="Trading Performance" metrics={tradingMetrics} />
        <MetricCard title="Risk Analysis" metrics={riskMetrics} />
        <AccountLimits />
      </div>

      {/* Additional Info */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4 lg:gap-6">
        <Card className="bg-[#161b22] border-gray-700/50">
          <CardHeader className="pb-3 sm:pb-4">
            <CardTitle className="text-base sm:text-lg text-white flex items-center gap-2">
              <Activity className="h-4 w-4 sm:h-5 sm:w-5 text-[#58a6ff]" />
              <span className="truncate">Recent Activity</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-3">
              {[
                { action: "Buy Order Executed", symbol: "RELIANCE", time: "2 mins ago", amount: "+₹12,500" },
                { action: "Sell Order Placed", symbol: "TCS", time: "15 mins ago", amount: "-₹8,900" },
                { action: "Dividend Received", symbol: "INFY", time: "1 hour ago", amount: "+₹450" },
              ].map((activity, index) => (
                <div key={index} className="flex items-center justify-between py-2 border-b border-gray-700/50 last:border-0">
                  <div className="min-w-0 flex-1">
                    <p className="text-xs sm:text-sm font-medium text-gray-200 truncate">{activity.action}</p>
                    <p className="text-xs text-gray-500">{activity.symbol} • {activity.time}</p>
                  </div>
                  <span className={`text-xs sm:text-sm font-semibold flex-shrink-0 ml-2 ${
                    activity.amount.startsWith('+') ? 'text-emerald-400' : 'text-red-400'
                  }`}>
                    {activity.amount}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#161b22] border-gray-700/50">
          <CardHeader className="pb-3 sm:pb-4">
            <CardTitle className="text-base sm:text-lg text-white flex items-center gap-2">
              <DollarSign className="h-4 w-4 sm:h-5 sm:w-5 text-[#58a6ff]" />
              <span className="truncate">Account Settings</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-3 sm:space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs sm:text-sm text-gray-400">Auto Square-off</span>
                <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-xs">Enabled</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs sm:text-sm text-gray-400">Risk Management</span>
                <Badge className="bg-[#0969da]/20 text-[#58a6ff] border-[#0969da]/30 text-xs">Active</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs sm:text-sm text-gray-400">Paper Trading Mode</span>
                <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30 text-xs">On</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs sm:text-sm text-gray-400">Account Type</span>
                <Badge variant="outline" className="border-gray-600 text-gray-400 text-xs">Virtual</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
