import { useEffect, useRef, useState, useCallback } from "react";
import { useNotifications } from "./useNotifications";

export function useSystemNotifications() {
  const { notify } = useNotifications();
  const [unreadCount, setUnreadCount] = useState(0);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    const token = localStorage.getItem("accessToken");
    if (!token) return;

    if (socketRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.hostname === "localhost" ? "localhost:8000" : window.location.host;
    const wsUrl = `${protocol}//${host}/ws/notifications/?token=${token}`;

    console.log("Connecting to System Notifications WS...");
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log("System Notifications WS Connected");
      setConnected(true);
      reconnectAttemptsRef.current = 0;
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "notification" && payload.data) {
          const { title, message, severity } = payload.data;
          
          // Increment unread count globally
          setUnreadCount((prev) => prev + 1);

          // Dispatch toast based on severity
          if (severity === "CRITICAL") {
            notify.error(`${title}: ${message}`, { duration: 8000 });
          } else if (severity === "WARNING") {
            notify.warning(`${title}: ${message}`, { duration: 5000 });
          } else {
            notify.info(`${title}: ${message}`, { duration: 4000 });
          }
        }
      } catch (error) {
        console.error("Error parsing notification WS message:", error);
      }
    };

    socket.onclose = () => {
      console.log("System Notifications WS Disconnected");
      setConnected(false);
      
      // Reconnection logic
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current += 1;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
        console.log(`Reconnecting System Notifications WS in ${delay}ms...`);
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      }
    };

    socket.onerror = (error) => {
      console.error("System Notifications WS Error:", error);
    };

    socketRef.current = socket;
  }, [notify]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [connect]);

  // Provide a method to manually clear unread count from the UI (e.g. when opening the NotificationCenter)
  const clearUnreadCount = useCallback(() => {
    setUnreadCount(0);
  }, []);

  // Set the unread count from an initial API call if needed
  const initializeUnreadCount = useCallback((count) => {
    setUnreadCount(count);
  }, []);

  return {
    connected,
    unreadCount,
    clearUnreadCount,
    initializeUnreadCount
  };
}
