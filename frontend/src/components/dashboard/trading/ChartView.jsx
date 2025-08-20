import React, { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { TrendingUp, Volume2, Activity, AlertCircle, Wifi, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import TimeframeSelector from "./TimeframeSelector";
import WebSocketStatus from "./WebSocketStatus";
import { useWebSocketContext } from "@/contexts/websocket-context";
import api from "@/services/api";
import toast from "react-hot-toast";

// Import lightweight-charts properly
let createChart, ColorType, CrosshairMode;

const initializeChart = async () => {
  try {
    const lightweightCharts = await import('lightweight-charts');
    createChart = lightweightCharts.createChart;
    ColorType = lightweightCharts.ColorType;
    CrosshairMode = lightweightCharts.CrosshairMode;
    return true;
  } catch (error) {
    console.error('Failed to load lightweight-charts:', error);
    return false;
  }
};

const CHART_CONFIG = {
  layout: {
    background: { type: 'solid', color: '#0f172a' },
    textColor: '#94a3b8',
    fontSize: 12,
    fontFamily: 'Inter, sans-serif',
  },
  grid: {
    vertLines: { color: '#1e293b', style: 0, visible: true },
    horzLines: { color: '#1e293b', style: 0, visible: true },
  },
  crosshair: {
    mode: 0, // Normal mode
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

// Simple fallback chart component
const FallbackChart = ({ symbol, lastPrice, priceChange }) => (
  <div className="w-full h-[500px] bg-slate-900 flex items-center justify-center">
    <div className="text-center p-8">
      <div className="mb-6">
        <Activity className="h-16 w-16 text-blue-400 mx-auto mb-4" />
        <h3 className="text-xl font-bold text-white mb-2">{symbol}</h3>
        {lastPrice && (
          <div className="text-2xl font-mono text-white mb-2">
            ₹{lastPrice.toFixed(2)}
          </div>
        )}
        {priceChange && (
          <div className={`text-lg ${priceChange.change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {priceChange.change >= 0 ? '+' : ''}{priceChange.change.toFixed(2)} 
            ({priceChange.percentage.toFixed(2)}%)
          </div>
        )}
      </div>
      <div className="text-gray-400 text-sm">
        <p>Chart visualization unavailable</p>
        <p>Price data is still updating</p>
      </div>
    </div>
  </div>
);

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
  const [chartInitialized, setChartInitialized] = useState(false);
  const [chartLibraryLoaded, setChartLibraryLoaded] = useState(false);

  const { 
    isConnected, 
    subscribe, 
    unsubscribe, 
    getTickData, 
    connectionStatus,
    useMockData
  } = useWebSocketContext();

  // Initialize chart library
  useEffect(() => {
    initializeChart().then(success => {
      setChartLibraryLoaded(success);
      if (!success) {
        console.warn('Falling back to simple chart display');
      }
    });
  }, []);

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
    if (!chartContainerRef.current || !chartLibraryLoaded || !createChart) {
      return;
    }

    try {
      // Set chart config with proper ColorType handling
      const config = {
        ...CHART_CONFIG,
        width: chartContainerRef.current.clientWidth,
        height: 500,
      };
      
      // Handle ColorType if available
      if (ColorType) {
        config.layout.background = { type: ColorType.Solid, color: '#0f172a' };
      }
      
      // Handle CrosshairMode if available
      if (CrosshairMode) {
        config.crosshair.mode = CrosshairMode.Normal;
      }

      const chart = createChart(chartContainerRef.current, config);
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
      setChartInitialized(true);

    } catch (error) {
      console.error('Error initializing chart:', error);
      setChartInitialized(false);
    }

    return () => {
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
      }
      if (chartRef.current) {
        try {
          chartRef.current.remove();
        } catch (error) {
          console.error('Error removing chart:', error);
        }
      }
      setChartInitialized(false);
    };
  }, [chartLibraryLoaded]);

  // Load historical data with better error handling
  const loadHistoricalData = useCallback(async (symbolToLoad, timeframeToLoad) => {
    if (!symbolToLoad) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get('/api/v1/marketdata/historical/', {
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
      
      // Generate mock data for demo purposes
      console.log('Generating mock historical data for demo');
      const mockData = generateMockHistoricalData(symbolToLoad, timeframeToLoad, 100);
      setHistoricalData(mockData);
      
      const totalVolume = mockData.reduce((sum, item) => sum + parseFloat(item.volume || 0), 0);
      setVolume24h(totalVolume);
      
      if (!useMockData) {
        setError('Using simulated data - backend unavailable');
        toast.error('Using demo data - backend connection failed', { duration: 3000 });
      }
    } finally {
      setIsLoading(false);
    }
  }, [useMockData]);

  // Generate mock historical data
  const generateMockHistoricalData = (symbol, timeframe, limit) => {
    const basePrices = {
      'RELIANCE': 2450.0,
      'TCS': 3200.0,
      'INFY': 1450.0,
      'HDFCBANK': 1650.0,
      'ICICIBANK': 920.0,
    };

    const basePrice = basePrices[symbol] || 2000;
    const data = [];
    let currentPrice = basePrice;
    const now = Math.floor(Date.now() / 1000);

    for (let i = limit - 1; i >= 0; i--) {
      const timestamp = now - (i * 300); // 5 minute intervals
      
      // Generate realistic price movement
      const volatility = 0.02;
      const change = (Math.random() - 0.5) * volatility;
      currentPrice *= (1 + change);
      
      const high = currentPrice * (1 + Math.random() * 0.01);
      const low = currentPrice * (1 - Math.random() * 0.01);
      const open = currentPrice * (1 + (Math.random() - 0.5) * 0.005);
      
      data.push({
        timestamp,
        open: open.toFixed(2),
        high: Math.max(high, open, currentPrice).toFixed(2),
        low: Math.min(low, open, currentPrice).toFixed(2),
        close: currentPrice.toFixed(2),
        volume: Math.floor(Math.random() * 100000) + 50000,
        symbol
      });
    }

    return data;
  };

  // Update chart data when processed data changes
  useEffect(() => {
    if (!chartInitialized || !candlestickSeriesRef.current || !volumeSeriesRef.current) return;

    const { candleData, volumeData } = processedChartData;

    if (candleData.length > 0) {
      try {
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
      } catch (error) {
        console.error('Error updating chart data:', error);
      }
    }
  }, [processedChartData, chartInitialized]);

  // Handle live tick data updates
  useEffect(() => {
    if (!symbol) return;

    const handleTickUpdate = (tickData) => {
      if (tickData.symbol === symbol && tickData.ltp) {
        setLastPrice(tickData.ltp);
        
        // Update chart if available
        if (chartInitialized && candlestickSeriesRef.current) {
          try {
            const currentTime = Math.floor(Date.now() / 1000);
            const timeframeInterval = TIMEFRAMES.find(tf => tf.value === timeframe)?.interval || 300;
            const roundedTime = Math.floor(currentTime / timeframeInterval) * timeframeInterval;
            
            const newCandle = {
              time: roundedTime,
              open: tickData.ltp,
              high: tickData.ltp,
              low: tickData.ltp,
              close: tickData.ltp,
            };
            
            candlestickSeriesRef.current.update(newCandle);
          } catch (error) {
            console.error('Error updating live data:', error);
          }
        }
      }
    };

    const unsubscribeFunc = subscribe(symbol, handleTickUpdate);
    
    return () => {
      if (unsubscribeFunc) unsubscribeFunc();
    };
  }, [symbol, subscribe, timeframe, chartInitialized]);

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

        {/* Mode indicators */}
        <div className="flex gap-2 mt-2">
          {useMockData && (
            <Badge variant="outline" className="text-xs border-yellow-600 text-yellow-400 bg-yellow-500/10">
              <Activity className="h-3 w-3 mr-1" />
              Demo Mode
            </Badge>
          )}
          {!chartLibraryLoaded && (
            <Badge variant="outline" className="text-xs border-orange-600 text-orange-400 bg-orange-500/10">
              <AlertCircle className="h-3 w-3 mr-1" />
              Simple Chart Mode
            </Badge>
          )}
        </div>
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

          {error && (
            <div className="bg-yellow-900/20 border-l-4 border-yellow-400 p-3 mb-4 mx-4">
              <div className="flex items-center gap-2 text-yellow-300 text-sm">
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
            </div>
          )}

          {!chartLibraryLoaded || !chartInitialized ? (
            <FallbackChart 
              symbol={symbol} 
              lastPrice={lastPrice} 
              priceChange={priceChange} 
            />
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
