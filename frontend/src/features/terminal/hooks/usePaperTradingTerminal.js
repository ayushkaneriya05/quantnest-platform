import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSelector } from "react-redux";
import { useNotifications } from "@/shared/hooks/useNotifications";

import tradingTerminalApi from "@/features/terminal/services/tradingTerminalApi.js";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";

export function usePaperTradingTerminal(initialSymbol = null) {
  const { notify } = useNotifications();
  const manualTradingTerminalUpdate = useSelector(
    (state) => state.websocket.manualTradingTerminalUpdate,
  );
  const refreshTimerRef = useRef(null);
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedSymbol, setSelectedSymbol] = useState(initialSymbol);
  const [selectedInstrumentId, setSelectedInstrumentId] = useState(null);
  const [watchlistWidth, setWatchlistWidth] = useState(320);
  const [isOrderModalOpen, setIsOrderModalOpen] = useState(false);
  const [transactionType, setTransactionType] = useState("BUY");

  const refreshSnapshot = useCallback(async () => {
    try {
      const response = await tradingTerminalApi.getSnapshot();
      const data = response.data;
      setSnapshot(data);

      setSelectedSymbol((current) => {
        if (!current && data.watchlist?.length) {
          const first = data.watchlist[0];
          setSelectedInstrumentId(first.id);
          return first.sym_ticker || first.symbol;
        }

        const match = data.watchlist?.find(
          (item) => (item.sym_ticker || item.symbol) === current,
        );
        if (match) {
          setSelectedInstrumentId(match.id);
        }

        return current;
      });
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to load paper trading terminal."));
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    refreshSnapshot();
  }, [refreshSnapshot]);

  useEffect(() => {
    if (!manualTradingTerminalUpdate) return;

    if (["ORDER_UPDATE", "POSITION_UPDATE"].includes(manualTradingTerminalUpdate.event_type)) {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
      refreshTimerRef.current = setTimeout(() => {
        refreshSnapshot();
      }, 150);
    }
  }, [manualTradingTerminalUpdate, refreshSnapshot]);

  useEffect(
    () => () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    },
    [],
  );

  const openOrderModal = useCallback((side) => {
    setTransactionType(side);
    setIsOrderModalOpen(true);
  }, []);

  const closeOrderModal = useCallback(() => {
    setIsOrderModalOpen(false);
  }, []);

  const handleOrderPlaced = useCallback(async () => {
    setIsOrderModalOpen(false);
    await refreshSnapshot();
  }, [refreshSnapshot]);

  const addToWatchlist = useCallback(
    async (instrument) => {
      try {
        await tradingTerminalApi.addToWatchlist(instrument.id);
        await refreshSnapshot();
        setSelectedInstrumentId(instrument.id);
        setSelectedSymbol(instrument.sym_ticker || instrument.symbol);
        notify.success(`${instrument.sym_ticker || instrument.symbol} added to watchlist`);
      } catch (error) {
        notify.error(getApiErrorMessage(error, "Could not add symbol to watchlist."));
      }
    },
    [notify, refreshSnapshot],
  );

  const removeFromWatchlist = useCallback(
    async (instrumentId) => {
      try {
        await tradingTerminalApi.removeFromWatchlist(instrumentId);
        setSnapshot((current) => {
          if (!current) return current;
          const nextWatchlist = current.watchlist.filter(
            (item) => item.id !== instrumentId,
          );
          if (
            selectedSymbol &&
            !nextWatchlist.some(
              (item) => (item.sym_ticker || item.symbol) === selectedSymbol,
            )
          ) {
            setSelectedInstrumentId(nextWatchlist[0]?.id || null);
            setSelectedSymbol(
              nextWatchlist[0]?.sym_ticker ||
                nextWatchlist[0]?.symbol ||
                initialSymbol,
            );
          }
          return { ...current, watchlist: nextWatchlist };
        });
        notify.success("Removed from watchlist");
      } catch (error) {
        notify.error(getApiErrorMessage(error, "Could not remove symbol from watchlist."));
      }
    },
    [initialSymbol, notify, selectedSymbol],
  );

  const account = snapshot?.account ?? null;
  const watchlist = useMemo(
    () => snapshot?.watchlist ?? [],
    [snapshot?.watchlist],
  );
  const positions = useMemo(
    () => snapshot?.positions ?? [],
    [snapshot?.positions],
  );

  useEffect(() => {
    if (!watchlist.length || !selectedSymbol) return;
    const match = watchlist.find(
      (item) => (item.sym_ticker || item.symbol) === selectedSymbol,
    );
    if (match && selectedInstrumentId !== match.id) {
      setSelectedInstrumentId(match.id);
    }
  }, [selectedSymbol, selectedInstrumentId, watchlist]);
  const openOrders = useMemo(
    () => snapshot?.open_orders ?? [],
    [snapshot?.open_orders],
  );
  const recentTrades = useMemo(
    () => snapshot?.recent_trades ?? [],
    [snapshot?.recent_trades],
  );

  const terminalMetrics = useMemo(
    () => ({
      balance: Number(account?.balance ?? 0),
      margin: Number(account?.margin ?? 0),
      marketValue: Number(account?.market_value ?? 0),
      realizedPnl: Number(account?.realized_pnl ?? 0),
      unrealizedPnl: Number(account?.unrealized_pnl ?? 0),
      positionsCount: positions.length,
      openOrdersCount: openOrders.length,
      watchlistCount: watchlist.length,
    }),
    [account, positions.length, openOrders.length, watchlist.length],
  );

  return useMemo(
    () => ({
      loading,
      snapshot,
      account,
      watchlist,
      positions,
      openOrders,
      recentTrades,
      terminalMetrics,
      selectedSymbol,
      selectedInstrumentId,
      setSelectedSymbol,
      setSelectedInstrumentId,
      watchlistWidth,
      setWatchlistWidth,
      isOrderModalOpen,
      transactionType,
      openOrderModal,
      closeOrderModal,
      handleOrderPlaced,
      refreshSnapshot,
      addToWatchlist,
      removeFromWatchlist,
    }),
    [
      loading,
      snapshot,
      account,
      watchlist,
      positions,
      openOrders,
      recentTrades,
      terminalMetrics,
      selectedSymbol,
      watchlistWidth,
      isOrderModalOpen,
      transactionType,
      openOrderModal,
      closeOrderModal,
      handleOrderPlaced,
      refreshSnapshot,
      addToWatchlist,
      removeFromWatchlist,
    ],
  );
}

export default usePaperTradingTerminal;
