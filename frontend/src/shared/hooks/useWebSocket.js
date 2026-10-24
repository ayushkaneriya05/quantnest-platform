import { useCallback, useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  setConnected,
  setConnectionStatus,
  setManualTradingTerminalUpdate,
  updateTickData,
  addSubscription,
  removeSubscription,
  incrementReconnectAttempts,
  resetReconnectAttempts,
} from "../store/websocketSlice";
import api, { ensureFreshAccessToken, getWebSocketUrl } from "../services/api";
import { useNotifications } from "./useNotifications";
import { isObservedQuote, isNewerQuote, normalizeMarketSymbol as normalizeSymbol } from "../utils/marketData";

const socketRef = { current: null };
const reconnectTimerRef = { current: null };
const reconnectAttemptsRef = { current: 0 };
const intentionalCloseRef = { current: false };
const subscriptionCallbacks = new Map();
const subscriptionRefCounts = new Map();
const chartCallbacks = new Map();
const terminalCallbacks = new Set();
const fetchingPrices = new Map();
let mountedConsumers = 0;

// Deliver every ledger event before React batches renders.
export function subscribeTerminalUpdates(callback) {
  terminalCallbacks.add(callback);
  return () => terminalCallbacks.delete(callback);
}


export function useWebSocket() {
  const { notify } = useNotifications();
  const dispatch = useDispatch();
  const {
    isConnected,
    connectionStatus,
    tickData,
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

  const notifySymbolSubscribers = useCallback((symbol, payload) => {
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
    ({ data: tick }) => {
      const symbol = tick.symbol;
      if (!symbol) return;
      if (!isNewerQuote(tick, tickDataRef.current[symbol])) return;

      const now = Date.now();
      if (!lastTickUpdateRef.current[symbol] || now - lastTickUpdateRef.current[symbol] > 200) {
        lastTickUpdateRef.current[symbol] = now;
        dispatch(updateTickData({ symbol, data: tick }));
      }
      notifySymbolSubscribers(symbol, tick);
    },
    [dispatch, notifySymbolSubscribers]
  );

  const connect = useCallback(() => {
    if (
      socketRef.current &&
      (socketRef.current.readyState === WebSocket.OPEN ||
        socketRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const retry = () => {
      if (intentionalCloseRef.current || mountedConsumers === 0) return;
      const attempts = reconnectAttemptsRef.current;
      dispatch(incrementReconnectAttempts());
      const delay = Math.min(1000 * 1.5 ** Math.min(attempts, 10), 30000);
      reconnectTimerRef.current = setTimeout(async () => {
        try {
          await ensureFreshAccessToken();
          if (!intentionalCloseRef.current && mountedConsumers > 0) connect();
        } catch { retry(); }
      }, delay);
    };
    try {
      intentionalCloseRef.current = false;
      dispatch(setConnectionStatus("connecting"));
      socketRef.current = new WebSocket(getWebSocketUrl("/ws/marketdata/"));

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

        subscriptionRefCounts.forEach((count, symbol) => {
          if (count > 0) {
            sendMessage({ type: "subscribe", instrument: symbol });
          }
        });
        chartCallbacks.forEach((callbacks, key) => {
          const [symbol, interval] = JSON.parse(key);
          sendMessage({ type: 'subscribe_chart', instrument: symbol, interval });
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
          } else if (data.type === "subscription.error") {
            notify.warning(data.message, { title: "Market data unavailable" });
          } else if (data.type === "request.error") {
            notify.error(data.message, { title: "Market data request failed" });
          } else if (data.type === "tick") {
            handleTickData(data);
          } else if (["ORDER_UPDATE", "POSITION_UPDATE"].includes(data.event_type)) {
            terminalCallbacks.forEach((callback) => callback(data));
            dispatch(setManualTradingTerminalUpdate(data));
          } else if (data.type === 'chart.candle') {
            chartCallbacks.get(JSON.stringify([data.symbol, data.interval]))?.forEach((callback) => callback(data.candle));

          }
        } catch (error) {
          console.error("WS message parse error:", error);
        }
      };

      socketRef.current.onclose = (event) => {
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

        if (event.code !== 4401 && !intentionalCloseRef.current && mountedConsumers > 0) {
          retry();
        }
      };

      socketRef.current.onerror = (error) => {
        console.error("WebSocket error:", error);
        dispatch(setConnectionStatus("error"));
      };
    } catch (error) {
      console.error("WS setup error:", error);
      dispatch(setConnectionStatus("error"));
      retry();
    }
  }, [
    dispatch,
    handleTickData,
    notify,
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
      socketRef.current.onclose = null;
      socketRef.current.onmessage = null;
      socketRef.current.onopen = null;
      socketRef.current.onerror = null;
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
      if (!symbol) return () => {};
      const normalizedSymbol = normalizeSymbol(symbol);

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
          instrument: normalizedSymbol,
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
            instrument: normalizedSymbol,
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
      if (isObservedQuote(liveTick) && !options.force) {
        return liveTick;
      }

      if (!fetchingPrices.has(normalizedSymbol)) {
        const request = api.get(`/market/latest-tick/?instrument=${encodeURIComponent(normalizedSymbol)}`)
          .then(({ data }) => {
            const current = tickDataRef.current[normalizedSymbol];
            const latest = isNewerQuote(data, current) ? data : current;
            if (latest) dispatch(updateTickData({ symbol: normalizedSymbol, data: latest }));
            return latest ?? null;
          })
          .catch(() => null)
          .finally(() => fetchingPrices.delete(normalizedSymbol));
        fetchingPrices.set(normalizedSymbol, request);
      }
      return fetchingPrices.get(normalizedSymbol);
    },
    [dispatch]
  );

  const getTickData = useCallback(
    (symbol) => symbol ? tickDataRef.current[normalizeSymbol(symbol)] ?? null : null,
    []
  );

  const subscribeChart = useCallback((symbol, interval, callback) => {
    const key = JSON.stringify([symbol, interval]);
    if (!chartCallbacks.has(key)) {
      chartCallbacks.set(key, new Set());
      sendMessage({ type: 'subscribe_chart', instrument: symbol, interval });
    }
    chartCallbacks.get(key).add(callback);
    return () => {
      const callbacks = chartCallbacks.get(key);
      callbacks?.delete(callback);
      if (!callbacks?.size) {
        chartCallbacks.delete(key);
        sendMessage({ type: 'unsubscribe_chart', instrument: symbol, interval });
      }
    };
  }, [sendMessage]);

  return {
    isConnected,
    connectionStatus,
    tickData,
    subscriptions,
    connect,
    disconnect,
    sendMessage,
    subscribe,
    subscribeChart,
    getLatestPrice,
    getTickData,
  };
}
