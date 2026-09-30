import { useEffect, useRef, useState, useCallback } from "react";

export function useLiveTradingWebSocket(onMessageCallback) {
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef(null);
  const activeRef = useRef(false);
  const reconnectTimer = useRef(null);
  const reconnectAttempts = useRef(0);
  const callbackRef = useRef(onMessageCallback);
  callbackRef.current = onMessageCallback;

  const connect = useCallback(() => {
    if (!activeRef.current) return;
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
          // Current backend payload is {event_type, data}; accept the previous
          // wrapper during rolling deployments while both server versions run.
          const payload = data.event_type ? data : data.message;
          if (payload?.event_type && callbackRef.current) {
            callbackRef.current(payload);
          }
        } catch (e) {
          console.error("Live WS parse error:", e);
        }
      };

      ws.current.onclose = () => {
        setIsConnected(false);
        if (!activeRef.current) return;
        const attempts = reconnectAttempts.current;
        reconnectAttempts.current += 1;
        const delay = Math.min(1000 * 2 ** attempts, 30000);
        reconnectTimer.current = setTimeout(() => connect(), delay);
      };
    } catch (e) {
      console.error("Live WS setup error:", e);
    }
  }, []);

  useEffect(() => {
    activeRef.current = true;
    connect();
    return () => {
      activeRef.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (ws.current) ws.current.close(1000, "Component unmounted");
    };
  }, [connect]);

  return { isConnected };
}
