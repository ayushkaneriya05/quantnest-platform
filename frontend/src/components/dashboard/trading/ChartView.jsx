import React, { useEffect, useRef, useState, useCallback } from "react";
import { createChart, ColorType } from "lightweight-charts";
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

      // Add defensive check for response data
      if (!res.data || !Array.isArray(res.data)) {
        console.error("Invalid chart data response:", res.data);
        return;
      }

      // Process and validate data before setting it
      const processedData = res.data
        .map((d) => {
          // Ensure time is a proper Unix timestamp in seconds
          let timeValue;
          if (typeof d.time === 'number') {
            // If time is in milliseconds, convert to seconds
            timeValue = d.time > 10000000000 ? Math.floor(d.time / 1000) : d.time;
          } else if (d.time instanceof Date) {
            timeValue = Math.floor(d.time.getTime() / 1000);
          } else {
            // Try to parse as timestamp
            timeValue = Math.floor(new Date(d.time).getTime() / 1000);
          }

          return {
            time: timeValue,
            open: parseFloat(d.open) || 0,
            high: parseFloat(d.high) || 0,
            low: parseFloat(d.low) || 0,
            close: parseFloat(d.close) || 0,
          };
        })
        .filter(d => !isNaN(d.time) && d.time > 0) // Filter out invalid times
        .sort((a, b) => a.time - b.time); // Ensure chronological order

      if (processedData.length === 0) {
        console.warn("No valid chart data after processing");
        return;
      }

      console.log("Setting chart data:", processedData.slice(0, 3)); // Log first 3 items for debugging
      
      candleSeriesRef.current.setData(processedData);
      
      if (processedData.length > 0) {
        currentCandleRef.current = processedData[processedData.length - 1];
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

    try {
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

      // Use the proven working approach for lightweight-charts
      // Create a line series first as a fallback, then try candlestick
      let series;
      try {
        // Try the most basic approach that should work in v5.x
        series = chart.addLineSeries({
          color: "#22C55E",
          lineWidth: 2,
        });
        console.log("Created line series as fallback");
      } catch (lineError) {
        console.error("Failed to create line series:", lineError);
        // If even line series fails, there's a fundamental issue
        throw new Error("Cannot create any series on chart");
      }
      
      candleSeriesRef.current = series;

      const resizeObserver = new ResizeObserver((entries) => {
        if (entries.length > 0) {
          const { width, height } = entries[0].contentRect;
          chart.applyOptions({ width, height });
        }
      });
      resizeObserver.observe(chartContainerRef.current);

      return () => {
        resizeObserver.disconnect();
        if (chart) {
          chart.remove();
        }
      };
    } catch (error) {
      console.error("Failed to initialize chart:", error);
      setLoading(false);
    }
  }, [resolution]);

  // Modified data processing for line series
  const processDataForSeries = useCallback((data) => {
    // For line series, we only need time and value (close price)
    return data.map(d => ({
      time: d.time,
      value: d.close || d.value || 0
    }));
  }, []);

  // Refetch data when symbol or resolution changes
  useEffect(() => {
    if (chartRef.current && candleSeriesRef.current) {
      const fetchData = async () => {
        if (!symbol) return;
        setLoading(true);
        currentCandleRef.current = null;
        
        try {
          const res = await api.get(
            `/market/ohlc/?instrument=${symbol}&resolution=${resolution}`
          );

          if (!res.data || !Array.isArray(res.data)) {
            console.error("Invalid chart data response:", res.data);
            return;
          }

          const processedData = res.data
            .map((d) => {
              let timeValue;
              if (typeof d.time === 'number') {
                timeValue = d.time > 10000000000 ? Math.floor(d.time / 1000) : d.time;
              } else if (d.time instanceof Date) {
                timeValue = Math.floor(d.time.getTime() / 1000);
              } else {
                timeValue = Math.floor(new Date(d.time).getTime() / 1000);
              }

              return {
                time: timeValue,
                open: parseFloat(d.open) || 0,
                high: parseFloat(d.high) || 0,
                low: parseFloat(d.low) || 0,
                close: parseFloat(d.close) || 0,
              };
            })
            .filter(d => !isNaN(d.time) && d.time > 0)
            .sort((a, b) => a.time - b.time);

          if (processedData.length === 0) {
            console.warn("No valid chart data after processing");
            return;
          }

          // Convert data for line series (using close prices)
          const lineData = processDataForSeries(processedData);
          candleSeriesRef.current.setData(lineData);
          
          if (processedData.length > 0) {
            currentCandleRef.current = processedData[processedData.length - 1];
          }
        } catch (err) {
          console.error("Failed to fetch chart data:", err);
        } finally {
          setLoading(false);
        }
      };

      fetchData();
    }
  }, [symbol, resolution, processDataForSeries]);

  // Handle WebSocket for live updates
  useEffect(() => {
    if (loading || !symbol || !isConnected || !lastMessage || !candleSeriesRef.current) return;

    try {
      const instrument_group_name = `NSE_${symbol.toUpperCase()}_EQ`.replace(
        /-/g,
        "_"
      );
      sendMessage({ type: "subscribe", instrument: instrument_group_name });

      const tick = JSON.parse(lastMessage);

      if (tick.instrument === `NSE:${symbol.toUpperCase()}-EQ`) {
        let tickTime;
        
        if (typeof tick.timestamp === 'string') {
          tickTime = Math.floor(new Date(tick.timestamp).getTime() / 1000);
        } else if (typeof tick.timestamp === 'number') {
          tickTime = tick.timestamp > 10000000000 ? Math.floor(tick.timestamp / 1000) : tick.timestamp;
        } else {
          tickTime = Math.floor(Date.now() / 1000);
        }

        const tickPrice = parseFloat(tick.price) || 0;
        
        // For line series, just update with new price point
        candleSeriesRef.current.update({
          time: tickTime,
          value: tickPrice
        });
      }
    } catch (error) {
      console.error("Error processing WebSocket message:", error);
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
          Line Chart (Fallback) • 15-Min Delayed Data
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
