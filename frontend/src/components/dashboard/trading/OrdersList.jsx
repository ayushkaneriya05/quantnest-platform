// src/components/trading/OrdersList.jsx
import React, { useEffect, useState } from "react";
import { useTrading } from "@/contexts/TradingContext";

export default function OrdersList() {
  const trading = useTrading();
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      await trading.fetchAll();
    } catch (e) {}
    setLoading(false);
  }

  useEffect(() => {
    load();
    const onRefresh = () => load();
    window.addEventListener("quantnest:refresh_orders", onRefresh);
    return () =>
      window.removeEventListener("quantnest:refresh_orders", onRefresh);
  }, []);

  const cancel = async (id) => {
    if (!confirm("Cancel order?")) return;
    await trading.cancelOrder(id);
    await trading.fetchAll();
  };

  return (
    <div className="space-y-2">
      {loading && <div className="text-sm text-muted-foreground">loading…</div>}
      {trading.orders.map((o) => (
        <div
          key={o.id}
          className="p-2 bg-slate-800 rounded flex items-center justify-between"
        >
          <div>
            <div className="flex gap-2 items-baseline">
              <div className="font-medium">{o.symbol}</div>
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
          <div className="flex gap-2">
            {o.status === "PENDING" && (
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => cancel(o.id)}
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
