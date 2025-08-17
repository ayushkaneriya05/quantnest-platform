// src/components/trading/Orderbook.jsx
import React, { useEffect, useState } from "react";
import api from "@/services/api";

export default function Orderbook({ symbol }) {
  const [book, setBook] = useState({ bids: [], asks: [] });

  async function load() {
    if (!symbol) return;
    try {
      const res = await api.get(
        `/paper/orderbook/${encodeURIComponent(symbol)}/?depth=8`
      );
      setBook(res.data || res);
    } catch (e) {
      // fallback: empty
    }
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
  }, [symbol]);

  return (
    <Card className="p-3">
      <div className="font-semibold mb-2">Orderbook</div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <div className="text-xs text-muted-foreground mb-1">Bids</div>
          <ul className="space-y-1">
            {book.bids?.map((b, i) => (
              <li key={i} className="flex justify-between">
                <span>{b.qty}</span>
                <span>{b.price}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="text-xs text-muted-foreground mb-1">Asks</div>
          <ul className="space-y-1">
            {book.asks?.map((a, i) => (
              <li key={i} className="flex justify-between">
                <span>{a.price}</span>
                <span>{a.qty}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}
