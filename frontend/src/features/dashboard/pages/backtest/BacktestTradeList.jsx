import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  CardContent,
} from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import {
  ChevronLeft,
  ChevronRight,
  Search,
  TrendingUp,
  TrendingDown,
  Filter,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Download,
  FileText,
  DollarSign,
  Activity
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/shared/components/ui/dialog";
import { backtestApi } from "@/shared/services/backtestApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { GlobalLoader } from '@/shared/components/ui/global-loader';

export default function BacktestTradeList() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();

  const [run, setRun] = useState(null);
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [instrumentFilter, setInstrumentFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [selectedTrade, setSelectedTrade] = useState(null);
  const PAGE_SIZE = 50;

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    try {
      const [runData, tradesData] = await Promise.all([
        backtestApi.getRun(id),
        backtestApi.getRunTrades(id),
      ]);
      setRun(runData.data);
      setTrades(tradesData.data);
    } catch (error) {
      notify.error("Failed to load trades");
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (val) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(val || 0);
  };

  const formatTime = (dateString) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleString("en-IN", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const filteredTrades = trades.filter((t) => {
    if (filter === "winning" && t.net_pnl <= 0) return false;
    if (filter === "losing" && t.net_pnl >= 0) return false;
    if (instrumentFilter !== "all" && t.instrument_symbol !== instrumentFilter) return false;
    if (
      search &&
      !t.instrument_symbol?.toLowerCase().includes(search.toLowerCase())
    )
      return false;
    return true;
  });

  const stats = {
    total: trades.length,
    winners: trades.filter((t) => t.net_pnl > 0).length,
    losers: trades.filter((t) => t.net_pnl < 0).length,
    totalPnl: trades.reduce((sum, t) => sum + parseFloat(t.net_pnl || 0), 0),
  };

  // Paginated slice
  const totalPages = Math.max(1, Math.ceil(filteredTrades.length / PAGE_SIZE));
  const paginatedTrades = filteredTrades.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE
  );

  // Reset page on filter/search change
  useEffect(() => {
    setPage(1);
  }, [filter, search, instrumentFilter]);

  const instrumentOptions = ["all", ...new Set(trades.map((trade) => trade.instrument_symbol).filter(Boolean))];

  useSetPageActions(
    <Button
      variant="outline"
      size="sm"
      onClick={() => navigate(`/dashboard/backtest/results/${id}`)}
      className="bg-gray-900 border-gray-800 hover:bg-gray-800 h-9"
    >
      <ChevronLeft className="h-4 w-4 mr-2" />
      Back to Results
    </Button>
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <GlobalLoader />
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-6 lg:py-8 space-y-6">
      {/* Stats Dashboard */}

      {/* Stats Dashboard */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          {
            label: "Total Trades",
            value: stats.total,
            icon: Filter,
            color: "text-white",
          },
          {
            label: "Winners",
            value: stats.winners,
            icon: TrendingUp,
            color: "text-green-400",
          },
          {
            label: "Losers",
            value: stats.losers,
            icon: TrendingDown,
            color: "text-red-400",
          },
          {
            label: "Total P&L",
            value: formatCurrency(stats.totalPnl),
            icon: TrendingUp,
            color: stats.totalPnl >= 0 ? "text-green-400" : "text-red-400",
          },
        ].map((stat, i) => (
          <Card key={i} className="bg-gray-900/50 border-gray-800">
            <CardContent className="p-4 flex items-center gap-4">
              <div className={`p-2 rounded-lg bg-gray-800 ${stat.color}`}>
                <stat.icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">
                  {stat.label}
                </p>
                <p className={`text-xl font-bold ${stat.color}`}>
                  {stat.value}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters & Search */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-center bg-gray-900/40 p-4 rounded-xl border border-gray-800">
        <div className="relative w-full md:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search symbol..."
            className="pl-9 bg-gray-800/50 border-gray-700 text-white focus:ring-indigo-500"
          />
        </div>
        <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
          <Select
            value={instrumentFilter}
            onValueChange={setInstrumentFilter}
          >
            <SelectTrigger className="w-[180px] bg-gray-800 border-gray-700 text-white text-sm focus:ring-0">
              <SelectValue placeholder="All Instruments" />
            </SelectTrigger>
            <SelectContent className="bg-gray-900 border-gray-800 text-white">
              {instrumentOptions.map((option) => (
                <SelectItem key={option} value={option} className="focus:bg-gray-800 focus:text-white">
                  {option === "all" ? "All Instruments" : option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="flex bg-gray-800 p-1 rounded-lg">
            {["all", "winning", "losing"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                  filter === f
                    ? "bg-indigo-600 text-white shadow-lg"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Trade Table */}
      <Card className="bg-gray-900/50 border-gray-800 overflow-hidden">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-gray-800/50 border-b border-gray-700 text-xs text-gray-400 uppercase tracking-wider">
                  <th className="px-6 py-4 font-semibold">Instrument</th>
                  <th className="px-6 py-4 font-semibold">Side</th>
                  <th className="px-6 py-4 font-semibold">Timing</th>
                  <th className="px-6 py-4 font-semibold text-right">Qty</th>
                  <th className="px-6 py-4 font-semibold text-right">
                    Entry/Exit Price
                  </th>
                  <th className="px-6 py-4 font-semibold text-right">
                    MAE / MFE (₹)
                  </th>
                  <th className="px-6 py-4 font-semibold text-right">
                    Net P&L
                  </th>
                  <th className="px-6 py-4 font-semibold">Exit Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {paginatedTrades.map((trade) => (
                  <tr
                    key={trade.id}
                    onClick={() => setSelectedTrade(trade)}
                    className="hover:bg-gray-800/30 transition-colors group cursor-pointer"
                  >
                    <td className="px-6 py-4">
                      <div className="text-sm font-bold text-white">
                        {trade.instrument_symbol}
                      </div>
                      <div className="text-[10px] text-gray-500 flex items-center gap-1 mt-0.5 uppercase">
                        <Clock className="h-3 w-3" />
                        {trade.holding_duration_minutes}m duration
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          trade.side === "BUY"
                            ? "bg-green-500/10 text-green-400"
                            : "bg-red-500/10 text-red-400"
                        }`}
                      >
                        {trade.side === "BUY" ? (
                          <ArrowUpRight className="h-3 w-3" />
                        ) : (
                          <ArrowDownRight className="h-3 w-3" />
                        )}
                        {trade.side}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-[11px] text-gray-300">
                        IN: {formatTime(trade.entry_time)}
                      </div>
                      <div className="text-[11px] text-gray-500">
                        OUT: {formatTime(trade.exit_time)}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="text-sm font-medium text-gray-200">
                        {trade.quantity}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="text-sm text-white">
                        ₹{parseFloat(trade.entry_price).toFixed(2)}
                      </div>
                      <div className="text-xs text-gray-500">
                        ₹{parseFloat(trade.exit_price || 0).toFixed(2)}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="text-[11px] text-red-500 font-medium">
                        -{formatCurrency(trade.mae)}
                      </div>
                      <div className="text-[11px] text-green-500 font-medium">
                        +{formatCurrency(trade.mfe)}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div
                        className={`text-sm font-bold ${parseFloat(trade.net_pnl) >= 0 ? "text-green-400" : "text-red-400"}`}
                      >
                        {formatCurrency(trade.net_pnl)}
                      </div>
                      <div
                        className={`text-[10px] opacity-70 ${parseFloat(trade.net_pnl) >= 0 ? "text-green-400" : "text-red-400"}`}
                      >
                        {parseFloat(trade.pnl_pct).toFixed(2)}%
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <Badge
                        variant="outline"
                        className="text-[10px] border-gray-700 text-gray-400 font-normal"
                      >
                        {trade.exit_reason || "Signal"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredTrades.length === 0 && (
              <div className="p-8 text-center text-gray-500">
                No trades found matching your filters.
              </div>
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-gray-800">
              <span className="text-xs text-gray-500">
                Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filteredTrades.length)} of {filteredTrades.length} trades
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="border-gray-700 bg-gray-900 h-8 px-3"
                >
                  <ChevronLeft className="h-3.5 w-3.5 mr-1" />
                  Prev
                </Button>
                <span className="text-xs text-gray-400 font-medium tabular-nums">
                  {page} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                  className="border-gray-700 bg-gray-900 h-8 px-3"
                >
                  Next
                  <ChevronRight className="h-3.5 w-3.5 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Trade Details Modal */}
      <Dialog open={!!selectedTrade} onOpenChange={(open) => !open && setSelectedTrade(null)}>
        <DialogContent className="bg-gray-900 border-gray-800 text-white max-w-2xl max-h-[85vh] overflow-y-auto w-[90vw] [&>button]:text-gray-400 [&>button]:hover:text-white sm:p-6 p-4">
          <DialogHeader className="mb-4">
            <div className="flex items-center gap-3">
              <div
                className={`flex items-center justify-center p-2.5 rounded-xl ${selectedTrade?.side === "BUY" ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"}`}
              >
                {selectedTrade?.side === "BUY" ? (
                  <ArrowUpRight className="h-6 w-6" />
                ) : (
                  <ArrowDownRight className="h-6 w-6" />
                )}
              </div>
              <div>
                <DialogTitle className="text-xl font-bold tracking-tight">
                  {selectedTrade?.instrument_symbol}
                </DialogTitle>
                <DialogDescription className="text-sm font-medium text-gray-400 mt-1 flex items-center gap-2">
                  <Badge variant="outline" className="border-gray-700 font-bold tracking-wider rounded-lg px-2 text-[10px]">
                    {selectedTrade?.side}
                  </Badge>
                  <span className="flex items-center">
                    <Clock className="w-3.5 h-3.5 mr-1 text-gray-500" />
                    {selectedTrade?.holding_duration_minutes}m holding
                  </span>
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {selectedTrade && (
            <div className="space-y-6">
              {/* Financial Summary */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="bg-gray-800/50 rounded-xl p-3 border border-gray-700/50">
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                    Entry Price
                  </div>
                  <div className="text-sm font-bold text-white">
                    ₹{parseFloat(selectedTrade.entry_price).toFixed(2)}
                  </div>
                </div>
                <div className="bg-gray-800/50 rounded-xl p-3 border border-gray-700/50">
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                    Exit Price
                  </div>
                  <div className="text-sm font-bold text-white">
                    ₹{parseFloat(selectedTrade.exit_price || 0).toFixed(2)}
                  </div>
                </div>
                <div className="bg-gray-800/50 rounded-xl p-3 border border-gray-700/50">
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                    Quantity
                  </div>
                  <div className="text-sm font-bold text-gray-300">
                    {selectedTrade.quantity}
                  </div>
                </div>
                <div className="bg-gray-800/50 rounded-xl p-3 border border-gray-700/50">
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                    Net P&L
                  </div>
                  <div
                    className={`text-sm font-bold ${parseFloat(selectedTrade.net_pnl) >= 0 ? "text-green-400" : "text-red-400"}`}
                  >
                    {formatCurrency(selectedTrade.net_pnl)}
                  </div>
                </div>
              </div>

              {/* Advanced Analytics */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="bg-gray-800/30 border-gray-700 shadow-sm">
                  <CardContent className="p-4 space-y-4">
                    <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider border-b border-gray-700/50 pb-2 flex items-center gap-2">
                       <Activity className="w-4 h-4 text-indigo-400" /> Efficiency
                    </h4>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-400">Max Adverse Excursion (MAE)</span>
                        <span className="font-bold text-red-400">
                          -{formatCurrency(selectedTrade.mae)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-400">Max Favorable Excursion (MFE)</span>
                        <span className="font-bold text-green-400">
                          +{formatCurrency(selectedTrade.mfe)}
                        </span>
                      </div>
                      <div className="h-px bg-gray-700/50 w-full" />
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-400">Exit Reason</span>
                        <Badge variant="secondary" className="bg-gray-700 hover:bg-gray-600 text-[10px] text-gray-300">
                           {selectedTrade.exit_reason || "Signal"}
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-gray-800/30 border-gray-700 shadow-sm">
                  <CardContent className="p-4 space-y-4">
                    <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider border-b border-gray-700/50 pb-2 flex items-center gap-2">
                      <DollarSign className="w-4 h-4 text-amber-400" /> Transaction Costs
                    </h4>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-400">Gross P&L</span>
                        <span className={`font-medium ${parseFloat(selectedTrade.gross_pnl) >= 0 ? "text-green-400" : "text-red-400"}`}>
                           {formatCurrency(selectedTrade.gross_pnl)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-400">Brokerage Paid</span>
                        <span className="font-medium text-gray-300">
                          {formatCurrency(selectedTrade.brokerage)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-400">Estimated Slippage</span>
                        <span className="font-medium text-gray-300">
                          {formatCurrency(selectedTrade.slippage)}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

               {/* Timestamps */}
              <div className="flex flex-col sm:flex-row justify-between bg-gray-800/40 rounded-xl p-4 border border-gray-700/30 text-xs text-gray-400">
                <div className="flex flex-col mb-2 sm:mb-0">
                   <span className="font-semibold uppercase tracking-wider mb-1 opacity-70">Entry Time</span>
                   <span className="font-medium text-gray-300">{formatTime(selectedTrade.entry_time)}</span>
                </div>
                <div className="flex flex-col sm:text-right">
                   <span className="font-semibold uppercase tracking-wider mb-1 opacity-70">Exit Time</span>
                   <span className="font-medium text-gray-300">{formatTime(selectedTrade.exit_time)}</span>
                </div>
              </div>

            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
