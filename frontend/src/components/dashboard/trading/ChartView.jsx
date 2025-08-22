import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
} from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Button } from "../../ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../ui/select";
import { Tabs, TabsList, TabsTrigger } from "../../ui/tabs";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Activity,
  AlertCircle,
  Loader2,
  Eye,
  EyeOff,
  Clock,
} from "lucide-react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
} from "lightweight-charts";
import api from "@/services/api";
import { useWebSocket } from "../../../contexts/websocket-context";
import { toast } from "react-hot-toast";
import { cn } from "../../../lib/utils";

// Constants for chart configuration
const TIMEFRAMES = [
  { value: "1m", label: "1M", interval: 60 * 1000 },
  { value: "5m", label: "5M", interval: 5 * 60 * 1000 },
  { value: "15m", label: "15M", interval: 15 * 60 * 1000 },
  { value: "1h", label: "1H", interval: 60 * 60 * 1000 },
  { value: "1D", label: "1D", interval: 24 * 60 * 60 * 1000 },
  { value: "1W", label: "1W", interval: 7 * 24 * 60 * 60 * 1000 },
];

const CHART_TYPES = [
  { value: "candles", label: "Candlesticks", icon: BarChart3 },
  { value: "line", label: "Line", icon: Activity },
];

const ChartView = ({
  instrument,
  symbol,
  className,
  height = 500,
  showControls = true,
  defaultTimeframe = "1D",
  defaultChartType = "candles",
  onBuyClick,
  onSellClick,
}) => {
  // State Management
  const [selectedTimeframe, setSelectedTimeframe] = useState(defaultTimeframe);
  const [selectedChartType, setSelectedChartType] = useState(defaultChartType);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastPrice, setLastPrice] = useState(null);
  const [priceChange, setPriceChange] = useState(null);
  const [showVolume, setShowVolume] = useState(true);
  const [ohlc, setOhlc] = useState(null);

  // Refs for chart elements and data
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candlestickSeriesRef = useRef(null);
  const lineSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const lastCandleRef = useRef(null);

  const { isConnected, subscribe, getLatestPrice } = useWebSocket();

  const normalizedInstrument = useMemo(() => {
    if (instrument) return instrument;
    if (symbol) return { symbol, company_name: symbol };
    return null;
  }, [instrument, symbol]);

  // --- Chart Initialization Effect ---
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        textColor: "#d1d4dc",
        background: { type: ColorType.Solid, color: "#0d1117" },
        fontSize: 12,
      },
      grid: {
        vertLines: { color: "#363a45" },
        horzLines: { color: "#363a45" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#4e5260" },
      timeScale: {
        borderColor: "#4e5260",
        timeVisible: true,
        localization: {
          timeFormatter: (timestamp) => {
            const date = new Date(timestamp * 1000);
            return date.toLocaleTimeString("en-IN", {
              timeZone: "Asia/Kolkata",
              hour: "2-digit",
              minute: "2-digit",
              hour12: false,
            });
          },
        },
      },
      width: chartContainerRef.current.clientWidth,
      height,
    });
    chartRef.current = chart;

    candlestickSeriesRef.current = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });
    lineSeriesRef.current = chart.addSeries(LineSeries, {
      color: "#2196f3",
      lineWidth: 2,
      visible: false,
    });
    volumeSeriesRef.current = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "",
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    chart.subscribeCrosshairMove((param) => {
      if (param.time && param.seriesData.get(candlestickSeriesRef.current)) {
        setOhlc(param.seriesData.get(candlestickSeriesRef.current));
      } else {
        setOhlc(lastCandleRef.current);
      }
    });

    const resizeObserver = new ResizeObserver((entries) => {
      if (entries[0]) {
        const { width } = entries[0].contentRect;
        chart.applyOptions({ width });
      }
    });
    resizeObserver.observe(chartContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      // FIX: Set ref to null immediately to prevent access to disposed object
      chartRef.current = null;
    };
  }, [height]);

  // --- Historical Data Fetching ---
  const fetchHistoricalData = useCallback(
    async (abortSignal) => {
      if (!normalizedInstrument?.symbol || !candlestickSeriesRef.current)
        return;
      setIsLoading(true);
      setError(null);
      try {
        const response = await api.get(
          `/market/ohlc/?instrument=${normalizedInstrument.symbol}&resolution=${selectedTimeframe}`,
          { signal: abortSignal }
        );
        const transformed = response.data
          .map((c) => ({
            time: Math.floor(new Date(c.time).getTime() / 1000),
            open: parseFloat(c.open),
            high: parseFloat(c.high),
            low: parseFloat(c.low),
            close: parseFloat(c.close),
            volume: parseInt(c.volume || 0, 10),
          }))
          .sort((a, b) => a.time - b.time);

        if (chartRef.current) {
          // Check if chart still exists before updating
          candlestickSeriesRef.current.setData(transformed);
          lineSeriesRef.current.setData(
            transformed.map((d) => ({ time: d.time, value: d.close }))
          );
          volumeSeriesRef.current.setData(
            transformed.map((d) => ({
              time: d.time,
              value: d.volume,
              color: d.close >= d.open ? "#22c55e40" : "#ef444440",
            }))
          );

          if (transformed.length > 0) {
            const lastCandle = transformed[transformed.length - 1];
            lastCandleRef.current = lastCandle;
            setOhlc(lastCandle);

            if (!isConnected) {
              const lastTickResponse = await api.get(
                `/market/latest-tick/?instrument=${normalizedInstrument.symbol}`,
                { signal: abortSignal }
              );
              const lastTick = lastTickResponse.data;
              if (lastTick) {
                setLastPrice(lastTick.price);
                const change = lastTick.price - lastTick.prev_close;
                const changePercent = (change / lastTick.prev_close) * 100;
                setPriceChange({
                  change: change.toFixed(2),
                  changePercent: isNaN(changePercent)
                    ? "0.00"
                    : changePercent.toFixed(2),
                  isPositive: change >= 0,
                });
              }
            }
            chartRef.current.timeScale().fitContent();
          } else {
            const lastKnownPrice = await getLatestPrice(
              normalizedInstrument.symbol
            );
            if (lastKnownPrice) setLastPrice(lastKnownPrice);
          }
        }
      } catch (err) {
        // FIX: Don't show an error toast if the request was intentionally cancelled
        if (err.name !== "CanceledError") {
          setError("Failed to load chart data. Please try again.");
          toast.error("Failed to load chart data.");
        }
      } finally {
        setIsLoading(false);
      }
    },
    [normalizedInstrument, selectedTimeframe, isConnected, getLatestPrice]
  );

  useEffect(() => {
    // FIX: Implement AbortController to cancel API requests when the component unmounts
    const controller = new AbortController();
    fetchHistoricalData(controller.signal);

    return () => {
      controller.abort(); // Cancel the request on cleanup
    };
  }, [fetchHistoricalData]);

  // --- Live WebSocket Tick Handling ---
  useEffect(() => {
    if (!normalizedInstrument?.symbol || !isConnected) return;
    const unsubscribe = subscribe(normalizedInstrument.symbol, (tick) => {
      if (!tick || !chartRef.current) return; // Check if chart still exists
      const tf = TIMEFRAMES.find((t) => t.value === selectedTimeframe);
      if (!tf) return;

      const bucket = tf.interval / 1000;
      const tickTime = Math.floor(new Date(tick.timestamp).getTime() / 1000);
      const alignedTime = Math.floor(tickTime / bucket) * bucket;

      let candle = lastCandleRef.current
        ? { ...lastCandleRef.current }
        : { time: 0 };

      if (alignedTime === candle.time) {
        candle.high = Math.max(candle.high, tick.price);
        candle.low = Math.min(candle.low, tick.price);
        candle.close = tick.price;
        candle.volume = (candle.volume || 0) + (tick.last_traded_qty || 0);
      } else if (alignedTime > candle.time) {
        candle = {
          time: alignedTime,
          open: tick.price,
          high: tick.price,
          low: tick.price,
          close: tick.price,
          volume: tick.last_traded_qty || 0,
        };
      }

      lastCandleRef.current = candle;
      candlestickSeriesRef.current.update(candle);
      lineSeriesRef.current.update({ time: candle.time, value: candle.close });
      volumeSeriesRef.current.update({
        time: candle.time,
        value: candle.volume,
        color: candle.close >= candle.open ? "#22c55e40" : "#ef444440",
      });

      setLastPrice(tick.price);
      setOhlc(candle);
      setPriceChange({
        change: tick.change.toFixed(2),
        changePercent: tick.change_percent.toFixed(2),
        isPositive: tick.change >= 0,
      });
    });
    return () => unsubscribe();
  }, [normalizedInstrument, selectedTimeframe, subscribe, isConnected]);

  // --- UI Effects for Toggling Chart Features ---
  useEffect(() => {
    if (!chartRef.current) return;
    candlestickSeriesRef.current.applyOptions({
      visible: selectedChartType === "candles",
    });
    lineSeriesRef.current.applyOptions({
      visible: selectedChartType !== "candles",
    });
  }, [selectedChartType]);

  useEffect(() => {
    if (!chartRef.current) return;
    volumeSeriesRef.current.applyOptions({ visible: showVolume });
    chartRef.current.priceScale("right").applyOptions({
      scaleMargins: { top: 0.1, bottom: showVolume ? 0.25 : 0.05 },
    });
  }, [showVolume]);

  const formatPrice = (p) => (p ? `₹${parseFloat(p).toFixed(2)}` : "--");

  return (
    <Card
      className={cn(
        "w-full bg-[#0d1117] border-[#4e5260] flex flex-col",
        className
      )}
    >
      {showControls && (
        <CardHeader className="p-3 bg-[#0d1117] border-b border-[#4e5260]">
          {/* Top Row: Symbol, Price, Change */}
          <div className="flex items-start justify-between">
            <div className="flex flex-col items-start gap-1">
              <div className="flex items-center gap-4">
                <CardTitle className="text-xl text-[#d1d4dc]">
                  {normalizedInstrument?.symbol || "Select Instrument"}
                </CardTitle>
                <div className="flex items-center gap-2">
                  <div
                    className={cn(
                      "h-2 w-2 rounded-full",
                      isConnected ? "bg-[#22c55e]" : "bg-[#ef4444]"
                    )}
                  />
                  <span className="text-xs text-[#758696]">
                    {isConnected ? "Live" : "Offline"}
                  </span>
                  <div className="flex items-center gap-1 text-xs text-yellow-400/80 bg-yellow-900/30 px-1.5 py-0.5 rounded-sm">
                    <Clock className="h-3 w-3" />
                    <span>15-Min Delayed</span>
                  </div>
                </div>
              </div>
              {lastPrice && (
                <div className="flex items-baseline gap-3">
                  <span className="text-2xl font-bold text-[#d1d4dc]">
                    {formatPrice(lastPrice)}
                  </span>
                  {priceChange && (
                    <div
                      className={cn(
                        "flex items-baseline gap-1 font-medium",
                        priceChange.isPositive
                          ? "text-[#22c55e]"
                          : "text-[#ef4444]"
                      )}
                    >
                      {priceChange.isPositive ? (
                        <TrendingUp className="h-4 w-4" />
                      ) : (
                        <TrendingDown className="h-4 w-4" />
                      )}
                      <span>
                        {priceChange.change} ({priceChange.changePercent}%)
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
            {(onBuyClick || onSellClick) && (
              <div className="flex gap-2">
                {onBuyClick && (
                  <Button
                    onClick={onBuyClick}
                    size="lg"
                    className="bg-green-600 hover:bg-green-700 text-white font-semibold"
                  >
                    Buy
                  </Button>
                )}
                {onSellClick && (
                  <Button
                    onClick={onSellClick}
                    size="lg"
                    className="bg-red-600 hover:bg-red-700 text-white font-semibold"
                  >
                    Sell
                  </Button>
                )}
              </div>
            )}
          </div>

          {/* OHLC Display */}
          {ohlc && (
            <div className="flex items-center gap-4 text-xs text-gray-400 mt-2">
              <span>
                O <span className="text-gray-200">{ohlc.open?.toFixed(2)}</span>
              </span>
              <span>
                H <span className="text-gray-200">{ohlc.high?.toFixed(2)}</span>
              </span>
              <span>
                L <span className="text-gray-200">{ohlc.low?.toFixed(2)}</span>
              </span>
              <span>
                C{" "}
                <span className="text-gray-200">{ohlc.close?.toFixed(2)}</span>
              </span>
            </div>
          )}

          {/* Bottom Row: Timeframe, Chart Type */}
          <div className="flex items-center justify-between mt-2">
            <Tabs
              value={selectedTimeframe}
              onValueChange={setSelectedTimeframe}
            >
              <TabsList className="h-8 bg-[#2a2e39] border-[#4e5260]">
                {TIMEFRAMES.map((t) => (
                  <TabsTrigger
                    key={t.value}
                    value={t.value}
                    className="text-xs px-2.5 text-[#d1d4dc] data-[state=active]:bg-[#4e5260] data-[state=active]:text-white hover:text-white"
                  >
                    {t.label}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowVolume(!showVolume)}
                className="text-slate-400 hover:text-white hover:bg-gray-700/50"
              >
                {showVolume ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>
              <Select
                value={selectedChartType}
                onValueChange={setSelectedChartType}
              >
                <SelectTrigger className="w-36 bg-[#2a2e39] border-[#4e5260] text-[#d1d4dc] h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#2a2e39] border-[#4e5260]">
                  {CHART_TYPES.map((type) => (
                    <SelectItem
                      key={type.value}
                      value={type.value}
                      className="text-[#d1d4dc] hover:text-white hover:bg-[#4e5260]"
                    >
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
        </CardHeader>
      )}
      <CardContent className="p-0 flex-grow relative overflow-hidden">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0d1117]">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
          </div>
        )}
        {error && !isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0d1117]">
            <div className="text-center text-red-400">
              <AlertCircle className="h-12 w-12 mx-auto mb-4" />
              <p>{error}</p>
            </div>
          </div>
        )}
        <div
          ref={chartContainerRef}
          className={cn(
            "w-full h-full",
            isLoading || error ? "invisible" : "visible"
          )}
        />
        {!normalizedInstrument && !isLoading && !error && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0d1117]">
            <div className="text-center">
              <BarChart3 className="h-12 w-12 text-[#758696] mx-auto mb-4" />
              <p className="text-[#758696]">
                Select an instrument to view chart
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default ChartView;
