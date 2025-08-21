import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  DollarSign, 
  TrendingUp, 
  Wallet, 
  PieChart, 
  RefreshCw,
  AlertCircle,
  Activity,
  Shield,
  Target,
  BarChart3,
  Zap,
  Clock,
  Award
} from "lucide-react";
import api from "@/services/api";
import toast from "react-hot-toast";

const MetricCard = ({ icon: Icon, title, value, subtitle, variant = "default", className = "" }) => (
  <Card className={`bg-slate-900/50 border-slate-700/50 ${className}`}>
    <CardContent className="p-4 lg:p-6">
      <div className="flex items-center gap-3 lg:gap-4">
        <div className={`p-2 lg:p-3 rounded-xl ${
          variant === 'positive' ? 'bg-emerald-500/20' :
          variant === 'negative' ? 'bg-red-500/20' :
          variant === 'warning' ? 'bg-yellow-500/20' :
          'bg-blue-500/20'
        }`}>
          <Icon className={`h-4 w-4 lg:h-5 lg:w-5 ${
            variant === 'positive' ? 'text-emerald-400' :
            variant === 'negative' ? 'text-red-400' :
            variant === 'warning' ? 'text-yellow-400' :
            'text-blue-400'
          }`} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs lg:text-sm font-medium text-gray-400 uppercase tracking-wider mb-1">
            {title}
          </p>
          <p className="text-lg lg:text-xl xl:text-2xl font-bold text-white truncate">{value}</p>
          {subtitle && (
            <p className="text-xs lg:text-sm text-gray-500 truncate mt-1">{subtitle}</p>
          )}
        </div>
      </div>
    </CardContent>
  </Card>
);

const StatBlock = ({ title, value, subtitle, className = "" }) => (
  <div className={`text-center ${className}`}>
    <div className="text-xl lg:text-2xl font-bold text-white mb-1">
      {value}
    </div>
    <div className="text-sm lg:text-base text-gray-400 mb-1">{title}</div>
    {subtitle && (
      <div className="text-xs text-gray-500">{subtitle}</div>
    )}
  </div>
);

export default function AccountSummary() {
  const [accountData, setAccountData] = useState(null);
  const [portfolioSummary, setPortfolioSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchAccountData = async () => {
    try {
      const [accountRes, portfolioRes] = await Promise.all([
        api.get('/api/v1/trading/account/'),
        api.get('/api/v1/trading/portfolio/summary/')
      ]);

      setAccountData(accountRes.data);
      setPortfolioSummary(portfolioRes.data);
    } catch (error) {
      console.error('Failed to fetch account data:', error);
      toast.error('Failed to load account data');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAccountData();
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchAccountData();
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount || 0);
  };

  const formatPercentage = (value) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 lg:h-28 bg-slate-900/50 rounded-lg animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="h-48 bg-slate-900/50 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!accountData || !portfolioSummary) {
    return (
      <Card className="bg-slate-900/50 border-slate-700/50">
        <CardContent className="p-8 text-center">
          <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-300 mb-2">Failed to Load Account Data</h3>
          <p className="text-sm text-gray-500 mb-4">Unable to retrieve your account information</p>
          <Button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  const totalPnlVariant = portfolioSummary.total_pnl >= 0 ? 'positive' : 'negative';
  const returnPercentage = portfolioSummary.return_percentage || 0;
  const marginUsagePercent = accountData.balance > 0 ? ((accountData.margin_used || 0) / accountData.balance * 100) : 0;
  const marginVariant = marginUsagePercent > 80 ? 'negative' : marginUsagePercent > 60 ? 'warning' : 'default';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl lg:text-2xl font-bold text-white">Paper Trading Account</h2>
          <div className="flex items-center gap-2 mt-1">
            <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">
              <Activity className="h-3 w-3 mr-1" />
              Demo Mode
            </Badge>
            <span className="text-xs text-gray-500">
              Last updated: {new Date().toLocaleTimeString()}
            </span>
          </div>
        </div>
        <Button
          onClick={handleRefresh}
          disabled={isRefreshing}
          variant="outline"
          size="sm"
          className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white hover:border-slate-500"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Main Account Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6">
        <MetricCard
          icon={Wallet}
          title="Available Balance"
          value={formatCurrency(accountData.balance)}
          subtitle="Cash for new trades"
          variant="default"
        />

        <MetricCard
          icon={TrendingUp}
          title="Total P&L"
          value={formatCurrency(portfolioSummary.total_pnl)}
          subtitle={formatPercentage(returnPercentage)}
          variant={totalPnlVariant}
        />

        <MetricCard
          icon={Award}
          title="Win Rate"
          value="68.5%"
          subtitle="Based on closed trades"
          variant="positive"
        />
      </div>

      {/* Trading Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6">
        <MetricCard
          icon={BarChart3}
          title="Active Positions"
          value={portfolioSummary.positions_count.toString()}
          subtitle={`${portfolioSummary.open_orders_count} pending orders`}
          variant="default"
        />

        <MetricCard
          icon={Clock}
          title="Account Age"
          value="12 Days"
          subtitle="Paper trading mode"
          variant="default"
        />

        <MetricCard
          icon={Activity}
          title="Trade Frequency"
          value="47 trades"
          subtitle="This month"
          variant="default"
        />
      </div>

      {/* Detailed Statistics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
        {/* Trading Performance */}
        <Card className="bg-slate-900/50 border-slate-700/50">
          <CardHeader>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-emerald-400" />
              Trading Performance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 lg:gap-6">
              <StatBlock
                title="Day's P&L"
                value="₹+8,450"
                subtitle="+0.85%"
              />
              <StatBlock
                title="Week's P&L"
                value="₹+24,200"
                subtitle="+2.42%"
              />
              <StatBlock
                title="Max Drawdown"
                value="-₹12,500"
                subtitle="-1.25%"
              />
              <StatBlock
                title="Total Trades"
                value="47"
                subtitle="This month"
              />
              <StatBlock
                title="Avg Trade"
                value="₹+1,064"
                subtitle="Per trade"
              />
              <StatBlock
                title="Best Trade"
                value="₹+8,750"
                subtitle="RELIANCE"
              />
            </div>
          </CardContent>
        </Card>

        {/* Risk Management */}
        <Card className="bg-slate-900/50 border-slate-700/50">
          <CardHeader>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Shield className="h-5 w-5 text-blue-400" />
              Risk Management
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <StatBlock
                  title="Risk Per Trade"
                  value="2%"
                  subtitle="Of portfolio"
                />
                <StatBlock
                  title="Max Position Size"
                  value="₹50,000"
                  subtitle="Per stock"
                />
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-400">Portfolio Diversification</span>
                  <span className="text-sm text-white">Good</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div className="bg-emerald-500 h-2 rounded-full" style={{ width: '75%' }}></div>
                </div>
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-400">Risk Score</span>
                  <span className="text-sm text-yellow-400">Medium</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div className="bg-yellow-500 h-2 rounded-full" style={{ width: '60%' }}></div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Account Limits */}
      <Card className="bg-slate-900/50 border-slate-700/50">
        <CardHeader>
          <CardTitle className="text-lg text-white flex items-center gap-2">
            <Clock className="h-5 w-5 text-gray-400" />
            Account Limits & Usage
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div>
              <div className="text-sm text-gray-400 mb-2">Daily Trade Limit</div>
              <div className="text-lg font-bold text-white">47 / 100</div>
              <div className="w-full bg-gray-700 rounded-full h-1 mt-1">
                <div className="bg-blue-500 h-1 rounded-full" style={{ width: '47%' }}></div>
              </div>
            </div>
            
            <div>
              <div className="text-sm text-gray-400 mb-2">Monthly Volume</div>
              <div className="text-lg font-bold text-white">₹45.2L / ₹100L</div>
              <div className="w-full bg-gray-700 rounded-full h-1 mt-1">
                <div className="bg-emerald-500 h-1 rounded-full" style={{ width: '45%' }}></div>
              </div>
            </div>
            
            <div>
              <div className="text-sm text-gray-400 mb-2">Leverage Usage</div>
              <div className="text-lg font-bold text-white">2.3x / 5x</div>
              <div className="w-full bg-gray-700 rounded-full h-1 mt-1">
                <div className="bg-yellow-500 h-1 rounded-full" style={{ width: '46%' }}></div>
              </div>
            </div>
            
            <div>
              <div className="text-sm text-gray-400 mb-2">Account Age</div>
              <div className="text-lg font-bold text-white">12 Days</div>
              <div className="text-xs text-gray-500">Paper trading</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
