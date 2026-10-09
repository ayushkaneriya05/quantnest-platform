import { useTheme } from "@/shared/context/theme";
import { getChartPalette } from "@/shared/lib/chartTheme";
import PropTypes from "prop-types";
import { useEffect, useRef, useState, useCallback } from "react";
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
  TickMarkType,
} from "lightweight-charts";

import { Button } from "@/shared/components/ui/button";
import { useWebSocket } from "@/shared/hooks/useWebSocket";
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

import useRealtimeCandles from "@/features/terminal/hooks/useRealtimeCandles.js";
import { GlobalLoader } from '@/shared/components/ui/global-loader';

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

const createISTFormatter = (options) => new Intl.DateTimeFormat("en-IN", {
  timeZone: IST_TIME_ZONE,
  ...options,
});

// Keep axis labels short and let the chart prioritize calendar boundaries when zooming.
const TICK_FORMATTERS = {
  [TickMarkType.Year]: createISTFormatter({ year: "numeric" }),
  [TickMarkType.Month]: createISTFormatter({ month: "short" }),
  [TickMarkType.DayOfMonth]: createISTFormatter({ day: "numeric" }),
  [TickMarkType.Time]: createISTFormatter({ hour: "2-digit", minute: "2-digit", hourCycle: "h23" }),
  [TickMarkType.TimeWithSeconds]: createISTFormatter({ hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }),
};
const DATE_OPTIONS = { weekday: "short", day: "2-digit", month: "short", year: "numeric" };
const DATE_FORMATTER = createISTFormatter(DATE_OPTIONS);
const DATE_TIME_FORMATTER = createISTFormatter({ ...DATE_OPTIONS, hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const BUSINESS_DAY_FORMATTER = createISTFormatter({ year: "numeric", month: "2-digit", day: "2-digit" });

const isIntradayTimeframe = (timeframe) => timeframe !== "1D" && timeframe !== "1W";

const getChartDate = (time) => {
  if (typeof time === "number") return new Date(time * 1000);
  if (typeof time === "string") return new Date(`${time}T00:00:00Z`);
  if (time && typeof time === "object") return new Date(Date.UTC(time.year, time.month - 1, time.day));
  return new Date(NaN);
};

const formatChartTickIST = (time, tickMarkType) => {
  const date = getChartDate(time);
  if (!Number.isFinite(date.getTime())) return null;
  return TICK_FORMATTERS[tickMarkType]?.format(date) ?? null;
};

const formatChartTimeIST = (time, withTime) => {
  const date = getChartDate(time);
  if (!Number.isFinite(date.getTime())) return "";
  return withTime ? `${DATE_TIME_FORMATTER.format(date)} IST` : DATE_FORMATTER.format(date);
};

const toChartTime = (unixSeconds, timeframe) => {
  if (isIntradayTimeframe(timeframe)) return unixSeconds;
  // Daily/weekly bars are trading dates. Using IST business days also places
  // month/year markers correctly when a candle's UTC timestamp is the prior day.
  const parts = BUSINESS_DAY_FORMATTER.formatToParts(new Date(unixSeconds * 1000));
  return ["year", "month", "day"].map((type) => parts.find((part) => part.type === type).value).join("-");
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
  const { resolvedTheme } = useTheme();
  const [selectedTimeframe, setSelectedTimeframe] = useState(propInterval);
  const [selectedChartType, setSelectedChartType] = useState("candles");
  const [showVolume, setShowVolume] = useState(false);
  const [hoveredCandle, setHoveredCandle] = useState(null);
  const { getTickData } = useWebSocket();

  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const timeframeRef = useRef(selectedTimeframe);
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
  const paletteRef = useRef(null);

  // DOM Refs for ultra-fast direct mutations
  const priceRef = useRef(null);
  const priceChangeWrapperRef = useRef(null);
  const priceChangeIconUpRef = useRef(null);
  const priceChangeIconDownRef = useRef(null);
  const priceChangeTextRef = useRef(null);

  const handleTickUpdate = useCallback((event) => {
    const latestTickPrice = Number(event.price ?? event.ltp);
    if (Number.isFinite(latestTickPrice) && latestTickPrice > 0) {
      if (priceRef.current) {
        priceRef.current.innerText = formatCurrency(latestTickPrice);
      }
      
      const change = Number(event.change);
      const changePercent = Number(event.change_percent ?? 0);
      
      if (Number.isFinite(change) && priceChangeWrapperRef.current && priceChangeTextRef.current) {
        priceChangeWrapperRef.current.style.display = "flex";
        const isUp = change >= 0;
        
        priceChangeWrapperRef.current.className = cn(
            "flex items-center gap-1 text-sm font-semibold",
            isUp ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"
        );
        
        priceChangeTextRef.current.innerText = `${isUp ? "+" : ""}${change.toFixed(2)} (${changePercent.toFixed(2)}%)`;
        
        if (priceChangeIconUpRef.current) priceChangeIconUpRef.current.style.display = isUp ? "block" : "none";
        if (priceChangeIconDownRef.current) priceChangeIconDownRef.current.style.display = !isUp ? "block" : "none";
      }
    }
  }, []);

  const handleRealtimeCandleUpdate = useCallback((realtimeCandle) => {
    if (!chartRef.current || !candleSeriesRef.current || !realtimeCandle) return;

    const arr = chartDataRef.current;
    const time = toChartTime(realtimeCandle.time, timeframeRef.current);
    const lastTime = arr.length ? toChartTime(arr[arr.length - 1].time, timeframeRef.current) : null;
    if (lastTime !== null && time < lastTime) {
        return;
    }

    candleSeriesRef.current.update({ ...realtimeCandle, time });
    lineSeriesRef.current.update({ time, value: realtimeCandle.close });
    if (volumeSeriesRef.current) {
      volumeSeriesRef.current.update({
          time,
          value: realtimeCandle.volume,
          color: realtimeCandle.close >= realtimeCandle.open ? paletteRef.current.up : paletteRef.current.down,
      });
    }

    if (lastTime === time) {
        arr[arr.length - 1] = realtimeCandle;
    } else {
        arr.push(realtimeCandle);
    }
  }, []);

  const {
    historicalData,
    status,
    isLoadingOlder,
    hasMoreHistory,
    loadOlder,
  } = useRealtimeCandles(symbol, selectedTimeframe, handleRealtimeCandleUpdate, handleTickUpdate);

  useEffect(() => {
    loadOlderRef.current = loadOlder;
    isLoadingOlderRef.current = isLoadingOlder;
    hasMoreHistoryRef.current = hasMoreHistory;
  }, [hasMoreHistory, isLoadingOlder, loadOlder]);

  useEffect(() => {
    timeframeRef.current = selectedTimeframe;
    chartRef.current?.applyOptions({ timeScale: { timeVisible: isIntradayTimeframe(selectedTimeframe) } });
    shouldFitContentRef.current = true;
    userNavigatedHistoryRef.current = false;
    setHoveredCandle(null);
    chartDataRef.current = [];

    if (candleSeriesRef.current) candleSeriesRef.current.setData([]);
    if (lineSeriesRef.current) lineSeriesRef.current.setData([]);
    if (volumeSeriesRef.current) volumeSeriesRef.current.setData([]);
  }, [selectedTimeframe, symbol]);

  const currentCandle = chartDataRef.current[chartDataRef.current.length - 1] ?? null;
  const latestCandle = hoveredCandle ?? currentCandle;
  
  // Get the effective tick data from the Redux store (aware of market phase / adjusted close)
  const effectiveTick = getTickData(symbol);
  const displayPrice = effectiveTick?.price ?? currentCandle?.close;

  // Init Chart instance
  useEffect(() => {
    let chart;
    let observer;
    let visibleRangeHandler;
    let markUserNavigation;
    let container;

    const initChart = () => {
      if (!containerRef.current) return;
      container = containerRef.current;

      const width = container.clientWidth;
      const height = container.clientHeight;
      markUserNavigation = () => {
        userNavigatedHistoryRef.current = true;
      };
      container.addEventListener("wheel", markUserNavigation, { passive: true });
      container.addEventListener("pointerdown", markUserNavigation);

      const palette = getChartPalette();
      paletteRef.current = palette;
      chart = createChart(container, {
        layout: {
          background: { type: ColorType.Solid, color: palette.background },
          textColor: palette.text,
          fontSize: 12,
          fontFamily: "Inter, sans-serif",
        },
        grid: {
          vertLines: { color: palette.grid, style: 1 },
          horzLines: { color: palette.grid, style: 1 },
        },
        crosshair: { mode: CrosshairMode.Normal },
        width: width || 800,
        height: height || 400,
        timeScale: {
          borderColor: palette.border,
          borderVisible: true,
          timeVisible: isIntradayTimeframe(timeframeRef.current),
          secondsVisible: false,
          barSpacing: 10,
          rightOffset: 5,
          tickMarkFormatter: formatChartTickIST,
        },
        localization: {
          locale: "en-IN",
          timeFormatter: (time) => formatChartTimeIST(time, isIntradayTimeframe(timeframeRef.current)),
        },
        rightPriceScale: {
          borderColor: palette.border,
          borderVisible: true,
          scaleMargins: { top: 0.1, bottom: 0.25 },
        },
        handleScroll: true,
        handleScale: true,
      });

      chartRef.current = chart;
      candleSeriesRef.current = chart.addSeries(CandlestickSeries, {
        upColor: palette.up,
        downColor: palette.down,
        borderVisible: false,
        wickUpColor: palette.up,
        wickDownColor: palette.down,
      });
      lineSeriesRef.current = chart.addSeries(LineSeries, {
        color: palette.line,
        lineWidth: 2,
        visible: false,
      });
      volumeSeriesRef.current = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "",
        scaleMargins: { top: 0.8, bottom: 0.05 },
        color: palette.border,
        visible: false,
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
      if (container && markUserNavigation) {
        container.removeEventListener("wheel", markUserNavigation);
        container.removeEventListener("pointerdown", markUserNavigation);
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

  // Change only presentation; preserve candles, zoom, and subscriptions.
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      const palette = getChartPalette();
      paletteRef.current = palette;
      chartRef.current?.applyOptions({
        layout: { background: { type: ColorType.Solid, color: palette.background }, textColor: palette.text },
        grid: { vertLines: { color: palette.grid }, horzLines: { color: palette.grid } },
        timeScale: { borderColor: palette.border }, rightPriceScale: { borderColor: palette.border },
      });
      candleSeriesRef.current?.applyOptions({ upColor: palette.up, downColor: palette.down, wickUpColor: palette.up, wickDownColor: palette.down });
      lineSeriesRef.current?.applyOptions({ color: palette.line });
      if (volumeSeriesRef.current && chartDataRef.current.length) {
        const range = chartRef.current.timeScale().getVisibleLogicalRange();
        volumeSeriesRef.current.setData(chartDataRef.current.map((item) => ({
          time: toChartTime(item.time, timeframeRef.current), value: item.volume,
          color: item.close >= item.open ? palette.up : palette.down,
        })));
        if (range) chartRef.current.timeScale().setVisibleLogicalRange(range);
      }
    });
    return () => cancelAnimationFrame(frame);
  }, [resolvedTheme]);

  // Handle Historical Data (Set Data)
  useEffect(() => {
    if (!chartRef.current || !candleSeriesRef.current || !historicalData || historicalData.length === 0) return;
    
    // Merge new historical data with any existing data (including real-time ticks)
    const currentData = chartDataRef.current;
    const map = new Map();
    historicalData.forEach(c => map.set(toChartTime(c.time, timeframeRef.current), c));
    currentData.forEach(c => map.set(toChartTime(c.time, timeframeRef.current), c));
    
    const merged = Array.from(map.values()).sort((a, b) => a.time - b.time);
    chartDataRef.current = merged;

    // Build the line & volume arrays
    const candles = merged.map((item) => ({ ...item, time: toChartTime(item.time, timeframeRef.current) }));
    const lines = candles.map((item) => ({ time: item.time, value: item.close }));
    const volumes = candles.map((item) => ({
      time: item.time,
      value: item.volume,
      color: item.close >= item.open ? paletteRef.current.up : paletteRef.current.down,
    }));

    // Get the previous visible range before setting new data
    const previousLogicalRange = chartRef.current.timeScale().getVisibleLogicalRange();

    // Update charts using setData (Heavy operation, only do on historical load)
    candleSeriesRef.current.setData(candles);
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
    <Card className={cn("flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-3xl border border-border bg-background/80", className)}>
      <CardHeader className="border-b border-border px-3 py-3 shrink-0 sm:px-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-baseline gap-4 mb-1">
              <CardTitle className="text-lg sm:text-2xl font-bold text-foreground uppercase tracking-tight">
                {symbol}
              </CardTitle>
              <div className="flex items-baseline gap-3">
                <span ref={priceRef} className="text-lg sm:text-2xl font-bold text-foreground tabular-nums">
                  {formatCurrency(displayPrice)}
                </span>
                <div
                  ref={priceChangeWrapperRef}
                  className="flex items-center gap-1 text-sm font-semibold"
                  style={{ display: "none" }}
                >
                  <div ref={priceChangeIconUpRef} style={{ display: "none" }}><TrendingUp className="h-3.5 w-3.5" /></div>
                  <div ref={priceChangeIconDownRef} style={{ display: "none" }}><TrendingDown className="h-3.5 w-3.5" /></div>
                  <span ref={priceChangeTextRef}></span>
                </div>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={onBuyClick} className="bg-emerald-700 text-white hover:bg-emerald-800 font-bold px-6 rounded-xl">Buy</Button>
            <Button size="sm" onClick={onSellClick} className="bg-rose-600 text-white hover:bg-rose-700 font-bold px-6 rounded-xl">Sell</Button>
          </div>
        </div>

        <div className="mt-2 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <Tabs value={selectedTimeframe} onValueChange={setSelectedTimeframe}>
            <TabsList className="h-10 w-full bg-card">
              {TIMEFRAMES.map((item) => (
                <TabsTrigger key={item.value} value={item.value} className="min-w-0 flex-1 px-2 text-xs data-[state=active]:bg-sky-500 data-[state=active]:text-white">
                  {item.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>

          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={() => setShowVolume((c) => !c)} aria-label={showVolume ? "Hide volume" : "Show volume"} aria-pressed={showVolume} className="text-muted-foreground hover:bg-card hover:text-foreground">
              {showVolume ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </Button>
            <Select value={selectedChartType} onValueChange={setSelectedChartType}>
              <SelectTrigger className="h-9 w-36 border-border bg-card text-foreground">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="border-border bg-card text-foreground">
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
          <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-1 text-[11px] font-medium text-muted-foreground border-t border-border/50 pt-3">
            <div className="flex items-center gap-1.5">
              <span className="text-muted-foreground">O</span>
              <span className="text-foreground tabular-nums">{Number(latestCandle.open).toFixed(2)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-muted-foreground">H</span>
              <span className="text-emerald-700 dark:text-emerald-400 tabular-nums">{Number(latestCandle.high).toFixed(2)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-muted-foreground">L</span>
              <span className="text-rose-700 dark:text-rose-400 tabular-nums">{Number(latestCandle.low).toFixed(2)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-muted-foreground">C</span>
              <span className="text-foreground tabular-nums">{Number(latestCandle.close).toFixed(2)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-muted-foreground">V</span>
              <span className="text-muted-foreground tabular-nums">{Number(latestCandle.volume ?? 0).toLocaleString("en-IN")}</span>
            </div>
          </div>
        )}
      </CardHeader>

      <CardContent className="relative flex-1 p-0 min-h-0 min-w-0 overflow-hidden">
        {status === "loading" && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-background/60 backdrop-blur-sm transition-all">
            <GlobalLoader />
            <p className="mt-4 text-sm font-medium text-foreground">Loading chart data...</p>
          </div>
        )}

        {isLoadingOlder && (
          <div className="absolute left-4 top-4 z-20 flex items-center gap-2 rounded-xl border border-border bg-background/90 px-3 py-2 text-xs font-semibold text-foreground shadow-lg">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-700 dark:text-sky-400" />
            Loading history
          </div>
        )}

        {status === "ready" && historicalData.length === 0 && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-background/60 transition-all text-muted-foreground">
            <BarChart3 className="h-12 w-12 mb-4 opacity-20" />
            <p>No historical data available for this symbol.</p>
          </div>
        )}

        {status === "error" && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/80">
            <div className="text-center text-foreground">
              <AlertCircle className="mx-auto mb-3 h-10 w-10 text-rose-700 dark:text-rose-400" />
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
          <div className="absolute inset-0 z-10 flex h-full items-center justify-center text-muted-foreground bg-background/80">
            Select a symbol to load the trading terminal.
          </div>
        )}
      </CardContent>
    </Card>
  );
}

ChartView.propTypes = {
  symbol: PropTypes.string,
  interval: PropTypes.string,
  onBuyClick: PropTypes.func,
  onSellClick: PropTypes.func,
  className: PropTypes.string,
};
