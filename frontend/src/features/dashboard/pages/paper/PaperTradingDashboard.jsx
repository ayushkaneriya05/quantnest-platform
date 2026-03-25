/**
 * Paper Trading Dashboard - main overview
 */
import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { 
  Play, Pause, RefreshCw, DollarSign, TrendingUp, TrendingDown,
  BarChart2, Activity, Layers, Settings
} from 'lucide-react';
import { paperApi } from '@/shared/services/paperApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useSetPageActions } from '@/shared/hooks/useSetPageActions';

export default function PaperTradingDashboard() {
  const { notify } = useNotifications();
  const [account, setAccount] = useState(null);
  const [positions, setPositions] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [accData, posData, analyticsData] = await Promise.all([
        paperApi.getActiveAccount(),
        paperApi.getPositions(),
        paperApi.getTradeAnalytics()
      ]);
      setAccount(accData.data);
      setPositions(posData.data);
      setAnalytics(analyticsData.data);
    } catch (error) {
      // Account might not exist yet
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const handleReset = async () => {
    if (!account || !confirm('Reset account? All positions and history will be cleared.')) return;
    try {
      await paperApi.resetAccount(account.id);
      notify.success('Account reset successfully');
      fetchData();
    } catch (error) {
      notify.error('Failed to reset account');
    }
  };

  // Set page actions in header
  const pageActions = useMemo(() => (
    <div className="flex gap-2">
      <Button variant="outline" size="sm" onClick={fetchData} className="border-gray-700">
        <RefreshCw className="h-4 w-4" />
      </Button>
      <Button variant="outline" size="sm" onClick={handleReset} className="border-gray-700 text-red-400">
        Reset
      </Button>
      <Link to="/dashboard/paper/orders">
        <Button className="bg-indigo-600 hover:bg-indigo-700" size="sm">
          <Play className="h-4 w-4 mr-1" />
          Place Order
        </Button>
      </Link>
    </div>
  ), [account]);

  useSetPageActions(account ? pageActions : null);

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', { 
      style: 'currency', currency: 'INR', maximumFractionDigits: 0 
    }).format(val || 0);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  if (!account || !account.id) {
    return (
      <div className="container-padding py-6 lg:py-8">
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-12 text-center">
            <Play className="h-12 w-12 text-indigo-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-white mb-2">Start Paper Trading</h2>
            <p className="text-gray-400 mb-6">Create a paper trading account to practice your strategies</p>
            <Link to="/dashboard/paper/accounts">
              <Button className="bg-indigo-600 hover:bg-indigo-700">
                Create Account
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const pnlColor = account.total_pnl >= 0 ? 'text-green-400' : 'text-red-400';
  const todayColor = account.today_pnl >= 0 ? 'text-green-400' : 'text-red-400';

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Account Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-500/20 rounded-lg">
                <DollarSign className="h-5 w-5 text-indigo-400" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Balance</p>
                <p className="text-lg font-bold text-white">{formatCurrency(account.current_balance)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <div className={`p-2 ${account.total_pnl >= 0 ? 'bg-green-500/20' : 'bg-red-500/20'} rounded-lg`}>
                {account.total_pnl >= 0 ? 
                  <TrendingUp className="h-5 w-5 text-green-400" /> : 
                  <TrendingDown className="h-5 w-5 text-red-400" />
                }
              </div>
              <div>
                <p className="text-xs text-gray-400">Total P&L</p>
                <p className={`text-lg font-bold ${pnlColor}`}>
                  {account.total_pnl >= 0 ? '+' : ''}{formatCurrency(account.total_pnl)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <div className={`p-2 ${account.today_pnl >= 0 ? 'bg-green-500/20' : 'bg-red-500/20'} rounded-lg`}>
                <Activity className="h-5 w-5 text-indigo-400" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Today's P&L</p>
                <p className={`text-lg font-bold ${todayColor}`}>
                  {account.today_pnl >= 0 ? '+' : ''}{formatCurrency(account.today_pnl)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <BarChart2 className="h-5 w-5 text-purple-400" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Win Rate</p>
                <p className="text-lg font-bold text-white">
                  {(analytics?.win_rate || 0).toFixed(1)}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Stats */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Open Positions */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-white">Open Positions</CardTitle>
            <Link to="/dashboard/paper/positions">
              <Badge variant="outline" className="border-gray-600 cursor-pointer">
                View All
              </Badge>
            </Link>
          </CardHeader>
          <CardContent>
            {positions.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No open positions</p>
            ) : (
              <div className="space-y-3">
                {positions.slice(0, 5).map((pos) => (
                  <div key={pos.id} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                    <div>
                      <p className="text-white font-medium">{pos.instrument_symbol}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge className={pos.side === 'BUY' ? 'bg-green-600' : 'bg-red-600'}>
                          {pos.side}
                        </Badge>
                        <span className="text-sm text-gray-400">{pos.quantity} @ ₹{parseFloat(pos.avg_price).toFixed(2)}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`font-medium ${parseFloat(pos.unrealized_pnl) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(pos.unrealized_pnl)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {parseFloat(pos.unrealized_pnl_pct).toFixed(2)}%
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Performance Stats */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Performance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-gray-800/50 rounded-lg text-center">
                <p className="text-2xl font-bold text-white">{analytics?.total_trades || 0}</p>
                <p className="text-xs text-gray-400">Total Trades</p>
              </div>
              <div className="p-3 bg-gray-800/50 rounded-lg text-center">
                <p className="text-2xl font-bold text-green-400">{analytics?.winning_trades || 0}</p>
                <p className="text-xs text-gray-400">Winning</p>
              </div>
              <div className="p-3 bg-gray-800/50 rounded-lg text-center">
                <p className="text-2xl font-bold text-red-400">{analytics?.losing_trades || 0}</p>
                <p className="text-xs text-gray-400">Losing</p>
              </div>
              <div className="p-3 bg-gray-800/50 rounded-lg text-center">
                <p className="text-2xl font-bold text-white">{formatCurrency(analytics?.avg_pnl)}</p>
                <p className="text-xs text-gray-400">Avg P&L</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-4 gap-4">
        <Link to="/dashboard/paper/orders">
          <Card className="bg-gray-900/50 border-gray-800 hover:border-indigo-600 transition-colors cursor-pointer">
            <CardContent className="py-4 text-center">
              <Play className="h-6 w-6 text-indigo-400 mx-auto mb-2" />
              <p className="text-white font-medium">Orders</p>
            </CardContent>
          </Card>
        </Link>
        <Link to="/dashboard/paper/positions">
          <Card className="bg-gray-900/50 border-gray-800 hover:border-indigo-600 transition-colors cursor-pointer">
            <CardContent className="py-4 text-center">
              <Layers className="h-6 w-6 text-indigo-400 mx-auto mb-2" />
              <p className="text-white font-medium">Positions</p>
            </CardContent>
          </Card>
        </Link>
        <Link to="/dashboard/paper/trades">
          <Card className="bg-gray-900/50 border-gray-800 hover:border-indigo-600 transition-colors cursor-pointer">
            <CardContent className="py-4 text-center">
              <BarChart2 className="h-6 w-6 text-indigo-400 mx-auto mb-2" />
              <p className="text-white font-medium">Trades</p>
            </CardContent>
          </Card>
        </Link>
        <Link to="/dashboard/paper/accounts">
          <Card className="bg-gray-900/50 border-gray-800 hover:border-indigo-600 transition-colors cursor-pointer">
            <CardContent className="py-4 text-center">
              <Settings className="h-6 w-6 text-indigo-400 mx-auto mb-2" />
              <p className="text-white font-medium">Accounts</p>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
