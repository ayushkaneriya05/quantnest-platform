import { useEffect, useMemo } from "react";
import { useEnums } from "@/shared/context/EnumsContext";
import { useWebSocket } from "./useWebSocket";
import { isObservedQuote } from "../utils/marketData";

/**
 * Calculate P&L from LivePosition serializer rows and the central quote store.
 * Paper and Terminal adapters below supply this same row format.
 */
export function useLivePositionsPnL(positions = []) {
  const { values } = useEnums();
  const sell = values.Side?.SELL;
  const { subscribe, tickData, isConnected } = useWebSocket();
  const symbols = useMemo(
    () => [...new Set(positions
      .map((position) => position.instrument_symbol)
      .filter(Boolean))].sort(),
    [positions],
  );
  const symbolsKey = symbols.join("\u001f");

  // Position polling may replace the array every few seconds. Subscribe only
  // when the instrument set changes, not on every refresh.
  useEffect(() => {
    const symbolsToSubscribe = symbolsKey ? symbolsKey.split("\u001f") : [];
    const unsubscribe = symbolsToSubscribe.map((symbol) => subscribe(symbol));
    return () => unsubscribe.forEach((cleanup) => cleanup());
  }, [subscribe, symbolsKey]);

  // Calculate live data
  return useMemo(() => {
    const livePnLByPositionId = {};
    const resultTotals = {
      totalInvested: 0,
      totalUnrealizedPnL: 0,
      totalCurrentValue: 0,
    };

    positions.forEach((pos) => {
      const quantity = Number(pos.quantity) * Number(pos.qty_multiplier ?? 1);
      const avgPrice = Number(pos.avg_price);
      const tickPrice = Number(tickData[pos.instrument_symbol]?.price);
      const quote = tickData[pos.instrument_symbol];
      const hasLivePrice = isConnected && isObservedQuote(quote)
        && (!pos.mark_at || Date.parse(quote.timestamp) >= Date.parse(pos.mark_at));
      const storedPrice = Number(pos.current_price);
      const livePrice = hasLivePrice ? tickPrice : storedPrice > 0 ? storedPrice : avgPrice;
      const calculatedPnl = (livePrice - avgPrice) * quantity * (pos.side === sell ? -1 : 1);
      const pnl = hasLivePrice ? calculatedPnl : Number(pos.unrealized_pnl ?? calculatedPnl);
      const invested = avgPrice * quantity;
      const pnlPercent = invested > 0
        ? (pnl / invested) * 100
        : 0;

      livePnLByPositionId[pos.id] = {
        pnl,
        pnlPercent,
        livePrice,
        isLive: hasLivePrice,
      };

      resultTotals.totalInvested += invested;
      resultTotals.totalUnrealizedPnL += pnl;
      resultTotals.totalCurrentValue += livePrice * quantity;
    });

    return { livePnLByPositionId, totals: resultTotals };
  }, [positions, tickData, isConnected, sell]);
}

export function usePaperPositionsPnL(positions = []) {
  const rows = useMemo(() => positions.map((position) => ({
    ...position,
    instrument_symbol: position.instrument_sym_ticker,
  })), [positions]);
  return useLivePositionsPnL(rows);
}

export function useTerminalPositionsPnL(positions = []) {
  const { values } = useEnums();
  const buy = values.Side?.BUY, sell = values.Side?.SELL;
  const rows = useMemo(() => positions.map((position) => ({
    id: position.id,
    instrument_symbol: position.instrument.sym_ticker,
    quantity: Math.abs(position.quantity) * Number(position.instrument.qty_multiplier),
    side: position.quantity < 0 ? sell : buy,
    avg_price: position.average_price,
    current_price: position.current_price,
    mark_at: position.mark_at,
    unrealized_pnl: position.unrealized_pnl,
  })), [positions, buy, sell]);
  return useLivePositionsPnL(rows);
}
