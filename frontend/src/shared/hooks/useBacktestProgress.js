/**
 * useBacktestProgress — WebSocket hook for real-time backtest progress updates
 * Replaces polling with real-time WebSocket updates for better UX
 */
import { useEffect, useRef, useCallback } from "react";

const getWsUrl = () => {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const host =
    window.location.hostname === "localhost"
      ? "localhost:8000"
      : window.location.host;
  return `${protocol}://${host}/ws/backtest/progress/`;
};

export const useBacktestProgress = (
  backtestId,
  onProgress,
  onComplete,
  onError,
) => {
  const wsRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttemptsRef = useRef(5);
  const reconnectTimeoutRef = useRef(null);
  const isIntentionalCloseRef = useRef(false);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    isIntentionalCloseRef.current = false;

    try {
      const token = localStorage.getItem("accessToken");
      const wsUrlWithToken = `${getWsUrl()}?token=${encodeURIComponent(token)}`;

      wsRef.current = new WebSocket(wsUrlWithToken);

      wsRef.current.onopen = () => {
        console.log("✅ Connected to backtest progress stream");
        reconnectAttemptsRef.current = 0;
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (!backtestId || data.run_id === backtestId) {
            if (data.status === "COMPLETED") {
              onComplete?.(data);
            } else if (data.status === "FAILED") {
              onError?.(data);
            } else {
              onProgress?.(data);
            }
          }
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error("❌ WebSocket error:", error);
        onError?.({ error: "Connection error" });
      };

      wsRef.current.onclose = () => {
        console.log("🔌 Disconnected from backtest progress stream");
        if (!isIntentionalCloseRef.current) {
          attemptReconnect();
        }
      };
    } catch (err) {
      console.error("Failed to create WebSocket:", err);
      attemptReconnect();
    }
  }, [backtestId, onProgress, onComplete, onError]);

  const attemptReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= maxReconnectAttemptsRef.current) {
      console.warn("Max reconnection attempts reached");
      return;
    }

    const delay = Math.min(
      1000 * Math.pow(2, reconnectAttemptsRef.current),
      10000,
    );
    reconnectAttemptsRef.current += 1;

    console.log(
      `Attempting reconnect in ${delay}ms... (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttemptsRef.current})`,
    );

    reconnectTimeoutRef.current = setTimeout(connect, delay);
  }, [connect]);

  useEffect(() => {
    connect();

    return () => {
      isIntentionalCloseRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return wsRef.current;
};
