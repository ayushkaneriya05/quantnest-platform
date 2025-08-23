// frontend/src/contexts/websocket-context.jsx
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
import api from "@/services/api";

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

  const ws = useRef(null);
  const subscriptions = useRef(new Set());
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectInterval = useRef(null);

  const subscriptionCallbacks = useRef(new Map());
  const fetchingPrices = useRef(new Set());

  const getWebSocketUrl = () => {
    const token = localStorage.getItem("accessToken");
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host =
      window.location.hostname === "localhost"
        ? "localhost:8000"
        : window.location.host;
    return `${protocol}//${host}/ws/marketdata/?token=${token}`;
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

  const handleTickData = useCallback((data) => {
    if (!data.instrument) return;
    const symbol = data.instrument.split(":")[1].split("-")[0];

    setTickData((prev) =>
      new Map(prev).set(symbol, { ...data, timestamp: Date.now() })
    );

    if (subscriptionCallbacks.current.has(symbol)) {
      subscriptionCallbacks.current.get(symbol).forEach((cb) => {
        try {
          cb(data);
        } catch (e) {
          console.error(`Error in subscription callback for ${symbol}:`, e);
        }
      });
    }
  }, []);

  const handleOrderUpdate = useCallback((data) => {
    setOrderUpdates((prev) => [data, ...prev.slice(0, 99)]); // Keep last 100 updates
    const instrumentSymbol = data.instrument?.symbol || "N/A";
    toast.success(`Order Update: ${instrumentSymbol} ${data.status}`);
  }, []);

  const handlePositionUpdate = useCallback((data) => {
    setPositionUpdates((prev) => [data, ...prev.slice(0, 99)]); // Keep last 100 updates
  }, []);

  const connect = useCallback(() => {
    if (ws.current && ws.current.readyState !== WebSocket.CLOSED) {
      return;
    }

    try {
      setConnectionStatus("connecting");
      const wsUrl = getWebSocketUrl();
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setIsConnected(true);
        setConnectionStatus("connected");
        console.log("✅ WebSocket connected");
        reconnectAttempts.current = 0;
        if (reconnectInterval.current) {
          clearTimeout(reconnectInterval.current);
          reconnectInterval.current = null;
        }

        subscriptions.current.forEach((symbol) => {
          sendMessage({ type: "subscribe", instrument: `NSE:${symbol}-EQ` });
        });

        toast.success("Live market data connected", { duration: 2000 });
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          // console.log("WS message:", data);
          if (data.type === "tick") handleTickData(data);
          else if (data.type === "order_update") handleOrderUpdate(data);
          else if (data.type === "position_update") handlePositionUpdate(data);
        } catch (e) {
          console.error("WS message parse error:", e);
        }
      };

      ws.current.onclose = () => {
        setIsConnected(false);
        setConnectionStatus("disconnected");

        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 10000);
          reconnectInterval.current = setTimeout(connect, delay);
        } else {
          toast.error("Could not connect to live data.", { duration: 4000 });
        }
      };

      ws.current.onerror = (err) => {
        console.error("WebSocket error:", err);
        setConnectionStatus("error");
        ws.current.close();
      };
    } catch (e) {
      console.error("WS setup error:", e);
      setConnectionStatus("error");
    }
  }, [handleTickData, handleOrderUpdate, handlePositionUpdate, sendMessage]);

  const disconnect = useCallback(() => {
    if (reconnectInterval.current) clearTimeout(reconnectInterval.current);
    reconnectAttempts.current = maxReconnectAttempts;
    ws.current?.close(1000, "Manual disconnect");
  }, []);

  const subscribe = useCallback(
    (symbol, callback) => {
      if (!symbol) return () => {};

      if (callback) {
        if (!subscriptionCallbacks.current.has(symbol)) {
          subscriptionCallbacks.current.set(symbol, new Set());
        }
        subscriptionCallbacks.current.get(symbol).add(callback);
      }

      if (!subscriptions.current.has(symbol)) {
        subscriptions.current.add(symbol);
        sendMessage({ type: "subscribe", instrument: `NSE:${symbol}-EQ` });
      }

      return () => {
        if (callback && subscriptionCallbacks.current.has(symbol)) {
          const cbs = subscriptionCallbacks.current.get(symbol);
          cbs.delete(callback);

          if (cbs.size === 0) {
            subscriptionCallbacks.current.delete(symbol);
            subscriptions.current.delete(symbol);
            sendMessage({
              type: "unsubscribe",
              instrument: `NSE:${symbol}-EQ`,
            });
          }
        }
      };
    },
    [sendMessage]
  );

  const getLatestPrice = useCallback(
    async (symbol) => {
      if (!symbol) return null;

      const liveTick = tickData.get(symbol);
      if (liveTick) {
        return liveTick.price;
      }

      if (!fetchingPrices.current.has(symbol)) {
        fetchingPrices.current.add(symbol);
        try {
          const response = await api.get(
            `/market/latest-tick/?instrument=${symbol}`
          );
          const lastKnownTick = response.data;

          setTickData((prev) => {
            const next = new Map(prev);
            if (!next.has(symbol)) {
              next.set(symbol, {
                ...lastKnownTick,
              });
            }
            return next;
          });
          fetchingPrices.current.delete(symbol);
          return lastKnownTick.price;
        } catch (err) {
          console.error(`Failed to fetch latest price for ${symbol}:`, err);
          fetchingPrices.current.delete(symbol);
          return null;
        }
      }
      return null;
    },
    [tickData]
  );

  const getTickData = useCallback(
    (symbol) => tickData.get(symbol) ?? null,
    [tickData]
  );

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
        subscriptions: Array.from(subscriptions.current),
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
