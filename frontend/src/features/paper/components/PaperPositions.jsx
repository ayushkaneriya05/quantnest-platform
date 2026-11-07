import Pagination from "@/shared/components/Pagination";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { usePagination } from "@/shared/hooks/usePagination";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import {useStableCallback} from "@/shared/hooks/useStableCallback";
import PropTypes from "prop-types";
import { useEffect, useRef, useState } from "react";
import { Card, CardContent } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { Layers, TrendingDown, TrendingUp } from "lucide-react";
import { paperApi } from "@/shared/services/paperApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { formatCurrency, formatNumber } from "@/shared/utils/formatters";
import { useLivePositionSummary, usePaperPositionsPnL } from "@/shared/hooks/useLivePositionsPnL";
import { usePaperTradingUpdate } from "@/shared/hooks/usePaperTradingWebSocket";


export default function PaperPositions({ selectedAccountId, refreshKey = 0 }) {
  const fetchPositions = useStableCallback(async () => {
    const generation = ++request.current;
    setLoading(true);
    setError("");
    try {
      const response = await paperApi.getPositions({ page, page_size: pageSize, account_id: selectedAccountId || undefined });
      if (generation !== request.current) return;
      setPositions(response.data.results);
      setMetadata(response.data);
      accept(response.data);
    } catch (error) {
      if (generation === request.current) setError(getApiErrorMessage(error, "Could not load positions."));
    } finally { if (generation === request.current) setLoading(false); }
  });

  const { notify } = useNotifications();
  const lastMessage = usePaperTradingUpdate();
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { page, pageSize, setPage, setPageSize, accept } = usePagination(String(selectedAccountId), 'positions');
  const [metadata, setMetadata] = useState({ count: 0 });
  const [snapshot, setSummary] = useState({});
  const summary = useLivePositionSummary(snapshot);
  const request = useRef(0);
  useEffect(() => {
    setPositions([]); setSummary({});
    const guard = request; return () => { guard.current++; };
  }, [selectedAccountId]);
  const refreshTimerRef = useRef(null);



  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 30000);
    const guard = request;
    return () => {
      guard.current++;
      clearInterval(interval);
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
  }, [fetchPositions, page, pageSize, selectedAccountId, refreshKey]);

  useEffect(() => {
    if (!lastMessage || !["POSITION_UPDATE", "RECONNECTED"].includes(lastMessage.event_type)) return;
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    refreshTimerRef.current = setTimeout(fetchPositions, 150);
  }, [lastMessage, fetchPositions]);

  useEffect(() => {
    const controller = new AbortController();
    paperApi.getPositionsSummary({ account_id: selectedAccountId || undefined }, controller.signal)
      .then(response => { if (!controller.signal.aborted) setSummary(response.data); })
      .catch(error => { if (!controller.signal.aborted) notify.error(getApiErrorMessage(error, "Could not load summary.")); });
    return () => controller.abort();
  }, [selectedAccountId, refreshKey, lastMessage, notify]);
  const { livePnLByPositionId } = usePaperPositionsPnL(positions);
  const totalValue = Number(summary.current_value || 0);
  const totalUnrealizedPnl = Number(summary.unrealized_pnl || 0);
  if (error) return <WorkspaceState error={error} onRetry={fetchPositions} />;
  if (loading && !metadata.page) return <GlobalLoader fullHeight={false} />;

  return (
    <div className="space-y-3 animate-in fade-in duration-300">
      <div className="grid grid-cols-3 gap-3">
        <Card className="bg-card/50 border-border">
          <CardContent className="py-3 text-center">
            <p className="text-2xl font-bold text-foreground">
              {metadata.count}
            </p>
            <p className="text-xs text-muted-foreground">Open Positions</p>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border">
          <CardContent className="py-3 text-center">
            <p className="text-2xl font-bold text-foreground">
              {formatCurrency(totalValue)}
            </p>
            <p className="text-xs text-muted-foreground">Total Value</p>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border">
          <CardContent className="py-3 text-center">
            <p
              className={`text-2xl font-bold ${totalUnrealizedPnl >= 0 ? "text-success" : "text-loss"}`}
            >
              {totalUnrealizedPnl >= 0 ? "+" : ""}
              {formatCurrency(totalUnrealizedPnl)}
            </p>
            <p className="text-xs text-muted-foreground">Unrealized P&L</p>
          </CardContent>
        </Card>
      </div>

      {metadata.count === 0 ? (
        <Card className="bg-card/50 border-border">
          <CardContent className="py-12 text-center">
            <Layers className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
            <h3 className="text-lg font-medium text-foreground">
              No open positions
            </h3>
            <p className="text-muted-foreground text-sm">
              Place orders in this account to open positions.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {positions.map((position) => (
            <Card key={position.id} className="bg-card/50 border-border hover:border-border transition-colors">
              <CardContent className="py-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-3 rounded-lg ${position.side === "BUY" ? "bg-success/10" : "bg-loss/10"}`}
                    >
                      {position.side === "BUY" ? (
                        <TrendingUp className="h-6 w-6 text-success" />
                      ) : (
                        <TrendingDown className="h-6 w-6 text-loss" />
                      )}
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-foreground">
                        {position.instrument_symbol}
                      </h3>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge
                          className={
                            position.side === "BUY"
                              ? "bg-success text-success-foreground"
                              : "bg-loss text-loss-foreground"
                          }
                        >
                          {position.side}
                        </Badge>
                        {position.strategy_name && (
                          <Badge variant="outline" className="border-border text-muted-foreground">
                            {position.strategy_name}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-xs text-muted-foreground">Quantity</p>
                      <p className="text-foreground font-medium">
                        {formatNumber(position.quantity, { maximumFractionDigits: 0 })}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-muted-foreground">Avg Price</p>
                      <p className="text-foreground font-medium text-sm">
                        {formatCurrency(position.avg_price)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-muted-foreground">Current</p>
                      <p className="text-foreground font-medium text-sm">
                        {formatCurrency(livePnLByPositionId[position.id]?.livePrice ?? position.current_price)}
                      </p>
                    </div>
                    <div className="text-right min-w-[100px]">
                      <p className="text-xs text-muted-foreground">P&L</p>
                      <p
                        className={`font-bold ${(livePnLByPositionId[position.id]?.pnl ?? Number(position.unrealized_pnl || 0)) >= 0 ? "text-success" : "text-loss"}`}
                      >
                        {formatCurrency(livePnLByPositionId[position.id]?.pnl ?? position.unrealized_pnl)}
                      </p>
                      <p className="text-[10px] text-muted-foreground">
                        ({formatNumber(Number(livePnLByPositionId[position.id]?.pnlPercent ?? position.unrealized_pnl_pct ?? 0))}%)
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}

        </div>
      )}
          <Pagination
            page={page}
            count={metadata.count}
            pageSize={pageSize} loading={loading} onPageSizeChange={setPageSize} label="Paper positions pages"
            onPageChange={setPage}
          />
    </div>
  );
}

PaperPositions.propTypes = {
  ...PaperPositions.propTypes,
  selectedAccountId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  refreshKey: PropTypes.number,
};
