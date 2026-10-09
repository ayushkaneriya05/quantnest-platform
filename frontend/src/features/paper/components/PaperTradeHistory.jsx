import { useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import {
  BarChart2,
  Calendar,
  Search,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { paperApi } from "@/shared/services/paperApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { usePaperTradingUpdate } from "@/shared/hooks/usePaperTradingWebSocket";
import { formatCurrency, formatDateTime } from "@/shared/utils/formatters";
import PaperTablePagination from "@/features/paper/components/PaperTablePagination.jsx";

const PAGE_SIZE = 10;

export default function PaperTradeHistory({ selectedAccountId }) {
  const { notify } = useNotifications();
  const lastMessage = usePaperTradingUpdate();
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [pnlMode, setPnlMode] = useState("net");
  const [page, setPage] = useState(1);

  const totalCharges = (trade) =>
    Number(trade.charges_breakdown?.total ?? trade.charges_json?.total_charges ?? 0);

  const displayPnl = (trade) =>
    pnlMode === "net" ? Number(trade.net_pnl || 0) : Number(trade.net_pnl || 0) + totalCharges(trade);

  const displayPnlPercent = (trade) => {
    const entryValue = Number(trade.entry_price || 0) * Number(trade.quantity || 0);
    return entryValue ? (displayPnl(trade) / entryValue) * 100 : 0;
  };

  const fetchData = async () => {
    try {
      const tradesRes = await paperApi.getTrades();
      setTrades(tradesRes.data || []);
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to load trades"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (["ORDER_UPDATE", "POSITION_UPDATE"].includes(lastMessage?.event_type)) {
      fetchData();
    }
  }, [lastMessage]);

  const filteredTrades = useMemo(
    () =>
      trades.filter((trade) => {
        if (String(trade.account) !== String(selectedAccountId)) return false;
        if (filter === "winning" && displayPnl(trade) <= 0) return false;
        if (filter === "losing" && displayPnl(trade) >= 0) return false;
        if (
          search &&
          !trade.instrument_symbol?.toLowerCase().includes(search.toLowerCase())
        )
          return false;
        return true;
      }),
    [filter, pnlMode, search, selectedAccountId, trades],
  );

  useEffect(() => setPage(1), [filter, pnlMode, search, selectedAccountId]);
  const pageCount = Math.max(1, Math.ceil(filteredTrades.length / PAGE_SIZE));
  const pageTrades = filteredTrades.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

  const analytics = useMemo(() => {
    const total = filteredTrades.length;
    const winners = filteredTrades.filter((trade) => {
      return displayPnl(trade) > 0;
    });
    const losers = filteredTrades.filter((trade) => {
      return displayPnl(trade) < 0;
    });
    const totalPnl = filteredTrades.reduce((sum, trade) => {
      return sum + displayPnl(trade);
    }, 0);
    return {
      total_trades: total,
      win_rate: total ? (winners.length / total) * 100 : 0,
      total_pnl: totalPnl,
      avg_pnl: total ? totalPnl / total : 0,
      winning_trades: winners.length,
      losing_trades: losers.length,
    };
  }, [filteredTrades, pnlMode]);

  const formatDuration = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  if (loading) return null;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-card/50 border-border">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-foreground">
              {analytics.total_trades}
            </p>
            <p className="text-xs text-muted-foreground">Total Trades</p>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-indigo-700 dark:text-indigo-400">
              {analytics.win_rate.toFixed(1)}%
            </p>
            <p className="text-xs text-muted-foreground">Win Rate</p>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border">
          <CardContent className="py-4 text-center">
            <p
              className={`text-2xl font-bold ${analytics.total_pnl >= 0 ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"}`}
            >
              {formatCurrency(analytics.total_pnl)}
            </p>
            <p className="text-xs text-muted-foreground">Total P&L</p>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-foreground">
              {formatCurrency(analytics.avg_pnl)}
            </p>
            <p className="text-xs text-muted-foreground">Avg P&L</p>
          </CardContent>
        </Card>
      </div>

      <div className="flex gap-4 items-center">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search symbol..."
            className="pl-9 bg-secondary border-border text-foreground h-10"
          />
        </div>
        <div className="flex gap-1.5 bg-card/50 p-1 rounded-lg border border-border">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setPnlMode("net")}
            className={`text-xs h-8 px-4 ${pnlMode === "net" ? "bg-indigo-500/10 text-indigo-700 dark:text-indigo-400" : "text-muted-foreground hover:text-foreground"}`}
          >
            Net
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setPnlMode("gross")}
            className={`text-xs h-8 px-4 ${pnlMode === "gross" ? "bg-indigo-500/10 text-indigo-700 dark:text-indigo-400" : "text-muted-foreground hover:text-foreground"}`}
          >
            Gross
          </Button>
        </div>
        <div className="flex gap-1.5 bg-card/50 p-1 rounded-lg border border-border">
          {["all", "winning", "losing"].map((value) => (
            <Button
              key={value}
              variant="ghost"
              size="sm"
              onClick={() => setFilter(value)}
              className={`text-xs h-8 px-4 ${
                filter === value 
                  ? "bg-indigo-500/10 text-indigo-700 dark:text-indigo-400" 
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {value.charAt(0).toUpperCase() + value.slice(1)}
            </Button>
          ))}
        </div>
      </div>

      {filteredTrades.length === 0 ? (
        <Card className="bg-card/50 border-border">
          <CardContent className="py-12 text-center">
            <BarChart2 className="h-10 w-10 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium text-foreground">
              No trades found
            </h3>
            <p className="text-muted-foreground text-sm">
              This account does not have matching trade history yet.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {pageTrades.map((trade) => (
            <Card
              key={trade.id}
              className={`bg-card/50 border-border overflow-hidden ${displayPnl(trade) > 0 ? "border-l-4 border-l-emerald-500" : displayPnl(trade) < 0 ? "border-l-4 border-l-rose-500" : "border-l-4 border-l-gray-600"}`}
            >
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div
                      className={`p-2 rounded-lg ${displayPnl(trade) >= 0 ? "bg-emerald-500/10" : "bg-rose-500/10"}`}
                    >
                      {displayPnl(trade) >= 0 ? (
                        <TrendingUp className="h-5 w-5 text-emerald-700 dark:text-emerald-400" />
                      ) : (
                        <TrendingDown className="h-5 w-5 text-rose-700 dark:text-rose-400" />
                      )}
                    </div>
                    <div>
                      <h4 className="text-foreground font-semibold">
                        {trade.instrument_symbol}
                      </h4>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge
                          className={`text-[10px] h-4 px-1.5 ${
                            trade.side === "BUY" ? "bg-emerald-700 text-white" : "bg-rose-600 text-white"
                          }`}
                        >
                          {trade.side}
                        </Badge>
                        <span className="text-[11px] text-muted-foreground">
                          {trade.quantity} units
                        </span>
                        {trade.strategy_name && (
                          <Badge
                            variant="outline"
                            className="border-border text-muted-foreground text-[10px] h-4"
                          >
                            {trade.strategy_name}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Entry</p>
                      <p className="text-foreground text-sm font-mono">
                        {formatCurrency(trade.entry_price)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Exit</p>
                      <p className="text-foreground text-sm font-mono">
                        {formatCurrency(trade.exit_price)}
                      </p>
                    </div>
                    <div className="text-right hidden sm:block">
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Duration</p>
                      <p className="text-foreground text-sm">
                        {formatDuration(trade.holding_duration_seconds)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Charges</p>
                      <p className="text-foreground text-sm">
                        {formatCurrency(totalCharges(trade))}
                      </p>
                    </div>
                    <div className="text-right min-w-24">
                      <p
                        className={`text-lg font-bold ${displayPnl(trade) >= 0 ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"}`}
                      >
                        {displayPnl(trade) > 0 ? "+" : ""}
                        {formatCurrency(displayPnl(trade))}
                      </p>
                      <p className="text-[11px] text-muted-foreground">
                        {displayPnlPercent(trade).toFixed(2)}%
                      </p>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4 mt-3 pt-3 border-t border-border/50 text-[11px] text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <Calendar className="h-3 w-3" />
                    Entry: {formatDateTime(trade.entry_time)}
                  </span>
                  <span className="hidden sm:inline">•</span>
                  <span>Exit: {formatDateTime(trade.exit_time)}</span>
                  {trade.exit_reason && (
                    <Badge variant="outline" className="ml-auto border-border text-muted-foreground text-[10px]">
                      {trade.exit_reason}
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
          <PaperTablePagination
            page={page}
            count={filteredTrades.length}
            pageSize={PAGE_SIZE}
            onPageChange={(nextPage) => setPage(Math.min(nextPage, pageCount))}
          />
        </div>
      )}
    </div>
  );
}
