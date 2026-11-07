import Pagination from "@/shared/components/Pagination";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { usePagination } from "@/shared/hooks/usePagination";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import {useStableCallback} from "@/shared/hooks/useStableCallback";
import PropTypes from "prop-types";
import { useEffect, useRef, useState } from "react";
import {
  Card,
  CardContent,
} from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { OverflowTooltip } from "@/shared/components/ui/tooltip";
import { paperApi } from "@/shared/services/paperApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { usePaperTradingUpdate } from "@/shared/hooks/usePaperTradingWebSocket";
import { formatCurrency, formatDateTime, formatNumber } from "@/shared/utils/formatters";

const ORDER_STATUS_STYLES = {
  PENDING: "bg-warning/10 text-warning border-warning/30",
  PLACED: "bg-brand/10 text-brand border-brand/30",
  PARTIAL_FILL: "bg-brand/10 text-brand border-brand/30",
  FILLED: "bg-success/10 text-success border-success/30",
  CANCELLED: "bg-muted/10 text-muted-foreground border-border/30",
  REJECTED: "bg-loss/10 text-loss border-loss/30",
  EXPIRED: "bg-muted/10 text-muted-foreground border-border/30",
};

export default function PaperOrderBook({ selectedAccountId, refreshKey = 0 }) {
  const fetchData = useStableCallback(async () => {
    const generation = ++request.current;
    setLoading(true);
    setError("");
    try {
      const response = await paperApi.getOrders({ page, page_size: pageSize, account_id: selectedAccountId || undefined });
      if (generation !== request.current) return;
      setOrders(response.data.results);
      setMetadata(response.data);
      accept(response.data);
    } catch (error) {
      if (generation === request.current) setError(getApiErrorMessage(error, "Could not load orders."));
    } finally { if (generation === request.current) setLoading(false); }
  });

  const { notify } = useNotifications();
  const lastMessage = usePaperTradingUpdate();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { page, pageSize, setPage, setPageSize, accept } = usePagination(String(selectedAccountId), 'orders');
  const [metadata, setMetadata] = useState({ count: 0 });
  const [summary, setSummary] = useState({});
  const request = useRef(0);
  useEffect(() => {
    setOrders([]); setSummary({});
    const guard = request; return () => { guard.current++; };
  }, [selectedAccountId]);



  useEffect(() => {
    const timer = setTimeout(fetchData, 0);
    const guard = request;
    return () => { clearTimeout(timer); guard.current++; };
  }, [fetchData, page, pageSize, selectedAccountId, refreshKey]);

  useEffect(() => {
    if (lastMessage?.event_type === "ORDER_UPDATE") {
      fetchData();
    }
  }, [lastMessage, fetchData]);

  useEffect(() => {
    const controller = new AbortController();
    paperApi.getOrdersSummary({ account_id: selectedAccountId || undefined }, controller.signal)
      .then(response => { if (!controller.signal.aborted) setSummary(response.data); })
      .catch(error => { if (!controller.signal.aborted) notify.error(getApiErrorMessage(error, "Could not load summary.")); });
    return () => controller.abort();
  }, [selectedAccountId, refreshKey, lastMessage, notify]);
  if (error) return <WorkspaceState error={error} onRetry={fetchData} />;
  if (loading && !metadata.page) return <GlobalLoader fullHeight={false} />;

  return (
    <div className="space-y-3 animate-in fade-in duration-300">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { label: "Total orders", value: summary.total, color: "text-foreground" },
          { label: "Filled", value: summary.filled, color: "text-success" },
          { label: "Active", value: summary.active, color: "text-warning" },
          { label: "Rejected", value: summary.rejected, color: "text-loss" },
        ].map((item) => (
          <Card key={item.label} className="bg-card/50 border-border">
            <CardContent className="py-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">{item.label}</p>
              <p className={`mt-2 text-2xl font-bold ${item.color}`}>{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card className="bg-card/50 border-border">
        <CardContent className="p-0">
          {metadata.count === 0 ? (
            <div className="p-12 text-center text-muted-foreground italic text-sm">
              No orders found.
            </div>
          ) : (
            <div className="overflow-x-auto scrollbar-thin-theme">
              <table className="w-full text-sm">
                <thead className="bg-secondary/20 border-b border-border">
                  <tr className="text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                    <th className="px-4 py-3 font-medium">Placed / Filled</th>
                    <th className="px-4 py-3 font-medium">Symbol</th>
                    <th className="px-4 py-3 font-medium">Side</th>
                    <th className="px-4 py-3 font-medium">Qty / Filled</th>
                    <th className="px-4 py-3 font-medium">Fill Price</th>
                    <th className="px-4 py-3 font-medium text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {orders.map((order) => (
                    <tr key={order.id} className="hover:bg-secondary/10 transition-colors">
                      <td className="px-4 py-3 text-muted-foreground font-mono text-[12px] whitespace-nowrap">
                        <span className="block">{formatDateTime(order.placed_at)}</span>
                        {order.executed_at && (
                          <span className="block mt-1 text-[10px]">
                            Filled: {formatDateTime(order.executed_at)}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col">
                          <span className="text-foreground font-medium">{order.instrument_symbol}</span>
                          <span className="text-[10px] text-muted-foreground">{order.strategy_name || "Manual"}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          className={`text-[10px] h-5 px-1.5 ${
                            order.side === "BUY"
                              ? "bg-success/10 text-success border-success/20"
                              : "bg-loss/10 text-loss border-loss/20"
                          }`}
                        >
                          {order.side}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-foreground font-medium">
                        {formatNumber(order.quantity, { maximumFractionDigits: 0 })} <span className="text-muted-foreground">/ {formatNumber(order.filled_quantity, { maximumFractionDigits: 0 })}</span>
                      </td>
                      <td className="px-4 py-3 text-foreground font-mono text-[12px]">
                        {order.avg_fill_price ? formatCurrency(order.avg_fill_price) : "-"}
                        {order.status === "FILLED" && Number(order.slippage_amount || 0) > 0 && (
                          <span className="block text-[10px] text-muted-foreground">
                            Slippage {formatCurrency(order.slippage_amount)} ({formatNumber(Number(order.slippage_pct_applied || 0))}%)
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex flex-col items-end">
                          <Badge className={`text-[10px] h-5 px-1.5 ${ORDER_STATUS_STYLES[order.status] || "bg-muted/10 text-muted-foreground border-border/30"}`}>
                            {order.status}
                          </Badge>
                          {order.status === "REJECTED" && order.rejection_reason && (
                            <OverflowTooltip className="text-[10px] text-loss mt-1 max-w-[150px]">
                              {order.rejection_reason}
                            </OverflowTooltip>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
        {(
          <Pagination page={page} count={metadata.count} pageSize={pageSize} loading={loading} onPageSizeChange={setPageSize} label="Paper orders pages" onPageChange={setPage} />
        )}
      </Card>
    </div>
  );
}

PaperOrderBook.propTypes = {
  ...PaperOrderBook.propTypes,
  selectedAccountId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  refreshKey: PropTypes.number,
};
