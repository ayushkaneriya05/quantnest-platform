import { useCallback, useEffect, useRef, useState } from "react";
import { useLiveTradingWebSocket } from "@/shared/hooks/useLiveTradingWebSocket";
import { useStableCallback } from "@/shared/hooks/useStableCallback";
import { usePagination, useQueryState } from "@/shared/hooks/usePagination";
import { liveTradingApi } from "@/shared/services/liveTradingApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useLivePositionSummary } from "@/shared/hooks/useLivePositionsPnL";

const emptyPage = () => ({ count: 0, results: [] });

export function useLiveTradingData({ includePortfolio = false, activeTab = "portfolio", sessionStatus = "all", notify } = {}) {
  const [summary, setSummary] = useState({});
  const [sessions, setSessions] = useState([]);
  const [sessionMetadata, setSessionMetadata] = useState(emptyPage);
  const [positions, setPositions] = useState(emptyPage);
  const [orders, setOrders] = useState(emptyPage);
  const [trades, setTrades] = useState(emptyPage);
  const [positionsSummary, setPositionsSummary] = useState({});
  const [ordersSummary, setOrdersSummary] = useState({});
  const [tradesSummary, setTradesSummary] = useState({});
  const liveSummary = useLivePositionSummary(summary);
  const livePositionsSummary = useLivePositionSummary(positionsSummary);
  const [positionAllocation, setPositionAllocation] = useQueryState("allocation", "", { namespace: "positions", replace: false });
  const [orderAllocation, setOrderAllocation] = useQueryState("allocation", "", { namespace: "orders", replace: false });
  const [tradeAllocation, setTradeAllocation] = useQueryState("allocation", "", { namespace: "trades", replace: false });
  const [orderStatus, setOrderStatus] = useQueryState("status", "", { namespace: "orders", replace: false });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [listLoading, setListLoading] = useState(false);
  const [error, setError] = useState("");
  const positionPages = usePagination(positionAllocation, "positions");
  const orderPages = usePagination(JSON.stringify([orderAllocation, orderStatus]), "orders");
  const tradePages = usePagination(tradeAllocation, "trades");
  const sessionPages = usePagination(sessionStatus, "sessions");
  const requests = useRef({});
  const summaryIdentity = useRef("");
  const timer = useRef(null);

  // Only the visible table loads display rows; compact summary inputs cover all exposure.
  const fetchPage = useStableCallback(async (withSummary = false) => {
    const kind = includePortfolio ? activeTab : "sessions";
    const config = {
      sessions: { paging: sessionPages, filters: sessionStatus === "all" ? {} : { status: sessionStatus },
        save: data => { setSessions(data.results); setSessionMetadata(data); }, query: liveTradingApi.getSessions },
      positions: { paging: positionPages, filters: positionAllocation ? { allocation: positionAllocation } : {},
        save: setPositions, query: liveTradingApi.getPositions, aggregate: liveTradingApi.getPositionsSummary, saveSummary: setPositionsSummary },
      orders: { paging: orderPages, filters: { ...(orderAllocation ? { allocation: orderAllocation } : {}), ...(orderStatus ? { status: orderStatus } : {}) },
        save: setOrders, query: liveTradingApi.getOrders, aggregate: liveTradingApi.getOrdersSummary, saveSummary: setOrdersSummary },
      trades: { paging: tradePages, filters: tradeAllocation ? { allocation: tradeAllocation } : {},
        save: setTrades, query: liveTradingApi.getTrades, aggregate: liveTradingApi.getTradesSummary, saveSummary: setTradesSummary },
    }[kind];
    if (!config) { setError(""); setListLoading(false); return; }
    const { paging, filters, save, query, aggregate, saveSummary } = config;
    requests.current[kind]?.abort();
    const controller = new AbortController(); requests.current[kind] = controller;
    setListLoading(true); setError("");
    const identity = JSON.stringify([kind, filters]);
    try {
      const response = await query({ ...filters, page: paging.page, page_size: paging.pageSize }, controller.signal);
      if (controller.signal.aborted) return;
      save(response.data); paging.accept(response.data);
      if (aggregate && (withSummary || summaryIdentity.current !== identity)) {
        const snapshot = await aggregate(filters, controller.signal);
        if (!controller.signal.aborted) { saveSummary(snapshot.data); summaryIdentity.current = identity; }
      }
    } catch (error) { if (!controller.signal.aborted) setError(getApiErrorMessage(error, "Could not load live records.")); }
    finally { if (!controller.signal.aborted) setListLoading(false); }
  });
  const fetchSummary = useStableCallback(async () => {
    requests.current.summary?.abort();
    const controller = new AbortController(); requests.current.summary = controller;
    try {
      const response = await liveTradingApi.getSummary(controller.signal);
      if (!controller.signal.aborted) setSummary(response.data);
    } catch (error) { if (!controller.signal.aborted) notify?.error(getApiErrorMessage(error, "Could not refresh live trading.")); }
    finally { if (!controller.signal.aborted) setLoading(false); }
  });
  const loadData = useStableCallback(async (spinner = true) => {
    if (spinner) setLoading(true);
    await Promise.all([fetchSummary(), fetchPage(true)]);
    setRefreshing(false);
  });
  useEffect(() => {
    fetchSummary();
    const poll = setInterval(() => loadData(false), 30000);
    const active = requests.current;
    const timers = timer;
    return () => { clearInterval(poll); clearTimeout(timers.current); Object.values(active).forEach(controller => controller.abort()); };
  }, [loadData, fetchSummary]);
  useEffect(() => { summaryIdentity.current = ''; }, [activeTab]);
  useEffect(() => {
    fetchPage();
    const kind = includePortfolio ? activeTab : "sessions";
    const pending = requests.current;
    return () => pending[kind]?.abort();
  }, [fetchPage, activeTab, sessionStatus, includePortfolio, positionPages.page, positionPages.pageSize, orderPages.page, orderPages.pageSize, tradePages.page, tradePages.pageSize, sessionPages.page, sessionPages.pageSize, positionAllocation, orderAllocation, orderStatus, tradeAllocation]);
  const liveUpdate = useCallback(() => { clearTimeout(timer.current); timer.current = setTimeout(() => loadData(false), 200); }, [loadData]);
  const { isConnected } = useLiveTradingWebSocket(liveUpdate);
  const refresh = useCallback(() => { setRefreshing(true); return loadData(false); }, [loadData]);
  return {
    summary: { ...liveSummary, day_pnl: Number(summary.realized_today || 0) + Number(liveSummary.unrealized_pnl || 0),
      profitable_positions: liveSummary.profitable ?? summary.profitable_positions,
      losing_positions: liveSummary.losing ?? summary.losing_positions },
    sessions: sessions.map(session => ({ ...session, pnl: Number(session.allocation?.realized_pnl || 0)
      + Number(liveSummary.by_account?.[session.allocation?.id]?.unrealized_pnl || 0) })),
    sessionMetadata, positions, orders, trades, positionsSummary: livePositionsSummary, ordersSummary, tradesSummary,
    loading, refreshing, listLoading, error, isConnected, refresh, loadData,
    positionPages, orderPages, tradePages, sessionPages,
    positionAllocation, orderAllocation, tradeAllocation, orderStatus,
    filterPositions: value => { requests.current.positions?.abort(); setPositions(emptyPage()); setPositionsSummary({}); setPositionAllocation(value); },
    filterOrderAllocation: value => { requests.current.orders?.abort(); setOrders(emptyPage()); setOrdersSummary({}); setOrderAllocation(value); },
    filterOrders: value => { requests.current.orders?.abort(); setOrders(emptyPage()); setOrdersSummary({}); setOrderStatus(value); },
    filterTrades: value => { requests.current.trades?.abort(); setTrades(emptyPage()); setTradesSummary({}); setTradeAllocation(value); },
  };
}
