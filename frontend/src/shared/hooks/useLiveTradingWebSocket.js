import { useEffect, useRef, useState, useCallback } from "react";
import toast from "react-hot-toast";

export function useLiveTradingWebSocket(onMessageCallback) {
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef(null);
  const reconnectTimer = useRef(null);
  const reconnectAttempts = useRef(0);

  const connect = useCallback(() => {
    if (ws.current && (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      const token = localStorage.getItem("accessToken");
      if (!token) return;

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.hostname === "localhost" ? "localhost:8000" : window.location.host;
      const wsUrl = `${protocol}//${host}/ws/live/?token=${token}`;
      
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setIsConnected(true);
        reconnectAttempts.current = 0;
        if (reconnectTimer.current) {
          clearTimeout(reconnectTimer.current);
          reconnectTimer.current = null;
        }
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "live_update" || data.type === "live.update") {
            const payload = data.message || data;
            if (onMessageCallback) {
              onMessageCallback(payload);
            }
          }
        } catch (e) {
          console.error("Live WS parse error:", e);
        }
      };

      ws.current.onclose = () => {
        setIsConnected(false);
        const attempts = reconnectAttempts.current;
        if (attempts < 5) {
          reconnectAttempts.current += 1;
          const delay = Math.min(1000 * 2 ** attempts, 30000);
          reconnectTimer.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          toast.error("Live trading websocket disconnected.");
        }
      };
    } catch (e) {
      console.error("Live WS setup error:", e);
    }
  }, [onMessageCallback]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (ws.current) ws.current.close(1000, "Component unmounted");
    };
  }, [connect]);

  return { isConnected };
}
