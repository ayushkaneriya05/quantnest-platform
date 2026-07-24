import { useState, useCallback } from "react";
import tradingTerminalApi from "../services/tradingTerminalApi";
import { useNotifications } from "@/shared/hooks/useNotifications";

export default function useHistoricalData() {
  const { notify } = useNotifications();

  // Orders State
  const [orders, setOrders] = useState([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersTotalCount, setOrdersTotalCount] = useState(0);

  // Trades State
  const [trades, setTrades] = useState([]);
  const [tradesLoading, setTradesLoading] = useState(false);
  const [tradesTotalCount, setTradesTotalCount] = useState(0);

  // P&L State
  const [pnlLogs, setPnlLogs] = useState([]);
  const [pnlLoading, setPnlLoading] = useState(false);
  const [pnlTotalCount, setPnlTotalCount] = useState(0);

  const fetchOrders = useCallback(async (params = {}) => {
    try {
      setOrdersLoading(true);
      const response = await tradingTerminalApi.getOrdersHistory(params);
      
      if (response.data.results) {
        setOrders(response.data.results);
        setOrdersTotalCount(response.data.count);
      } else {
        setOrders(response.data);
        setOrdersTotalCount(response.data.length);
      }
    } catch (error) {
      notify.error("Failed to load order history");
    } finally {
      setOrdersLoading(false);
    }
  }, [notify]);

  const fetchTrades = useCallback(async (params = {}) => {
    try {
      setTradesLoading(true);
      const response = await tradingTerminalApi.getTradesHistory(params);
      
      if (response.data.results) {
        setTrades(response.data.results);
        setTradesTotalCount(response.data.count);
      } else {
        setTrades(response.data);
        setTradesTotalCount(response.data.length);
      }
    } catch (error) {
      notify.error("Failed to load trade history");
    } finally {
      setTradesLoading(false);
    }
  }, [notify]);

  const fetchPnlLogs = useCallback(async (params = {}) => {
    try {
      setPnlLoading(true);
      const response = await tradingTerminalApi.getPnlHistory(params);
      
      if (response.data.results) {
        setPnlLogs(response.data.results);
        setPnlTotalCount(response.data.count);
      } else {
        setPnlLogs(response.data);
        setPnlTotalCount(response.data.length);
      }
    } catch (error) {
      notify.error("Failed to load P&L history");
    } finally {
      setPnlLoading(false);
    }
  }, [notify]);

  return {
    orders,
    ordersLoading,
    ordersTotalCount,
    fetchOrders,
    
    trades,
    tradesLoading,
    tradesTotalCount,
    fetchTrades,

    pnlLogs,
    pnlLoading,
    pnlTotalCount,
    fetchPnlLogs,
  };
}
