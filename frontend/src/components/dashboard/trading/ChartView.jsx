import React, { useEffect, useRef, useState, useCallback } from "react";
// ** FIX 1: Import the series type and ColorType **
import { createChart, ColorType, CandlestickSeries } from "lightweight-charts";
import api from "@/services/api";
import TimeframeSelector from "./TimeframeSelector";
import { useWebSocket } from "@/hooks/use-websocket";

// Helper to get the start of a candle based on resolution
const getCandleStartTime = (timestamp, resolutionInSeconds) => {
  return Math.floor(timestamp / resolutionInSeconds) * resolutionInSeconds;
};

export default function ChartView({ symbol }) {
  const { lastMessage, isConnected, sendMessage } = useWebSocket(
    "ws://localhost:8000/ws/marketdata/"
  );
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [resolution, setResolution] = useState("1D");
  const currentCandleRef = useRef(null);

  const resolutionToSeconds = (res) => {
    const unit = res.slice(-1);
    const value = parseInt(res.slice(0, -1), 10);
    if (unit === "m") return value * 60;
    if (unit === "h") return value * 3600;
    if (unit === "D") return value * 86400;
    if (unit === "W") return value * 604800;
    return 86400; // Default to 1 Day
  };

  const fetchHistoricalData = useCallback(async () => {
    if (!symbol || !candleSeriesRef.current) return;
    setLoading(true);
    currentCandleRef.current = null;
    try {
      const res = await api.get(
        `/market/ohlc/?instrument=${symbol}&resolution=${resolution}`
      );
      const data = res.data.map((d) => ({
        time: d.time / 1000,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }));
      candleSeriesRef.current.setData(data);
      if (data.length > 0) {
        currentCandleRef.current = data[data.length - 1];
      }
    } catch (err) {
      console.error("Failed to fetch chart data:", err);
    } finally {
      setLoading(false);
    }
  }, [symbol, resolution]);

  // Initialize chart on mount and handle resizing
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#0A0A1A" },
        textColor: "#D1D5DB",
      },
      grid: {
        vertLines: { color: "#1F2937" },
        horzLines: { color: "#1F2937" },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: resolution.includes("m"),
      },
      width: chartContainerRef.current.clientWidth,
      height: 500,
    });
    chartRef.current = chart;

    // ** ERROR FIX HERE **
    // Use the correct `addSeries` method with the `CandlestickSeries` type
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#22C55E",
      downColor: "#EF4444",
      borderVisible: false,
      wickUpColor: "#22C55E",
      wickDownColor: "#EF4444",
    });
    candleSeriesRef.current = candleSeries;

    const resizeObserver = new ResizeObserver((entries) => {
      if (entries.length > 0) {
        const { width, height } = entries[0].contentRect;
        chart.applyOptions({ width, height });
      }
    });
    resizeObserver.observe(chartContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [resolution]);

  // Refetch data when symbol or resolution changes
  useEffect(() => {
    fetchHistoricalData();
  }, [fetchHistoricalData]);

  // Handle WebSocket for live updates
  useEffect(() => {
    if (loading || !symbol || !isConnected || !lastMessage) return;

    const instrument_group_name = `NSE_${symbol.toUpperCase()}_EQ`.replace(
      /-/g,
      "_"
    );
    sendMessage({ type: "subscribe", instrument: instrument_group_name });

    const tick = JSON.parse(lastMessage);

    if (
      candleSeriesRef.current &&
      tick.instrument === `NSE:${symbol.toUpperCase()}-EQ`
    ) {
      const tickTime = new Date(tick.timestamp).getTime() / 1000;
      const tickPrice = tick.price;
      const resInSeconds = resolutionToSeconds(resolution);
      const candleStartTime = getCandleStartTime(tickTime, resInSeconds);

      if (
        currentCandleRef.current &&
        candleStartTime === currentCandleRef.current.time
      ) {
        currentCandleRef.current.high = Math.max(
          currentCandleRef.current.high,
          tickPrice
        );
        currentCandleRef.current.low = Math.min(
          currentCandleRef.current.low,
          tickPrice
        );
        currentCandleRef.current.close = tickPrice;
      } else {
        currentCandleRef.current = {
          time: candleStartTime,
          open: tickPrice,
          high: tickPrice,
          low: tickPrice,
          close: tickPrice,
        };
      }

      candleSeriesRef.current.update(currentCandleRef.current);
    }
  }, [loading, symbol, resolution, isConnected, sendMessage, lastMessage]);

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-center px-2">
        <TimeframeSelector
          selected={resolution}
          onSelect={setResolution}
          disabled={loading}
        />
        <div className="bg-red-900/50 text-red-300 text-xs px-2 py-1 rounded-md border border-red-800/50">
          15-Min Delayed Data
        </div>
      </div>
      <div className="relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-950/50 z-10">
            Loading Chart...
          </div>
        )}
        <div
          ref={chartContainerRef}
          style={{
            visibility: loading ? "hidden" : "visible",
            height: "500px",
          }}
        />
      </div>
    </div>
  );
}
