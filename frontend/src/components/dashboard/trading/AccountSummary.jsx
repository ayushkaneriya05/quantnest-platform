import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  DollarSign, 
  TrendingUp, 
  Wallet, 
  PieChart, 
  RefreshCw,
  AlertCircle,
  Activity
} from "lucide-react";
import api from "@/services/api";
import toast from "react-hot-toast";

const MetricCard = ({ icon: Icon, title, value, subtitle, variant = "default" }) => (
  <Card className="bg-slate-900/50 border-slate-700/50">
    <CardContent className="p-6">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-xl ${
          variant === 'positive' ? 'bg-emerald-500/20' :
          variant === 'negative' ? 'bg-red-500/20' :
          'bg-blue-500/20'
        }`}>
          <Icon className={`h-6 w-6 ${
            variant === 'positive' ? 'text-emerald-400' :
            variant === 'negative' ? 'text-red-400' :
            'text-blue-400'
          }`} />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-1">
            {title}
          </p>
          <p className="text-2xl font-bold text-white">{value}</p>
          {subtitle && (
            <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
      </div>
    </CardContent>
  </Card>
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-slate-900/50 rounded-lg animate-pulse" />
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Account Overview</h2>
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

      {/* Main Account Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          icon={Wallet}
          title="Account Balance"
          value={formatCurrency(accountData.balance)}
          subtitle="Available cash for trading"
          variant="default"
        />
        
        <MetricCard
          icon={PieChart}
          title="Portfolio Value"
          value={formatCurrency(portfolioSummary.total_current_value)}
          subtitle="Current market value"
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
          icon={Activity}
          title="Active Trading"
          value={`${portfolioSummary.positions_count} / ${portfolioSummary.open_orders_count}`}
          subtitle="Positions / Pending Orders"
          variant="default"
        />
      </div>

      {/* Summary Stats */}
      <Card className="bg-slate-900/50 border-slate-700/50">
        <CardHeader>
          <CardTitle className="text-lg text-white">Trading Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-white mb-1">
                {formatCurrency(portfolioSummary.total_investment)}
              </div>
              <div className="text-sm text-gray-400">Total Investment</div>
            </div>
            
            <div className="text-center">
              <div className={`text-2xl font-bold mb-1 ${
                portfolioSummary.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'
              }`}>
                {formatPercentage(returnPercentage)}
              </div>
              <div className="text-sm text-gray-400">Portfolio Return</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-white mb-1">
                {formatCurrency(accountData.buying_power || accountData.balance * 5)}
              </div>
              <div className="text-sm text-gray-400">Buying Power</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
