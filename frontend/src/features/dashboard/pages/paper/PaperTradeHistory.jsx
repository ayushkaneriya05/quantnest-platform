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
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";

export default function PaperTradeHistory({ selectedAccountId }) {
  const { notify } = useNotifications();
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");

  const fetchData = async () => {
    try {
      const tradesRes = await paperApi.getTrades();
      setTrades(tradesRes.data || []);
    } catch (error) {
      notify.error("Failed to load trades");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const filteredTrades = useMemo(
    () =>
      trades.filter((trade) => {
        if (String(trade.account) !== String(selectedAccountId)) return false;
        if (filter === "winning" && !trade.is_winner) return false;
        if (filter === "losing" && trade.is_winner) return false;
        if (
          search &&
          !trade.instrument_symbol?.toLowerCase().includes(search.toLowerCase())
        )
          return false;
        return true;
      }),
    [filter, search, selectedAccountId, trades],
  );

  const analytics = useMemo(() => {
    const total = filteredTrades.length;
    const winners = filteredTrades.filter(
      (trade) => Number(trade.net_pnl || 0) > 0,
    );
    const losers = filteredTrades.filter(
      (trade) => Number(trade.net_pnl || 0) < 0,
    );
    const totalPnl = filteredTrades.reduce(
      (sum, trade) => sum + Number(trade.net_pnl || 0),
      0,
    );
    return {
      total_trades: total,
      win_rate: total ? (winners.length / total) * 100 : 0,
      total_pnl: totalPnl,
      avg_pnl: total ? totalPnl / total : 0,
      winning_trades: winners.length,
      losing_trades: losers.length,
    };
  }, [filteredTrades]);

  const formatCurrency = (value) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(value || 0);

  const formatTime = (dateString) =>
    new Date(dateString).toLocaleString("en-IN", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });

  const formatDuration = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  if (loading) return null;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-white">
              {analytics.total_trades}
            </p>
            <p className="text-xs text-gray-400">Total Trades</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-indigo-400">
              {analytics.win_rate.toFixed(1)}%
            </p>
            <p className="text-xs text-gray-400">Win Rate</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p
              className={`text-2xl font-bold ${analytics.total_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}
            >
              {formatCurrency(analytics.total_pnl)}
            </p>
            <p className="text-xs text-gray-400">Total P&L</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-white">
              {formatCurrency(analytics.avg_pnl)}
            </p>
            <p className="text-xs text-gray-400">Avg P&L</p>
          </CardContent>
        </Card>
      </div>

      <div className="flex gap-4 items-center">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search symbol..."
            className="pl-9 bg-gray-800 border-gray-700 text-white h-10"
          />
        </div>
        <div className="flex gap-1.5 bg-gray-900/50 p-1 rounded-lg border border-gray-800">
          {["all", "winning", "losing"].map((value) => (
            <Button
              key={value}
              variant="ghost"
              size="sm"
              onClick={() => setFilter(value)}
              className={`text-xs h-8 px-4 ${
                filter === value 
                  ? "bg-indigo-500/10 text-indigo-400" 
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              {value.charAt(0).toUpperCase() + value.slice(1)}
            </Button>
          ))}
        </div>
      </div>

      {filteredTrades.length === 0 ? (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-12 text-center">
            <BarChart2 className="h-10 w-10 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-300">
              No trades found
            </h3>
            <p className="text-gray-500 text-sm">
              This account does not have matching trade history yet.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredTrades.map((trade) => (
            <Card
              key={trade.id}
              className={`bg-gray-900/50 border-gray-800 overflow-hidden ${trade.is_winner ? "border-l-4 border-l-emerald-500" : "border-l-4 border-l-rose-500"}`}
            >
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div
                      className={`p-2 rounded-lg ${trade.is_winner ? "bg-emerald-500/10" : "bg-rose-500/10"}`}
                    >
                      {trade.is_winner ? (
                        <TrendingUp className="h-5 w-5 text-emerald-400" />
                      ) : (
                        <TrendingDown className="h-5 w-5 text-rose-400" />
                      )}
                    </div>
                    <div>
                      <h4 className="text-white font-semibold">
                        {trade.instrument_symbol}
                      </h4>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge
                          className={`text-[10px] h-4 px-1.5 ${
                            trade.side === "BUY" ? "bg-emerald-600" : "bg-rose-600"
                          }`}
                        >
                          {trade.side}
                        </Badge>
                        <span className="text-[11px] text-gray-500">
                          {trade.quantity} units
                        </span>
                        {trade.strategy_name && (
                          <Badge
                            variant="outline"
                            className="border-gray-800 text-gray-500 text-[10px] h-4"
                          >
                            {trade.strategy_name}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <p className="text-[10px] text-gray-500 uppercase tracking-wider">Entry</p>
                      <p className="text-white text-sm font-mono">
                        ₹{parseFloat(trade.entry_price).toFixed(2)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-gray-500 uppercase tracking-wider">Exit</p>
                      <p className="text-white text-sm font-mono">
                        ₹{parseFloat(trade.exit_price).toFixed(2)}
                      </p>
                    </div>
                    <div className="text-right hidden sm:block">
                      <p className="text-[10px] text-gray-500 uppercase tracking-wider">Duration</p>
                      <p className="text-gray-300 text-sm">
                        {formatDuration(trade.holding_duration_seconds)}
                      </p>
                    </div>
                    <div className="text-right min-w-24">
                      <p
                        className={`text-lg font-bold ${trade.is_winner ? "text-emerald-400" : "text-rose-400"}`}
                      >
                        {trade.is_winner ? "+" : ""}
                        {formatCurrency(trade.net_pnl)}
                      </p>
                      <p className="text-[11px] text-gray-500">
                        {parseFloat(trade.pnl_pct).toFixed(2)}%
                      </p>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4 mt-3 pt-3 border-t border-gray-800/50 text-[11px] text-gray-500">
                  <span className="flex items-center gap-1.5">
                    <Calendar className="h-3 w-3" />
                    Entry: {formatTime(trade.entry_time)}
                  </span>
                  <span className="hidden sm:inline">•</span>
                  <span>Exit: {formatTime(trade.exit_time)}</span>
                  {trade.exit_reason && (
                    <Badge variant="outline" className="ml-auto border-gray-800 text-gray-600 text-[10px]">
                      {trade.exit_reason}
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
