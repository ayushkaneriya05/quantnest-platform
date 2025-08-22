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
  const [selectedTimeframe, setSelectedTimeframe] = useState(defaultTimeframe);
  const [selectedChartType, setSelectedChartType] = useState(defaultChartType);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastPrice, setLastPrice] = useState(null);
  const [priceChange, setPriceChange] = useState(null);
  const [showVolume, setShowVolume] = useState(true);

  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candlestickSeriesRef = useRef(null);
  const lineSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const lastCandleRef = useRef(null);

  const { isConnected, subscribe } = useWebSocket();

  const normalizedInstrument = useMemo(() => {
    if (instrument) return instrument;
    if (symbol) return { symbol, company_name: symbol };
    return null;
  }, [instrument, symbol]);

  // Chart Initialization Effect
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
      rightPriceScale: {
        borderColor: "#4e5260",
        scaleMargins: { top: 0.1, bottom: 0.25 },
      },
      timeScale: { borderColor: "#4e5260", timeVisible: true },
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
      priceScaleId: "volume_scale",
      scaleMargins: { top: 0.75, bottom: 0 },
    });

    const resizeObserver = new ResizeObserver((entries) => {
      if (entries[0]) {
        const { width, height } = entries[0].contentRect;
        chart.applyOptions({ width, height });
      }
    });
    resizeObserver.observe(chartContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [height]);

  // Historical Data Fetching Effect
  const fetchHistoricalData = useCallback(async () => {
    if (!normalizedInstrument?.symbol || !candlestickSeriesRef.current) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.get(
        `/market/ohlc/?instrument=${normalizedInstrument.symbol}&resolution=${selectedTimeframe}`
      );

      const transformed = response.data
        .map((c) => ({
          time: Math.floor(c.time / 1000),
          open: parseFloat(c.open),
          high: parseFloat(c.high),
          low: parseFloat(c.low),
          close: parseFloat(c.close),
          volume: parseInt(c.volume || 0, 10),
        }))
        .sort((a, b) => a.time - b.time);

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
        lastCandleRef.current = transformed[transformed.length - 1];
        setLastPrice(lastCandleRef.current.close);
        if (transformed.length > 1) {
          const prev = transformed[transformed.length - 2];
          const change = lastCandleRef.current.close - prev.close;
          setPriceChange({
            change: change.toFixed(2),
            changePercent: ((change / prev.close) * 100).toFixed(2),
            isPositive: change >= 0,
          });
        }

        // **FIX 2: Corrected initial zoom logic**
        if (selectedTimeframe === "1D" || selectedTimeframe === "1W") {
          const lastDataPoint = transformed[transformed.length - 1];
          // Approx 150 trading days for 5 months
          const fromIndex = Math.max(0, transformed.length - 150);
          const fromTimestamp = transformed[fromIndex].time;
          chartRef.current.timeScale().setVisibleRange({
            from: fromTimestamp,
            to: lastDataPoint.time,
          });
        } else {
          chartRef.current.timeScale().fitContent();
        }
      } else {
        lastCandleRef.current = null;
      }
    } catch (e) {
      setError("Failed to load chart data. Please try again.");
      toast.error("Failed to load chart data.");
    } finally {
      setIsLoading(false);
    }
  }, [normalizedInstrument, selectedTimeframe]);

  useEffect(() => {
    fetchHistoricalData();
  }, [fetchHistoricalData]);

  // WebSocket Logic Effect
  useEffect(() => {
    if (!normalizedInstrument?.symbol) return;

    const unsubscribe = subscribe(normalizedInstrument.symbol, (tick) => {
      if (!tick || !candlestickSeriesRef.current || !lastCandleRef.current)
        return;

      const tf = TIMEFRAMES.find((tf) => tf.value === selectedTimeframe);
      if (!tf) return;
      const bucket = tf.interval / 1000;
      const tickTime = Math.floor(new Date(tick.timestamp).getTime() / 1000);
      const alignedTime = Math.floor(tickTime / bucket) * bucket;

      let candle = { ...lastCandleRef.current };
      if (alignedTime === candle.time) {
        candle.high = Math.max(candle.high, tick.price);
        candle.low = Math.min(candle.low, tick.price);
        candle.close = tick.price;
        candle.volume = tick.volume_traded_today;
      } else if (alignedTime > candle.time) {
        candle = {
          time: alignedTime,
          open: tick.price,
          high: tick.price,
          low: tick.price,
          close: tick.price,
          volume: tick.volume_traded_today,
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

      setLastPrice(candle.close);
    });

    return () => unsubscribe();
  }, [normalizedInstrument, selectedTimeframe, subscribe]);

  // Chart Type Visibility Effect
  useEffect(() => {
    if (!candlestickSeriesRef.current || !lineSeriesRef.current) return;
    if (selectedChartType === "candles") {
      candlestickSeriesRef.current.applyOptions({ visible: true });
      lineSeriesRef.current.applyOptions({ visible: false });
    } else {
      candlestickSeriesRef.current.applyOptions({ visible: false });
      lineSeriesRef.current.applyOptions({ visible: true });
    }
  }, [selectedChartType]);

  // Volume Visibility Effect
  useEffect(() => {
    if (!volumeSeriesRef.current || !chartRef.current) return;

    volumeSeriesRef.current.applyOptions({ visible: showVolume });

    chartRef.current.priceScale("right").applyOptions({
      scaleMargins: { top: 0.1, bottom: showVolume ? 0.25 : 0.05 },
    });
  }, [showVolume]);

  const formatPrice = (p) => (p ? `₹${parseFloat(p).toFixed(2)}` : "--");
  return (
    <Card className={cn("w-full bg-[#0d1117] border-[#4e5260]", className)}>
      {showControls && (
        <CardHeader className="pb-4 bg-[#0d1117] border-b border-[#4e5260]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <CardTitle className="text-2xl text-[#d1d4dc]">
                {normalizedInstrument?.symbol || "Select Instrument"}
              </CardTitle>
              {lastPrice && (
                <div className="flex items-center gap-6 mt-2">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-bold text-[#d1d4dc]">
                      {formatPrice(lastPrice)}
                    </span>
                    {priceChange && (
                      <div
                        className={cn(
                          "flex items-center gap-1",
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
                        <span className="font-medium">
                          {priceChange.change} ({priceChange.changePercent}%)
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-1">
                    <div
                      className={cn(
                        "h-2 w-2 rounded-full",
                        isConnected ? "bg-[#22c55e]" : "bg-[#ef4444]"
                      )}
                    />
                    <span className="text-xs text-[#758696]">
                      {isConnected ? "Live" : "Offline"}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between mt-4">
            <Tabs
              value={selectedTimeframe}
              onValueChange={setSelectedTimeframe}
            >
              <TabsList className="grid grid-cols-6 bg-[#2a2e39] border-[#4e5260]">
                {TIMEFRAMES.map((t) => (
                  <TabsTrigger
                    key={t.value}
                    value={t.value}
                    className="text-xs px-3 text-[#d1d4dc] data-[state=active]:bg-[#4e5260] data-[state=active]:text-white hover:text-white"
                  >
                    {t.label}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>

            <div className="flex items-center gap-2">
              <div className="flex items-center text-[#d1d4dc]">
                Volume
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
              </div>

              <Select
                value={selectedChartType}
                onValueChange={setSelectedChartType}
              >
                <SelectTrigger className="w-32 bg-[#2a2e39] border-[#4e5260] text-[#d1d4dc]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#2a2e39] border-[#4e5260]">
                  {CHART_TYPES.map((type) => {
                    const Icon = type.icon;
                    return (
                      <SelectItem
                        key={type.value}
                        value={type.value}
                        className="text-[#d1d4dc] hover:text-white hover:bg-[#4e5260]"
                      >
                        <div className="flex items-center gap-2">
                          <Icon className="h-4 w-4" />
                          {type.label}
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>

            {(onBuyClick || onSellClick) && (
              <div className="flex gap-4">
                {onBuyClick && (
                  <Button
                    onClick={onBuyClick}
                    size="lg"
                    className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 font-semibold transition-all duration-200 shadow-lg hover:shadow-green-500/25 text-md"
                  >
                    Buy
                  </Button>
                )}
                {onSellClick && (
                  <Button
                    onClick={onSellClick}
                    size="lg"
                    className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 font-semibold transition-all duration-200 shadow-lg hover:shadow-red-500/25 text-md"
                  >
                    Sell
                  </Button>
                )}
              </div>
            )}
          </div>
        </CardHeader>
      )}
      <CardContent className="p-0">
        {isLoading && (
          <div
            className="flex items-center justify-center"
            style={{ height: `${height}px` }}
          >
            <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
          </div>
        )}
        {error && !isLoading && (
          <div
            className="flex items-center justify-center"
            style={{ height: `${height}px` }}
          >
            <div className="text-center text-red-400">
              <AlertCircle className="h-12 w-12 mx-auto mb-4" />
              <p>{error}</p>
            </div>
          </div>
        )}
        <div
          ref={chartContainerRef}
          className={cn("w-full", isLoading || error ? "hidden" : "block")}
          style={{ height: `${height}px` }}
        />
        {!normalizedInstrument && !isLoading && !error && (
          <div className="flex items-center justify-center h-96">
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
