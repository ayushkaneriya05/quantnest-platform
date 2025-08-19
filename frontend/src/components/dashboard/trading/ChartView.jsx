import React, { useEffect, useRef, useState, useCallback } from "react";
import { createChart } from "lightweight-charts";
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
  const chartContainerRef = useRef();
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [resolution, setResolution] = useState("1D");
  const currentCandleRef = useRef(null);

  const resolutionToSeconds = (res) => {
    const unit = res.slice(-1);
    const value = parseInt(res.slice(0, -1), 10);
    if (unit === "m") return value * 60;
    if (unit === "h") return value * 60 * 60;
    if (unit === "D") return value * 24 * 60 * 60;
    if (unit === "W") return value * 7 * 24 * 60 * 60;
    return 86400; // Default to 1 Day
  };

  const fetchHistoricalData = useCallback(async () => {
    if (!symbol || !candleSeriesRef.current) return;
    setLoading(true);
    currentCandleRef.current = null;
    try {
      const res = await api.get(
        `/trading/ohlc/?instrument=${symbol}&resolution=${resolution}`
      );
      const data = res.data.map((d) => ({
        time: d.time / 1000, // Convert ms to seconds for the library
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

  // Initialize chart on mount
  useEffect(() => {
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 500,
      layout: { background: { color: "#0A0A1A" }, textColor: "#D1D5DB" },
      grid: {
        vertLines: { color: "#1F2937" },
        horzLines: { color: "#1F2937" },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: resolution.includes("m"),
      },
    });
    chartRef.current = chart;
    candleSeriesRef.current = chart.addCandlestickSeries({
      upColor: "#22C55E",
      downColor: "#EF4444",
      borderDownColor: "#EF4444",
      borderUpColor: "#22C55E",
      wickDownColor: "#EF4444",
      wickUpColor: "#22C55E",
    });
    return () => chart.remove();
  }, []);

  // Refetch data when symbol or resolution changes
  useEffect(() => {
    fetchHistoricalData();
  }, [fetchHistoricalData]);

  useEffect(() => {
    if (loading || !symbol || !isConnected) return;
    const instrument_group_name = `NSE_${symbol.toUpperCase()}_EQ`.replace(
      /-/g,
      "_"
    );
    sendMessage({ type: "subscribe", instrument: instrument_group_name });
  }, [loading, symbol, isConnected, sendMessage]);

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
          style={{ visibility: loading ? "hidden" : "visible" }}
        />
      </div>
    </div>
  );
}
