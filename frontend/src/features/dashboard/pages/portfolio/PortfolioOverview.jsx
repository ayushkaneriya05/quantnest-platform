/**
 * Portfolio Overview — real-time dashboard powered by Portfolio + DailyPerformance APIs.
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import {
  Wallet, TrendingUp, TrendingDown,
  DollarSign, Activity, BarChart3, PieChart, ShieldAlert,
  Calendar, Loader2, AlertTriangle, Settings
} from 'lucide-react';
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from "@/shared/components/ui/dialog";
import { portfolioApi } from '@/shared/services/portfolioApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { usePageTitle } from '@/shared/hooks/use-page-title';

export default function PortfolioOverview() {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const [portfolio, setPortfolio] = useState(null);
  const [performance, setPerformance] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editOpen, setEditOpen] = useState(false);
  const [editForm, setEditForm] = useState({ name: '', initial_capital: 0 });

  usePageTitle({
    title: 'Portfolio Overview',
    subtitle: 'Track your capital, allocations, and performance',
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [portRes, perfRes] = await Promise.all([
        portfolioApi.getMyPortfolio(),
        portfolioApi.getDailyPerformance(),
      ]);
      setPortfolio(portRes.data);
      setPerformance(Array.isArray(perfRes.data) ? perfRes.data : (perfRes.data?.results || []));
    } catch (err) {
      notify.error('Failed to load portfolio data');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (val) => {
    if (val == null) return '₹0';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const formatPct = (val) => {
    if (val == null) return '0%';
    const num = parseFloat(val);
    return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
  };

  // Compute stats from DailyPerformance data
  const perfStats = useMemo(() => {
    if (!performance.length) return { weekPnl: 0, monthPnl: 0, bestDay: null, worstDay: null, avgWinRate: 0, totalFees: 0, totalTradesToday: 0, avgPnlPct: 0 };

    const sorted = [...performance].sort((a, b) => new Date(b.date) - new Date(a.date));
    const last7 = sorted.slice(0, 7);
    const last30 = sorted.slice(0, 30);

    const weekPnl = last7.reduce((s, d) => s + parseFloat(d.total_pnl || 0), 0);
    const monthPnl = last30.reduce((s, d) => s + parseFloat(d.total_pnl || 0), 0);

    let bestDay = sorted[0], worstDay = sorted[0];
    sorted.forEach(d => {
      if (parseFloat(d.total_pnl) > parseFloat(bestDay.total_pnl)) bestDay = d;
      if (parseFloat(d.total_pnl) < parseFloat(worstDay.total_pnl)) worstDay = d;
    });

    const totalTrades = last30.reduce((s, d) => s + (d.winning_trades || 0) + (d.losing_trades || 0), 0);
    const totalWins = last30.reduce((s, d) => s + (d.winning_trades || 0), 0);
    const avgWinRate = totalTrades > 0 ? (totalWins / totalTrades) * 100 : 0;

    const totalFees = last30.reduce(
      (s, d) => s + parseFloat(d.brokerage_paid || 0) + parseFloat(d.taxes_paid || 0),
      0
    );

    const totalTradesToday = last30.reduce((s, d) => s + (d.trades_count || 0), 0);
    const avgPnlPct = last30.length > 0
      ? last30.reduce((s, d) => s + parseFloat(d.pnl_percentage || 0), 0) / last30.length
      : 0;

    return { weekPnl, monthPnl, bestDay, worstDay, avgWinRate, totalFees, totalTradesToday, avgPnlPct };
  }, [performance]);

  // P&L bar data (last 14 days)
  const pnlBars = useMemo(() => {
    if (!performance.length) return [];
    const sorted = [...performance].sort((a, b) => new Date(a.date) - new Date(b.date));
    const last14 = sorted.slice(-14);
    const maxAbs = Math.max(...last14.map(d => Math.abs(parseFloat(d.total_pnl || 0))), 1);
    return last14.map(d => ({
      date: d.date,
      pnl: parseFloat(d.total_pnl || 0),
      pct: (Math.abs(parseFloat(d.total_pnl || 0)) / maxAbs) * 100,
    }));
  }, [performance]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (!portfolio) {
    return (
      <div className="container-padding py-6 lg:py-8">
        <Card className="bg-gray-900/50 border-gray-800 max-w-xl mx-auto text-center p-8">
          <AlertTriangle className="h-10 w-10 text-amber-400 mx-auto mb-4" />
          <p className="text-gray-300">Portfolio not found. Please set up your portfolio.</p>
        </Card>
      </div>
    );
  }

  const totalValue = parseFloat(portfolio.total_value || 0);
  const currentCapital = parseFloat(portfolio.current_capital || 0);
  const investedValue = parseFloat(portfolio.invested_value || 0);
  const todayPnl = parseFloat(portfolio.today_pnl || 0);
  const realizedPnl = parseFloat(portfolio.realized_pnl || 0);
  const unrealizedPnl = parseFloat(portfolio.unrealized_pnl || 0);
  const drawdown = parseFloat(portfolio.current_drawdown || 0);
  const initialCapital = parseFloat(portfolio.initial_capital || 0);
  const totalReturn = initialCapital > 0 ? ((totalValue - initialCapital) / initialCapital) * 100 : 0;

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">

      {/* Portfolio Settings Edit Button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">{portfolio.name}</h2>
          <p className="text-xs text-gray-500">Started with {formatCurrency(initialCapital)}</p>
        </div>
        <Button
          variant="ghost" size="sm"
          className="text-gray-400 hover:text-white"
          onClick={() => {
            setEditForm({ name: portfolio.name, initial_capital: initialCapital });
            setEditOpen(true);
          }}
        >
          <Settings className="h-4 w-4 mr-1" /> Edit
        </Button>
      </div>
      
      {/* ── KPI Row ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Value', value: formatCurrency(totalValue), icon: Wallet, color: 'indigo', sub: `Initial: ${formatCurrency(initialCapital)}` },
          { label: 'Available Cash', value: formatCurrency(currentCapital), icon: DollarSign, color: 'green', sub: `Invested: ${formatCurrency(investedValue)}` },
          { label: "Today's P&L", value: formatCurrency(todayPnl), icon: todayPnl >= 0 ? TrendingUp : TrendingDown, color: todayPnl >= 0 ? 'emerald' : 'red', sub: `${portfolio.today_trades || 0} trades today`, pnl: true },
          { label: 'Total Return', value: formatPct(totalReturn), icon: Activity, color: totalReturn >= 0 ? 'emerald' : 'red', sub: `Peak: ${formatCurrency(portfolio.peak_value || 0)}`, pnl: true },
        ].map((kpi, i) => {
          const Icon = kpi.icon;
          return (
            <Card key={i} className="bg-gray-900/50 border-gray-800">
              <CardContent className="py-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 bg-${kpi.color}-500/20 rounded-lg`}>
                    <Icon className={`h-5 w-5 text-${kpi.color}-400`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-gray-400 truncate">{kpi.label}</p>
                    <p className={`text-lg font-bold truncate ${kpi.pnl ? (parseFloat(String(kpi.value).replace(/[^0-9.-]/g, '')) >= 0 ? 'text-emerald-400' : 'text-red-400') : 'text-white'}`}>
                      {kpi.value}
                    </p>
                    <p className="text-[10px] text-gray-500 truncate">{kpi.sub}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* ── P&L + Drawdown Row ── */}
      <div className="grid md:grid-cols-3 gap-6">

        {/* P&L Breakdown */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-white text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-indigo-400" />
              P&L Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              { label: 'Realized P&L', value: realizedPnl },
              { label: 'Unrealized P&L', value: unrealizedPnl },
              { label: 'Week P&L', value: perfStats.weekPnl },
              { label: 'Month P&L', value: perfStats.monthPnl },
            ].map((item, i) => (
              <div key={i} className="flex justify-between items-center">
                <span className="text-sm text-gray-400">{item.label}</span>
                <span className={`text-sm font-medium ${item.value >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {item.value >= 0 ? '+' : ''}{formatCurrency(item.value)}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Drawdown Gauge */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-white text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-400" />
              Drawdown
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center py-4">
            <div className="relative w-28 h-28">
              <svg className="w-28 h-28 -rotate-90" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="50" stroke="#1f2937" strokeWidth="10" fill="none" />
                <circle
                  cx="60" cy="60" r="50"
                  stroke={drawdown > 10 ? '#ef4444' : drawdown > 5 ? '#f59e0b' : '#10b981'}
                  strokeWidth="10" fill="none"
                  strokeDasharray={`${Math.min(drawdown, 100) * 3.14} 314.16`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className={`text-2xl font-bold ${drawdown > 10 ? 'text-red-400' : drawdown > 5 ? 'text-amber-400' : 'text-emerald-400'}`}>
                  {drawdown.toFixed(1)}%
                </span>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">Current Drawdown from Peak</p>
            {portfolio.peak_date && (
              <p className="text-[10px] text-gray-600 mt-1">Peak on {portfolio.peak_date}</p>
            )}
          </CardContent>
        </Card>

        {/* Monthly Stats */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-white text-sm flex items-center gap-2">
              <Calendar className="h-4 w-4 text-purple-400" />
              30-Day Stats
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              { label: 'Win Rate', value: `${perfStats.avgWinRate.toFixed(1)}%`, color: perfStats.avgWinRate >= 50 ? 'text-emerald-400' : 'text-amber-400' },
              { label: 'Avg Daily P&L %', value: `${perfStats.avgPnlPct >= 0 ? '+' : ''}${perfStats.avgPnlPct.toFixed(2)}%`, color: perfStats.avgPnlPct >= 0 ? 'text-emerald-400' : 'text-red-400' },
              { label: 'Total Trades', value: perfStats.totalTradesToday.toString(), color: 'text-white' },
              { label: 'Best Day', value: perfStats.bestDay ? formatCurrency(perfStats.bestDay.total_pnl) : '—', color: 'text-emerald-400' },
              { label: 'Worst Day', value: perfStats.worstDay ? formatCurrency(perfStats.worstDay.total_pnl) : '—', color: 'text-red-400' },
              { label: 'Total Fees', value: formatCurrency(perfStats.totalFees), color: 'text-gray-300' },
            ].map((item, i) => (
              <div key={i} className="flex justify-between items-center">
                <span className="text-sm text-gray-400">{item.label}</span>
                <span className={`text-sm font-medium ${item.color}`}>{item.value}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* ── Daily P&L Chart (last 14 days) ── */}
      {pnlBars.length > 0 && (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-white text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-indigo-400" />
              Daily P&L — Last 14 Days
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-1 h-32">
              {pnlBars.map((bar, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
                  <div
                    className={`w-full rounded-sm transition-all ${bar.pnl >= 0 ? 'bg-emerald-500/80' : 'bg-red-500/80'}`}
                    style={{ height: `${Math.max(bar.pct, 4)}%` }}
                  />
                  {/* Tooltip */}
                  <div className="absolute bottom-full mb-1 hidden group-hover:block bg-gray-800 text-xs text-white px-2 py-1 rounded shadow-lg whitespace-nowrap z-10">
                    {bar.date}: {bar.pnl >= 0 ? '+' : ''}{formatCurrency(bar.pnl)}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-between mt-2">
              <span className="text-[10px] text-gray-600">{pnlBars[0]?.date}</span>
              <span className="text-[10px] text-gray-600">{pnlBars[pnlBars.length - 1]?.date}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Quick Links ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Allocations', path: '/dashboard/portfolio/allocations', icon: PieChart, color: 'indigo' },
          { label: 'Transactions', path: '/dashboard/portfolio/transactions', icon: DollarSign, color: 'green' },
          { label: 'Exposure', path: '/dashboard/portfolio/exposure', icon: Activity, color: 'purple' },
          { label: 'Risk Management', path: '/dashboard/portfolio/risk', icon: ShieldAlert, color: 'orange' },
        ].map((link, i) => {
          const Icon = link.icon;
          return (
            <button
              key={i}
              onClick={() => navigate(link.path)}
              className={`flex items-center gap-3 p-3 bg-gray-900/50 border border-gray-800 rounded-lg hover:bg-gray-800/70 transition-all text-left`}
            >
              <div className={`p-2 bg-${link.color}-500/20 rounded-lg`}>
                <Icon className={`h-4 w-4 text-${link.color}-400`} />
              </div>
              <span className="text-sm text-gray-300 font-medium">{link.label}</span>
            </button>
          );
        })}
      </div>

      {/* Portfolio Edit Modal */}
      <Dialog open={editOpen} onOpenChange={(open) => { if (!open) setEditOpen(false); }}>
        <DialogContent className="bg-gray-900 border-gray-800 text-white sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Portfolio Settings</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-gray-400">Portfolio Name</Label>
              <Input
                value={editForm.name}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                className="bg-gray-800 border-gray-700 text-white"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-gray-400">Initial Capital (₹)</Label>
              <Input
                type="number"
                value={editForm.initial_capital}
                onChange={(e) => setEditForm({ ...editForm, initial_capital: parseFloat(e.target.value) || 0 })}
                className="bg-gray-800 border-gray-700 text-white"
              />
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setEditOpen(false)} className="border-gray-700">
              Cancel
            </Button>
            <Button
              className="bg-indigo-600 hover:bg-indigo-700"
              onClick={async () => {
                try {
                  await portfolioApi.updatePortfolio(portfolio.id, editForm);
                  setPortfolio({ ...portfolio, ...editForm });
                  setEditOpen(false);
                  notify.success('Portfolio updated');
                } catch (err) {
                  notify.error('Failed to update');
                }
              }}
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
