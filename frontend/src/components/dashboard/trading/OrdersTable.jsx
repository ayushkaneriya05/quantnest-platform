// src/components/trading/OrdersTable.jsx
import React, { useEffect, useState } from "react";
import api from "@/services/api";
import { cn } from "@/lib/utils";

export default function OrdersTable() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const res = await api.get("/paper/orders/list/");
      setOrders(res.data || res);
    } catch (e) {
      console.warn(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    window.addEventListener("quantnest:refresh_orders", load);
    return () => window.removeEventListener("quantnest:refresh_orders", load);
  }, []);

  async function cancel(o) {
    try {
      await api.post(`/paper/orders/${o.id}/cancel/`, {});
      load();
    } catch (e) {
      alert("Cancel failed");
    }
  }

  return (
    <div className="card p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="font-semibold">Orders</div>
        <div className="text-sm text-muted-foreground">
          {orders.length} recent
        </div>
      </div>

      <div className="space-y-2">
        {loading && (
          <div className="text-sm text-muted-foreground">loading…</div>
        )}
        {orders.map((o) => (
          <div
            key={o.id}
            className="flex items-center justify-between bg-muted/20 p-2 rounded"
          >
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <div className="text-sm font-medium">{o.symbol}</div>
                <div className="text-xs text-muted-foreground">
                  {o.order_type}
                </div>
                <div className="text-xs">{o.status}</div>
              </div>
              <div className="text-xs text-muted-foreground">
                qty {o.qty} • filled {o.filled_qty} • avg{" "}
                {o.avg_fill_price ?? "-"}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {o.status === "PENDING" && (
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => cancel(o)}
                >
                  Cancel
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
