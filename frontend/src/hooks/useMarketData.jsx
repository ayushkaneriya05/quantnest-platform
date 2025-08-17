// src/hooks/useMarketData.js
import { useEffect, useRef, useState } from "react";

export default function useMarketData(symbol, onUserMessage) {
  const wsRef = useRef(null);
  const [tick, setTick] = useState(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!symbol) return;
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const token =
      localStorage.getItem("token") || localStorage.getItem("accessToken");
    const tokenQs = token ? `?token=${encodeURIComponent(token)}` : "";
    const wsUrl = `${protocol}://${window.location.host}/ws/marketdata/${tokenQs}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      ws.send(JSON.stringify({ action: "subscribe", symbol }));
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "tick" && msg.data && msg.data.symbol === symbol) {
          setTick(msg.data);
        } else {
          onUserMessage && onUserMessage(msg);
        }
      } catch (err) {
        // ignore parse error
      }
    };

    ws.onclose = () => {
      setConnected(false);
      // simple reconnect after short delay (improve in prod)
      setTimeout(() => window.location.reload(), 1500);
    };

    return () => {
      try {
        ws.send(JSON.stringify({ action: "unsubscribe", symbol }));
      } catch (e) {}
      try {
        ws.close();
      } catch (e) {}
    };
  }, [symbol]);

  return { tick, connected, ws: wsRef.current };
}
