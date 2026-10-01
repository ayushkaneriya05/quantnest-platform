import React, { useEffect, useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { paperApi } from "@/shared/services/paperApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { usePaperTradingUpdate } from "@/shared/hooks/usePaperTradingWebSocket";
import { formatCurrency, formatDateTime } from "@/shared/utils/formatters";
import PaperTablePagination from "./components/PaperTablePagination";

const ORDER_STATUS_STYLES = {
  PENDING: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  PLACED: "bg-sky-500/10 text-sky-400 border-sky-500/30",
  PARTIAL_FILL: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  FILLED: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  CANCELLED: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  REJECTED: "bg-rose-500/10 text-rose-400 border-rose-500/30",
  EXPIRED: "bg-slate-500/10 text-slate-400 border-slate-500/30",
};
const PAGE_SIZE = 10;

export default function PaperOrderBook({ selectedAccountId }) {
  const { notify } = useNotifications();
  const lastMessage = usePaperTradingUpdate();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  const fetchData = async () => {
    try {
      const ordersData = await paperApi.getOrders();
      setOrders(ordersData.data || []);
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to load order history"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (lastMessage?.event_type === "ORDER_UPDATE") {
      fetchData();
    }
  }, [lastMessage]);

  const filteredOrders = useMemo(
    () =>
      orders.filter(
        (order) => String(order.account) === String(selectedAccountId),
      ),
    [orders, selectedAccountId],
  );

  useEffect(() => setPage(1), [selectedAccountId]);

  const orderStats = useMemo(() => ({
    total: filteredOrders.length,
    filled: filteredOrders.filter((order) => order.status === "FILLED").length,
    active: filteredOrders.filter((order) => ["PENDING", "PLACED", "PARTIAL_FILL"].includes(order.status)).length,
    rejected: filteredOrders.filter((order) => order.status === "REJECTED").length,
  }), [filteredOrders]);
  const pageCount = Math.max(1, Math.ceil(filteredOrders.length / PAGE_SIZE));
  const pageOrders = filteredOrders.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

  if (loading) return null;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { label: "Total orders", value: orderStats.total, color: "text-white" },
          { label: "Filled", value: orderStats.filled, color: "text-emerald-400" },
          { label: "Active", value: orderStats.active, color: "text-amber-400" },
          { label: "Rejected", value: orderStats.rejected, color: "text-rose-400" },
        ].map((item) => (
          <Card key={item.label} className="bg-gray-900/50 border-gray-800">
            <CardContent className="py-4">
              <p className="text-xs uppercase tracking-wide text-gray-500">{item.label}</p>
              <p className={`mt-2 text-2xl font-bold ${item.color}`}>{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader className="flex flex-row items-center justify-between py-2">
          <CardTitle className="text-white text-base">Order Book</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {filteredOrders.length === 0 ? (
            <div className="p-12 text-center text-gray-500 italic text-sm">
              No orders found.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-800/20 border-y border-gray-800">
                  <tr className="text-left text-[11px] uppercase tracking-wider text-gray-500">
                    <th className="px-4 py-3 font-medium">Time</th>
                    <th className="px-4 py-3 font-medium">Symbol</th>
                    <th className="px-4 py-3 font-medium">Side</th>
                    <th className="px-4 py-3 font-medium">Qty / Filled</th>
                    <th className="px-4 py-3 font-medium">Fill Price</th>
                    <th className="px-4 py-3 font-medium text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/50">
                  {pageOrders.map((order) => (
                    <tr key={order.id} className="hover:bg-gray-800/10 transition-colors">
                      <td className="px-4 py-3 text-gray-400 font-mono text-[12px] whitespace-nowrap">
                        {formatDateTime(order.executed_at || order.placed_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col">
                          <span className="text-white font-medium">{order.instrument_symbol}</span>
                          <span className="text-[10px] text-gray-500">{order.strategy_name || "Manual"}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          className={`text-[10px] h-5 px-1.5 ${
                            order.side === "BUY" 
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" 
                              : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                          }`}
                        >
                          {order.side}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-gray-300 font-medium">
                        {order.quantity} <span className="text-gray-500">/ {order.filled_quantity}</span>
                      </td>
                      <td className="px-4 py-3 text-white font-mono text-[12px]">
                        {order.avg_fill_price ? formatCurrency(order.avg_fill_price) : "-"}
                        {order.status === "FILLED" && Number(order.slippage_amount || 0) > 0 && (
                          <span className="block text-[10px] text-gray-500">
                            Slippage {formatCurrency(order.slippage_amount)} ({Number(order.slippage_pct_applied || 0).toFixed(4)}%)
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex flex-col items-end">
                          <Badge className={`text-[10px] h-5 px-1.5 ${ORDER_STATUS_STYLES[order.status] || "bg-slate-500/10 text-slate-400 border-slate-500/30"}`}>
                            {order.status}
                          </Badge>
                          {order.status === "REJECTED" && order.rejection_reason && (
                            <span className="text-[10px] text-red-400 mt-1 max-w-[150px] truncate" title={order.rejection_reason}>
                              {order.rejection_reason}
                            </span>
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
        {filteredOrders.length > 0 && (
          <PaperTablePagination page={page} count={filteredOrders.length} pageSize={PAGE_SIZE} onPageChange={(nextPage) => setPage(Math.min(nextPage, pageCount))} />
        )}
      </Card>
    </div>
  );
}
