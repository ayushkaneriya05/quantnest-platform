import Pagination from "@/shared/components/Pagination";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { usePagination, useQueryState } from "@/shared/hooks/usePagination";
import PageTabs from "@/shared/components/PageTabs";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import {useStableCallback} from "@/shared/hooks/useStableCallback";
import PropTypes from "prop-types";
import { useCallback, useEffect, useRef, useState } from "react";
import { Card, CardContent } from "@/shared/components/ui/card";
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
import { formatCurrency, formatDateTime, formatNumber } from "@/shared/utils/formatters";

const totalCharges = (trade) => Number(trade.charges_breakdown?.total ?? trade.charges_json?.total_charges ?? 0);

export default function PaperTradeHistory({ selectedAccountId, refreshKey = 0 }) {
  const fetchData = useStableCallback(async () => {
    const generation = ++request.current;
    setLoading(true);
    setError("");
    try {
      const response = await paperApi.getTrades({ page, page_size: pageSize, account_id: selectedAccountId || undefined, filter, search, pnl_mode: pnlMode });
      if (generation !== request.current) return;
      setTrades(response.data.results);
      setMetadata(response.data);
      accept(response.data);
    } catch (error) {
      if (generation === request.current) setError(getApiErrorMessage(error, "Could not load trades."));
    } finally { if (generation === request.current) setLoading(false); }
  });

  const { notify } = useNotifications();
  const lastMessage = usePaperTradingUpdate();
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useQueryState("search", "", { namespace: "trades", replace: true });
  const [filter, setFilter] = useQueryState("outcome", "all", { namespace: "trades", replace: false });
  const [pnlMode, setPnlMode] = useQueryState("pnl_mode", "net", { namespace: "trades", replace: false });
  const { page, pageSize, setPage, setPageSize, accept } = usePagination(JSON.stringify([selectedAccountId, filter, search, pnlMode]), 'trades');
  const [metadata, setMetadata] = useState({ count: 0 });
  const [summary, setSummary] = useState({});
  const request = useRef(0);
  useEffect(() => {
    setTrades([]); setSummary({});
    const guard = request; return () => { guard.current++; };
  }, [selectedAccountId, filter, search, pnlMode]);

  const displayPnl = useCallback((trade) =>
    pnlMode === "net" ? Number(trade.net_pnl || 0) : Number(trade.net_pnl || 0) + totalCharges(trade), [pnlMode]);

  const displayPnlPercent = (trade) => {
    const entryValue = Number(trade.entry_price || 0) * Number(trade.quantity || 0);
    return entryValue ? (displayPnl(trade) / entryValue) * 100 : 0;
  };



  useEffect(() => {
    const timer = setTimeout(fetchData, search ? 250 : 0);
    const guard = request;
    return () => { clearTimeout(timer); guard.current++; };
  }, [fetchData, page, pageSize, selectedAccountId, refreshKey, filter, search, pnlMode]);

  useEffect(() => {
    if (["ORDER_UPDATE", "POSITION_UPDATE"].includes(lastMessage?.event_type)) {
      fetchData();
    }
  }, [lastMessage, fetchData]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => paperApi.getTradeAnalytics({ account_id: selectedAccountId || undefined, filter, search, pnl_mode: pnlMode }, controller.signal)
      .then(response => { if (!controller.signal.aborted) setSummary(response.data); })
      .catch(error => { if (!controller.signal.aborted) notify.error(getApiErrorMessage(error, "Could not load summary.")); }), search ? 250 : 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [selectedAccountId, refreshKey, lastMessage, notify, filter, search, pnlMode]);
  const formatDuration = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  if (error) return <WorkspaceState error={error} onRetry={fetchData} />;
  if (loading && !metadata.page) return <GlobalLoader fullHeight={false} />;

  return (
    <div className="space-y-3 animate-in fade-in duration-300">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="bg-card/50 border-border">
          <CardContent className="py-3 text-center">
            <p className="text-2xl font-bold text-foreground">
              {formatNumber(summary.total_trades, { maximumFractionDigits: 0 })}
            </p>
            <p className="text-xs text-muted-foreground">Total Trades</p>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border">
          <CardContent className="py-3 text-center">
            <p className="text-2xl font-bold text-brand">
              {formatNumber(summary.win_rate)}%
            </p>
            <p className="text-xs text-muted-foreground">Win Rate</p>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border">
          <CardContent className="py-3 text-center">
            <p
              className={`text-2xl font-bold ${summary.total_pnl >= 0 ? "text-success" : "text-loss"}`}
            >
              {formatCurrency(summary.total_pnl)}
            </p>
            <p className="text-xs text-muted-foreground">Total P&L</p>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border">
          <CardContent className="py-3 text-center">
            <p className="text-2xl font-bold text-foreground">
              {formatCurrency(summary.avg_pnl)}
            </p>
            <p className="text-xs text-muted-foreground">Avg P&L</p>
          </CardContent>
        </Card>
      </div>

      <div className="flex min-w-0 flex-wrap gap-2 items-center">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search symbol..."
            className="pl-9 bg-secondary border-border text-foreground"
          />
        </div>
        <PageTabs appearance="outline" label="Profit display" value={pnlMode} onValueChange={setPnlMode} items={[{ value: "net", label: "Net" }, { value: "gross", label: "Gross" }]} />
        <PageTabs appearance="outline" label="Trade outcome" value={filter} onValueChange={setFilter} items={["all", "winning", "losing"].map(value => ({ value, label: value.charAt(0).toUpperCase() + value.slice(1) }))} />
      </div>

      {metadata.count === 0 ? (
        <Card className="bg-card/50 border-border">
          <CardContent className="py-12 text-center">
            <BarChart2 className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
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
          {trades.map((trade) => (
            <Card
              key={trade.id}
              className={`bg-card/50 border-border overflow-hidden ${displayPnl(trade) > 0 ? "border-l-4 border-l-emerald-500" : displayPnl(trade) < 0 ? "border-l-4 border-l-rose-500" : "border-l-4 border-l-gray-600"}`}
            >
              <CardContent className="py-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-2 rounded-lg ${displayPnl(trade) >= 0 ? "bg-success/10" : "bg-loss/10"}`}
                    >
                      {displayPnl(trade) >= 0 ? (
                        <TrendingUp className="h-5 w-5 text-success" />
                      ) : (
                        <TrendingDown className="h-5 w-5 text-loss" />
                      )}
                    </div>
                    <div>
                      <h4 className="text-foreground font-semibold">
                        {trade.instrument_symbol}
                      </h4>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge
                          className={`text-[10px] h-4 px-1.5 ${
                            trade.side === "BUY" ? "bg-success text-success-foreground" : "bg-loss text-loss-foreground"
                          }`}
                        >
                          {trade.side}
                        </Badge>
                        <span className="text-[11px] text-muted-foreground">
                          {formatNumber(trade.quantity, { maximumFractionDigits: 0 })} units
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

                  <div className="flex items-center gap-3">
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
                        className={`text-lg font-bold ${displayPnl(trade) >= 0 ? "text-success" : "text-loss"}`}
                      >
                        {displayPnl(trade) > 0 ? "+" : ""}
                        {formatCurrency(displayPnl(trade))}
                      </p>
                      <p className="text-[11px] text-muted-foreground">
                        {formatNumber(displayPnlPercent(trade))}%
                      </p>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3 mt-3 pt-3 border-t border-border/50 text-[11px] text-muted-foreground">
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

        </div>
      )}
          <Pagination
            page={page}
            count={metadata.count}
            pageSize={pageSize} loading={loading} onPageSizeChange={setPageSize} label="Paper trades pages"
            onPageChange={setPage}
          />
    </div>
  );
}

PaperTradeHistory.propTypes = {
  ...PaperTradeHistory.propTypes,
  selectedAccountId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  refreshKey: PropTypes.number,
};
