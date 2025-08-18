// src/context/TradingContext.jsx
import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
} from "react";
import api from "@/services/api"; // your existing axios wrapper
import orderService from "@/services/orderService";

const TradingContext = createContext(null);

export function TradingProvider({ children }) {
  const [orders, setOrders] = useState([]);
  const [positions, setPositions] = useState([]);
  const [trades, setTrades] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [orderbook, setOrderbook] = useState({ bids: [], asks: [] });
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const pendingRefresh = useRef(false);

  const fetchAll = useCallback(async () => {
    try {
      const [oRes, pRes, tRes] = await Promise.all([
        api.get("/paper/orders/list/"),
        api.get("/paper/positions/"),
        api.get("/paper/orders/trades/"),
      ]);
      setOrders(oRes.data || oRes);
      setPositions(pRes.data || pRes);
      setTrades((tRes.data || tRes).slice(0, 500));
    } catch (e) {
      // ignore for now
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // websocket connection to Channels consumer /ws/marketdata/
  useEffect(() => {
    const token = localStorage.getItem("accessToken");
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${protocol}://${
      window.location.host
    }/ws/marketdata/?token=${encodeURIComponent(token || "")}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        // tick messages -> bubble event for charts
        if (msg.type === "tick" && msg.data) {
          window.dispatchEvent(
            new CustomEvent("quantnest:tick", { detail: msg.data })
          );
        }
        // user messages: order_update, position_update, account_update
        if (
          msg.type === "order_update" ||
          msg.type === "position_update" ||
          msg.type === "account_update"
        ) {
          // schedule a partial refresh of local lists
          if (!pendingRefresh.current) {
            pendingRefresh.current = true;
            setTimeout(() => {
              fetchAll();
              pendingRefresh.current = false;
            }, 300); // small debounce
          }
        }
      } catch (err) {
        console.warn("WS parse err", err);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      console.log("WebSocket closed. Attempting to handle gracefully.");

      // Don't use a drastic page reload. Instead, try to refresh the token
      // or log the user out if the token is invalid. The API interceptor
      // in api.jsx will handle this automatically on the next API call.
      // We can simply trigger a data fetch to see if we are still authenticated.
      setTimeout(() => {
        // This will trigger the 401 interceptor in api.jsx if the token is bad
        fetchAll().catch(() => {
          console.error("Could not re-authenticate after WebSocket closure.");
          // If fetchAll fails after a ws close, the interceptor will handle the logout/redirect.
        });
      }, 2000); // Wait 2 seconds before trying
    };
    return () => {
      try {
        ws.close();
      } catch (e) {}
    };
  }, [fetchAll]);

  // orderbook snapshot helper
  const fetchOrderbook = useCallback(async (symbol, depth = 12) => {
    if (!symbol) return;
    try {
      const res = await api.get(
        `/paper/orderbook/${encodeURIComponent(symbol)}/?depth=${depth}`
      );
      const payload = res.data || res;
      setOrderbook(payload);
      return payload;
    } catch (e) {
      return null;
    }
  }, []);

  // actions
  const placeOrder = useCallback(
    async (payload) => {
      const res = await orderService.placeOrder(payload);
      await fetchAll();
      return res;
    },
    [fetchAll]
  );

  const placeBracket = useCallback(
    async (payload) => {
      const res = await orderService.placeBracket(payload);
      await fetchAll();
      return res;
    },
    [fetchAll]
  );

  const placeCover = useCallback(
    async (payload) => {
      const res = await orderService.placeCover(payload);
      await fetchAll();
      return res;
    },
    [fetchAll]
  );

  const cancelOrder = useCallback(
    async (orderId) => {
      const res = await orderService.cancel(orderId);
      await fetchAll();
      return res;
    },
    [fetchAll]
  );

  const modifyOrder = useCallback(
    async (orderId, body) => {
      const res = await orderService.modify(orderId, body);
      await fetchAll();
      return res;
    },
    [fetchAll]
  );

  const fetchAuditLogs = useCallback(async (params) => {
    try {
      const res = await orderService.fetchAudit(params);
      setAuditLogs(res.data || res);
      return res;
    } catch (e) {
      return null;
    }
  }, []);

  const modifyPositionSLTP = useCallback(
    async (positionId, sl, tp) => {
      const res = await api.post(`/paper/positions/${positionId}/`, {
        sl_price: sl,
        tp_price: tp,
      });
      await fetchAll();
      return res;
    },
    [fetchAll]
  );

  const value = {
    orders,
    positions,
    trades,
    auditLogs,
    orderbook,
    connected,
    placeOrder,
    placeBracket,
    placeCover,
    cancelOrder,
    modifyOrder,
    fetchOrderbook,
    fetchAll,
    fetchAuditLogs,
    modifyPositionSLTP, // Added to context value
  };

  return (
    <TradingContext.Provider value={value}>{children}</TradingContext.Provider>
  );
}

export function useTrading() {
  const ctx = useContext(TradingContext);
  if (!ctx) throw new Error("useTrading must be used inside TradingProvider");
  return ctx;
}
