import RefreshButton from "@/shared/components/RefreshButton";
import Pagination from "@/shared/components/Pagination";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { usePagination, useQueryState } from "@/shared/hooks/usePagination";
import PageTabs from "@/shared/components/PageTabs";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import React, { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import {
  Card,
  CardContent,
} from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import {
  ChevronLeft,
  Search,
  TrendingUp,
  TrendingDown,
  Filter,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
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
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { formatCurrency, formatDateTime, formatNumber } from "@/shared/utils/formatters";

export default function BacktestTradeList() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [run, setRun] = useState(null);
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useQueryState("outcome", "all", { namespace: "", replace: false });
  const [search, setSearch] = useQueryState("search", "", { namespace: "", replace: true });
  const [instrumentFilter, setInstrumentFilter] = useQueryState("instrument", "all", { namespace: "", replace: false });
  const [instrumentOptions, setInstrumentOptions] = useState([]);
  const { page, pageSize, setPage, setPageSize, accept } = usePagination(JSON.stringify([id, filter, search, instrumentFilter]));
  const generation = useRef(0);
  const [selectedTrade, setSelectedTrade] = useState(null);


  const [totalCount, setTotalCount] = useState(0);

  const fetchData = useCallback(async () => {
    const request = ++generation.current;
    setLoading(true);
    setError("");
    try {
      const [runData, tradesData] = await Promise.all([
        backtestApi.getRun(id),
        backtestApi.getRunTrades(id, { page, page_size: pageSize, filter, search, instrument: instrumentFilter }),
      ]);
      if (request !== generation.current) return;
      setRun(runData.data);
      setTrades(tradesData.data.results);
      setTotalCount(tradesData.data.count);
      setInstrumentOptions(tradesData.data.instrument_options);
      accept(tradesData.data);
    } catch (error) {
      if (request === generation.current) setError(getApiErrorMessage(error, "Failed to load backtest trades"));
    } finally {
      if (request === generation.current) setLoading(false);
    }
  }, [id, page, pageSize, accept, filter, search, instrumentFilter]);

  useEffect(() => {
    const timer = setTimeout(fetchData, search ? 250 : 0);
    const guard = generation;
    return () => { clearTimeout(timer); guard.current++; };
  }, [fetchData, search]);


  const stats = {
    total: run?.metrics?.total_trades || 0,
    winners: run?.metrics?.winning_trades || 0,
    losers: run?.metrics?.losing_trades || 0,
    totalPnl: Number(run?.metrics?.final_capital || 0) - Number(run?.initial_capital || 0),
  };



  const pageActions = React.useMemo(() => (
    <div className="flex items-center gap-2"><RefreshButton onClick={fetchData} label="Refresh backtest trades" loading={loading} /><Button
      variant="outline"
      size="sm"
      onClick={() => navigate(`/backtests/results/${id}`)}
      className=""
    >
      <ChevronLeft className="h-4 w-4 mr-2" />
      Back to Results
    </Button></div>
  ), [navigate, id, fetchData, loading]);

  useSetPageActions(pageActions);

  if (error) return <div className="page-content"><WorkspaceState error={error} onRetry={fetchData} /></div>;
  if (loading && !run) {
    return (
      <div className="flex justify-center items-center h-96">
        <GlobalLoader />
      </div>
    );
  }

  return (
    <div className="page-content">
      {/* Stats Dashboard */}

      {/* Stats Dashboard */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          {
            label: "Total Trades",
            value: stats.total,
            icon: Filter,
            color: "text-foreground",
          },
          {
            label: "Winners",
            value: stats.winners,
            icon: TrendingUp,
            color: "text-success",
          },
          {
            label: "Losers",
            value: stats.losers,
            icon: TrendingDown,
            color: "text-loss",
          },
          {
            label: "Total P&L",
            value: formatCurrency(stats.totalPnl),
            icon: TrendingUp,
            color: stats.totalPnl >= 0 ? "text-success" : "text-loss",
          },
        ].map((stat, i) => (
          <Card key={i} className="bg-card/50 border-border">
            <CardContent className="p-3 flex items-center gap-3">
              <div className={`p-2 rounded-lg bg-secondary ${stat.color}`}>
                <stat.icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
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
      <div className="flex flex-col md:flex-row gap-2 justify-between items-start md:items-center">
        <div className="relative w-full md:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search symbol..."
            className="pl-9 bg-secondary/50 border-border text-foreground focus:ring-brand"
          />
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-2 w-full md:w-auto">
          <Select
            value={instrumentFilter}
            onValueChange={setInstrumentFilter}
          >
            <SelectTrigger className="w-full sm:w-[180px] bg-secondary border-border text-foreground text-sm">
              <SelectValue placeholder="All Instruments" />
            </SelectTrigger>
            <SelectContent className="bg-card border-border text-foreground">
              {["all", ...instrumentOptions].map((option) => (
                <SelectItem key={option} value={option} className="focus:bg-secondary focus:text-foreground">
                  {option === "all" ? "All Instruments" : option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <PageTabs appearance="outline" label="Trade outcome" value={filter} onValueChange={setFilter} items={["all", "winning", "losing"].map(value => ({ value, label: value.charAt(0).toUpperCase() + value.slice(1) }))} />
        </div>
      </div>

      {/* Trade Table */}
      <Card className="bg-card/50 border-border overflow-hidden">
        <CardContent className="p-0">
          <div className="overflow-x-auto scrollbar-thin-theme">
            <table className="w-full min-w-[1080px] text-left whitespace-nowrap [&_th]:px-3 [&_th]:py-2 [&_td]:px-3 [&_td]:py-2">
              <thead>
                <tr className="bg-secondary/50 border-b border-border text-xs text-muted-foreground uppercase tracking-wider">
                  <th className="px-3 py-3 font-semibold">Instrument</th>
                  <th className="px-3 py-3 font-semibold">Side</th>
                  <th className="px-3 py-3 font-semibold">Timing</th>
                  <th className="px-3 py-3 font-semibold text-right">Qty</th>
                  <th className="px-3 py-3 font-semibold text-right">
                    Entry/Exit Price
                  </th>
                  <th className="px-3 py-3 font-semibold text-right">
                    MAE / MFE (₹)
                  </th>
                  <th className="px-3 py-3 font-semibold text-right">
                    Net P&L
                  </th>
                  <th className="px-3 py-3 font-semibold text-right">
                    Charges (₹)
                  </th>
                  <th className="px-3 py-3 font-semibold">Exit Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {trades.map((trade) => (
                  <tr
                    key={trade.id}
                    onClick={() => setSelectedTrade(trade)}
                    className="hover:bg-secondary/30 transition-colors group cursor-pointer"
                  >
                    <td className="px-3 py-3">
                      <div className="text-sm font-bold text-foreground">
                        {trade.instrument_symbol}
                      </div>
                      <div className="text-[10px] text-muted-foreground flex items-center gap-1 mt-0.5 uppercase">
                        <Clock className="h-3 w-3" />
                        {formatNumber(trade.holding_duration_minutes)}m duration
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <div
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          trade.side === "BUY"
                            ? "bg-success/10 text-success"
                            : "bg-loss/10 text-loss"
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
                    <td className="px-3 py-3">
                      <div className="text-[11px] text-foreground">
                        IN: {formatDateTime(trade.entry_time)}
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        OUT: {formatDateTime(trade.exit_time)}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <span className="text-sm font-medium text-foreground">
                        {formatNumber(trade.quantity, { maximumFractionDigits: 0 })}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <div className="text-sm text-foreground">
                        {formatCurrency(trade.entry_price)}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {formatCurrency(trade.exit_price || 0)}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <div className="text-[11px] text-loss font-medium">
                        -{formatCurrency(trade.mae)}
                      </div>
                      <div className="text-[11px] text-success font-medium">
                        +{formatCurrency(trade.mfe)}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <div
                        className={`text-sm font-bold ${parseFloat(trade.net_pnl) >= 0 ? "text-success" : "text-loss"}`}
                      >
                        {formatCurrency(trade.net_pnl)}
                      </div>
                      <div
                        className={`text-[10px] opacity-70 ${parseFloat(trade.net_pnl) >= 0 ? "text-success" : "text-loss"}`}
                      >
                        {formatNumber(trade.pnl_pct)}%
                      </div>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <span className="text-sm font-medium text-foreground">
                        {formatCurrency(trade.charges_breakdown?.total ?? trade.charges_json?.total_charges ?? 0)}
                      </span>
                    </td>
                    <td className="px-3 py-3">
                      <Badge
                        variant="outline"
                        className="text-[10px] border-border text-muted-foreground font-normal"
                      >
                        {trade.exit_reason || "Signal"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {trades.length === 0 && (
              <div className="p-8 text-center text-muted-foreground">
                No trades found matching your filters.
              </div>
            )}
          </div>

          <Pagination page={page} pageSize={pageSize} count={totalCount} loading={loading} onPageChange={setPage} onPageSizeChange={setPageSize} label="Backtest trade pages" />
        </CardContent>
      </Card>

      {/* Trade Details Modal */}
      <Dialog open={!!selectedTrade} onOpenChange={(open) => !open && setSelectedTrade(null)}>
        <DialogContent className="bg-card border-border text-foreground max-w-2xl max-h-[95dvh] overflow-y-auto scrollbar-theme w-[90vw] [&>button]:text-muted-foreground [&>button]:hover:text-foreground sm:p-3 p-3">
          <DialogHeader className="mb-2">
            <div className="flex items-center gap-3">
              <div
                className={`flex items-center justify-center p-2.5 rounded-xl ${selectedTrade?.side === "BUY" ? "bg-success/10 text-success" : "bg-loss/10 text-loss"}`}
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
                <DialogDescription className="text-sm font-medium text-muted-foreground mt-1 flex items-center gap-2">
                  <Badge variant="outline" className="border-border font-bold tracking-wider rounded-lg px-2 text-[10px]">
                    {selectedTrade?.side}
                  </Badge>
                  <span className="flex items-center">
                    <Clock className="w-3.5 h-3.5 mr-1 text-muted-foreground" />
                    {formatNumber(selectedTrade?.holding_duration_minutes)}m holding
                  </span>
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {selectedTrade && (
            <div className="space-y-3">
              {/* Financial Summary */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                <div className="bg-secondary/50 rounded-xl p-2.5 border border-border/50">
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">
                    Entry Price
                  </div>
                  <div className="text-sm font-bold text-foreground">
                    {formatCurrency(selectedTrade.entry_price)}
                  </div>
                </div>
                <div className="bg-secondary/50 rounded-xl p-2.5 border border-border/50">
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">
                    Exit Price
                  </div>
                  <div className="text-sm font-bold text-foreground">
                    {formatCurrency(selectedTrade.exit_price || 0)}
                  </div>
                </div>
                <div className="bg-secondary/50 rounded-xl p-2.5 border border-border/50">
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">
                    Quantity
                  </div>
                  <div className="text-sm font-bold text-foreground">
                    {formatNumber(selectedTrade.quantity, { maximumFractionDigits: 0 })}
                  </div>
                </div>
                <div className="bg-secondary/50 rounded-xl p-2.5 border border-border/50">
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">
                    Net P&L
                  </div>
                  <div
                    className={`text-sm font-bold ${parseFloat(selectedTrade.net_pnl) >= 0 ? "text-success" : "text-loss"}`}
                  >
                    {formatCurrency(selectedTrade.net_pnl)}
                  </div>
                </div>
              </div>

              {/* Advanced Analytics */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <Card className="bg-secondary/30 border-border shadow-sm">
                  <CardContent className="p-3 space-y-3">
                    <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider border-b border-border/50 pb-1.5 flex items-center gap-2">
                       <Activity className="w-4 h-4 text-brand" /> Efficiency
                    </h4>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground">Max Adverse Excursion (MAE)</span>
                        <span className="font-bold text-loss">
                          -{formatCurrency(selectedTrade.mae)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground">Max Favorable Excursion (MFE)</span>
                        <span className="font-bold text-success">
                          +{formatCurrency(selectedTrade.mfe)}
                        </span>
                      </div>
                      <div className="h-px bg-muted/50 w-full" />
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground">Exit Reason</span>
                        <Badge variant="secondary" className="bg-muted hover:bg-muted text-[10px] text-foreground">
                           {selectedTrade.exit_reason || "Signal"}
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-secondary/30 border-border shadow-sm">
                  <CardContent className="p-3 space-y-3">
                    <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider border-b border-border/50 pb-1.5 flex items-center gap-2">
                      <DollarSign className="w-4 h-4 text-warning" /> Transaction Costs
                    </h4>
                    <div className="space-y-1.5">
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground">Gross P&L</span>
                        <span className={`font-medium ${parseFloat(selectedTrade.gross_pnl) >= 0 ? "text-success" : "text-loss"}`}>
                           {formatCurrency(selectedTrade.gross_pnl)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground">Brokerage Paid</span>
                        <span className="font-medium text-foreground">
                          {formatCurrency(selectedTrade.charges_breakdown?.brokerage || 0)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground">STT/CTT</span>
                        <span className="font-medium text-foreground">
                          {formatCurrency(selectedTrade.charges_breakdown?.stt || 0)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground">Exchange Txn</span>
                        <span className="font-medium text-foreground">
                          {formatCurrency(selectedTrade.charges_breakdown?.exchange_txn || 0)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground">SEBI + Stamp</span>
                        <span className="font-medium text-foreground">
                          {formatCurrency((selectedTrade.charges_breakdown?.sebi || 0) + (selectedTrade.charges_breakdown?.stamp_duty || 0))}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground">GST</span>
                        <span className="font-medium text-foreground">
                          {formatCurrency(selectedTrade.charges_breakdown?.gst || 0)}
                        </span>
                      </div>
                      <div className="h-px bg-muted/50 w-full" />
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground">Estimated Slippage</span>
                        <span className="font-medium text-foreground">
                          {formatCurrency(selectedTrade.slippage)}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

               {/* Timestamps */}
              <div className="flex flex-col sm:flex-row justify-between bg-secondary/40 rounded-xl p-3 border border-border/30 text-xs text-muted-foreground mt-2">
                <div className="flex flex-col mb-1 sm:mb-0">
                   <span className="font-semibold uppercase tracking-wider mb-0.5 opacity-70">Entry Time</span>
                   <span className="font-medium text-foreground">{formatDateTime(selectedTrade.entry_time)}</span>
                </div>
                <div className="flex flex-col sm:text-right">
                   <span className="font-semibold uppercase tracking-wider mb-0.5 opacity-70">Exit Time</span>
                   <span className="font-medium text-foreground">{formatDateTime(selectedTrade.exit_time)}</span>
                </div>
              </div>

            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
