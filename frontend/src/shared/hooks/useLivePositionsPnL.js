import { useEffect, useMemo, useRef } from "react";
import { useWebSocket } from "./useWebSocket";

/**
 * Hook to manage live PnL calculations for a list of positions.
 * Subscribes to market data ticks for all position symbols.
 * 
 * @param {Array} positions - Array of position objects
 * @returns {Object} - { livePnLByPositionId, totals, getLivePrice }
 */
export function useLivePositionsPnL(positions = []) {
  const { subscribe, tickData } = useWebSocket();
  const subscribedSymbolsRef = useRef(new Set());
  const cleanupFnsRef = useRef(new Map());

  // Subscribe to all unique symbols
  useEffect(() => {
    if (!positions || positions.length === 0) return;

    const symbolsToSubscribe = new Set();
    
    positions.forEach((pos) => {
      // Handle both Paper and Live position structures
      const symbol = pos.instrument?.symbol || pos.instrument?.sym_ticker || pos.instrument_symbol || pos.symbol;
      if (symbol && pos.status !== "CLOSED") {
        symbolsToSubscribe.add(symbol);
      }
    });

    // Unsubscribe from symbols that are no longer needed
    subscribedSymbolsRef.current.forEach((symbol) => {
      if (!symbolsToSubscribe.has(symbol)) {
        const unsubscribe = cleanupFnsRef.current.get(symbol);
        if (unsubscribe) {
          unsubscribe();
          cleanupFnsRef.current.delete(symbol);
        }
      }
    });

    // Subscribe to new symbols
    symbolsToSubscribe.forEach((symbol) => {
      if (!subscribedSymbolsRef.current.has(symbol)) {
        // useWebSocket.subscribe returns an unsubscribe function
        const unsubscribe = subscribe(symbol);
        cleanupFnsRef.current.set(symbol, unsubscribe);
      }
    });

    subscribedSymbolsRef.current = symbolsToSubscribe;

    // Cleanup all on unmount
    return () => {
      cleanupFnsRef.current.forEach((unsubscribe) => unsubscribe && unsubscribe());
      cleanupFnsRef.current.clear();
      subscribedSymbolsRef.current.clear();
    };
  }, [positions, subscribe]);

  // Safe number parsing
  const safeNumber = (val, fallback = 0) => {
    if (val === undefined || val === null || val === "" || isNaN(Number(val))) {
      return fallback;
    }
    return Number(val);
  };

  // Calculate live data
  const { livePnLByPositionId, totals, livePrices } = useMemo(() => {
    const livePnLByPositionId = {};
    const livePrices = {};
    const resultTotals = {
      totalInvested: 0,
      totalUnrealizedPnL: 0,
      totalCurrentValue: 0,
    };

    if (!positions || !Array.isArray(positions)) {
      return { livePnLByPositionId, totals: resultTotals, livePrices };
    }

    positions.forEach((pos) => {
      if (pos.status === "CLOSED") return;

      const symbol = pos.instrument?.symbol || pos.instrument?.sym_ticker || pos.instrument_symbol || pos.symbol;
      const quantity = safeNumber(pos.quantity);
      // For paper trading, average_price might be used. Live trading might use avg_price.
      const avgPrice = safeNumber(pos.average_price, safeNumber(pos.avg_price));
      
      // Get live tick price if available, otherwise fallback to static server price
      const tickPrice = tickData[symbol]?.price;
      const livePrice = tickPrice !== undefined ? tickPrice : safeNumber(pos.current_price, avgPrice);
      
      livePrices[symbol] = livePrice;

      // Calculate PnL based on side (LONG vs SHORT)
      let pnl = 0;
      const side = (pos.side || "").toUpperCase();
      
      if (side === "LONG" || side === "BUY" || !side) {
        pnl = (livePrice - avgPrice) * quantity;
      } else if (side === "SHORT" || side === "SELL") {
        pnl = (avgPrice - livePrice) * quantity;
      }

      livePnLByPositionId[pos.id] = {
        pnl,
        pnlPercent: avgPrice > 0 ? (pnl / (avgPrice * quantity)) * 100 : 0,
        livePrice,
        isLive: tickPrice !== undefined
      };

      const invested = avgPrice * quantity;
      
      resultTotals.totalInvested += invested;
      resultTotals.totalUnrealizedPnL += pnl;
      resultTotals.totalCurrentValue += (invested + pnl);
    });

    return { livePnLByPositionId, totals: resultTotals, livePrices };
  }, [positions, tickData]);

  const getLivePrice = (symbol) => {
    return tickData[symbol]?.price;
  };

  return {
    livePnLByPositionId,
    totals,
    getLivePrice,
    livePrices
  };
}
