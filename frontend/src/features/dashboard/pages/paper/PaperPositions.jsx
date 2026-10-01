import { useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { Layers, TrendingDown, TrendingUp } from "lucide-react";
import { paperApi } from "@/shared/services/paperApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useNotifications } from "@/shared/hooks/useNotifications";
import PaperTablePagination from "./components/PaperTablePagination";
import { formatCurrency } from "@/shared/utils/formatters";
import { useLivePositionsPnL } from "@/shared/hooks/useLivePositionsPnL";
import { usePaperTradingUpdate } from "@/shared/hooks/usePaperTradingWebSocket";

const PAGE_SIZE = 10;

export default function PaperPositions({ selectedAccountId }) {
  const { notify } = useNotifications();
  const lastMessage = usePaperTradingUpdate();
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const refreshTimerRef = useRef(null);

  const fetchPositions = async () => {
    try {
      const positionsRes = await paperApi.getPositions();
      setPositions(positionsRes.data || []);
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to load positions"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 30000);
    return () => {
      clearInterval(interval);
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!lastMessage || lastMessage.event_type !== "POSITION_UPDATE") return;
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    refreshTimerRef.current = setTimeout(fetchPositions, 150);
  }, [lastMessage]);

  const filteredPositions = useMemo(
    () =>
      positions.filter(
        (position) => String(position.account) === String(selectedAccountId),
      ),
    [positions, selectedAccountId],
  );
  const { livePnLByPositionId } = useLivePositionsPnL(filteredPositions);

  useEffect(() => setPage(1), [selectedAccountId]);
  const pageCount = Math.max(1, Math.ceil(filteredPositions.length / PAGE_SIZE));
  const pagePositions = filteredPositions.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

  const totalValue = filteredPositions.reduce(
    (sum, position) => {
      const livePosition = livePnLByPositionId[position.id];
      const currentPrice = livePosition?.livePrice ?? Number(position.current_price || 0);
      return sum + currentPrice * Number(position.quantity || 0);
    },
    0,
  );
  const totalUnrealizedPnl = filteredPositions.reduce(
    (sum, position) => sum + (livePnLByPositionId[position.id]?.pnl ?? Number(position.unrealized_pnl || 0)),
    0,
  );

  if (loading) return null;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="grid grid-cols-3 gap-4">
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-white">
              {filteredPositions.length}
            </p>
            <p className="text-xs text-gray-400">Open Positions</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-white">
              {formatCurrency(totalValue)}
            </p>
            <p className="text-xs text-gray-400">Total Value</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p
              className={`text-2xl font-bold ${totalUnrealizedPnl >= 0 ? "text-green-400" : "text-red-400"}`}
            >
              {totalUnrealizedPnl >= 0 ? "+" : ""}
              {formatCurrency(totalUnrealizedPnl)}
            </p>
            <p className="text-xs text-gray-400">Unrealized P&L</p>
          </CardContent>
        </Card>
      </div>

      {filteredPositions.length === 0 ? (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-12 text-center">
            <Layers className="h-10 w-10 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-300">
              No open positions
            </h3>
            <p className="text-gray-500 text-sm">
              Place orders in this account to open positions.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {pagePositions.map((position) => (
            <Card key={position.id} className="bg-gray-900/50 border-gray-800 hover:border-gray-700 transition-colors">
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div
                      className={`p-3 rounded-lg ${position.side === "BUY" ? "bg-emerald-500/10" : "bg-rose-500/10"}`}
                    >
                      {position.side === "BUY" ? (
                        <TrendingUp className="h-6 w-6 text-emerald-400" />
                      ) : (
                        <TrendingDown className="h-6 w-6 text-rose-400" />
                      )}
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-white">
                        {position.instrument_symbol}
                      </h3>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge
                          className={
                            position.side === "BUY"
                              ? "bg-emerald-600"
                              : "bg-rose-600"
                          }
                        >
                          {position.side}
                        </Badge>
                        {position.strategy_name && (
                          <Badge variant="outline" className="border-gray-700 text-gray-400">
                            {position.strategy_name}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-8">
                    <div className="text-right">
                      <p className="text-xs text-gray-500">Quantity</p>
                      <p className="text-white font-medium">
                        {position.quantity}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-500">Avg Price</p>
                      <p className="text-white font-medium text-sm">
                        {formatCurrency(position.avg_price)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-500">Current</p>
                      <p className="text-white font-medium text-sm">
                        {formatCurrency(livePnLByPositionId[position.id]?.livePrice ?? position.current_price)}
                      </p>
                    </div>
                    <div className="text-right min-w-[100px]">
                      <p className="text-xs text-gray-500">P&L</p>
                      <p
                        className={`font-bold ${(livePnLByPositionId[position.id]?.pnl ?? Number(position.unrealized_pnl || 0)) >= 0 ? "text-emerald-400" : "text-rose-400"}`}
                      >
                        {formatCurrency(livePnLByPositionId[position.id]?.pnl ?? position.unrealized_pnl)}
                      </p>
                      <p className="text-[10px] text-gray-500">
                        ({Number(livePnLByPositionId[position.id]?.pnlPercent ?? position.unrealized_pnl_pct ?? 0).toFixed(2)}%)
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
          <PaperTablePagination
            page={page}
            count={filteredPositions.length}
            pageSize={PAGE_SIZE}
            onPageChange={(nextPage) => setPage(Math.min(nextPage, pageCount))}
          />
        </div>
      )}
    </div>
  );
}
