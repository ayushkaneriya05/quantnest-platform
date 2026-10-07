import { useEffect, useRef, useState, useCallback } from "react";
import { ensureFreshAccessToken, getWebSocketUrl } from "../services/api";

export function useLiveTradingWebSocket(onMessageCallback) {
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef(null);
  const activeRef = useRef(false);
  const connectionRevision = useRef(0);
  const reconnectTimer = useRef(null);
  const reconnectAttempts = useRef(0);
  const callbackRef = useRef(onMessageCallback);
  callbackRef.current = onMessageCallback;

  const connect = useCallback(async () => {
    if (!activeRef.current) return;
    if (ws.current && (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const retry = () => {
      if (!activeRef.current) return;
      const attempts = reconnectAttempts.current++;
      reconnectTimer.current = setTimeout(connect, Math.min(1000 * 2 ** Math.min(attempts, 5), 30000));
    };
    try {
      const revision = connectionRevision.current;
      await ensureFreshAccessToken();
      if (!activeRef.current || revision !== connectionRevision.current) return;
      ws.current = new WebSocket(getWebSocketUrl("/ws/live/"));

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
          const payload = data;
          if (payload?.event_type && callbackRef.current) {
            callbackRef.current(payload);
          }
        } catch (e) {
          console.error("Live WS parse error:", e);
        }
      };

      ws.current.onclose = (event) => {
        setIsConnected(false);
        if (!activeRef.current || event.code === 4401) return;
        retry();
      };
    } catch (e) {
      console.error("Live WS setup error:", e);
      retry();
    }
  }, []);

  useEffect(() => {
    activeRef.current = true;
    connect();
    return () => {
      activeRef.current = false;
      connectionRevision.current += 1;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (ws.current) {
        ws.current.onclose = null;
        ws.current.onmessage = null;
        ws.current.onopen = null;
        ws.current.close(1000, "Component unmounted");
        ws.current = null;
      }
    };
  }, [connect]);

  return { isConnected };
}
