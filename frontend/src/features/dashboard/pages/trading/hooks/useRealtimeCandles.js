import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useWebSocket } from "@/shared/hooks/useWebSocket";
import tradingTerminalApi from "../services/tradingTerminalApi";

const TIMEFRAME_BUCKETS = {
  "1m": 60,
  "5m": 300,
  "15m": 900,
  "1h": 3600,
  "1D": 86400,
  "1W": 604800,
};

const PAGE_LIMIT = 300;

function alignTime(unixSeconds, interval) {
  const bucket = TIMEFRAME_BUCKETS[interval] ?? TIMEFRAME_BUCKETS["1m"];
  return Math.floor(unixSeconds / bucket) * bucket;
}

function parseUnixTime(value) {
  if (value == null || value === "") return null;

  if (typeof value === "number") {
    if (!Number.isFinite(value)) return null;
    return Math.floor(value > 1_000_000_000_000 ? value / 1000 : value);
  }

  const numericValue = Number(value);
  if (Number.isFinite(numericValue)) {
    return Math.floor(
      numericValue > 1_000_000_000_000 ? numericValue / 1000 : numericValue,
    );
  }

  const parsedDate = Date.parse(value);
  if (!Number.isFinite(parsedDate)) return null;
  return Math.floor(parsedDate / 1000);
}

function normalizePrice(value, fallback = null) {
  const numericValue = Number(value ?? fallback);
  return Number.isFinite(numericValue) ? numericValue : null;
}

function normalizeCandle(candle) {
  if (!candle) return null;

  const time = parseUnixTime(
    candle.time ?? candle.timestamp ?? candle.updated_at,
  );
  const close = normalizePrice(candle.close ?? candle.price ?? candle.ltp);
  const open = normalizePrice(candle.open, close);
  const high = normalizePrice(
    candle.high,
    Math.max(open ?? close ?? 0, close ?? open ?? 0),
  );
  const low = normalizePrice(
    candle.low,
    Math.min(open ?? close ?? 0, close ?? open ?? 0),
  );
  const volume = normalizePrice(candle.volume ?? candle.last_traded_qty, 0);

  if (
    !Number.isFinite(time) ||
    !Number.isFinite(open) ||
    !Number.isFinite(high) ||
    !Number.isFinite(low) ||
    !Number.isFinite(close) ||
    !Number.isFinite(volume)
  ) {
    return null;
  }

  return {
    time,
    open,
    high: Math.max(high, open, close),
    low: Math.min(low, open, close),
    close,
    volume,
  };
}

function normalizeCandles(rawCandles = []) {
  const normalized = rawCandles
    .map(normalizeCandle)
    .filter(Boolean)
    .sort((a, b) => a.time - b.time);
  
  // Deduplicate to prevent lightweight-charts strictly increasing time errors
  const unique = [];
  let lastTime = null;
  for (const item of normalized) {
    if (item.time !== lastTime) {
      unique.push(item);
      lastTime = item.time;
    }
  }
  return unique;
}

function resolveNextBefore(responseData, loadedCandles) {
  if (responseData.pagination?.next_before != null) {
    return responseData.pagination.next_before;
  }
  if (loadedCandles.length) {
    return loadedCandles[0].time - 1;
  }
  return null;
}

function isCanceledRequest(error) {
  return error?.code === "ERR_CANCELED" || error?.name === "CanceledError";
}

function normalizeMarketSymbol(value) {
  if (!value) return "";
  const symbol = typeof value === "string" ? value : String(value);
  const normalized = symbol.includes(":") ? symbol.split(":")[1] : symbol;
  return normalized.replace(/-(EQ|INDEX)$/i, "");
}

export function useRealtimeCandles(symbol, interval, onRealtimeCandleUpdate, onTickUpdate) {
  const [historicalData, setHistoricalData] = useState([]);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  
  const [isLoadingOlder, setIsLoadingOlder] = useState(false);
  const [hasMoreHistory, setHasMoreHistory] = useState(false);
  const [nextBefore, setNextBefore] = useState(null);
  
  const activeRequestRef = useRef(0);
  const activeAbortRef = useRef(null);
  const olderAbortRef = useRef(null);
  const loadingOlderRef = useRef(false);
  
  const { subscribe, isConnected, getLatestPrice } = useWebSocket();
  
  // Track the current building realtime candle so we can update its OHLC correctly
  const buildingCandleRef = useRef(null);

  const pendingRealtimeCandle = useRef(null);
  const rafId = useRef(null);

  const loadCandles = useCallback(async () => {
    activeAbortRef.current?.abort();
    olderAbortRef.current?.abort();
    loadingOlderRef.current = false;
    setIsLoadingOlder(false);

    const controller = new AbortController();
    activeAbortRef.current = controller;

    const requestId = activeRequestRef.current + 1;
    activeRequestRef.current = requestId;

    if (!symbol) {
      setHistoricalData([]);
      buildingCandleRef.current = null;
      setStatus("idle");
      setHasMoreHistory(false);
      setNextBefore(null);
      activeAbortRef.current = null;
      return;
    }

    setStatus("loading");
    setError(null);
    buildingCandleRef.current = null;
    setHistoricalData([]);

    try {
      const response = await tradingTerminalApi.getCandles({
        symbol,
        interval,
        limit: PAGE_LIMIT,
        signal: controller.signal,
      });
      if (controller.signal.aborted || requestId !== activeRequestRef.current)
        return;

      const normalizedCandles = normalizeCandles(response.data.candles);
      setHistoricalData(normalizedCandles);
      setHasMoreHistory(Boolean(response.data.pagination?.has_more));
      setNextBefore(resolveNextBefore(response.data, normalizedCandles));
      setStatus("ready");
      
      if (normalizedCandles.length > 0) {
        const lastCandle = normalizedCandles[normalizedCandles.length - 1];
        if (buildingCandleRef.current && buildingCandleRef.current.time === lastCandle.time) {
            // A realtime tick arrived during fetch for the same period. Merge them.
            normalizedCandles[normalizedCandles.length - 1] = {
                ...lastCandle,
                high: Math.max(lastCandle.high, buildingCandleRef.current.high),
                low: Math.min(lastCandle.low, buildingCandleRef.current.low),
                close: buildingCandleRef.current.close,
                volume: Math.max(lastCandle.volume, buildingCandleRef.current.volume),
            };
            buildingCandleRef.current = { ...normalizedCandles[normalizedCandles.length - 1] };
        } else if (buildingCandleRef.current && buildingCandleRef.current.time > lastCandle.time) {
            // A realtime tick started a new period during fetch
            normalizedCandles.push(buildingCandleRef.current);
        } else {
            buildingCandleRef.current = { ...lastCandle };
        }
      }
      if (response.data.source?.fetched_count > 0) {
        getLatestPrice(symbol, { force: true });
      }
    } catch (loadError) {
      if (isCanceledRequest(loadError)) return;
      if (requestId !== activeRequestRef.current) return;
      setError(loadError);
      setStatus("error");
    } finally {
      if (activeAbortRef.current === controller) {
        activeAbortRef.current = null;
      }
    }
  }, [getLatestPrice, interval, symbol]);

  const loadOlder = useCallback(async () => {
    if (
      !symbol ||
      loadingOlderRef.current ||
      isLoadingOlder ||
      !hasMoreHistory ||
      !nextBefore
    )
      return;

    olderAbortRef.current?.abort();
    const controller = new AbortController();
    olderAbortRef.current = controller;
    loadingOlderRef.current = true;
    setIsLoadingOlder(true);
    
    try {
      const response = await tradingTerminalApi.getCandles({
        symbol,
        interval,
        limit: PAGE_LIMIT,
        before: nextBefore,
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;

      const olderCandles = normalizeCandles(response.data.candles);

      if (olderCandles.length) {
        // Prepend to historical data
        setHistoricalData((current) => {
            // merge and ensure uniqueness
            const map = new Map();
            olderCandles.forEach(c => map.set(c.time, c));
            current.forEach(c => map.set(c.time, c));
            return Array.from(map.values()).sort((a, b) => a.time - b.time);
        });
      }

      setHasMoreHistory(
        Boolean(response.data.pagination?.has_more) && olderCandles.length > 0,
      );
      setNextBefore(resolveNextBefore(response.data, olderCandles));
    } catch (loadError) {
      if (isCanceledRequest(loadError)) return;
      setError(loadError);
    } finally {
      if (olderAbortRef.current === controller) {
        olderAbortRef.current = null;
        loadingOlderRef.current = false;
        setIsLoadingOlder(false);
      }
    }
  }, [
    hasMoreHistory,
    interval,
    isLoadingOlder,
    nextBefore,
    symbol,
  ]);

  useEffect(() => {
    loadCandles();
    return () => {
      activeAbortRef.current?.abort();
      olderAbortRef.current?.abort();
      loadingOlderRef.current = false;
    };
  }, [loadCandles]);

  useEffect(() => {
    if (!symbol || !isConnected) return undefined;

    const unsubscribe = subscribe(symbol, (event) => {
      let nextCandle = null;
      
      if (event?.candle) {
        const candleTime = parseUnixTime(event.candle.time ?? event.timestamp);
        const candleClose = normalizePrice(
          event.candle.close ?? event.candle.price,
        );
        if (!Number.isFinite(candleTime) || !Number.isFinite(candleClose))
          return;

        const alignedTime =
          interval === "1m" ? candleTime : alignTime(candleTime, interval);
        const candleOpen = normalizePrice(event.candle.open, candleClose);
        const candleHigh = normalizePrice(event.candle.high, candleClose);
        const candleLow = normalizePrice(event.candle.low, candleClose);
        
        nextCandle = {
          time: alignedTime,
          open: candleOpen,
          high: candleHigh,
          low: candleLow,
          close: candleClose,
          volume: normalizePrice(event.candle.volume, 0),
        };
      } else {
        const price = normalizePrice(event.price ?? event.ltp);
        if (!Number.isFinite(price)) return;

        const lastTradedQty = normalizePrice(event.last_traded_qty, 0);
        const unixSeconds =
          parseUnixTime(event.timestamp ?? event.updated_at ?? event.time) ??
          Math.floor(Date.now() / 1000);
        const alignedTime = alignTime(unixSeconds, interval);

        nextCandle = {
          time: alignedTime,
          open: price,
          high: price,
          low: price,
          close: price,
          volume: lastTradedQty,
        };
      }

      // Update the building candle logic
      const building = buildingCandleRef.current;
      let finalCandle;
      if (!building || building.time !== nextCandle.time) {
          // New timeframe bucket — use this candle as the starting point
          buildingCandleRef.current = nextCandle;
          finalCandle = nextCandle;
      } else {
          // Update existing candle period
          finalCandle = {
              ...building,
              // Keep the ORIGINAL open from when this bucket started
              high: Math.max(building.high, nextCandle.high),
              low: Math.min(building.low, nextCandle.low),
              close: nextCandle.close,
              volume: building.volume + nextCandle.volume,
          };
          buildingCandleRef.current = finalCandle;
      }

      pendingRealtimeCandle.current = finalCandle;
      
      if (rafId.current === null) {
        // Store raw event on a ref to avoid closure staleness
        buildingCandleRef.current.latestEvent = event;
        
        rafId.current = requestAnimationFrame(() => {
          if (onRealtimeCandleUpdate) {
            onRealtimeCandleUpdate(pendingRealtimeCandle.current);
          }
          if (onTickUpdate && buildingCandleRef.current.latestEvent) {
            onTickUpdate(buildingCandleRef.current.latestEvent);
          }
          rafId.current = null;
        });
      }
    });

    return () => {
      unsubscribe();
      if (rafId.current !== null) {
        cancelAnimationFrame(rafId.current);
        rafId.current = null;
      }
    };
  }, [interval, isConnected, subscribe, symbol, onRealtimeCandleUpdate, onTickUpdate]);

  useEffect(() => {
    if (symbol) {
      getLatestPrice(symbol).then(tick => {
        if (tick && onTickUpdate) {
            onTickUpdate(tick);
        }
      });
    }
  }, [getLatestPrice, symbol, onTickUpdate]);

  return {
    historicalData,
    status,
    error,
    isLoadingOlder,
    hasMoreHistory,
    loadOlder,
  };
}

export default useRealtimeCandles;
