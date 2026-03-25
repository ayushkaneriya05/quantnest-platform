/**
 * Backtest Results - view backtest metrics and summary
 */
import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { 
  TrendingUp, TrendingDown, BarChart2, Activity, 
  ChevronLeft, RefreshCw, ListIcon, LineChart, Dices
} from 'lucide-react';
import { backtestApi } from '@/shared/services/backtestApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useSetPageActions } from '@/shared/hooks/useSetPageActions';

const STATUS_STYLES = {
  PENDING: { bg: 'bg-yellow-600', text: 'Pending' },
  RUNNING: { bg: 'bg-blue-600', text: 'Running' },
  COMPLETED: { bg: 'bg-green-600', text: 'Completed' },
  FAILED: { bg: 'bg-red-600', text: 'Failed' },
  CANCELLED: { bg: 'bg-gray-600', text: 'Cancelled' },
};

export default function BacktestResults() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  
  const [run, setRun] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [runData, metricsData] = await Promise.all([
        backtestApi.getRun(id),
        backtestApi.getRunMetrics(id)
      ]);
      setRun(runData.data);
      setMetrics(metricsData.data);
    } catch (error) {
      notify.error('Failed to load backtest');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => {
      if (run?.status === 'RUNNING') fetchData();
    }, 3000);
    return () => clearInterval(interval);
  }, [id, run?.status]);

  // Set page actions in header
  const pageActions = useMemo(() => (
    <div className="flex gap-2">
      <Button 
        variant="outline" 
        size="sm"
        onClick={fetchData}
        className="border-gray-700"
      >
        <RefreshCw className="h-4 w-4" />
      </Button>
      <Link to={`/dashboard/backtest/trades/${id}`}>
        <Button variant="outline" size="sm" className="border-gray-700">
          <ListIcon className="h-4 w-4 mr-1" />
          Trades
        </Button>
      </Link>
      <Link to={`/dashboard/backtest/charts/${id}`}>
        <Button variant="outline" size="sm" className="border-gray-700">
          <LineChart className="h-4 w-4 mr-1" />
          Charts
        </Button>
      </Link>
    </div>
  ), [id]);

  useSetPageActions(pageActions);

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', { 
      style: 'currency', currency: 'INR', maximumFractionDigits: 0 
    }).format(val || 0);
  };

  const formatPercent = (val) => `${(val || 0).toFixed(2)}%`;
  const formatRatio = (val) => (val || 0).toFixed(2);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  const status = STATUS_STYLES[run?.status] || STATUS_STYLES.PENDING;

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Progress (if running) */}
      {run?.status === 'RUNNING' && (
        <Card className="bg-blue-900/20 border-blue-800/50">
          <CardContent className="py-4">
            <div className="flex items-center gap-4">
              <div className="animate-spin rounded-full h-6 w-6 border-2 border-blue-400 border-t-transparent" />
              <div className="flex-1">
                <p className="text-white">Backtest in progress...</p>
                <div className="h-2 bg-gray-700 rounded-full mt-2 overflow-hidden">
                  <div 
                    className="h-full bg-blue-500 rounded-full transition-all"
                    style={{ width: `${run.progress_pct || 0}%` }}
                  />
                </div>
              </div>
              <span className="text-blue-400 font-medium">{run.progress_pct || 0}%</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4">
            <p className="text-xs text-gray-400">Final Capital</p>
            <p className={`text-xl font-bold ${metrics?.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatCurrency(metrics?.final_capital)}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4">
            <p className="text-xs text-gray-400">Total Return</p>
            <p className={`text-xl font-bold ${metrics?.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {metrics?.total_return_pct >= 0 ? '+' : ''}{formatPercent(metrics?.total_return_pct)}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4">
            <p className="text-xs text-gray-400">Sharpe Ratio</p>
            <p className="text-xl font-bold text-white">{formatRatio(metrics?.sharpe_ratio)}</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4">
            <p className="text-xs text-gray-400">Max Drawdown</p>
            <p className="text-xl font-bold text-red-400">{formatPercent(metrics?.max_drawdown_pct)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Metrics Grid */}
      <div className="grid md:grid-cols-3 gap-6">
        {/* Trade Stats */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Trade Statistics</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-400">Total Trades</span>
              <span className="text-white font-medium">{metrics?.total_trades || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Winning</span>
              <span className="text-green-400">{metrics?.winning_trades || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Losing</span>
              <span className="text-red-400">{metrics?.losing_trades || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Win Rate</span>
              <span className="text-white font-medium">{formatPercent(metrics?.win_rate)}</span>
            </div>
          </CardContent>
        </Card>

        {/* P&L Stats */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">P&L Statistics</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-400">Avg Win</span>
              <span className="text-green-400">{formatCurrency(metrics?.avg_win)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Avg Loss</span>
              <span className="text-red-400">{formatCurrency(metrics?.avg_loss)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Largest Win</span>
              <span className="text-green-400">{formatCurrency(metrics?.largest_win)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Largest Loss</span>
              <span className="text-red-400">{formatCurrency(metrics?.largest_loss)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Risk Metrics */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Risk Metrics</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-400">Profit Factor</span>
              <span className="text-white font-medium">{formatRatio(metrics?.profit_factor)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Sortino Ratio</span>
              <span className="text-white">{formatRatio(metrics?.sortino_ratio)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Calmar Ratio</span>
              <span className="text-white">{formatRatio(metrics?.calmar_ratio)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Recovery Factor</span>
              <span className="text-white">{formatRatio(metrics?.recovery_factor)}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
