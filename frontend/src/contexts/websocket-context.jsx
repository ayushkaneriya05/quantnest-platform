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

const WebSocketContext = createContext();

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    console.warn(
      "useWebSocketContext must be used within a WebSocketProvider. Using fallback values."
    );
    const noop = () => {};
    const noopUnsub = () => noop;
    return {
      isConnected: false,
      connectionStatus: "disconnected",
      lastMessage: null,
      tickData: new Map(),
      marketData: {},
      orderUpdates: [],
      positionUpdates: [],
      connect: () => console.warn("WebSocket not available"),
      disconnect: () => console.warn("WebSocket not available"),
      sendMessage: () => false,
      subscribe: noopUnsub,
      unsubscribe: noop,
      // common aliases
      subscribeToInstrument: noopUnsub,
      unsubscribeFromInstrument: noop,
      addMarketDataListener: noopUnsub,
      removeMarketDataListener: noop,
      getLatestPrice: () => null,
      getTickData: () => null,
      subscriptions: [],
      useMockData: false,
    };
  }
  return context;
};

export const WebSocketProvider = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const [lastMessage, setLastMessage] = useState(null);
  const [subscriptions, setSubscriptions] = useState(new Set());
  const [tickData, setTickData] = useState(new Map());
  const [orderUpdates, setOrderUpdates] = useState([]);
  const [positionUpdates, setPositionUpdates] = useState([]);
  const [useMockData, setUseMockData] = useState(false);

  const ws = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 3;
  const reconnectInterval = useRef(null);
  const subscriptionCallbacks = useRef(new Map());
  const mockDataInterval = useRef(null);

  const generateMockTickData = useCallback((symbol) => {
    const basePrices = {
      RELIANCE: 2450.0,
      TCS: 3200.0,
      INFY: 1450.0,
      HDFCBANK: 1650.0,
      ICICIBANK: 920.0,
      WIPRO: 410.0,
      LT: 3400.0,
      BHARTIARTL: 1180.0,
      SBIN: 780.0,
      ITC: 460.0,
    };
    const basePrice = basePrices[symbol] || 2000;
    const variation = (Math.random() - 0.5) * 0.02;
    const currentPrice = basePrice * (1 + variation);
    return {
      symbol,
      ltp: currentPrice,
      open: currentPrice * (1 - Math.random() * 0.002),
      high: currentPrice * (1 + Math.random() * 0.004),
      low: currentPrice * (1 - Math.random() * 0.004),
      close: currentPrice,
      type: "tick",
      timestamp: Math.floor(Date.now() / 1000),
      volume: Math.floor(Math.random() * 100000) + 50000,
      change: currentPrice - basePrice,
      change_percent: (variation * 100).toFixed(2),
    };
  }, []);

  const startMockDataGeneration = useCallback(() => {
    if (mockDataInterval.current) return;
    mockDataInterval.current = setInterval(() => {
      subscriptions.forEach((symbol) => {
        const mockData = generateMockTickData(symbol);
        handleTickData(mockData);
        if (subscriptionCallbacks.current.has(symbol)) {
          subscriptionCallbacks.current.get(symbol).forEach((cb) => {
            try {
              cb(mockData);
            } catch (e) {
              console.error("Mock cb error:", e);
            }
          });
        }
      });
    }, 2000);
  }, [subscriptions, generateMockTickData]);

  const stopMockDataGeneration = useCallback(() => {
    if (mockDataInterval.current) {
      clearInterval(mockDataInterval.current);
      mockDataInterval.current = null;
    }
  }, []);

  const getWebSocketUrl = () => {
    const accessToken = localStorage.getItem("accessToken");
    if (typeof window !== "undefined") {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.hostname;
      if (host === "localhost" || host === "127.0.0.1") {
        return `ws://localhost:8000/ws/marketdata/?token=${accessToken}`;
      }
      const port = window.location.port ? `:${window.location.port}` : "";
      return `${protocol}//${host}${port}/ws/marketdata/${accessToken}`;
    }
    return `ws://localhost:8000/ws/marketdata/${accessToken}`;
  };

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;
    try {
      setConnectionStatus("connecting");

      if (typeof WebSocket === "undefined") {
        console.warn("WebSocket not available; using mock data");
        setConnectionStatus("mock");
        setUseMockData(true);
        startMockDataGeneration();
        return;
      }

      const wsUrl = getWebSocketUrl();
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setIsConnected(true);
        setConnectionStatus("connected");
        setUseMockData(false);
        reconnectAttempts.current = 0;
        stopMockDataGeneration();

        subscriptions.forEach((symbol) => {
          ws.current?.send(
            JSON.stringify({ type: "subscribe", instrument: symbol })
          );
        });

        toast.success("Live market data connected", { duration: 3000 });
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);

          if (data.type === "tick" || data.symbol) {
            handleTickData(data);
          } else if (data.type === "order_update") {
            handleOrderUpdate(data);
          } else if (data.type === "position_update") {
            handlePositionUpdate(data);
          }

          if (data.symbol && subscriptionCallbacks.current.has(data.symbol)) {
            subscriptionCallbacks.current.get(data.symbol).forEach((cb) => {
              try {
                cb(data);
              } catch (e) {
                console.error("Sub cb error:", e);
              }
            });
          }
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
          setConnectionStatus("mock");
          setUseMockData(true);
          startMockDataGeneration();
          toast.error("Live data unavailable, using simulation mode", {
            duration: 4000,
          });
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
      setUseMockData(true);
      startMockDataGeneration();
      toast.error("Using simulated market data", { duration: 3000 });
    }
  }, [startMockDataGeneration, stopMockDataGeneration, subscriptions]);

  const attemptReconnect = useCallback(() => {
    if (reconnectAttempts.current >= maxReconnectAttempts) return;
    reconnectAttempts.current++;
    setConnectionStatus("reconnecting");
    const delay = Math.min(2000 * reconnectAttempts.current, 10000);
    reconnectInterval.current = setTimeout(() => connect(), delay);
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectInterval.current) clearTimeout(reconnectInterval.current);
    stopMockDataGeneration();
    if (ws.current) {
      ws.current.close(1000, "Manual disconnect");
      ws.current = null;
    }
    setIsConnected(false);
    setConnectionStatus("disconnected");
    setUseMockData(false);
  }, [stopMockDataGeneration]);

  const sendMessage = useCallback(
    (message) => {
      if (useMockData) return true;
      if (ws.current?.readyState === WebSocket.OPEN) {
        try {
          ws.current.send(JSON.stringify(message));
          return true;
        } catch (e) {
          console.error("WS send error:", e);
          return false;
        }
      } else {
        console.warn("WebSocket not connected - message not sent:", message);
        return false;
      }
    },
    [useMockData]
  );

  const subscribe = useCallback((symbol, callback) => {
    if (!symbol) return () => {};
    setSubscriptions((prev) => new Set([...prev, symbol]));

    if (callback) {
      if (!subscriptionCallbacks.current.has(symbol)) {
        subscriptionCallbacks.current.set(symbol, new Set());
      }
      subscriptionCallbacks.current.get(symbol).add(callback);
    }

    if (useMockData) {
      setTimeout(() => {
        const mockData = generateMockTickData(symbol);
        handleTickData(mockData);
        if (callback) {
          try {
            callback(mockData);
          } catch (e) {
            console.error("Mock cb error:", e);
          }
        }
      }, 100);
    } else if (ws.current?.readyState === WebSocket.OPEN) {
      sendMessage({ type: "subscribe", instrument: symbol });
    }

    return () => unsubscribe(symbol, callback);
  });

  const unsubscribe = useCallback(
    (symbol, callback) => {
      if (!symbol) return;

      if (callback && subscriptionCallbacks.current.has(symbol)) {
        subscriptionCallbacks.current.get(symbol).delete(callback);
        if (subscriptionCallbacks.current.get(symbol).size === 0) {
          subscriptionCallbacks.current.delete(symbol);
        }
      }

      if (!subscriptionCallbacks.current.has(symbol)) {
        setSubscriptions((prev) => {
          const next = new Set(prev);
          next.delete(symbol);
          return next;
        });

        if (!useMockData && ws.current?.readyState === WebSocket.OPEN) {
          sendMessage({ type: "unsubscribe", instrument: symbol });
        }
      }
    },
    [sendMessage, useMockData]
  );

  const handleTickData = useCallback((data) => {
    if (!data.symbol) return;
    setTickData((prev) => {
      const next = new Map(prev);
      next.set(data.symbol, { ...data, timestamp: Date.now() });
      return next;
    });
  }, []);

  const handleOrderUpdate = useCallback((data) => {
    setOrderUpdates((prev) => [data, ...prev.slice(0, 99)]);
  }, []);

  const handlePositionUpdate = useCallback((data) => {
    setPositionUpdates((prev) => [data, ...prev.slice(0, 99)]);
  }, []);

  const getLatestPrice = useCallback(
    (symbol) => tickData.get(symbol)?.ltp ?? null,
    [tickData]
  );
  const getTickData = useCallback(
    (symbol) => tickData.get(symbol) ?? null,
    [tickData]
  );

  useEffect(() => {
    if (typeof window !== "undefined") connect();
    return () => {
      disconnect();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    return () => {
      if (reconnectInterval.current) clearTimeout(reconnectInterval.current);
      stopMockDataGeneration();
    };
  }, [stopMockDataGeneration]);

  const value = {
    // Connection state
    isConnected: isConnected || useMockData,
    connectionStatus: useMockData ? "mock" : connectionStatus,

    // Data
    lastMessage,
    tickData,
    marketData: Object.fromEntries(tickData), // convenient plain object
    orderUpdates,
    positionUpdates,

    // Methods (canonical)
    connect,
    disconnect,
    sendMessage,
    subscribe,
    unsubscribe,
    getLatestPrice,
    getTickData,

    // Methods (aliases for compatibility)
    subscribeToInstrument: subscribe,
    unsubscribeFromInstrument: unsubscribe,
    addMarketDataListener: subscribe,
    removeMarketDataListener: unsubscribe,

    // Subscription info
    subscriptions: Array.from(subscriptions),

    // Mock mode indicator
    useMockData,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

// keep this name, it's what components import
export const useWebSocket = () => {
  const ctx = useContext(WebSocketContext);
  if (!ctx)
    throw new Error("useWebSocket must be used within a WebSocketProvider");
  return ctx;
};
