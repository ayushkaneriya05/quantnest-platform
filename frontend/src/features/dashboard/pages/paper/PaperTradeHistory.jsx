/**
 * Paper Trade History - view completed trades
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { 
  ChevronLeft, Search, TrendingUp, TrendingDown, BarChart2, Calendar
} from 'lucide-react';
import { paperApi } from '@/shared/services/paperApi';
import { useNotifications } from '@/shared/hooks/useNotifications';

export default function PaperTradeHistory() {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const [trades, setTrades] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [tradesData, analyticsData] = await Promise.all([
        paperApi.getTrades(),
        paperApi.getTradeAnalytics()
      ]);
      setTrades(tradesData.data);
      setAnalytics(analyticsData.data);
    } catch (error) {
      notify.error('Failed to load trades');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', { 
      style: 'currency', currency: 'INR', maximumFractionDigits: 0 
    }).format(val || 0);
  };

  const formatTime = (dateString) => {
    return new Date(dateString).toLocaleString('en-IN', {
      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
    });
  };

  const formatDuration = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  const filteredTrades = trades.filter(t => {
    if (filter === 'winning' && !t.is_winner) return false;
    if (filter === 'losing' && t.is_winner) return false;
    if (search && !t.instrument_symbol?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Analytics Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-white">{analytics?.total_trades || 0}</p>
            <p className="text-xs text-gray-400">Total Trades</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-purple-400">{(analytics?.win_rate || 0).toFixed(1)}%</p>
            <p className="text-xs text-gray-400">Win Rate</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className={`text-2xl font-bold ${analytics?.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatCurrency(analytics?.total_pnl)}
            </p>
            <p className="text-xs text-gray-400">Total P&L</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-white">{formatCurrency(analytics?.avg_pnl)}</p>
            <p className="text-xs text-gray-400">Avg P&L</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4 items-center">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search symbol..."
            className="pl-9 bg-gray-800 border-gray-700 text-white"
          />
        </div>
        <div className="flex gap-2">
          {['all', 'winning', 'losing'].map(f => (
            <Button
              key={f}
              variant={filter === f ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilter(f)}
              className={filter === f ? 'bg-indigo-600' : 'border-gray-700'}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </Button>
          ))}
        </div>
      </div>

      {/* Trades List */}
      {filteredTrades.length === 0 ? (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-12 text-center">
            <BarChart2 className="h-10 w-10 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-300">No trades found</h3>
            <p className="text-gray-500">Start trading to build your history</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredTrades.map((trade) => (
            <Card key={trade.id} className={`bg-gray-900/50 border-gray-800 ${trade.is_winner ? 'border-l-4 border-l-green-500' : 'border-l-4 border-l-red-500'}`}>
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`p-2 rounded-lg ${trade.is_winner ? 'bg-green-900/30' : 'bg-red-900/30'}`}>
                      {trade.is_winner ? 
                        <TrendingUp className="h-5 w-5 text-green-400" /> :
                        <TrendingDown className="h-5 w-5 text-red-400" />
                      }
                    </div>
                    <div>
                      <h4 className="text-white font-medium">{trade.instrument_symbol}</h4>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge className={trade.side === 'BUY' ? 'bg-green-600' : 'bg-red-600'}>
                          {trade.side}
                        </Badge>
                        <span className="text-xs text-gray-500">{trade.quantity} units</span>
                        {trade.strategy_name && (
                          <Badge variant="outline" className="border-gray-600 text-xs">{trade.strategy_name}</Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <p className="text-xs text-gray-500">Entry</p>
                      <p className="text-white">₹{parseFloat(trade.entry_price).toFixed(2)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-500">Exit</p>
                      <p className="text-white">₹{parseFloat(trade.exit_price).toFixed(2)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-500">Duration</p>
                      <p className="text-gray-300">{formatDuration(trade.holding_duration_seconds)}</p>
                    </div>
                    <div className="text-right min-w-24">
                      <p className={`text-lg font-bold ${trade.is_winner ? 'text-green-400' : 'text-red-400'}`}>
                        {trade.is_winner ? '+' : ''}{formatCurrency(trade.net_pnl)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {parseFloat(trade.pnl_pct).toFixed(2)}%
                      </p>
                    </div>
                  </div>
                </div>
                <div className="flex gap-4 mt-3 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    Entry: {formatTime(trade.entry_time)}
                  </span>
                  <span>Exit: {formatTime(trade.exit_time)}</span>
                  {trade.exit_reason && <Badge variant="outline" className="border-gray-700">{trade.exit_reason}</Badge>}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
