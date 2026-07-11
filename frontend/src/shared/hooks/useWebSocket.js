import { useCallback, useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import toast from "react-hot-toast";
import {
  setConnected,
  setConnectionStatus,
  setLastMessage,
  updateTickData,
  addOrderUpdate,
  addPositionUpdate,
  addSubscription,
  removeSubscription,
  incrementReconnectAttempts,
  resetReconnectAttempts,
} from "../store/websocketSlice";
import api from "../services/api";

const socketRef = { current: null };
const reconnectTimerRef = { current: null };
const reconnectAttemptsRef = { current: 0 };
const intentionalCloseRef = { current: false };
const subscriptionCallbacks = new Map();
const subscriptionRefCounts = new Map();
const fetchingPrices = new Set();
let mountedConsumers = 0;

const originalSymbolMap = new Map();

const normalizeSymbol = (fullSymbol) => {
  if (!fullSymbol) return "";
  const normalized = fullSymbol.includes(":") ? fullSymbol.split(":")[1] : fullSymbol;
  return normalized.replace(/-(EQ|INDEX)$/, "");
};

export function useWebSocket() {
  const dispatch = useDispatch();
  const {
    isConnected,
    connectionStatus,
    lastMessage,
    tickData,
    orderUpdates,
    positionUpdates,
    subscriptions,
    reconnectAttempts,
  } = useSelector((state) => state.websocket);

  reconnectAttemptsRef.current = reconnectAttempts;

  const pingIntervalRef = useRef(null);
  const pongTimeoutRef = useRef(null);
  const lastTickUpdateRef = useRef({});

  const tickDataRef = useRef(tickData);
  useEffect(() => {
    tickDataRef.current = tickData;
  }, [tickData]);

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
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      try {
        socketRef.current.send(JSON.stringify(message));
        return true;
      } catch (error) {
        console.error("WS send error:", error);
        return false;
      }
    }
    return false;
  }, []);

  const notifySymbolSubscribers = useCallback((fullSymbol, payload) => {
    const symbol = normalizeSymbol(fullSymbol);
    if (!symbol || !subscriptionCallbacks.has(symbol)) return;

    subscriptionCallbacks.get(symbol).forEach((callback) => {
      try {
        callback(payload);
      } catch (error) {
        console.error(`Error in subscription callback for ${symbol}:`, error);
      }
    });
  }, []);

  const handleTickData = useCallback(
    (data) => {
      const tick = data?.data || data;
      const fullSymbol = tick?.symbol || data?.symbol || data?.instrument;
      const symbol = normalizeSymbol(fullSymbol);
      if (!symbol) return;

      const now = Date.now();
      if (!lastTickUpdateRef.current[symbol] || now - lastTickUpdateRef.current[symbol] > 200) {
        lastTickUpdateRef.current[symbol] = now;
        dispatch(updateTickData({ symbol, data: tick }));
      }
      notifySymbolSubscribers(fullSymbol, tick);
    },
    [dispatch, notifySymbolSubscribers]
  );

  const handleOrderUpdate = useCallback(
    (data) => {
      dispatch(addOrderUpdate(data));
      const instrumentSymbol =
        typeof data.instrument === "string"
          ? data.instrument
          : data.instrument?.symbol || "N/A";
      toast.success(`Order Update: ${instrumentSymbol} ${data.status}`);
    },
    [dispatch]
  );

  const handlePositionUpdate = useCallback(
    (data) => {
      dispatch(addPositionUpdate(data));
    },
    [dispatch]
  );

  const connect = useCallback(() => {
    if (
      socketRef.current &&
      (socketRef.current.readyState === WebSocket.OPEN ||
        socketRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    try {
      intentionalCloseRef.current = false;
      dispatch(setConnectionStatus("connecting"));
      socketRef.current = new WebSocket(getWebSocketUrl());

      socketRef.current.onopen = () => {
        dispatch(setConnected(true));
        dispatch(setConnectionStatus("connected"));
        dispatch(resetReconnectAttempts());

        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
          reconnectTimerRef.current = null;
        }

        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = setInterval(() => {
          sendMessage({ type: "ping" });
          pongTimeoutRef.current = setTimeout(() => {
            if (socketRef.current) {
              socketRef.current.close(4000, "Ping timeout");
            }
          }, 5000);
        }, 25000);

        subscriptionRefCounts.forEach((count, normalizedSymbol) => {
          if (count > 0) {
            const exactSymbol = originalSymbolMap.get(normalizedSymbol) || `NSE:${normalizedSymbol}-EQ`;
            sendMessage({ type: "subscribe", instrument: exactSymbol });
          }
        });
      };

      socketRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === "pong") {
            if (pongTimeoutRef.current) {
              clearTimeout(pongTimeoutRef.current);
              pongTimeoutRef.current = null;
            }
          } else if (data.type === "tick") {
            handleTickData(data);
          } else if (data.type === "candle.update" || data.type === "candle.closed") {
            notifySymbolSubscribers(data.symbol, data);
          } else if (data.type === "order_update" || data.type === "order.update") {
            handleOrderUpdate(data.data || data);
          } else if (data.type === "position_update" || data.type === "position.update") {
            handlePositionUpdate(data.data || data);
          }
        } catch (error) {
          console.error("WS message parse error:", error);
        }
      };

      socketRef.current.onclose = () => {
        dispatch(setConnected(false));
        dispatch(setConnectionStatus("disconnected"));

        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        if (pongTimeoutRef.current) {
          clearTimeout(pongTimeoutRef.current);
          pongTimeoutRef.current = null;
        }

        if (!intentionalCloseRef.current && mountedConsumers > 0) {
          const attempts = reconnectAttemptsRef.current;

          dispatch(incrementReconnectAttempts());
          const delay = Math.min(1000 * 1.5 ** attempts, 30000);
          reconnectTimerRef.current = setTimeout(connect, delay);
        }
      };

      socketRef.current.onerror = (error) => {
        console.error("WebSocket error:", error);
        dispatch(setConnectionStatus("error"));
      };
    } catch (error) {
      console.error("WS setup error:", error);
      dispatch(setConnectionStatus("error"));
    }
  }, [
    dispatch,
    handleOrderUpdate,
    handlePositionUpdate,
    handleTickData,
    notifySymbolSubscribers,
    sendMessage,
  ]);

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (pongTimeoutRef.current) {
      clearTimeout(pongTimeoutRef.current);
      pongTimeoutRef.current = null;
    }
    if (socketRef.current) {
      socketRef.current.close(1000, "Manual disconnect");
      socketRef.current = null;
    }
    dispatch(setConnected(false));
    dispatch(setConnectionStatus("disconnected"));
  }, [dispatch]);

  useEffect(() => {
    mountedConsumers += 1;
    connect();

    return () => {
      mountedConsumers = Math.max(0, mountedConsumers - 1);
      if (mountedConsumers === 0) {
        disconnect();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const subscribe = useCallback(
    (symbol, callback) => {
      const normalizedSymbol = normalizeSymbol(symbol);
      if (!normalizedSymbol) return () => {};

      const exactSymbol = symbol?.includes(":") ? symbol : `NSE:${normalizedSymbol}-EQ`;
      originalSymbolMap.set(normalizedSymbol, exactSymbol);

      if (callback) {
        if (!subscriptionCallbacks.has(normalizedSymbol)) {
          subscriptionCallbacks.set(normalizedSymbol, new Set());
        }
        subscriptionCallbacks.get(normalizedSymbol).add(callback);
      }

      const currentCount = subscriptionRefCounts.get(normalizedSymbol) || 0;
      subscriptionRefCounts.set(normalizedSymbol, currentCount + 1);

      if (currentCount === 0) {
        dispatch(addSubscription(normalizedSymbol));
        sendMessage({
          type: "subscribe",
          instrument: exactSymbol,
        });
      }

      return () => {
        if (callback && subscriptionCallbacks.has(normalizedSymbol)) {
          const callbacks = subscriptionCallbacks.get(normalizedSymbol);
          callbacks.delete(callback);
          if (callbacks.size === 0) {
            subscriptionCallbacks.delete(normalizedSymbol);
          }
        }

        const nextCount = Math.max(0, (subscriptionRefCounts.get(normalizedSymbol) || 1) - 1);
        if (nextCount === 0) {
          subscriptionRefCounts.delete(normalizedSymbol);
          dispatch(removeSubscription(normalizedSymbol));
          sendMessage({
            type: "unsubscribe",
            instrument: exactSymbol,
          });
        } else {
          subscriptionRefCounts.set(normalizedSymbol, nextCount);
        }
      };
    },
    [dispatch, sendMessage]
  );

  const getLatestPrice = useCallback(
    async (symbol, options = {}) => {
      if (!symbol) return null;

      const normalizedSymbol = normalizeSymbol(symbol);
      const liveTick = tickDataRef.current[normalizedSymbol];
      if (liveTick && !options.force) {
        return liveTick.price;
      }

      if (options.force || !fetchingPrices.has(normalizedSymbol)) {
        fetchingPrices.add(normalizedSymbol);
        try {
          const exactSymbol = symbol?.includes(":") ? symbol : (originalSymbolMap.get(normalizedSymbol) || `NSE:${normalizedSymbol}-EQ`);
          originalSymbolMap.set(normalizedSymbol, exactSymbol);
          const response = await api.get(
            `/market/latest-tick/?instrument=${encodeURIComponent(exactSymbol)}`
          );
          const lastKnownTick = response.data;

          dispatch(updateTickData({ symbol: normalizedSymbol, data: lastKnownTick }));
          fetchingPrices.delete(normalizedSymbol);
          return lastKnownTick.price;
        } catch (error) {
          fetchingPrices.delete(normalizedSymbol);
          return null;
        }
      }
      return null;
    },
    [dispatch]
  );

  const getTickData = useCallback(
    (symbol) => tickDataRef.current[normalizeSymbol(symbol)] ?? null,
    []
  );

  return {
    isConnected,
    connectionStatus,
    lastMessage,
    tickData,
    orderUpdates,
    positionUpdates,
    subscriptions,
    connect,
    disconnect,
    sendMessage,
    subscribe,
    getLatestPrice,
    getTickData,
  };
}
