import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  DollarSign, 
  TrendingUp, 
  TrendingDown, 
  Wallet, 
  PieChart, 
  BarChart3,
  Zap,
  Shield,
  RefreshCw,
  AlertCircle,
  Activity,
  Target
} from "lucide-react";
import { useWebSocketContext } from "@/contexts/websocket-context";
import api from "@/services/api";
import toast from "react-hot-toast";

const MetricCard = ({ icon: Icon, title, value, subtitle, change, variant = "default", className = "" }) => (
  <Card className={`bg-slate-900/50 border-slate-700/50 hover:border-slate-600/60 transition-all duration-300 ${className}`}>
    <CardContent className="p-4 lg:p-6">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
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
            <p className="text-lg lg:text-xl font-bold text-white truncate">{value}</p>
            {subtitle && (
              <p className="text-xs lg:text-sm text-gray-500 truncate">{subtitle}</p>
            )}
          </div>
        </div>
        {change && (
          <div className={`flex items-center gap-1 text-xs lg:text-sm ${
            change.isPositive ? 'text-emerald-400' : 'text-red-400'
          }`}>
            {change.isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            <span>{change.value}</span>
          </div>
        )}
      </div>
    </CardContent>
  </Card>
);

const PerformanceChart = ({ data, title }) => (
  <Card className="bg-slate-900/50 border-slate-700/50">
    <CardHeader className="pb-3">
      <CardTitle className="text-sm text-gray-400 uppercase tracking-wider">{title}</CardTitle>
    </CardHeader>
    <CardContent>
      <div className="space-y-3">
        {data.map((item, index) => (
          <div key={index} className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-2 h-2 rounded-full ${item.color}`}></div>
              <span className="text-sm text-gray-300">{item.label}</span>
            </div>
            <div className="text-right">
              <span className="text-sm font-medium text-white">{item.value}</span>
              <span className="text-xs text-gray-500 ml-2">{item.percentage}</span>
            </div>
          </div>
        ))}
      </div>
    </CardContent>
  </Card>
);

export default function AccountSummary() {
  const [accountData, setAccountData] = useState(null);
  const [portfolioSummary, setPortfolioSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const { isConnected, connectionStatus } = useWebSocketContext();

  const fetchAccountData = async () => {
    try {
      const [accountRes, portfolioRes] = await Promise.all([
        api.get('/trading/account/'),
        api.get('/trading/portfolio/summary/')
      ]);

      setAccountData(accountRes.data);
      setPortfolioSummary(portfolioRes.data);
      setLastUpdated(new Date());
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
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount || 0);
  };

  const formatPercentage = (value) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
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
          <Button onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  const totalPnlVariant = portfolioSummary.total_pnl >= 0 ? 'positive' : 'negative';
  const returnPercentage = portfolioSummary.return_percentage || 0;

  // Mock performance data for demonstration
  const sectorData = [
    { label: 'Technology', value: '₹3,45,000', percentage: '35%', color: 'bg-blue-500' },
    { label: 'Banking', value: '₹2,10,000', percentage: '21%', color: 'bg-green-500' },
    { label: 'Healthcare', value: '₹1,80,000', percentage: '18%', color: 'bg-purple-500' },
    { label: 'Energy', value: '₹1,35,000', percentage: '13.5%', color: 'bg-yellow-500' },
    { label: 'Others', value: '₹1,25,000', percentage: '12.5%', color: 'bg-gray-500' },
  ];

  const topPerformers = [
    { label: 'TCS', value: '+12.5%', percentage: '₹45,000', color: 'bg-emerald-500' },
    { label: 'RELIANCE', value: '+8.3%', percentage: '₹32,000', color: 'bg-emerald-500' },
    { label: 'INFY', value: '+6.7%', percentage: '₹28,000', color: 'bg-emerald-500' },
    { label: 'HDFCBANK', value: '-2.1%', percentage: '-₹8,500', color: 'bg-red-500' },
  ];

  return (
    <div className="space-y-6">
      {/* Header with Refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Account Summary</h2>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant={isConnected ? "default" : "destructive"} className="text-xs">
              {isConnected ? "Live" : "Offline"}
            </Badge>
            {lastUpdated && (
              <span className="text-xs text-gray-500">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>
        <Button 
          onClick={handleRefresh} 
          disabled={isRefreshing}
          variant="outline"
          size="sm"
          className="border-gray-700 text-gray-300 hover:bg-gray-800"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Main Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
        <MetricCard
          icon={Wallet}
          title="Account Balance"
          value={formatCurrency(accountData.balance)}
          subtitle="Available Cash"
          variant="default"
        />
        <MetricCard
          icon={PieChart}
          title="Portfolio Value"
          value={formatCurrency(portfolioSummary.total_current_value)}
          subtitle="Total Holdings"
          variant="default"
        />
        <MetricCard
          icon={TrendingUp}
          title="Total P&L"
          value={formatCurrency(portfolioSummary.total_pnl)}
          subtitle={formatPercentage(returnPercentage)}
          variant={totalPnlVariant}
          change={{
            value: formatPercentage(returnPercentage),
            isPositive: portfolioSummary.total_pnl >= 0
          }}
        />
        <MetricCard
          icon={Zap}
          title="Buying Power"
          value={formatCurrency(accountData.buying_power)}
          subtitle="Available for Trading"
          variant="default"
        />
      </div>

      {/* Additional Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
        <MetricCard
          icon={Shield}
          title="Margin Used"
          value={formatCurrency(accountData.margin_used)}
          subtitle={`${((accountData.margin_used / accountData.balance) * 100).toFixed(1)}% of balance`}
          variant={accountData.margin_used > accountData.balance * 0.7 ? 'warning' : 'default'}
        />
        <MetricCard
          icon={Activity}
          title="Active Positions"
          value={portfolioSummary.positions_count.toString()}
          subtitle={`${portfolioSummary.open_orders_count} pending orders`}
          variant="default"
        />
        <MetricCard
          icon={Target}
          title="Total Investment"
          value={formatCurrency(portfolioSummary.total_investment)}
          subtitle="Cost basis"
          variant="default"
        />
        <MetricCard
          icon={BarChart3}
          title="Day's P&L"
          value="₹+8,450"
          subtitle="+0.85% today"
          variant="positive"
          change={{
            value: "+0.85%",
            isPositive: true
          }}
        />
      </div>

      {/* Performance Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
        <PerformanceChart 
          data={sectorData}
          title="Portfolio by Sector"
        />
        <PerformanceChart 
          data={topPerformers}
          title="Top Performers"
        />
      </div>

      {/* Risk Metrics */}
      <Card className="bg-slate-900/50 border-slate-700/50">
        <CardHeader>
          <CardTitle className="text-sm text-gray-400 uppercase tracking-wider flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Risk Metrics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-slate-800/30 rounded-lg">
              <div className="text-2xl font-bold text-white mb-1">
                {((accountData.margin_used / accountData.balance) * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-400 uppercase tracking-wider">Margin Usage</div>
            </div>
            <div className="text-center p-4 bg-slate-800/30 rounded-lg">
              <div className="text-2xl font-bold text-white mb-1">
                {portfolioSummary.positions_count > 0 ? (portfolioSummary.total_current_value / portfolioSummary.positions_count / 1000).toFixed(0) + 'K' : '0'}
              </div>
              <div className="text-xs text-gray-400 uppercase tracking-wider">Avg Position Size</div>
            </div>
            <div className="text-center p-4 bg-slate-800/30 rounded-lg">
              <div className="text-2xl font-bold text-emerald-400 mb-1">
                {((portfolioSummary.total_current_value / (portfolioSummary.total_investment || 1)) * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-400 uppercase tracking-wider">Portfolio Health</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
