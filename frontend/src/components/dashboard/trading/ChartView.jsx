import React, { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { createChart, ColorType, CrosshairMode } from "lightweight-charts";
import { Calendar, TrendingUp, Volume2, Activity, AlertCircle, Wifi, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import TimeframeSelector from "./TimeframeSelector";
import WebSocketStatus from "./WebSocketStatus";
import { useWebSocketContext } from "@/contexts/websocket-context";
import api from "@/services/api";
import toast from "react-hot-toast";

const CHART_CONFIG = {
  layout: {
    background: { type: ColorType.Solid, color: '#0f172a' },
    textColor: '#94a3b8',
    fontSize: 12,
    fontFamily: 'Inter, sans-serif',
  },
  grid: {
    vertLines: { color: '#1e293b', style: 0, visible: true },
    horzLines: { color: '#1e293b', style: 0, visible: true },
  },
  crosshair: {
    mode: CrosshairMode.Normal,
    vertLine: {
      color: '#64748b',
      width: 1,
      style: 2,
      visible: true,
      labelVisible: true,
    },
    horzLine: {
      color: '#64748b',
      width: 1,
      style: 2,
      visible: true,
      labelVisible: true,
    },
  },
  timeScale: {
    borderColor: '#334155',
    timeVisible: true,
    secondsVisible: false,
  },
  rightPriceScale: {
    borderColor: '#334155',
    scaleMargins: { top: 0.1, bottom: 0.1 },
  },
};

const TIMEFRAMES = [
  { label: '1m', value: '1m', interval: 60 },
  { label: '5m', value: '5m', interval: 300 },
  { label: '15m', value: '15m', interval: 900 },
  { label: '1h', value: '1h', interval: 3600 },
  { label: '4h', value: '4h', interval: 14400 },
  { label: '1D', value: '1D', interval: 86400 },
];

export default function ChartView({ symbol = "RELIANCE" }) {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candlestickSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const resizeObserverRef = useRef(null);

  const [timeframe, setTimeframe] = useState('5m');
  const [isLoading, setIsLoading] = useState(true);
  const [historicalData, setHistoricalData] = useState([]);
  const [error, setError] = useState(null);
  const [lastPrice, setLastPrice] = useState(null);
  const [priceChange, setPriceChange] = useState({ change: 0, percentage: 0 });
  const [volume24h, setVolume24h] = useState(0);

  const { 
    isConnected, 
    subscribe, 
    unsubscribe, 
    getTickData, 
    connectionStatus,
    useMockData
  } = useWebSocketContext();

  // Memoized chart data processing
  const processedChartData = useMemo(() => {
    if (!historicalData.length) return { candleData: [], volumeData: [] };

    const candleData = historicalData.map(item => ({
      time: item.timestamp,
      open: parseFloat(item.open),
      high: parseFloat(item.high),
      low: parseFloat(item.low),
      close: parseFloat(item.close),
    }));

    const volumeData = historicalData.map(item => ({
      time: item.timestamp,
      value: parseFloat(item.volume || 0),
      color: parseFloat(item.close) >= parseFloat(item.open) ? '#10b981' : '#ef4444',
    }));

    return { candleData, volumeData };
  }, [historicalData]);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      ...CHART_CONFIG,
      width: chartContainerRef.current.clientWidth,
      height: 500,
    });

    chartRef.current = chart;

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    candlestickSeriesRef.current = candlestickSeries;

    // Add volume series
    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    });

    chart.priceScale('').applyOptions({
      scaleMargins: { top: 0.7, bottom: 0 },
    });

    volumeSeriesRef.current = volumeSeries;

    // Handle resize
    resizeObserverRef.current = new ResizeObserver(() => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    });

    resizeObserverRef.current.observe(chartContainerRef.current);

    return () => {
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
      }
      if (chartRef.current) {
        chartRef.current.remove();
      }
    };
  }, []);

  // Load historical data
  const loadHistoricalData = useCallback(async (symbolToLoad, timeframeToLoad) => {
    if (!symbolToLoad) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get('/marketdata/historical/', {
        params: {
          symbol: symbolToLoad,
          timeframe: timeframeToLoad,
          limit: 500,
        },
      });

      if (response.data && Array.isArray(response.data)) {
        setHistoricalData(response.data);
        
        // Calculate 24h volume
        const totalVolume = response.data.reduce((sum, item) => sum + parseFloat(item.volume || 0), 0);
        setVolume24h(totalVolume);
      } else {
        throw new Error('Invalid data format received');
      }
    } catch (err) {
      console.error('Failed to load historical data:', err);
      setError('Failed to load chart data. Please try again.');
      
      // Don't show error toast for demo mode
      if (!useMockData) {
        toast.error('Failed to load chart data');
      }
    } finally {
      setIsLoading(false);
    }
  }, [useMockData]);

  // Update chart data when processed data changes
  useEffect(() => {
    if (!candlestickSeriesRef.current || !volumeSeriesRef.current) return;

    const { candleData, volumeData } = processedChartData;

    if (candleData.length > 0) {
      candlestickSeriesRef.current.setData(candleData);
      volumeSeriesRef.current.setData(volumeData);
      
      // Set last price and calculate change
      const lastCandle = candleData[candleData.length - 1];
      const firstCandle = candleData[0];
      
      if (lastCandle && firstCandle) {
        setLastPrice(lastCandle.close);
        const change = lastCandle.close - firstCandle.open;
        const percentage = ((change / firstCandle.open) * 100);
        setPriceChange({ change, percentage });
      }
    }
  }, [processedChartData]);

  // Handle live tick data updates
  useEffect(() => {
    if (!symbol) return;

    const handleTickUpdate = (tickData) => {
      if (tickData.symbol === symbol && tickData.ltp) {
        const currentTime = Math.floor(Date.now() / 1000);
        const timeframeInterval = TIMEFRAMES.find(tf => tf.value === timeframe)?.interval || 300;
        
        // Round down to nearest timeframe interval
        const roundedTime = Math.floor(currentTime / timeframeInterval) * timeframeInterval;
        
        // Update the last candle or create a new one
        if (candlestickSeriesRef.current) {
          const lastCandle = historicalData[historicalData.length - 1];
          
          if (lastCandle && lastCandle.timestamp === roundedTime) {
            // Update existing candle
            const updatedCandle = {
              time: roundedTime,
              open: parseFloat(lastCandle.open),
              high: Math.max(parseFloat(lastCandle.high), tickData.ltp),
              low: Math.min(parseFloat(lastCandle.low), tickData.ltp),
              close: tickData.ltp,
            };
            
            candlestickSeriesRef.current.update(updatedCandle);
          } else {
            // Create new candle
            const newCandle = {
              time: roundedTime,
              open: tickData.ltp,
              high: tickData.ltp,
              low: tickData.ltp,
              close: tickData.ltp,
            };
            
            candlestickSeriesRef.current.update(newCandle);
          }
        }
        
        setLastPrice(tickData.ltp);
      }
    };

    const unsubscribeFunc = subscribe(symbol, handleTickUpdate);
    
    return () => {
      if (unsubscribeFunc) unsubscribeFunc();
    };
  }, [symbol, subscribe, timeframe, historicalData]);

  // Load data when symbol or timeframe changes
  useEffect(() => {
    loadHistoricalData(symbol, timeframe);
  }, [symbol, timeframe, loadHistoricalData]);

  const handleTimeframeChange = (newTimeframe) => {
    setTimeframe(newTimeframe);
  };

  const formatPrice = (price) => {
    return price ? `₹${price.toFixed(2)}` : '₹0.00';
  };

  const formatVolume = (volume) => {
    if (volume >= 1e7) return `${(volume / 1e7).toFixed(1)}Cr`;
    if (volume >= 1e5) return `${(volume / 1e5).toFixed(1)}L`;
    if (volume >= 1e3) return `${(volume / 1e3).toFixed(1)}K`;
    return volume.toString();
  };

  return (
    <Card className="w-full bg-slate-900/50 border-slate-700/50">
      <CardHeader className="pb-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex items-center gap-4">
            <CardTitle className="text-xl font-bold text-white flex items-center gap-2">
              {symbol}
              <WebSocketStatus />
            </CardTitle>
            
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-emerald-400" />
                <span className="text-white font-mono">
                  {formatPrice(lastPrice)}
                </span>
                <span className={`font-medium ${
                  priceChange.change >= 0 ? 'text-emerald-400' : 'text-red-400'
                }`}>
                  {priceChange.change >= 0 ? '+' : ''}{priceChange.change.toFixed(2)} 
                  ({priceChange.percentage.toFixed(2)}%)
                </span>
              </div>
              
              <div className="flex items-center gap-2">
                <Volume2 className="h-4 w-4 text-blue-400" />
                <span className="text-slate-300">
                  {formatVolume(volume24h)}
                </span>
              </div>
            </div>
          </div>

          <TimeframeSelector
            timeframes={TIMEFRAMES}
            selectedTimeframe={timeframe}
            onTimeframeChange={handleTimeframeChange}
          />
        </div>

        {/* Mode indicator */}
        {useMockData && (
          <div className="mt-2">
            <Badge variant="outline" className="text-xs border-yellow-600 text-yellow-400 bg-yellow-500/10">
              <Activity className="h-3 w-3 mr-1" />
              Demo Mode - Simulated Data
            </Badge>
          </div>
        )}
      </CardHeader>

      <CardContent className="p-0">
        <div className="relative">
          {isLoading && (
            <div className="absolute inset-0 bg-slate-900/80 flex items-center justify-center z-10">
              <div className="flex items-center gap-3 text-slate-300">
                <div className="animate-spin h-6 w-6 border-2 border-emerald-400 border-t-transparent rounded-full" />
                <span>Loading chart data...</span>
              </div>
            </div>
          )}

          {error ? (
            <div className="flex items-center justify-center h-96 bg-slate-900/50">
              <div className="text-center">
                <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
                <p className="text-red-400 font-medium mb-2">Failed to load chart</p>
                <p className="text-slate-400 text-sm mb-4">{error}</p>
                <Button 
                  onClick={() => loadHistoricalData(symbol, timeframe)}
                  variant="outline"
                  size="sm"
                >
                  Retry
                </Button>
              </div>
            </div>
          ) : (
            <div 
              ref={chartContainerRef} 
              className="w-full h-[500px] bg-slate-900"
              style={{ minHeight: '500px' }}
            />
          )}
        </div>
      </CardContent>
    </Card>
  );
}
