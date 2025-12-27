import { useEffect, useRef, useCallback } from "react";
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
    maxReconnectAttempts,
  } = useSelector((state) => state.websocket);

  const ws = useRef(null);
  const reconnectInterval = useRef(null);
  const subscriptionCallbacks = useRef(new Map());
  const subscriptionsRef = useRef(subscriptions);
  const fetchingPrices = useRef(new Set());
  subscriptionsRef.current = subscriptions;

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

  const handleTickData = useCallback(
    (data) => {
      if (!data.instrument) return;
      const symbol = data.instrument.split(":")[1].split("-")[0];

      dispatch(updateTickData({ symbol, data }));

      if (subscriptionCallbacks.current.has(symbol)) {
        subscriptionCallbacks.current.get(symbol).forEach((cb) => {
          try {
            cb(data);
          } catch (e) {
            console.error(`Error in subscription callback for ${symbol}:`, e);
          }
        });
      }
    },
    [dispatch]
  );

  const handleOrderUpdate = useCallback(
    (data) => {
      dispatch(addOrderUpdate(data));
      const instrumentSymbol = data.instrument?.symbol || "N/A";
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
    if (ws.current && ws.current.readyState !== WebSocket.CLOSED) {
      return;
    }

    try {
      dispatch(setConnectionStatus("connecting"));
      const wsUrl = getWebSocketUrl();
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        dispatch(setConnected(true));
        dispatch(setConnectionStatus("connected"));
        dispatch(resetReconnectAttempts());
        console.log("✅ WebSocket connected");
        if (reconnectInterval.current) {
          clearTimeout(reconnectInterval.current);
          reconnectInterval.current = null;
        }

        // Subscribe to all current subscriptions
        subscriptionsRef.current.forEach((symbol) => {
          sendMessage({ type: "subscribe", instrument: `NSE:${symbol}-EQ` });
        });

        toast.success("Live market data connected", { duration: 2000 });
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          dispatch(setLastMessage(data));
          // console.log("WS message:", data);
          if (data.type === "tick") handleTickData(data);
          else if (data.type === "order_update") handleOrderUpdate(data);
          else if (data.type === "position_update") handlePositionUpdate(data);
        } catch (e) {
          console.error("WS message parse error:", e);
        }
      };

      ws.current.onclose = () => {
        dispatch(setConnected(false));
        dispatch(setConnectionStatus("disconnected"));

        if (reconnectAttempts < maxReconnectAttempts) {
          dispatch(incrementReconnectAttempts());
          const delay = Math.min(1000 * 2 ** reconnectAttempts, 10000);
          reconnectInterval.current = setTimeout(connect, delay);
        } else {
          toast.error("Could not connect to live data.", { duration: 4000 });
        }
      };

      ws.current.onerror = (err) => {
        console.error("WebSocket error:", err);
        dispatch(setConnectionStatus("error"));
        ws.current.close();
      };
    } catch (e) {
      console.error("WS setup error:", e);
      dispatch(setConnectionStatus("error"));
    }
  }, [
    dispatch,
    reconnectAttempts,
    maxReconnectAttempts,
    sendMessage,
    handleTickData,
    handleOrderUpdate,
    handlePositionUpdate,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectInterval.current) clearTimeout(reconnectInterval.current);
    reconnectInterval.current = maxReconnectAttempts;
    ws.current?.close(1000, "Manual disconnect");
  }, [maxReconnectAttempts]);

  const subscribe = useCallback(
    (symbol, callback) => {
      if (!symbol) return () => {};

      if (callback) {
        if (!subscriptionCallbacks.current.has(symbol)) {
          subscriptionCallbacks.current.set(symbol, new Set());
        }
        subscriptionCallbacks.current.get(symbol).add(callback);
      }

      if (!subscriptions.includes(symbol)) {
        dispatch(addSubscription(symbol));
        sendMessage({ type: "subscribe", instrument: `NSE:${symbol}-EQ` });
      }

      return () => {
        if (callback && subscriptionCallbacks.current.has(symbol)) {
          const cbs = subscriptionCallbacks.current.get(symbol);
          cbs.delete(callback);

          if (cbs.size === 0) {
            subscriptionCallbacks.current.delete(symbol);
            dispatch(removeSubscription(symbol));
            sendMessage({
              type: "unsubscribe",
              instrument: `NSE:${symbol}-EQ`,
            });
          }
        }
      };
    },
    [dispatch, sendMessage]
  );

  const getLatestPrice = useCallback(
    async (symbol) => {
      if (!symbol) return null;

      const liveTick = tickData[symbol];
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

          dispatch(updateTickData({ symbol, data: lastKnownTick }));
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
    [tickData, dispatch]
  );

  const getTickData = useCallback(
    (symbol) => tickData[symbol] ?? null,
    [tickData]
  );

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

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
