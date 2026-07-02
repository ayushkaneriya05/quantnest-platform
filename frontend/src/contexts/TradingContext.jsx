// frontend/src/contexts/TradingContext.jsx
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import React from "react";
import api from "../services/api";
import { useSelector } from "react-redux";

const TradingContext = createContext();

export function TradingProvider({ children }) {
  const [orders, setOrders] = useState([]);
  const [positions, setPositions] = useState([]);
  const [trades, setTrades] = useState([]);
  const [account, setAccount] = useState(null);
  const { accessToken } = useSelector((state) => state.auth);

  const fetchAll = useCallback(async () => {
    try {
      const [oRes, pRes, tRes, aRes] = await Promise.all([
        api.get("/paper/orders/list/"),
        api.get("/paper/positions/"),
        api.get("/paper/orders/trades/"),
        api.get("/paper/account/"),
      ]);
      setOrders(oRes.data || []);
      setPositions(pRes.data || []);
      setTrades((tRes.data || []).slice(0, 500));
      setAccount(aRes.data);
    } catch (e) {
      console.error("Failed to fetch all trading data:", e);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // ✅ New WebSocket for real-time trading updates
  useEffect(() => {
    if (!accessToken) return;

    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${wsProtocol}://${window.location.host}/ws/trading/?token=${accessToken}`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("Trading WebSocket connected.");
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.message?.event === "UPDATE") {
        console.log(
          "Received trading update from server. Refetching all data."
        );
        fetchAll(); // Re-fetch all data when an update occurs
      }
    };

    ws.onclose = () => {
      console.log("Trading WebSocket disconnected.");
      // You can add reconnect logic here if needed
    };

    ws.onerror = (error) => {
      console.error("Trading WebSocket error:", error);
    };

    return () => {
      ws.close();
    };
  }, [accessToken, fetchAll]);

  return (
    <TradingContext.Provider
      value={{ orders, positions, trades, account, refresh: fetchAll }}
    >
      {children}
    </TradingContext.Provider>
  );
}

export const useTrading = () => useContext(TradingContext);
