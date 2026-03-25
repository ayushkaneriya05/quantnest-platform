/**
 * Equity & Drawdown Charts - visualize backtest performance
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { ChevronLeft, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { backtestApi } from '@/shared/services/backtestApi';
import { useNotifications } from '@/shared/hooks/useNotifications';

export default function EquityDrawdownCharts() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  
  const [run, setRun] = useState(null);
  const [equityCurve, setEquityCurve] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    try {
      const [runData, curveData, metricsData] = await Promise.all([
        backtestApi.getRun(id),
        backtestApi.getRunEquityCurve(id),
        backtestApi.getRunMetrics(id)
      ]);
      setRun(runData.data);
      setEquityCurve(curveData.data);
      setMetrics(metricsData.data);
    } catch (error) {
      notify.error('Failed to load chart data');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', { 
      style: 'currency', currency: 'INR', maximumFractionDigits: 0 
    }).format(val || 0);
  };

  // Calculate simple chart metrics
  const maxEquity = Math.max(...equityCurve.map(p => parseFloat(p.equity_value)), 0);
  const minEquity = Math.min(...equityCurve.map(p => parseFloat(p.equity_value)), 0);
  const maxDrawdown = Math.max(...equityCurve.map(p => parseFloat(p.drawdown_pct)), 0);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-xs text-gray-400">Starting Capital</p>
            <p className="text-xl font-bold text-white">
              {formatCurrency(run?.initial_capital)}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-xs text-gray-400">Final Capital</p>
            <p className={`text-xl font-bold ${metrics?.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatCurrency(metrics?.final_capital)}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-xs text-gray-400">Peak Value</p>
            <p className="text-xl font-bold text-green-400">{formatCurrency(maxEquity)}</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-xs text-gray-400">Max Drawdown</p>
            <p className="text-xl font-bold text-red-400">{maxDrawdown.toFixed(2)}%</p>
          </CardContent>
        </Card>
      </div>

      {/* Equity Curve */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-green-400" />
            Equity Curve
          </CardTitle>
        </CardHeader>
        <CardContent>
          {equityCurve.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-gray-500">
              No equity data available
            </div>
          ) : (
            <div className="h-64 flex items-end gap-px">
              {equityCurve.slice(-100).map((point, idx) => {
                const height = ((parseFloat(point.equity_value) - minEquity) / (maxEquity - minEquity)) * 100;
                return (
                  <div
                    key={idx}
                    className="flex-1 bg-green-500/50 hover:bg-green-400 transition-colors"
                    style={{ height: `${Math.max(height, 2)}%` }}
                    title={`${point.timestamp}: ${formatCurrency(point.equity_value)}`}
                  />
                );
              })}
            </div>
          )}
          <div className="flex justify-between text-xs text-gray-500 mt-2">
            <span>{run?.start_date}</span>
            <span>{run?.end_date}</span>
          </div>
        </CardContent>
      </Card>

      {/* Drawdown Chart */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <TrendingDown className="h-5 w-5 text-red-400" />
            Drawdown Chart
          </CardTitle>
        </CardHeader>
        <CardContent>
          {equityCurve.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-gray-500">
              No drawdown data available
            </div>
          ) : (
            <div className="h-48 flex items-start gap-px">
              {equityCurve.slice(-100).map((point, idx) => {
                const height = (parseFloat(point.drawdown_pct) / maxDrawdown) * 100;
                return (
                  <div
                    key={idx}
                    className="flex-1 bg-red-500/50 hover:bg-red-400 transition-colors"
                    style={{ height: `${Math.max(height, 1)}%` }}
                    title={`${point.timestamp}: -${parseFloat(point.drawdown_pct).toFixed(2)}%`}
                  />
                );
              })}
            </div>
          )}
          <div className="flex justify-between text-xs text-gray-500 mt-2">
            <span>{run?.start_date}</span>
            <span>{run?.end_date}</span>
          </div>
        </CardContent>
      </Card>

      {/* Monthly Returns (if applicable) */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Activity className="h-5 w-5 text-indigo-400" />
            Return Distribution
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-5 gap-2 text-center">
            <div className="p-3 bg-gray-800/50 rounded-lg">
              <p className="text-sm text-gray-400">CAGR</p>
              <p className="text-lg font-bold text-white">{(metrics?.cagr || 0).toFixed(2)}%</p>
            </div>
            <div className="p-3 bg-gray-800/50 rounded-lg">
              <p className="text-sm text-gray-400">Volatility</p>
              <p className="text-lg font-bold text-white">{(metrics?.volatility_pct || 0).toFixed(2)}%</p>
            </div>
            <div className="p-3 bg-gray-800/50 rounded-lg">
              <p className="text-sm text-gray-400">Sharpe</p>
              <p className="text-lg font-bold text-white">{(metrics?.sharpe_ratio || 0).toFixed(2)}</p>
            </div>
            <div className="p-3 bg-gray-800/50 rounded-lg">
              <p className="text-sm text-gray-400">Sortino</p>
              <p className="text-lg font-bold text-white">{(metrics?.sortino_ratio || 0).toFixed(2)}</p>
            </div>
            <div className="p-3 bg-gray-800/50 rounded-lg">
              <p className="text-sm text-gray-400">Calmar</p>
              <p className="text-lg font-bold text-white">{(metrics?.calmar_ratio || 0).toFixed(2)}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
