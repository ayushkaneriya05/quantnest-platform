import React, { useEffect, useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { paperApi } from "@/shared/services/paperApi";
import { useNotifications } from "@/shared/hooks/useNotifications";

const ORDER_STATUS_STYLES = {
  PENDING: { bg: "bg-yellow-600" },
  PLACED: { bg: "bg-blue-600" },
  FILLED: { bg: "bg-green-600" },
  CANCELLED: { bg: "bg-gray-600" },
  REJECTED: { bg: "bg-red-600" },
};

export default function PaperOrderBook({ selectedAccountId }) {
  const { notify } = useNotifications();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const ordersData = await paperApi.getOrders();
      setOrders(ordersData.data || []);
    } catch (error) {
      notify.error("Failed to load order history");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const filteredOrders = useMemo(
    () =>
      orders.filter(
        (order) => String(order.account) === String(selectedAccountId),
      ),
    [orders, selectedAccountId],
  );

  const formatTime = (dateString) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading) return null;

  if (loading) return null;

  const handleCancelOrder = async (orderId) => {
    try {
      await paperApi.cancelOrder(orderId);
      notify.success("Order cancelled");
      fetchData();
    } catch (error) {
      notify.error("Failed to cancel order");
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-white text-base">Order Book</CardTitle>
          <Badge variant="outline" className="text-[10px] text-gray-500 border-gray-800">
            {filteredOrders.length} records
          </Badge>
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
                    <th className="px-4 py-3 font-medium">Qty</th>
                    <th className="px-4 py-3 font-medium">Fill Price</th>
                    <th className="px-4 py-3 font-medium text-right">Status</th>
                    <th className="px-4 py-3 font-medium text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/50">
                  {filteredOrders.slice(0, 50).map((order) => (
                    <tr key={order.id} className="hover:bg-gray-800/10 transition-colors">
                      <td className="px-4 py-3 text-gray-400 font-mono text-[12px]">
                        {formatTime(order.executed_at || order.placed_at)}
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
                        {order.filled_quantity}
                      </td>
                      <td className="px-4 py-3 text-white font-mono text-[12px]">
                        {order.avg_fill_price
                          ? `₹${parseFloat(order.avg_fill_price).toFixed(2)}`
                          : "-"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex flex-col items-end">
                          <Badge className={`text-[10px] h-5 px-1.5 ${ORDER_STATUS_STYLES[order.status]?.bg || "bg-gray-600"} bg-opacity-20 border-opacity-30`}>
                            {order.status}
                          </Badge>
                          {order.status === "REJECTED" && order.rejection_reason && (
                            <span className="text-[10px] text-red-400 mt-1 max-w-[150px] truncate" title={order.rejection_reason}>
                              {order.rejection_reason}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        {order.status === "PENDING" && (
                          <button
                            onClick={() => handleCancelOrder(order.id)}
                            className="text-[11px] text-red-400 hover:text-red-300 transition-colors underline"
                          >
                            Cancel
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
