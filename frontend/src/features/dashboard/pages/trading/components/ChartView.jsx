import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertCircle,
  BarChart3,
  Eye,
  EyeOff,
  Loader2,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import {
  CandlestickSeries,
  ColorType,
  createChart,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
} from "lightweight-charts";

import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/shared/components/ui/tabs";
import { cn } from "@/shared/lib/utils";

import useRealtimeCandles from "../hooks/useRealtimeCandles";

const TIMEFRAMES = [
  { value: "1m", label: "1M" },
  { value: "5m", label: "5M" },
  { value: "15m", label: "15M" },
  { value: "1h", label: "1H" },
  { value: "1D", label: "1D" },
  { value: "1W", label: "1W" },
];

const CHART_TYPES = [
  { value: "candles", label: "Candles", icon: BarChart3 },
  { value: "line", label: "Line", icon: Activity },
];

const IST_TIME_ZONE = "Asia/Kolkata";

const parseUnixTime = (value) => {
  if (value == null || value === "") return null;
  const numericValue = Number(value);
  if (Number.isFinite(numericValue)) {
    return Math.floor(
      numericValue > 1_000_000_000_000 ? numericValue / 1000 : numericValue,
    );
  }
  const parsedDate = Date.parse(value);
  return Number.isFinite(parsedDate) ? Math.floor(parsedDate / 1000) : null;
};

const formatChartTimeIST = (time, withDate = false) => {
  const unixSeconds =
    typeof time === "object" && time?.timestamp ? time.timestamp : Number(time);
  if (!Number.isFinite(unixSeconds)) return "";
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: IST_TIME_ZONE,
    day: withDate ? "2-digit" : undefined,
    month: withDate ? "short" : undefined,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(unixSeconds * 1000));
};

const formatCurrency = (value) =>
  value == null
    ? "--"
    : new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(Number(value));

export default function ChartView({
  symbol,
  interval: propInterval = "1m",
  onBuyClick,
  onSellClick,
  className = "",
}) {
  const [selectedTimeframe, setSelectedTimeframe] = useState(propInterval);
  const [selectedChartType, setSelectedChartType] = useState("candles");
  const [showVolume, setShowVolume] = useState(false);
  const [hoveredCandle, setHoveredCandle] = useState(null);

  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const lineSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const loadOlderRef = useRef(null);
  const isLoadingOlderRef = useRef(false);
  const hasMoreHistoryRef = useRef(false);
  const shouldFitContentRef = useRef(true);
  const userNavigatedHistoryRef = useRef(false);
  
  // Track chart data directly inside a ref to be accessible
  const chartDataRef = useRef([]);

  const {
    historicalData,
    realtimeCandle,
    latestTick,
    status,
    isLoadingOlder,
    hasMoreHistory,
    loadOlder,
  } = useRealtimeCandles(symbol, selectedTimeframe);

  useEffect(() => {
    loadOlderRef.current = loadOlder;
    isLoadingOlderRef.current = isLoadingOlder;
    hasMoreHistoryRef.current = hasMoreHistory;
  }, [hasMoreHistory, isLoadingOlder, loadOlder]);

  useEffect(() => {
    shouldFitContentRef.current = true;
    userNavigatedHistoryRef.current = false;
    setHoveredCandle(null);
    chartDataRef.current = [];

    if (candleSeriesRef.current) candleSeriesRef.current.setData([]);
    if (lineSeriesRef.current) lineSeriesRef.current.setData([]);
    if (volumeSeriesRef.current) volumeSeriesRef.current.setData([]);
  }, [selectedTimeframe, symbol]);

  const latestCandle = hoveredCandle ?? chartDataRef.current[chartDataRef.current.length - 1] ?? null;
  const latestTickTime = parseUnixTime(latestTick?.timestamp ?? latestTick?.updated_at);
  const latestTickPrice = Number(latestTick?.price);
  const isLatestTickUsable =
    Number.isFinite(latestTickPrice) &&
    latestTickPrice > 0 &&
    (!latestCandle?.time ||
      !latestTickTime ||
      latestTickTime >= Number(latestCandle.time) - 60);
  const displayPrice = isLatestTickUsable ? latestTickPrice : latestCandle?.close;

  const priceChange = useMemo(() => {
    if (!isLatestTickUsable) return null;
    if (!latestTick?.change && latestTick?.change !== 0) return null;
    return {
      change: Number(latestTick.change),
      changePercent: Number(latestTick.change_percent ?? 0),
    };
  }, [isLatestTickUsable, latestTick]);

  // Init Chart instance
  useEffect(() => {
    let chart;
    let observer;
    let visibleRangeHandler;
    let markUserNavigation;

    const initChart = () => {
      if (!containerRef.current) return;
      const container = containerRef.current;

      const width = container.clientWidth;
      const height = container.clientHeight;
      markUserNavigation = () => {
        userNavigatedHistoryRef.current = true;
      };
      container.addEventListener("wheel", markUserNavigation, { passive: true });
      container.addEventListener("pointerdown", markUserNavigation);

      chart = createChart(container, {
        layout: {
          background: { type: ColorType.Solid, color: "#020617" },
          textColor: "#ffffff",
          fontSize: 12,
          fontFamily: "Inter, sans-serif",
        },
        grid: {
          vertLines: { color: "#1e293b", style: 1 },
          horzLines: { color: "#1e293b", style: 1 },
        },
        crosshair: { mode: CrosshairMode.Normal },
        width: width || 800,
        height: height || 400,
        timeScale: {
          borderColor: "#334155",
          borderVisible: true,
          timeVisible: true,
          secondsVisible: false,
          barSpacing: 10,
          rightOffset: 5,
          tickMarkFormatter: (time) => formatChartTimeIST(time),
        },
        localization: {
          locale: "en-IN",
          timeFormatter: (time) => formatChartTimeIST(time, true),
        },
        rightPriceScale: {
          borderColor: "#334155",
          borderVisible: true,
          scaleMargins: { top: 0.1, bottom: 0.25 },
        },
        handleScroll: true,
        handleScale: true,
      });

      chartRef.current = chart;
      candleSeriesRef.current = chart.addSeries(CandlestickSeries, {
        upColor: "#10b981",
        downColor: "#f43f5e",
        borderVisible: false,
        wickUpColor: "#10b981",
        wickDownColor: "#f43f5e",
      });
      lineSeriesRef.current = chart.addSeries(LineSeries, {
        color: "#38bdf8",
        lineWidth: 2,
        visible: false,
      });
      volumeSeriesRef.current = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "",
        scaleMargins: { top: 0.8, bottom: 0.05 },
        color: "#334155",
        visible: showVolume,
      });

      chart.subscribeCrosshairMove((param) => {
        if (!param.time) {
          setHoveredCandle(null);
          return;
        }

        const mainData =
          param.seriesData.get(candleSeriesRef.current) ??
          param.seriesData.get(lineSeriesRef.current);
        const volumeData = param.seriesData.get(volumeSeriesRef.current);

        if (mainData) {
          setHoveredCandle({
            ...mainData,
            volume: volumeData?.value ?? 0,
          });
        } else {
          setHoveredCandle(null);
        }
      });

      visibleRangeHandler = (logicalRange) => {
        if (
          !logicalRange ||
          !userNavigatedHistoryRef.current ||
          !hasMoreHistoryRef.current ||
          isLoadingOlderRef.current
        ) {
          return;
        }
        if (logicalRange.from < 25) {
          loadOlderRef.current?.();
        }
      };
      chart.timeScale().subscribeVisibleLogicalRangeChange(visibleRangeHandler);

      observer = new ResizeObserver(() => {
        if (!containerRef.current || !chartRef.current) return;
        const newWidth = containerRef.current.clientWidth;
        const newHeight = containerRef.current.clientHeight;
        if (newWidth === 0 || newHeight === 0) return;

        chartRef.current.applyOptions({
          width: newWidth,
          height: newHeight,
        });
        if (shouldFitContentRef.current) {
          chartRef.current.timeScale().fitContent();
        }
      });

      observer.observe(containerRef.current);
    };

    const frameId = requestAnimationFrame(initChart);

    return () => {
      cancelAnimationFrame(frameId);
      if (observer) observer.disconnect();
      if (containerRef.current && markUserNavigation) {
        containerRef.current.removeEventListener("wheel", markUserNavigation);
        containerRef.current.removeEventListener("pointerdown", markUserNavigation);
      }
      if (chart) {
        if (visibleRangeHandler) {
          chart.timeScale().unsubscribeVisibleLogicalRangeChange(visibleRangeHandler);
        }
        chart.remove();
        chartRef.current = null;
      }
    };
  }, []); // Chart init is completely independent of data/symbols

  // Handle Historical Data (Set Data)
  useEffect(() => {
    if (!chartRef.current || !candleSeriesRef.current || !historicalData || historicalData.length === 0) return;
    
    // Merge new historical data with any existing data (including real-time ticks)
    const currentData = chartDataRef.current;
    const map = new Map();
    historicalData.forEach(c => map.set(c.time, c));
    currentData.forEach(c => map.set(c.time, c));
    
    const merged = Array.from(map.values()).sort((a, b) => a.time - b.time);
    chartDataRef.current = merged;

    // Build the line & volume arrays
    const lines = merged.map((item) => ({ time: item.time, value: item.close }));
    const volumes = merged.map((item) => ({
      time: item.time,
      value: item.volume,
      color: item.close >= item.open ? "#10b98155" : "#f43f5e55",
    }));

    // Get the previous visible range before setting new data
    const previousLogicalRange = chartRef.current.timeScale().getVisibleLogicalRange();

    // Update charts using setData (Heavy operation, only do on historical load)
    candleSeriesRef.current.setData(merged);
    lineSeriesRef.current.setData(lines);
    volumeSeriesRef.current?.setData(volumes);

    if (shouldFitContentRef.current) {
      chartRef.current.timeScale().fitContent();
      shouldFitContentRef.current = false;
    } else if (previousLogicalRange) {
      const newItemsCount = merged.length - currentData.length;
      if (newItemsCount > 0) {
        chartRef.current.timeScale().setVisibleLogicalRange({
          from: previousLogicalRange.from + newItemsCount,
          to: previousLogicalRange.to + newItemsCount,
        });
      }
    }
  }, [historicalData]);

  // Handle Realtime Tick (Update Data incrementally)
  useEffect(() => {
    if (!chartRef.current || !candleSeriesRef.current || !realtimeCandle) return;

    const arr = chartDataRef.current;
    // Prevent 'Cannot update oldest data' exception in lightweight-charts
    // If the websocket tick is older than the latest historical candle, ignore it.
    if (arr.length > 0 && realtimeCandle.time < arr[arr.length - 1].time) {
        return;
    }

    // Use lightweight-charts high-performance .update()
    candleSeriesRef.current.update(realtimeCandle);
    lineSeriesRef.current.update({ time: realtimeCandle.time, value: realtimeCandle.close });
    if (volumeSeriesRef.current) {
      volumeSeriesRef.current.update({
          time: realtimeCandle.time,
          value: realtimeCandle.volume,
          color: realtimeCandle.close >= realtimeCandle.open ? "#10b98155" : "#f43f5e55",
      });
    }

    // Mirror to our local ref
    if (arr.length > 0 && arr[arr.length - 1].time === realtimeCandle.time) {
        arr[arr.length - 1] = realtimeCandle;
    } else {
        arr.push(realtimeCandle);
    }
  }, [realtimeCandle]);

  // Toggle chart types
  useEffect(() => {
    candleSeriesRef.current?.applyOptions({ visible: selectedChartType === "candles" });
    lineSeriesRef.current?.applyOptions({ visible: selectedChartType === "line" });
  }, [selectedChartType]);

  // Toggle volume
  useEffect(() => {
    volumeSeriesRef.current?.applyOptions({ visible: showVolume });
    chartRef.current?.priceScale("right").applyOptions({
      scaleMargins: { top: 0.1, bottom: showVolume ? 0.25 : 0.05 },
    });
  }, [showVolume]);

  return (
    <Card className={cn("flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/80", className)}>
      <CardHeader className="border-b border-slate-800 px-4 py-4 shrink-0">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-baseline gap-4 mb-1">
              <CardTitle className="text-2xl font-bold text-white uppercase tracking-tight">
                {symbol}
              </CardTitle>
              <div className="flex items-baseline gap-3">
                <span className="text-2xl font-bold text-white tabular-nums">
                  {formatCurrency(displayPrice)}
                </span>
                {priceChange && (
                  <div
                    className={cn(
                      "flex items-center gap-1 text-sm font-semibold",
                      priceChange.change >= 0 ? "text-emerald-400" : "text-rose-400"
                    )}
                  >
                    {priceChange.change >= 0 ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
                    <span>
                      {priceChange.change >= 0 ? "+" : ""}
                      {priceChange.change.toFixed(2)} ({priceChange.changePercent.toFixed(2)}%)
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={onBuyClick} className="bg-emerald-600 text-white hover:bg-emerald-500 font-bold px-6 rounded-xl">Buy</Button>
            <Button size="sm" onClick={onSellClick} className="bg-rose-600 text-white hover:bg-rose-500 font-bold px-6 rounded-xl">Sell</Button>
          </div>
        </div>

        <div className="mt-2 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <Tabs value={selectedTimeframe} onValueChange={setSelectedTimeframe}>
            <TabsList className="h-9 bg-slate-900">
              {TIMEFRAMES.map((item) => (
                <TabsTrigger key={item.value} value={item.value} className="px-3 text-xs data-[state=active]:bg-sky-500 data-[state=active]:text-slate-950">
                  {item.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>

          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={() => setShowVolume((c) => !c)} className="text-slate-400 hover:bg-slate-900 hover:text-white">
              {showVolume ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </Button>
            <Select value={selectedChartType} onValueChange={setSelectedChartType}>
              <SelectTrigger className="h-9 w-36 border-slate-800 bg-slate-900 text-slate-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="border-slate-800 bg-slate-900 text-slate-200">
                {CHART_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    <div className="flex items-center gap-2">
                      <type.icon className="h-4 w-4" />
                      {type.label}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {latestCandle && (
          <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-1 text-[11px] font-medium text-slate-500 border-t border-slate-800/50 pt-3">
            <div className="flex items-center gap-1.5">
              <span className="text-slate-600">O</span>
              <span className="text-slate-300 tabular-nums">{Number(latestCandle.open).toFixed(2)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-slate-600">H</span>
              <span className="text-emerald-400 tabular-nums">{Number(latestCandle.high).toFixed(2)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-slate-600">L</span>
              <span className="text-rose-400 tabular-nums">{Number(latestCandle.low).toFixed(2)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-slate-600">C</span>
              <span className="text-slate-300 tabular-nums">{Number(latestCandle.close).toFixed(2)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-slate-600">V</span>
              <span className="text-slate-400 tabular-nums">{Number(latestCandle.volume ?? 0).toLocaleString("en-IN")}</span>
            </div>
          </div>
        )}
      </CardHeader>

      <CardContent className="relative flex-1 p-0 min-h-0 min-w-0 overflow-hidden">
        {status === "loading" && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-slate-950/60 backdrop-blur-sm transition-all">
            <Loader2 className="h-10 w-10 animate-spin text-sky-500" />
            <p className="mt-4 text-sm font-medium text-slate-300">Loading chart data...</p>
          </div>
        )}

        {isLoadingOlder && (
          <div className="absolute left-4 top-4 z-20 flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/90 px-3 py-2 text-xs font-semibold text-slate-300 shadow-lg">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-400" />
            Loading history
          </div>
        )}

        {status === "ready" && historicalData.length === 0 && !realtimeCandle && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-slate-950/60 transition-all text-slate-400">
            <BarChart3 className="h-12 w-12 mb-4 opacity-20" />
            <p>No historical data available for this symbol.</p>
          </div>
        )}

        {status === "error" && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-950/80">
            <div className="text-center text-slate-300">
              <AlertCircle className="mx-auto mb-3 h-10 w-10 text-rose-400" />
              <p>Unable to load candles for this symbol.</p>
            </div>
          </div>
        )}

        <div
          ref={containerRef}
          className={cn(
            "h-full w-full",
            !symbol && "invisible pointer-events-none"
          )}
        />
        {!symbol && (
          <div className="absolute inset-0 z-10 flex h-full items-center justify-center text-slate-500 bg-slate-950/80">
            Select a symbol to load the trading terminal.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
