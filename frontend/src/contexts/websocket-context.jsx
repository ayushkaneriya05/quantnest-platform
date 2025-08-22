// websocket-context.jsx
import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
} from "react";
import toast from "react-hot-toast";
import sha1 from "crypto-js/sha1";

const WebSocketContext = createContext();

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context)
    throw new Error("useWebSocket must be used within a WebSocketProvider");
  return context;
};

export const WebSocketProvider = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const [lastMessage, setLastMessage] = useState(null);
  const [tickData, setTickData] = useState(new Map());
  const [orderUpdates, setOrderUpdates] = useState([]);
  const [positionUpdates, setPositionUpdates] = useState([]);
  const [subscriptions, setSubscriptions] = useState(new Set());

  const ws = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 3;
  const reconnectInterval = useRef(null);

  // Map original symbol ↔ hashed symbol for backend
  const symbolToHash = useRef(new Map());
  const hashToSymbol = useRef(new Map());

  // Map of symbol → Set of callbacks
  const subscriptionCallbacks = useRef(new Map());

  // --- Helpers ---
  const getWebSocketUrl = () => {
    const token = localStorage.getItem("accessToken");
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.hostname;
    const port = window.location.port ? `:${window.location.port}` : "";
    return host.includes("localhost")
      ? `ws://localhost:8000/ws/marketdata/?token=${token}`
      : `${protocol}//${host}${port}/ws/marketdata/${token}`;
  };

  const sendMessage = useCallback((message) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      try {
        ws.current.send(JSON.stringify(message));
        return true;
      } catch (e) {
        console.error("WS send error:", e);
        return false;
      }
    }
    console.warn("WebSocket not connected - message not sent:", message);
    return false;
  }, []);

  // --- Tick / Order / Position handlers ---
  const handleTickData = useCallback((data) => {
    if (!data.symbol) return;
    const symbol = hashToSymbol.current.get(data.symbol) || data.symbol;

    setTickData((prev) => {
      const next = new Map(prev);
      next.set(symbol, { ...data, timestamp: Date.now() });
      return next;
    });

    // Call subscribed callbacks
    if (subscriptionCallbacks.current.has(symbol)) {
      subscriptionCallbacks.current.get(symbol).forEach((cb) => {
        try {
          cb(data);
        } catch (e) {
          console.error("Callback error:", e);
        }
      });
    }
  }, []);

  const handleOrderUpdate = useCallback((data) => {
    setOrderUpdates((prev) => [data, ...prev.slice(0, 99)]);
  }, []);

  const handlePositionUpdate = useCallback((data) => {
    setPositionUpdates((prev) => [data, ...prev.slice(0, 99)]);
  }, []);

  // --- Reconnect logic ---
  const attemptReconnect = useCallback(() => {
    if (reconnectAttempts.current >= maxReconnectAttempts) return;
    reconnectAttempts.current++;
    setConnectionStatus("reconnecting");
    const delay = Math.min(2000 * reconnectAttempts.current, 10000);
    reconnectInterval.current = setTimeout(connect, delay);
  }, []);

  // --- Connect / Disconnect ---
  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    try {
      setConnectionStatus("connecting");
      const wsUrl = getWebSocketUrl();
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setIsConnected(true);
        setConnectionStatus("connected");
        reconnectAttempts.current = 0;

        // Resubscribe all symbols
        subscriptions.forEach((symbol) => {
          const hashed = symbolToHash.current.get(symbol);
          if (hashed) sendMessage({ type: "subscribe", instrument: hashed });
        });

        toast.success("Live market data connected", { duration: 3000 });
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);

          if (data.type === "tick" || data.symbol) handleTickData(data);
          else if (data.type === "order_update") handleOrderUpdate(data);
          else if (data.type === "position_update") handlePositionUpdate(data);
        } catch (e) {
          console.error("WS parse error:", e);
        }
      };

      ws.current.onclose = (event) => {
        setIsConnected(false);
        setConnectionStatus("disconnected");

        if (
          event.code !== 1000 &&
          reconnectAttempts.current < maxReconnectAttempts
        ) {
          attemptReconnect();
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          toast.error("Live data unavailable", { duration: 4000 });
        }
      };

      ws.current.onerror = () => {
        setConnectionStatus("error");
        if (reconnectAttempts.current === 0) {
          toast.error("Market data connection failed, will retry...", {
            duration: 3000,
          });
        }
      };
    } catch (e) {
      console.error("WS setup error:", e);
      setConnectionStatus("error");
      toast.error("Using simulated market data", { duration: 3000 });
    }
  }, [
    subscriptions,
    sendMessage,
    handleTickData,
    handleOrderUpdate,
    handlePositionUpdate,
    attemptReconnect,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectInterval.current) clearTimeout(reconnectInterval.current);
    ws.current?.close(1000, "Manual disconnect");
    ws.current = null;
    setIsConnected(false);
    setConnectionStatus("disconnected");
  }, []);

  // --- Subscribe / Unsubscribe ---
  const subscribe = useCallback(
    (symbol, callback) => {
      if (!symbol) return () => {};

      // Add callback
      if (callback) {
        if (!subscriptionCallbacks.current.has(symbol)) {
          subscriptionCallbacks.current.set(symbol, new Set());
        }
        subscriptionCallbacks.current.get(symbol).add(callback);
      }

      // Store subscription
      setSubscriptions((prev) => new Set([...prev, symbol]));

      // Hash symbol for backend
      const hashed = sha1(symbol).toString();
      symbolToHash.current.set(symbol, hashed);
      hashToSymbol.current.set(hashed, symbol);

      // Send subscribe message
      if (ws.current?.readyState === WebSocket.OPEN) {
        sendMessage({ type: "subscribe", instrument: hashed });
      }

      // Return unsubscribe function
      return () => {
        if (callback && subscriptionCallbacks.current.has(symbol)) {
          subscriptionCallbacks.current.get(symbol).delete(callback);
          if (subscriptionCallbacks.current.get(symbol).size === 0) {
            subscriptionCallbacks.current.delete(symbol);
            setSubscriptions((prev) => {
              const next = new Set(prev);
              next.delete(symbol);
              return next;
            });
            if (ws.current?.readyState === WebSocket.OPEN) {
              sendMessage({ type: "unsubscribe", instrument: hashed });
              symbolToHash.current.delete(symbol);
              hashToSymbol.current.delete(hashed);
            }
          }
        }
      };
    },
    [sendMessage]
  );

  const getLatestPrice = useCallback(
    (symbol) => tickData.get(symbol)?.price ?? null,
    [tickData]
  );
  const getTickData = useCallback(
    (symbol) => tickData.get(symbol) ?? null,
    [tickData]
  );

  // --- Auto-connect on mount ---
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return (
    <WebSocketContext.Provider
      value={{
        isConnected,
        connectionStatus,
        lastMessage,
        tickData,
        orderUpdates,
        positionUpdates,
        subscriptions: Array.from(subscriptions),
        connect,
        disconnect,
        sendMessage,
        subscribe,
        getLatestPrice,
        getTickData,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
};
