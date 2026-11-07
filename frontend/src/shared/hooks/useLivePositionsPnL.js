import { useEffect, useMemo } from "react";
import { useEnums } from "@/shared/context/EnumsContext";
import { useWebSocket } from "./useWebSocket";
import { valuePositions } from "../utils/positionValuation";

const EMPTY_POSITIONS = [];

/**
 * Calculate P&L from LivePosition serializer rows and the central quote store.
 * Paper and Terminal adapters below supply this same row format.
 */
export function useLivePositionsPnL(positions = EMPTY_POSITIONS) {
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

  return useMemo(() => {
    const valuation = valuePositions(positions, tickData, sell, isConnected);
    return { ...valuation, totals: {
      totalInvested: valuation.summary.invested,
      totalUnrealizedPnL: valuation.summary.unrealized_pnl,
      totalCurrentValue: valuation.summary.current_value,
    } };
  }, [positions, tickData, isConnected, sell]);
}

/** Summary inputs include all matching positions, even when the table is paged. */
export function useLivePositionSummary(snapshot) {
  const { summary } = useLivePositionsPnL(snapshot?.valuation_positions ?? EMPTY_POSITIONS);
  return useMemo(() => snapshot?.valuation_positions ? { ...snapshot, ...summary } : snapshot ?? {}, [snapshot, summary]);
}

export function usePaperPositionsPnL(positions = EMPTY_POSITIONS) {
  const rows = useMemo(() => positions.map((position) => ({
    ...position,
    instrument_symbol: position.instrument_sym_ticker,
  })), [positions]);
  return useLivePositionsPnL(rows);
}

export function useTerminalPositionsPnL(positions = EMPTY_POSITIONS) {
  const { values } = useEnums();
  const buy = values.Side?.BUY, sell = values.Side?.SELL;
  const rows = useMemo(() => positions.map((position) => ({
    id: position.id,
    instrument_symbol: position.instrument.sym_ticker,
    quantity: Math.abs(position.quantity),
    qty_multiplier: position.instrument.qty_multiplier,
    side: position.quantity < 0 ? sell : buy,
    avg_price: position.average_price,
    current_price: position.current_price,
    mark_at: position.mark_at,
    settled_pnl: position.settled_pnl,
  })), [positions, buy, sell]);
  return useLivePositionsPnL(rows);
}
