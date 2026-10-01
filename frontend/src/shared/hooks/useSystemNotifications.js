import { useEffect, useRef, useState, useCallback } from "react";
import { useSelector } from "react-redux";
import { useNotifications } from "./useNotifications";
import { notificationApi } from "../services/notificationApi";

export function useSystemNotifications() {
  const { notify } = useNotifications();
  const accessToken = useSelector((state) => state.auth.accessToken);
  const [unreadCount, setUnreadCount] = useState(0);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef(null);
  const seenNotificationIdsRef = useRef(new Set());
  const reconnectTimeoutRef = useRef(null);
  const stableConnectionTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);

  const connect = useCallback(() => {
    if (!accessToken) return;

    if (
      socketRef.current?.readyState === WebSocket.OPEN ||
      socketRef.current?.readyState === WebSocket.CONNECTING
    ) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.hostname === "localhost" ? "localhost:8000" : window.location.host;
    const wsUrl = `${protocol}//${host}/ws/notifications/?token=${encodeURIComponent(accessToken)}`;

    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      setConnected(true);
      // A successful reconnect can miss notifications sent while offline.
      // Refresh the persisted count so the badge recovers without a page reload.
      notificationApi.getSummary()
        .then(({ data }) => {
          if (socketRef.current === socket) {
            setUnreadCount(Math.max(0, Number(data?.unread) || 0));
          }
        })
        .catch((error) => {
          console.error("Failed to refresh unread notification count", error);
        });

      if (stableConnectionTimeoutRef.current) {
        clearTimeout(stableConnectionTimeoutRef.current);
      }
      stableConnectionTimeoutRef.current = setTimeout(() => {
        reconnectAttemptsRef.current = 0;
        stableConnectionTimeoutRef.current = null;
      }, 30000);
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "notification" && payload.data) {
          const { id, title, message, type } = payload.data;
          if (id != null) {
            if (seenNotificationIdsRef.current.has(String(id))) return;
            seenNotificationIdsRef.current.add(String(id));
            if (seenNotificationIdsRef.current.size > 500) {
              const oldestId = seenNotificationIdsRef.current.values().next().value;
              seenNotificationIdsRef.current.delete(oldestId);
            }
          }
          
          // Increment unread count globally
          setUnreadCount((prev) => prev + 1);

          const notifyByType = {
            INFO: notify.info,
            WARNING: notify.warning,
            CRITICAL: notify.critical,
          };
          (notifyByType[type] || notify.info)(message, {
            title,
            duration: type === "CRITICAL" ? 8000 : 5000,
          });
        }
      } catch (error) {
        console.error("Could not process notification update", error);
      }
    };

    socket.onclose = () => {
      if (socketRef.current !== socket) return;
      setConnected(false);
      if (stableConnectionTimeoutRef.current) {
        clearTimeout(stableConnectionTimeoutRef.current);
        stableConnectionTimeoutRef.current = null;
      }

      // Keep retrying with a capped exponential delay. A fixed retry count left
      // notifications disconnected indefinitely after a temporary outage.
      const attempt = reconnectAttemptsRef.current;
      reconnectAttemptsRef.current += 1;
      const delay = Math.min(1000 * (2 ** Math.min(attempt, 5)), 30000);
      reconnectTimeoutRef.current = setTimeout(connect, delay);
    };

    socket.onerror = (error) => {
      console.error("System Notifications WS Error:", error);
    };

    socketRef.current = socket;
  }, [accessToken, notify]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (stableConnectionTimeoutRef.current) {
        clearTimeout(stableConnectionTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.onclose = null;
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [connect]);

  const syncUnreadCount = useCallback((count) => {
    setUnreadCount(Math.max(0, Number(count) || 0));
  }, []);

  return {
    connected,
    unreadCount,
    syncUnreadCount,
  };
}
