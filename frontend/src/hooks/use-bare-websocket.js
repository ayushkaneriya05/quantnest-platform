// use-bare-websocket.js  (rename file and symbol)
import { useState, useEffect, useRef, useCallback } from "react";

export function useBareWebSocket(url) {
  const [lastMessage, setLastMessage] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef(null);
  const reconnectTimeout = useRef(null);

  const connect = useCallback(() => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) return;

    const socket = new WebSocket(url);
    ws.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
    };

    socket.onmessage = (event) => setLastMessage(event.data);
    socket.onclose = () => {
      setIsConnected(false);
      reconnectTimeout.current = setTimeout(() => connect(), 5000);
    };
    socket.onerror = () => socket.close();
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      ws.current?.close();
    };
  }, [connect]);

  const sendMessage = useCallback((data) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    }
  }, []);

  return { lastMessage, isConnected, sendMessage };
}
