// src/components/trading/PositionsList.jsx
import React from "react";
import { useTrading } from "@/contexts/TradingContext";

export default function PositionsList() {
  const trading = useTrading();

  if (!trading.positions || trading.positions.length === 0) {
    return <div className="text-sm text-muted-foreground">No positions</div>;
  }

  return (
    <div className="space-y-2">
      {trading.positions.map((p) => (
        <div
          key={p.symbol}
          className="p-2 bg-slate-800 rounded flex items-center justify-between"
        >
          <div>
            <div className="font-medium">
              {p.symbol}{" "}
              <span className="text-xs text-muted-foreground">
                {p.qty > 0 ? "LONG" : p.qty < 0 ? "SHORT" : "FLAT"}
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              Avg {p.avg_price} • R {p.realized_pnl} • U {p.unrealized_pnl}
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="text-xs">SL: {p.sl_price ?? "-"}</div>
            <div className="text-xs">TP: {p.tp_price ?? "-"}</div>
            <div>
              <button
                className="btn btn-ghost btn-sm"
                onClick={async () => {
                  const sl = prompt("SL price", p.sl_price || "");
                  const tp = prompt("TP price", p.tp_price || "");
                  if (sl === null && tp === null) return;
                  await trading.fetchAll(); // use endpoint /positions/<id>/sl_tp/ if available
                  // call API directly if context provides modifyPosition - otherwise refresh
                }}
              >
                Modify
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
