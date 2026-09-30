import { useEffect, useMemo, useState } from "react";
import { useWebSocket } from "./useWebSocket";

const getPositionSymbol = (position) =>
  position?.instrument?.sym_ticker ||
  position?.instrument_sym_ticker ||
  position?.instrument?.symbol ||
  position?.instrument_symbol ||
  position?.symbol ||
  "";

const safeNumber = (value, fallback = 0) => {
  if (value === undefined || value === null || value === "") return fallback;
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
};

/**
 * Hook to manage live PnL calculations for a list of positions.
 * Subscribes to market data ticks for all position symbols.
 *
 * @param {Array} positions - Array of position objects
 * @returns {Object} - { livePnLByPositionId, totals, getLivePrice }
 */
export function useLivePositionsPnL(positions = []) {
  const { subscribe, tickData } = useWebSocket();
  const [liveTickPrices, setLiveTickPrices] = useState({});
  const symbols = useMemo(
    () => [...new Set((Array.isArray(positions) ? positions : [])
      .filter((position) => position?.status !== "CLOSED")
      .map(getPositionSymbol)
      .filter(Boolean))].sort(),
    [positions],
  );
  const symbolsKey = symbols.join("\u001f");

  // Position polling may replace the array every few seconds. Subscribe only
  // when the instrument set changes, not on every refresh.
  useEffect(() => {
    const symbolsToSubscribe = symbolsKey ? symbolsKey.split("\u001f") : [];
    const unsubscribe = symbolsToSubscribe.map((symbol) => subscribe(symbol, (tick) => {
      const price = safeNumber(tick?.price ?? tick?.ltp, NaN);
      if (!Number.isFinite(price) || price <= 0) return;
      setLiveTickPrices((current) => current[symbol] === price
        ? current
        : { ...current, [symbol]: price });
    }));
    return () => unsubscribe.forEach((cleanup) => cleanup?.());
  }, [subscribe, symbolsKey]);

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

      const symbol = getPositionSymbol(pos);
      const quantity = safeNumber(pos.quantity);
      const avgPrice = safeNumber(pos.average_price, safeNumber(pos.avg_price));

      // Tick payloads carry canonical Fyers symbols and expose the LTP as price.
      const tick = tickData[symbol];
      const tickPrice = safeNumber(liveTickPrices[symbol] ?? tick?.price ?? tick?.ltp, NaN);
      const hasLivePrice = Number.isFinite(tickPrice) && tickPrice > 0;
      const livePrice = hasLivePrice ? tickPrice : safeNumber(pos.current_price, avgPrice);

      livePrices[symbol] = livePrice;

      // Calculate PnL based on side (LONG vs SHORT)
      let calculatedPnl = 0;
      const side = (pos.side || "").toUpperCase();

      if (side === "LONG" || side === "BUY" || !side) {
        calculatedPnl = (livePrice - avgPrice) * quantity;
      } else if (side === "SHORT" || side === "SELL") {
        calculatedPnl = (avgPrice - livePrice) * quantity;
      }
      const pnl = hasLivePrice
        ? calculatedPnl
        : safeNumber(pos.unrealized_pnl, calculatedPnl);
      const calculatedPnlPercent = avgPrice > 0 && quantity > 0
        ? (calculatedPnl / (avgPrice * quantity)) * 100
        : 0;
      const persistedPnlPercent = safeNumber(
        pos.unrealized_pnl_pct,
        safeNumber(pos.return_percent, calculatedPnlPercent),
      );

      livePnLByPositionId[pos.id] = {
        pnl,
        pnlPercent: hasLivePrice ? calculatedPnlPercent : persistedPnlPercent,
        livePrice,
        isLive: hasLivePrice,
      };

      const invested = avgPrice * quantity;

      resultTotals.totalInvested += invested;
      resultTotals.totalUnrealizedPnL += pnl;
      resultTotals.totalCurrentValue += livePrice * quantity;
    });

    return { livePnLByPositionId, totals: resultTotals, livePrices };
  }, [liveTickPrices, positions, tickData]);

  const getLivePrice = (symbol) => {
    return liveTickPrices[symbol] ?? tickData[symbol]?.price ?? tickData[symbol]?.ltp;
  };

  return {
    livePnLByPositionId,
    totals,
    getLivePrice,
    livePrices,
  };
}
