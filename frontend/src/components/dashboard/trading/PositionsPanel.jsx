// src/components/trading/PositionsPanel.jsx
import React, { useEffect, useState } from "react";
import { useTrading } from "@/contexts/TradingContext";

export default function PositionsPanel() {
  const { positions, fetchAll, modifyPositionSLTP } = useTrading();

  useEffect(() => {
    const id = setInterval(fetchAll, 5000);
    return () => clearInterval(id);
  }, [fetchAll]);

  async function handleModify(pos) {
    const sl = prompt("SL price", pos.sl_price || "");
    const tp = prompt("TP price", pos.tp_price || "");
    if (sl !== null || tp !== null) {
      try {
        await modifyPositionSLTP(pos.id, sl || null, tp || null);
      } catch (e) {
        alert("Failed to update SL/TP");
      }
    }
  }

  return (
    <div className="card p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="font-semibold">Positions</div>
      </div>
      <div className="space-y-2">
        {positions.length === 0 && (
          <div className="text-sm text-muted-foreground">No positions</div>
        )}
        {positions.map((p) => (
          <div
            key={p.symbol}
            className="bg-muted/20 p-2 rounded flex items-center justify-between"
          >
            <div>
              <div className="font-medium">
                {p.symbol}{" "}
                <span className="text-xs text-muted-foreground">
                  {p.qty > 0 ? "LONG" : p.qty < 0 ? "SHORT" : "FLAT"}
                </span>
              </div>
              <div className="text-xs text-muted-foreground">
                Avg {p.avg_price} • Realized {p.realized_pnl} • Unrealized{" "}
                {p.unrealized_pnl}
              </div>
            </div>
            <div className="flex flex-col items-end gap-2">
              <div className="text-xs">SL: {p.sl_price ?? "-"}</div>
              <div className="text-xs">TP: {p.tp_price ?? "-"}</div>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => handleModify(p)}
              >
                Modify
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
