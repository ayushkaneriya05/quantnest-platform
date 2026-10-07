import { useEffect, useRef } from "react";
import { ensureFreshAccessToken, getWebSocketUrl } from "../services/api";

export function useBacktestProgress(backtestId, onProgress, onComplete, onError, onReconnect) {
  const socketRef = useRef(null);
  const callbacks = useRef({});
  callbacks.current = { onProgress, onComplete, onError, onReconnect };

  useEffect(() => {
    let disposed = false;
    let timer;
    let attempts = 0;
    let hasConnected = false;

    const retry = () => {
      if (!disposed) timer = setTimeout(connect, Math.min(1000 * 2 ** Math.min(attempts++, 5), 30000));
    };
    async function connect() {
      try {
        await ensureFreshAccessToken();
        if (disposed) return;
        const socket = new WebSocket(getWebSocketUrl("/ws/backtest/progress/"));
        socketRef.current = socket;
        socket.onopen = () => {
          attempts = 0;
          if (hasConnected) callbacks.current.onReconnect?.();
          hasConnected = true;
        };
        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.run_id == null || (backtestId && String(data.run_id) !== String(backtestId))) return;
            if (["COMPLETED", "CANCELLED"].includes(data.status)) callbacks.current.onComplete?.(data);
            else if (data.status === "FAILED") callbacks.current.onError?.(data);
            else callbacks.current.onProgress?.(data);
          } catch (error) {
            console.error("Could not process backtest progress", error);
          }
        };
        socket.onclose = (event) => {
          if (event.code !== 4401) retry();
        };
      } catch {
        retry();
      }
    }
    connect();
    return () => {
      disposed = true;
      clearTimeout(timer);
      if (socketRef.current) {
        socketRef.current.onmessage = null;
        socketRef.current.onclose = null;
        socketRef.current.onopen = null;
        socketRef.current.close();
      }
      socketRef.current = null;
    };
  }, [backtestId]);

  return socketRef.current;
}
