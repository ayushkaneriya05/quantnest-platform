// src/components/trading/Orderbook.jsx
import React, { useEffect, useState, useRef } from "react";

export default function Orderbook({ symbol }) {
  const [book, setBook] = useState({ bids: [], asks: [] });
  const wsRef = useRef(null);

  useEffect(() => {
    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const url = `${protocol}://${window.location.host}/ws/orderbook/${symbol}/`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (
          message.type === "orderbook_snapshot" ||
          message.type === "orderbook_update"
        ) {
          setBook(message.data);
        }
      };

      ws.onclose = () => {
        // Optional: implement a reconnect strategy
        console.log("Orderbook WebSocket closed");
      };

      ws.onerror = (error) => {
        console.error("Orderbook WebSocket error:", error);
      };
    };

    if (symbol) {
      connect();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [symbol]);

  return (
    <div className="card p-3">
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
    </div>
  );
}
