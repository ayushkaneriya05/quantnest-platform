import React, { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import api from "@/services/api";

export default function PortfolioDisplay() {
  const { toast } = useToast();
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  // Assume you have a way to get live prices, e.g., via the WebSocket connection
  // For now, we'll mock it. In a real app, this would come from the WebSocket consumer.
  const [livePrices, setLivePrices] = useState({});

  const fetchData = useCallback(async () => {
    try {
      const posRes = await api.get("/trading/positions/");
      setPositions(posRes.data);
      const ordRes = await api.get("/trading/orders/");
      setOrders(ordRes.data.filter((o) => o.status === "OPEN"));
    } catch (error) {
      console.error("Failed to fetch portfolio data:", error);
    }
  }, []);

  useEffect(() => {
    fetchData();
    // Here you would also subscribe to your WebSocket for live price updates
  }, [fetchData]);

  const handleCancelOrder = async (orderId) => {
    try {
      await api.delete(`/trading/orders/${orderId}/`);
      toast({ title: "Success", description: "Order cancelled." });
      fetchData(); // Refresh data
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to cancel order.",
      });
    }
  };

  const calculatePnl = (position) => {
    const currentPrice =
      livePrices[position.instrument.symbol] || position.average_price;
    const pnl = (currentPrice - position.average_price) * position.quantity;
    return pnl.toFixed(2);
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-bold text-slate-100 mb-2">My Positions</h3>
        <div className="bg-gray-950 border border-gray-800 rounded-lg p-4 space-y-2">
          {positions.length > 0 ? (
            positions.map((pos) => (
              <div key={pos.id} className="grid grid-cols-4 gap-4 text-sm">
                <span className="font-medium text-slate-200">
                  {pos.instrument.symbol}
                </span>
                <span className="text-slate-300">
                  {pos.quantity} shares @ {pos.average_price}
                </span>
                {/* PnL would be calculated here */}
              </div>
            ))
          ) : (
            <p className="text-slate-500">No open positions.</p>
          )}
        </div>
      </div>
      <div>
        <h3 className="text-xl font-bold text-slate-100 mb-2">Open Orders</h3>
        <div className="bg-gray-950 border border-gray-800 rounded-lg p-4 space-y-2">
          {orders.length > 0 ? (
            orders.map((order) => (
              <div
                key={order.id}
                className="grid grid-cols-5 gap-4 items-center text-sm"
              >
                <span className="font-medium text-slate-200">
                  {order.instrument.symbol}
                </span>
                <span
                  className={
                    order.transaction_type === "BUY"
                      ? "text-green-400"
                      : "text-red-400"
                  }
                >
                  {order.transaction_type}
                </span>
                <span className="text-slate-300">
                  {order.quantity} @{" "}
                  {order.order_type === "MARKET" ? "Market" : order.price}
                </span>
                <span className="text-slate-400">{order.order_type}</span>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => handleCancelOrder(order.id)}
                >
                  Cancel
                </Button>
              </div>
            ))
          ) : (
            <p className="text-slate-500">No open orders.</p>
          )}
        </div>
      </div>
    </div>
  );
}
