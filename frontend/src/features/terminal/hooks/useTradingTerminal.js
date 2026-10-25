import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useEnums } from "@/shared/context/EnumsContext";
import { useSelector } from "react-redux";
import { useSearchParams } from "react-router-dom";
import { useNotifications } from "@/shared/hooks/useNotifications";
import tradingTerminalApi from "@/features/terminal/services/tradingTerminalApi.js";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { subscribeTerminalUpdates } from '@/shared/hooks/useWebSocket';
import { useStableCallback } from '@/shared/hooks/useStableCallback';

export default function useTradingTerminal() {
  const [params] = useSearchParams();
  const { notify } = useNotifications();
  const { values } = useEnums();
  const openStatus = values.TerminalOrderStatus?.OPEN;
  const connected = useSelector((state) => state.websocket.isConnected);
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [watchlistId, setWatchlistId] = useState(() => Number(params.get('watchlist')) || Number(localStorage.getItem('terminal.watchlist')) || 0);
  const [selectedSymbol, setSelectedSymbol] = useState(() => localStorage.getItem("terminal.symbol") || null);
  const sequence = useRef(0);
  const pendingEvents = useRef([]);
  const wasConnected = useRef(connected), connectedOnce = useRef(connected);
  const applyEvent = useCallback((current, update) => {
    if (!current || !openStatus) return current;
    const row = update.data;
    if (update.event_type === 'ORDER_UPDATE') {
      const working = current.open_orders.filter((order) => order.id !== row.id);
      if (row.status === openStatus) working.unshift(row);
      return { ...current, account: { ...current.account, ...row.account_snapshot }, open_orders: working };
    }
    if (update.event_type === 'POSITION_UPDATE') {
      const positions = current.positions.filter((position) => position.id !== row.id);
      if (!row.deleted && row.quantity) positions.push(row);
      return { ...current, positions };
    }
    return current;
  }, [openStatus]);
  const refreshSnapshot = useStableCallback(async () => {
    const identity = ++sequence.current;
    pendingEvents.current = [];
    try {
      const response = await tradingTerminalApi.getSnapshot(watchlistId);
      if (identity !== sequence.current) return;
      setSnapshot(pendingEvents.current.reduce(applyEvent, response.data));
      localStorage.setItem('terminal.watchlist', String(response.data.watchlist_id));
      setSelectedSymbol((current) => [...response.data.watchlist, ...response.data.positions.map((row) => row.instrument),
        ...response.data.open_orders.map((row) => row.instrument)].some((item) => item.sym_ticker === current) ? current : response.data.watchlist[0]?.sym_ticker || response.data.positions[0]?.instrument.sym_ticker || null);
    } catch (error) {
      if (error.response?.status === 404 && watchlistId) setWatchlistId(0);
      else notify.error(getApiErrorMessage(error, "Could not load the terminal."));
    }
    finally { if (identity === sequence.current) setLoading(false); }
  });
  useEffect(() => { refreshSnapshot(); }, [refreshSnapshot, watchlistId]);
  useEffect(() => {
    const reconnected = connected && !wasConnected.current && connectedOnce.current;
    wasConnected.current = connected;
    if (connected) connectedOnce.current = true;
    // An in-progress first load already includes buffered socket events.
    if (reconnected && snapshot) refreshSnapshot();
  }, [connected, snapshot, refreshSnapshot]);
  useEffect(() => {
    const onFocus = () => refreshSnapshot();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [refreshSnapshot]);
  useEffect(() => { if (selectedSymbol) localStorage.setItem("terminal.symbol", selectedSymbol); }, [selectedSymbol]);
  useEffect(() => {
    if (openStatus) setSnapshot((current) => pendingEvents.current.reduce(applyEvent, current));
  }, [applyEvent, openStatus]);
  useEffect(() => subscribeTerminalUpdates((event) => {
    pendingEvents.current = [...pendingEvents.current.slice(-499), event];
    setSnapshot((current) => applyEvent(current, event));
  }), [applyEvent]);
  useEffect(() => () => { sequence.current++; }, []);
  const addToWatchlist = useCallback(async (instrument) => {
    try {
      await tradingTerminalApi.addToWatchlist(instrument.sym_ticker, watchlistId);
      await refreshSnapshot();
      setSelectedSymbol(instrument.sym_ticker);
      notify.success("Added to watchlist");
    } catch (error) { notify.error(getApiErrorMessage(error, "Could not add instrument.")); }
  }, [notify, refreshSnapshot, watchlistId]);
  const removeFromWatchlist = useCallback(async (symTicker) => {
    try {
      await tradingTerminalApi.removeFromWatchlist(symTicker, watchlistId);
      setSnapshot((current) => ({ ...current, watchlist: current.watchlist.filter((item) => item.sym_ticker !== symTicker) }));
    } catch (error) { notify.error(getApiErrorMessage(error, "Could not remove instrument.")); }
  }, [notify, watchlistId]);
  const selectedInstrument = useMemo(() => {
    const instruments = [...(snapshot?.watchlist || []), ...(snapshot?.positions || []).map((p) => p.instrument), ...(snapshot?.open_orders || []).map((o) => o.instrument)];
    return instruments.find((item) => item.sym_ticker === selectedSymbol) || null;
  }, [snapshot?.watchlist, snapshot?.positions, snapshot?.open_orders, selectedSymbol]);
  useEffect(() => {
    if (snapshot && !selectedInstrument) setSelectedSymbol(snapshot.watchlist[0]?.sym_ticker || snapshot.positions[0]?.instrument.sym_ticker || snapshot.open_orders[0]?.instrument.sym_ticker || null);
  }, [snapshot, selectedInstrument]);
  return { loading, snapshot, account: snapshot?.account, watchlist: snapshot?.watchlist || [],
    positions: snapshot?.positions || [], openOrders: snapshot?.open_orders || [],
    watchlists: snapshot?.watchlists || [], watchlistId: snapshot?.watchlist_id || 0, setWatchlistId,
    selectedSymbol, selectedInstrument, setSelectedSymbol, refreshSnapshot, addToWatchlist, removeFromWatchlist };
}

