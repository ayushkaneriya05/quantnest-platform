import React, { useEffect, useRef, useState, useCallback } from "react";
// ** FIX 1: Import the series type and ColorType **
import { createChart, ColorType, CandlestickSeries } from "lightweight-charts";
import api from "@/services/api";
import TimeframeSelector from "./TimeframeSelector";
import { useWebSocket } from "@/hooks/use-websocket";
import { getDummyChartData } from "@/data/dummyChartData";

// Helper to get the start of a candle based on resolution
const getCandleStartTime = (timestamp, resolutionInSeconds) => {
  return Math.floor(timestamp / resolutionInSeconds) * resolutionInSeconds;
};

export default function ChartView({ symbol }) {
  // Make WebSocket optional - only connect if needed
  const webSocketUrl = "ws://localhost:8000/ws/marketdata/";
  const { lastMessage, isConnected, sendMessage } = useWebSocket(webSocketUrl);
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

      // Add defensive check for response data
      if (!res.data || !Array.isArray(res.data)) {
        console.error("Invalid chart data response:", res.data);
        throw new Error("Invalid API response");
      }

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
      console.warn("Failed to fetch chart data from API, using dummy data:", err);

      // Fallback to dummy data
      const dummyData = getDummyChartData(symbol, resolution);
      candleSeriesRef.current.setData(dummyData);

      if (dummyData.length > 0) {
        currentCandleRef.current = dummyData[dummyData.length - 1];
      }
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
    // Use the correct lightweight-charts v5 API
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#22C55E",
      downColor: "#EF4444",
      borderVisible: false,
      wickUpColor: "#22C55E",
      wickDownColor: "#EF4444",
    });
    candleSeriesRef.current = candleSeries;

    // Initialize with dummy data immediately to show chart
    if (symbol) {
      const initialData = getDummyChartData(symbol, resolution);
      candleSeries.setData(initialData);
      if (initialData.length > 0) {
        currentCandleRef.current = initialData[initialData.length - 1];
      }
      setLoading(false);
    }

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
  }, [resolution, symbol]);

  // Refetch data when symbol or resolution changes
  useEffect(() => {
    fetchHistoricalData();
  }, [fetchHistoricalData]);

  // Handle WebSocket for live updates (with error handling)
  useEffect(() => {
    if (loading || !symbol || !isConnected || !lastMessage) return;

    try {
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
    } catch (err) {
      console.warn("WebSocket message processing error:", err);
      // Continue without WebSocket updates - chart still works with dummy data
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
        <div className="bg-amber-900/50 text-amber-300 text-xs px-2 py-1 rounded-md border border-amber-800/50">
          Demo Data
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
