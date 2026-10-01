import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useCallback, useEffect, useRef, useState } from "react";
import { useLiveTradingWebSocket } from "@/shared/hooks/useLiveTradingWebSocket";
import { liveTradingApi } from "@/shared/services/liveTradingApi";

const PAGE_SIZE = 25;
const PNL_POSITION_PAGE_SIZE = 200;
const emptyPage = () => ({ count: 0, next: null, previous: null, results: [] });
const rowsFrom = (response) => {
  const data = response?.data;
  return Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
};

export function useLiveTradingData({ includePortfolio = false, notify } = {}) {
  const [summary, setSummary] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [positions, setPositions] = useState(emptyPage);
  const [pnlPositions, setPnlPositions] = useState([]);
  const [orders, setOrders] = useState(emptyPage);
  const [trades, setTrades] = useState(emptyPage);
  const [positionsSummary, setPositionsSummary] = useState({});
  const [ordersSummary, setOrdersSummary] = useState({});
  const [tradesSummary, setTradesSummary] = useState({});
  const [positionsPage, setPositionsPage] = useState(1);
  const [ordersPage, setOrdersPage] = useState(1);
  const [tradesPage, setTradesPage] = useState(1);
  const [positionAllocation, setPositionAllocation] = useState("");
  const [orderAllocation, setOrderAllocation] = useState("");
  const [tradeAllocation, setTradeAllocation] = useState("");
  const [orderStatus, setOrderStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const refreshTimer = useRef(null);
  const pollRef = useRef(null);

  const fetchSessions = useCallback(async () => {
    const response = await liveTradingApi.getSessions();
    setSessions(rowsFrom(response));
  }, []);

  const fetchSummary = useCallback(async () => {
    const response = await liveTradingApi.getSummary();
    setSummary(response.data || {});
  }, []);

  const fetchPositions = useCallback(async (page = positionsPage, allocation = positionAllocation) => {
    const response = await liveTradingApi.getPositions({ page, page_size: PAGE_SIZE, ...(allocation ? { allocation } : {}) });
    setPositions(response.data?.results ? response.data : { ...emptyPage(), results: rowsFrom(response) });
    setPositionsPage(page);
  }, [positionAllocation, positionsPage]);

  const fetchPositionsSummary = useCallback(async (allocation = positionAllocation) => {
    const response = await liveTradingApi.getPositionsSummary(allocation ? { allocation } : {});
    setPositionsSummary(response.data || {});
  }, [positionAllocation]);

  const fetchAllPositionsForPnL = useCallback(async () => {
    const firstResponse = await liveTradingApi.getPositions({ page: 1, page_size: PNL_POSITION_PAGE_SIZE });
    const allPositions = rowsFrom(firstResponse);
    const count = Number(firstResponse.data?.count ?? allPositions.length);
    const pageCount = Math.ceil(count / PNL_POSITION_PAGE_SIZE);
    if (pageCount > 1) {
      const remainingPages = await Promise.all(
        Array.from({ length: pageCount - 1 }, (_, index) =>
          liveTradingApi.getPositions({ page: index + 2, page_size: PNL_POSITION_PAGE_SIZE }),
        ),
      );
      remainingPages.forEach((response) => allPositions.push(...rowsFrom(response)));
    }
    setPnlPositions(allPositions);
  }, []);

  const fetchOrders = useCallback(async (page = ordersPage, status = orderStatus, allocation = orderAllocation) => {
    const response = await liveTradingApi.getOrders({ page, page_size: PAGE_SIZE, ...(status ? { status } : {}), ...(allocation ? { allocation } : {}) });
    setOrders(response.data?.results ? response.data : { ...emptyPage(), results: rowsFrom(response) });
    setOrdersPage(page);
  }, [orderStatus, orderAllocation, ordersPage]);

  const fetchOrdersSummary = useCallback(async (status = orderStatus, allocation = orderAllocation) => {
    const response = await liveTradingApi.getOrdersSummary({ ...(status ? { status } : {}), ...(allocation ? { allocation } : {}) });
    setOrdersSummary(response.data || {});
  }, [orderStatus, orderAllocation]);

  const fetchTrades = useCallback(async (page = tradesPage, allocation = tradeAllocation) => {
    const response = await liveTradingApi.getTrades({ page, page_size: PAGE_SIZE, ...(allocation ? { allocation } : {}) });
    setTrades(response.data?.results ? response.data : { ...emptyPage(), results: rowsFrom(response) });
    setTradesPage(page);
  }, [tradesPage, tradeAllocation]);

  const fetchTradesSummary = useCallback(async (allocation = tradeAllocation) => {
    const response = await liveTradingApi.getTradesSummary(allocation ? { allocation } : {});
    setTradesSummary(response.data || {});
  }, [tradeAllocation]);

  const loadData = useCallback(async (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    try {
      const tasks = [fetchSummary(), fetchSessions()];
      if (includePortfolio) tasks.push(
        fetchPositions(1, positionAllocation), fetchPositionsSummary(positionAllocation),
        fetchAllPositionsForPnL(),
        fetchOrders(1, orderStatus, orderAllocation), fetchOrdersSummary(orderStatus, orderAllocation),
        fetchTrades(1, tradeAllocation), fetchTradesSummary(tradeAllocation),
      );
      await Promise.all(tasks);
    } catch (error) {
      notify?.error(getApiErrorMessage(error, "Failed to load live trading data"));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [fetchAllPositionsForPnL, fetchOrders, fetchOrdersSummary, fetchPositions, fetchPositionsSummary, fetchSessions, fetchSummary, fetchTrades, fetchTradesSummary, includePortfolio, notify, orderAllocation, orderStatus, positionAllocation, tradeAllocation]);

  const handleLiveUpdate = useCallback((payload) => {
    const type = payload?.event_type;
    if (!["SESSION_UPDATE", "ORDER_UPDATE", "POSITION_UPDATE"].includes(type)) return;
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
    refreshTimer.current = setTimeout(() => {
      const tasks = [fetchSummary(), fetchSessions()];
      if (includePortfolio && type !== "SESSION_UPDATE") {
        tasks.push(fetchPositions(positionsPage, positionAllocation), fetchPositionsSummary(positionAllocation));
        tasks.push(fetchAllPositionsForPnL());
        tasks.push(fetchOrders(ordersPage, orderStatus, orderAllocation), fetchOrdersSummary(orderStatus, orderAllocation));
        tasks.push(fetchTrades(tradesPage, tradeAllocation), fetchTradesSummary(tradeAllocation));
      } else if (includePortfolio) {
        tasks.push(fetchPositions(1, positionAllocation), fetchPositionsSummary(positionAllocation));
        tasks.push(fetchAllPositionsForPnL());
        tasks.push(fetchOrders(1, orderStatus, orderAllocation), fetchOrdersSummary(orderStatus, orderAllocation));
        tasks.push(fetchTrades(1, tradeAllocation), fetchTradesSummary(tradeAllocation));
      }
      Promise.all(tasks).catch((error) => {
        console.error("Live trading refresh failed", error);
      });
    }, 200);
  }, [fetchAllPositionsForPnL, fetchOrders, fetchOrdersSummary, fetchPositions, fetchPositionsSummary, fetchSessions, fetchSummary, fetchTrades, fetchTradesSummary, includePortfolio, orderAllocation, orderStatus, ordersPage, positionAllocation, positionsPage, tradeAllocation, tradesPage]);

  const refreshSnapshot = useCallback(() => {
    const tasks = [fetchSummary(), fetchSessions()];
    if (includePortfolio) {
      tasks.push(fetchPositions(positionsPage, positionAllocation), fetchPositionsSummary(positionAllocation));
      tasks.push(fetchAllPositionsForPnL());
      tasks.push(fetchOrders(ordersPage, orderStatus, orderAllocation), fetchOrdersSummary(orderStatus, orderAllocation));
      tasks.push(fetchTrades(tradesPage, tradeAllocation), fetchTradesSummary(tradeAllocation));
    }
    Promise.all(tasks).catch((error) => console.error("Live trading polling refresh failed", error));
  }, [fetchAllPositionsForPnL, fetchOrders, fetchOrdersSummary, fetchPositions, fetchPositionsSummary, fetchSessions, fetchSummary, fetchTrades, fetchTradesSummary, includePortfolio, orderAllocation, orderStatus, ordersPage, positionAllocation, positionsPage, tradeAllocation, tradesPage]);
  pollRef.current = refreshSnapshot;

  const { isConnected } = useLiveTradingWebSocket(handleLiveUpdate);

  useEffect(() => {
    loadData();
    const pollTimer = setInterval(() => {
      pollRef.current?.();
    }, 30000);
    return () => {
      if (refreshTimer.current) clearTimeout(refreshTimer.current);
      clearInterval(pollTimer);
    };
  }, []);

  const refresh = useCallback(() => {
    setRefreshing(true);
    return loadData(false);
  }, [loadData]);

  const changePositionsPage = useCallback((page) => fetchPositions(page, positionAllocation), [fetchPositions, positionAllocation]);
  const changeOrdersPage = useCallback((page) => fetchOrders(page, orderStatus, orderAllocation), [fetchOrders, orderAllocation, orderStatus]);
  const changeTradesPage = useCallback((page) => fetchTrades(page, tradeAllocation), [fetchTrades, tradeAllocation]);
  const filterPositions = useCallback((allocation) => {
    setPositionAllocation(allocation);
    return Promise.all([fetchPositions(1, allocation), fetchPositionsSummary(allocation)]);
  }, [fetchPositions, fetchPositionsSummary]);
  const filterOrders = useCallback((status) => {
    setOrderStatus(status);
    return Promise.all([fetchOrders(1, status, orderAllocation), fetchOrdersSummary(status, orderAllocation)]);
  }, [fetchOrders, fetchOrdersSummary, orderAllocation]);
  const filterOrderAllocation = useCallback((allocation) => {
    setOrderAllocation(allocation);
    return Promise.all([fetchOrders(1, orderStatus, allocation), fetchOrdersSummary(orderStatus, allocation)]);
  }, [fetchOrders, fetchOrdersSummary, orderStatus]);
  const filterTrades = useCallback((allocation) => {
    setTradeAllocation(allocation);
    return Promise.all([fetchTrades(1, allocation), fetchTradesSummary(allocation)]);
  }, [fetchTrades, fetchTradesSummary]);

  return {
    summary,
    sessions,
    positions,
    pnlPositions,
    orders,
    trades,
    positionsSummary,
    ordersSummary,
    tradesSummary,
    positionsPage,
    ordersPage,
    tradesPage,
    positionAllocation,
    orderAllocation,
    tradeAllocation,
    orderStatus,
    loading,
    refreshing,
    isConnected,
    refresh,
    loadData,
    changePositionsPage,
    changeOrdersPage,
    changeTradesPage,
    filterPositions,
    filterOrders,
    filterOrderAllocation,
    filterTrades,
  };
}
