import { useCallback, useEffect, useRef, useState } from 'react';
import { useEnums } from '@/shared/context/EnumsContext';
import { useWebSocket } from '@/shared/hooks/useWebSocket';
import terminalApi from '../services/tradingTerminalApi';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';

export default function useRealtimeCandles(symbol, interval, onCandle, onTick) {
  const { values } = useEnums();
  const key = JSON.stringify([symbol, interval]);
  const limit = interval === values.ChartTimeframe.MN1 ? 60 : interval === values.ChartTimeframe.W1 ? 104 : 200;
  const [history, setHistory] = useState({ key: '', rows: [] });
  const [status, setStatus] = useState('idle'), [error, setError] = useState('');
  const [session, setSession] = useState(null), [revision, setRevision] = useState(0);
  const [fetchingHistory, setFetchingHistory] = useState(false);
  const [isLoadingOlder, setIsLoadingOlder] = useState(false), [hasMoreHistory, setHasMoreHistory] = useState(false);
  const cursor = useRef(null), older = useRef(null), connectedOnce = useRef(false);
  const { subscribe, subscribeChart, isConnected, getLatestPrice } = useWebSocket();

  const readWindow = useCallback(async (before, controller) => {
    let data;
    for (let page = 0; page < 2; page++) {
      if (controller.signal.aborted) return null;
      const response = await terminalApi.getCandles({ symbol, interval, limit, before,
        fetchMissing: page > 0, signal: controller.signal });
      if (controller.signal.aborted) return null;
      const pageData = response.data;
      data = pageData;
      setError(pageData.history_error);
      setHistory((current) => {
        const rows = new Map((current.key === key ? current.rows : []).map((row) => [row.time, row]));
        pageData.candles.forEach((row) => { if (!rows.has(row.time) || row.revision >= rows.get(row.time).revision) rows.set(row.time, row); });
        return { key, rows: [...rows.values()].sort((a, b) => a.time - b.time) };
      });
      if (!before) { setSession(data.session); setStatus(data.candles.length ? 'ready' : 'loading'); }
      if (!data.backfill_requested || data.history_error) break;
      setFetchingHistory(true);
    }
    return data;
  }, [symbol, interval, key, limit]);

  useEffect(() => {
    const controller = new AbortController();
    older.current?.abort(); older.current = null;
    setHistory((current) => current.key === key ? current : { key, rows: [] }); setError(''); setSession(null);
    setHasMoreHistory(false); setFetchingHistory(false); setIsLoadingOlder(false);
    cursor.current = null;
    if (!symbol) { setStatus('idle'); return () => controller.abort(); }
    setStatus('loading');
    readWindow(undefined, controller).then((data) => {
      if (!data || controller.signal.aborted) return;
      cursor.current = data.pagination.next_before;
      setHasMoreHistory(data.pagination.has_more);
      setStatus(data.candles.length ? 'ready' : data.history_error ? 'error' : 'empty');
    }).catch((failure) => {
      if (!controller.signal.aborted) { setError(getApiErrorMessage(failure, 'Could not load chart history.')); setStatus('error'); }
    }).finally(() => { if (!controller.signal.aborted) setFetchingHistory(false); });
    return () => { controller.abort(); older.current?.abort(); };
  }, [symbol, key, readWindow, revision]);

  const loadOlder = useCallback(async () => {
    if (!symbol || !cursor.current || older.current || fetchingHistory) return;
    const controller = new AbortController();
    older.current = controller; setIsLoadingOlder(true);
    try {
      const data = await readWindow(cursor.current, controller);
      if (!data || controller.signal.aborted) return;
      cursor.current = data.pagination.next_before;
      setHasMoreHistory(data.pagination.has_more);
    } catch (failure) {
      if (!controller.signal.aborted) setError(getApiErrorMessage(failure, 'Could not load older history.'));
    } finally {
      if (older.current === controller) { older.current = null; setIsLoadingOlder(false); setFetchingHistory(false); }
    }
  }, [symbol, fetchingHistory, readWindow]);
  const reload = useCallback(() => setRevision((value) => value + 1), []);
  useEffect(() => {
    if (!isConnected) return;
    // The initial HTTP read already runs independently of the socket handshake.
    if (connectedOnce.current) reload();
    connectedOnce.current = true;
  }, [isConnected, reload]);
  useEffect(() => {
    if (!session?.next_transition) return undefined;
    const timer = setTimeout(reload, Math.max(1000, session.next_transition * 1000 - Date.now() + 500));
    return () => clearTimeout(timer);
  }, [session, reload]);

  useEffect(() => {
    if (!symbol || !isConnected) return undefined;
    let frame = null, candle, mounted = true;
    const offChart = subscribeChart(symbol, interval, (next) => {
      candle = next;
      if (frame === null) frame = requestAnimationFrame(() => { onCandle?.(candle); frame = null; });
    });
    const offTick = subscribe(symbol, onTick);
    getLatestPrice(symbol).then((tick) => { if (mounted && tick) onTick?.(tick); });
    return () => { mounted = false; offChart(); offTick(); if (frame !== null) cancelAnimationFrame(frame); };
  }, [symbol, interval, isConnected, subscribeChart, subscribe, getLatestPrice, onCandle, onTick]);

  return { historicalData: history.key === key ? history.rows : [], status, error, session,
    hasMoreHistory, fetchingHistory, isLoadingOlder, loadOlder, reload };
}
