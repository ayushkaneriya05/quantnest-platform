/**
 * Backtest Trade List - all trades from a backtest run
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { 
  ChevronLeft, Search, TrendingUp, TrendingDown, Filter
} from 'lucide-react';
import { backtestApi } from '@/shared/services/backtestApi';
import { useNotifications } from '@/shared/hooks/useNotifications';

export default function BacktestTradeList() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  
  const [run, setRun] = useState(null);
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    try {
      const [runData, tradesData] = await Promise.all([
        backtestApi.getRun(id),
        backtestApi.getRunTrades(id)
      ]);
      setRun(runData.data);
      setTrades(tradesData.data);
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
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('en-IN', {
      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
    });
  };

  const filteredTrades = trades.filter(t => {
    if (filter === 'winning' && t.net_pnl <= 0) return false;
    if (filter === 'losing' && t.net_pnl >= 0) return false;
    if (search && !t.instrument_symbol?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const stats = {
    total: trades.length,
    winners: trades.filter(t => t.net_pnl > 0).length,
    losers: trades.filter(t => t.net_pnl < 0).length,
    totalPnl: trades.reduce((sum, t) => sum + parseFloat(t.net_pnl || 0), 0),
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-3 text-center">
            <p className="text-2xl font-bold text-white">{stats.total}</p>
            <p className="text-xs text-gray-400">Total Trades</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-3 text-center">
            <p className="text-2xl font-bold text-green-400">{stats.winners}</p>
            <p className="text-xs text-gray-400">Winners</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-3 text-center">
            <p className="text-2xl font-bold text-red-400">{stats.losers}</p>
            <p className="text-xs text-gray-400">Losers</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-3 text-center">
            <p className={`text-2xl font-bold ${stats.totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatCurrency(stats.totalPnl)}
            </p>
            <p className="text-xs text-gray-400">Total P&L</p>
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

      {/* Trade Table */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-800/50">
                <tr className="text-left text-xs text-gray-400">
                  <th className="p-3">Symbol</th>
                  <th className="p-3">Side</th>
                  <th className="p-3">Entry</th>
                  <th className="p-3">Exit</th>
                  <th className="p-3">Qty</th>
                  <th className="p-3">Entry Price</th>
                  <th className="p-3">Exit Price</th>
                  <th className="p-3">P&L</th>
                  <th className="p-3">Exit Reason</th>
                </tr>
              </thead>
              <tbody>
                {filteredTrades.map((trade, idx) => (
                  <tr key={trade.id} className="border-t border-gray-800 hover:bg-gray-800/30">
                    <td className="p-3 font-medium text-white">{trade.instrument_symbol}</td>
                    <td className="p-3">
                      <Badge className={trade.side === 'BUY' ? 'bg-green-600' : 'bg-red-600'}>
                        {trade.side}
                      </Badge>
                    </td>
                    <td className="p-3 text-gray-300 text-sm">{formatTime(trade.entry_time)}</td>
                    <td className="p-3 text-gray-300 text-sm">{formatTime(trade.exit_time)}</td>
                    <td className="p-3 text-white">{trade.quantity}</td>
                    <td className="p-3 text-white">₹{parseFloat(trade.entry_price).toFixed(2)}</td>
                    <td className="p-3 text-white">₹{parseFloat(trade.exit_price || 0).toFixed(2)}</td>
                    <td className={`p-3 font-medium ${parseFloat(trade.net_pnl) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatCurrency(trade.net_pnl)}
                    </td>
                    <td className="p-3 text-gray-400 text-sm">{trade.exit_reason || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
