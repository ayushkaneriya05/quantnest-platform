// src/components/dashboard/trading/Positions.jsx
import React from "react";
import { useTrading } from "@/contexts/TradingContext";
import api from "@/services/api";

export default function Positions() {
  const { positions, fetchAll } = useTrading();

  const handleModify = async (p) => {
    const sl = prompt(
      "Enter new Stop Loss price (leave blank to remove):",
      p.sl_price || ""
    );
    const tp = prompt(
      "Enter new Take Profit price (leave blank to remove):",
      p.tp_price || ""
    );

    if (sl === null && tp === null) return;

    try {
      await api.post(`/paper/positions/${p.id}/modify/`, {
        sl_price: sl || null,
        tp_price: tp || null,
      });
      await fetchAll();
    } catch (e) {
      alert(
        "Failed to update SL/TP. Ensure the backend endpoint is implemented."
      );
    }
  };

  const handleClose = async (p) => {
    if (
      !confirm(`Are you sure you want to close your position in ${p.symbol}?`)
    )
      return;

    try {
      const side = p.qty > 0 ? "SELL" : "BUY";
      await api.post("/paper/orders/", {
        symbol: p.symbol,
        side: side,
        qty: Math.abs(p.qty),
        order_type: "MARKET",
        product_type: "NRML",
      });
      await fetchAll();
    } catch (e) {
      alert("Failed to close position.");
    }
  };

  return (
    <div className="card p-3">
      <div className="font-semibold mb-2">Positions</div>
      <div className="space-y-2">
        {!positions || positions.length === 0 ? (
          <div className="text-sm text-muted-foreground">
            No open positions.
          </div>
        ) : (
          positions.map((p) => (
            <div
              key={p.symbol}
              className="p-2 bg-slate-800 rounded flex items-center justify-between"
            >
              <div>
                <div className="font-medium">
                  {p.symbol}{" "}
                  <span
                    className={`text-xs ${
                      p.qty > 0 ? "text-green-400" : "text-red-400"
                    }`}
                  >
                    {p.qty > 0 ? "LONG" : "SHORT"} ({p.qty})
                  </span>
                </div>
                <div className="text-xs text-muted-foreground">
                  Avg: {p.avg_price} | R PNL: {p.realized_pnl} | U PNL:{" "}
                  {p.unrealized_pnl}
                </div>
                <div className="text-xs">
                  SL: {p.sl_price ?? "-"} | TP: {p.tp_price ?? "-"}
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                <button
                  className="btn btn-xs btn-outline"
                  onClick={() => handleModify(p)}
                >
                  Modify
                </button>
                <button
                  className="btn btn-xs btn-danger"
                  onClick={() => handleClose(p)}
                >
                  Close
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
