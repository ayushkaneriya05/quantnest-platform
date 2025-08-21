import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../ui/tabs';
import { TrendingUp, TrendingDown, BarChart3, Activity, AlertCircle, Loader2 } from 'lucide-react';
import { 
  createChart, 
  ColorType, 
  CrosshairMode, 
  CandlestickSeries, 
  LineSeries, 
  HistogramSeries 
} from 'lightweight-charts';
import { useApi } from '../../../hooks/use-api';
import { useWebSocket } from '../../../contexts/websocket-context';
import { toast } from 'react-hot-toast';
import { cn } from '../../../lib/utils';

const TIMEFRAMES = [
  { value: '1m', label: '1M', interval: 60000 },
  { value: '5m', label: '5M', interval: 300000 },
  { value: '15m', label: '15M', interval: 900000 },
  { value: '1h', label: '1H', interval: 3600000 },
  { value: '1D', label: '1D', interval: 86400000 },
  { value: '1W', label: '1W', interval: 604800000 }
];

const CHART_TYPES = [
  { value: 'candles', label: 'Candlesticks', icon: BarChart3 },
  { value: 'line', label: 'Line', icon: Activity }
];

const ChartView = ({
  instrument,
  symbol, // Support legacy symbol prop
  className,
  height = 400,
  showControls = true,
  defaultTimeframe = '1D',
  defaultChartType = 'candles'
}) => {
  const [selectedTimeframe, setSelectedTimeframe] = useState(defaultTimeframe);
  const [selectedChartType, setSelectedChartType] = useState(defaultChartType);
  const [chartData, setChartData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastPrice, setLastPrice] = useState(null);
  const [priceChange, setPriceChange] = useState(null);
  const [volume, setVolume] = useState(null);
  
  const chartContainerRef = useRef();
  const chartRef = useRef();
  const candlestickSeriesRef = useRef();
  const lineSeriesRef = useRef();
  const volumeSeriesRef = useRef();
  const wsUnsubscribeRef = useRef();
  
  const { callApi } = useApi();
  const { marketData, subscribeToInstrument, addMarketDataListener, isConnected } = useWebSocket();

  // Normalize instrument - support both symbol string and instrument object
  const normalizedInstrument = useMemo(() => {
    if (instrument) {
      return instrument;
    } else if (symbol) {
      return {
        symbol: symbol,
        company_name: symbol // Fallback to symbol as company name
      };
    }
    return null;
  }, [instrument, symbol]);

  // Memoized chart options
  const chartOptions = useMemo(() => ({
    layout: {
      textColor: 'rgb(120, 123, 134)',
      background: {
        type: ColorType.Solid,
        color: 'transparent',
      },
    },
    grid: {
      vertLines: {
        color: 'rgba(197, 203, 206, 0.1)',
      },
      horzLines: {
        color: 'rgba(197, 203, 206, 0.1)',
      },
    },
    crosshair: {
      mode: CrosshairMode.Normal,
    },
    rightPriceScale: {
      borderColor: 'rgba(197, 203, 206, 0.2)',
    },
    timeScale: {
      borderColor: 'rgba(197, 203, 206, 0.2)',
      timeVisible: true,
      secondsVisible: false,
    },
    handleScroll: {
      mouseWheel: true,
      pressedMouseMove: true,
    },
    handleScale: {
      axisPressedMouseMove: true,
      mouseWheel: true,
      pinch: true,
    },
  }), []);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    try {
      const chart = createChart(chartContainerRef.current, {
        ...chartOptions,
        width: chartContainerRef.current.clientWidth,
        height: height,
      });

      chartRef.current = chart;

      // Add candlestick series using v5 API
      const candlestickSeries = chart.addSeries(CandlestickSeries, {
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
      });
      candlestickSeriesRef.current = candlestickSeries;

      // Add line series (initially hidden) using v5 API
      const lineSeries = chart.addSeries(LineSeries, {
        color: '#2962FF',
        lineWidth: 2,
        visible: false,
      });
      lineSeriesRef.current = lineSeries;

      // Add volume series using v5 API
      const volumeSeries = chart.addSeries(HistogramSeries, {
        color: '#26a69a',
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: '',
        scaleMargins: {
          top: 0.8,
          bottom: 0,
        },
      });
      volumeSeriesRef.current = volumeSeries;

      // Handle resize
      const handleResize = () => {
        if (chartContainerRef.current && chartRef.current) {
          chartRef.current.applyOptions({
            width: chartContainerRef.current.clientWidth,
          });
        }
      };

      window.addEventListener('resize', handleResize);

      return () => {
        window.removeEventListener('resize', handleResize);
        if (chartRef.current) {
          chartRef.current.remove();
        }
      };
    } catch (error) {
      console.error('Error initializing chart:', error);
      setError('Failed to initialize chart');
    }
  }, [chartOptions, height]);

  // Generate mock data for development
  const generateMockData = useCallback((symbol, timeframe) => {
    const now = Math.floor(Date.now() / 1000);
    const data = [];
    let basePrice = 2500; // Base price for mock data

    // Adjust intervals based on timeframe
    const intervals = {
      '1m': { count: 100, step: 60 },
      '5m': { count: 100, step: 300 },
      '15m': { count: 100, step: 900 },
      '1h': { count: 100, step: 3600 },
      '1D': { count: 30, step: 86400 },
      '1W': { count: 20, step: 604800 }
    };

    const { count, step } = intervals[timeframe] || intervals['1D'];

    for (let i = count; i >= 0; i--) {
      const time = now - (i * step);
      const volatility = 0.02; // 2% volatility
      const change = (Math.random() - 0.5) * volatility;

      const open = basePrice;
      const close = basePrice * (1 + change);
      const high = Math.max(open, close) * (1 + Math.random() * 0.01);
      const low = Math.min(open, close) * (1 - Math.random() * 0.01);
      const volume = Math.floor(Math.random() * 1000000) + 100000;

      data.push({
        time,
        open: parseFloat(open.toFixed(2)),
        high: parseFloat(high.toFixed(2)),
        low: parseFloat(low.toFixed(2)),
        close: parseFloat(close.toFixed(2)),
        volume
      });

      basePrice = close; // Next candle starts where this one ended
    }

    return data;
  }, []);

  // Fetch historical data
  const fetchHistoricalData = useCallback(async () => {
    if (!normalizedInstrument?.symbol) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await callApi(
        `/api/v1/market/historical/?instrument=${encodeURIComponent(normalizedInstrument.symbol)}&resolution=${selectedTimeframe}`,
        'GET'
      );

      if (response.success) {
        const data = response.data?.data || [];
        
        // Transform data for the chart
        const transformedData = data.map(candle => ({
          time: candle.time / 1000, // Convert to seconds
          open: parseFloat(candle.open),
          high: parseFloat(candle.high),
          low: parseFloat(candle.low),
          close: parseFloat(candle.close),
          volume: parseInt(candle.volume || 0)
        })).sort((a, b) => a.time - b.time);

        setChartData(transformedData);
        updateChart(transformedData);

        // Set initial price info
        if (transformedData.length > 0) {
          const latest = transformedData[transformedData.length - 1];
          const previous = transformedData[transformedData.length - 2];
          
          setLastPrice(latest.close);
          setVolume(latest.volume);
          
          if (previous) {
            const change = latest.close - previous.close;
            const changePercent = (change / previous.close) * 100;
            setPriceChange({
              change: change.toFixed(2),
              changePercent: changePercent.toFixed(2),
              isPositive: change >= 0
            });
          }
        }
      } else {
        throw new Error(response.error || 'Failed to fetch historical data');
      }
    } catch (error) {
      console.error('Error fetching historical data:', error);

      // Handle specific API errors
      let errorMessage = 'Failed to load chart data';
      if (error.message?.includes('Network Error') || error.code === 'ECONNREFUSED') {
        errorMessage = 'Backend server is not running. Please start the Django backend on port 8000.';
      } else if (error.response?.status === 404) {
        errorMessage = 'Chart data endpoint not found. Check API configuration.';
      } else {
        errorMessage = error.message || 'Failed to load chart data';
      }

      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [normalizedInstrument?.symbol, selectedTimeframe, callApi]);

  // Update chart with data
  const updateChart = useCallback((data) => {
    if (!chartRef.current || !data.length) return;

    try {
      if (selectedChartType === 'candles') {
        // Show candlestick series, hide line series
        candlestickSeriesRef.current?.applyOptions({ visible: true });
        lineSeriesRef.current?.applyOptions({ visible: false });
        
        candlestickSeriesRef.current?.setData(data);
        
        // Update volume data
        const volumeData = data.map(candle => ({
          time: candle.time,
          value: candle.volume,
          color: candle.close >= candle.open ? '#26a69a40' : '#ef535040'
        }));
        volumeSeriesRef.current?.setData(volumeData);
      } else {
        // Show line series, hide candlestick series
        candlestickSeriesRef.current?.applyOptions({ visible: false });
        lineSeriesRef.current?.applyOptions({ visible: true });
        
        const lineData = data.map(candle => ({
          time: candle.time,
          value: candle.close
        }));
        lineSeriesRef.current?.setData(lineData);
        
        // Update volume data
        const volumeData = data.map(candle => ({
          time: candle.time,
          value: candle.volume,
          color: '#26a69a40'
        }));
        volumeSeriesRef.current?.setData(volumeData);
      }

      // Fit content
      chartRef.current.timeScale().fitContent();
    } catch (error) {
      console.error('Error updating chart:', error);
    }
  }, [selectedChartType]);

  // Handle live data updates
  useEffect(() => {
    if (!normalizedInstrument?.symbol || !isConnected) return;

    // Subscribe to live data
    subscribeToInstrument(normalizedInstrument.symbol);

    // Add market data listener
    const unsubscribe = addMarketDataListener(normalizedInstrument.symbol, (data) => {
      if (!data || !chartRef.current) return;

      try {
        const newCandle = {
          time: Math.floor(new Date().getTime() / 1000),
          open: parseFloat(data.open),
          high: parseFloat(data.high),
          low: parseFloat(data.low),
          close: parseFloat(data.close),
          volume: parseInt(data.volume || 0)
        };

        // Update last price and calculate change
        setLastPrice(newCandle.close);
        setVolume(newCandle.volume);

        if (chartData.length > 0) {
          const previousClose = chartData[0]?.close || newCandle.open;
          const change = newCandle.close - previousClose;
          const changePercent = (change / previousClose) * 100;
          
          setPriceChange({
            change: change.toFixed(2),
            changePercent: changePercent.toFixed(2),
            isPositive: change >= 0
          });
        }

        // Update chart with new data point
        if (selectedChartType === 'candles') {
          candlestickSeriesRef.current?.update(newCandle);
        } else {
          lineSeriesRef.current?.update({
            time: newCandle.time,
            value: newCandle.close
          });
        }

        // Update volume
        volumeSeriesRef.current?.update({
          time: newCandle.time,
          value: newCandle.volume,
          color: newCandle.close >= newCandle.open ? '#26a69a40' : '#ef535040'
        });

      } catch (error) {
        console.error('Error processing live data:', error);
      }
    });

    wsUnsubscribeRef.current = unsubscribe;

    return () => {
      if (wsUnsubscribeRef.current) {
        wsUnsubscribeRef.current();
      }
    };
  }, [normalizedInstrument?.symbol, isConnected, subscribeToInstrument, addMarketDataListener, chartData, selectedChartType]);

  // Fetch data when instrument or timeframe changes
  useEffect(() => {
    fetchHistoricalData();
  }, [fetchHistoricalData]);

  // Update chart when chart type changes
  useEffect(() => {
    if (chartData.length > 0) {
      updateChart(chartData);
    }
  }, [selectedChartType, updateChart, chartData]);

  const formatPrice = (price) => {
    return price ? `₹${parseFloat(price).toFixed(2)}` : '--';
  };

  const formatVolume = (vol) => {
    if (!vol) return '--';
    if (vol >= 10000000) return `${(vol / 10000000).toFixed(1)}Cr`;
    if (vol >= 100000) return `${(vol / 100000).toFixed(1)}L`;
    if (vol >= 1000) return `${(vol / 1000).toFixed(1)}K`;
    return vol.toString();
  };

  return (
    <Card className={cn("w-full", className)}>
      {showControls && (
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <CardTitle className="text-lg">
                {normalizedInstrument?.symbol || 'Select Instrument'}
              </CardTitle>
              {normalizedInstrument?.company_name && normalizedInstrument.company_name !== normalizedInstrument.symbol && (
                <span className="text-sm text-muted-foreground">
                  {normalizedInstrument.company_name}
                </span>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              <Select value={selectedChartType} onValueChange={setSelectedChartType}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CHART_TYPES.map(type => {
                    const Icon = type.icon;
                    return (
                      <SelectItem key={type.value} value={type.value}>
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
          </div>

          {/* Price Information */}
          {lastPrice && (
            <div className="flex items-center gap-6 mt-2">
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold">
                  {formatPrice(lastPrice)}
                </span>
                {priceChange && (
                  <div className={cn(
                    "flex items-center gap-1",
                    priceChange.isPositive ? "text-green-600" : "text-red-600"
                  )}>
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
              
              {volume && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>Vol:</span>
                  <span className="font-medium">{formatVolume(volume)}</span>
                </div>
              )}
              
              <div className="flex items-center gap-1">
                <div className={cn(
                  "h-2 w-2 rounded-full",
                  isConnected ? "bg-green-500" : "bg-red-500"
                )} />
                <span className="text-xs text-muted-foreground">
                  {isConnected ? "Live" : "Offline"}
                </span>
              </div>
            </div>
          )}

          {/* Timeframe Selection */}
          <Tabs value={selectedTimeframe} onValueChange={setSelectedTimeframe} className="mt-4">
            <TabsList className="grid grid-cols-6 w-fit">
              {TIMEFRAMES.map(timeframe => (
                <TabsTrigger 
                  key={timeframe.value} 
                  value={timeframe.value}
                  className="text-xs px-3"
                >
                  {timeframe.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </CardHeader>
      )}

      <CardContent className={cn("p-0", showControls && "px-6 pb-6")}>
        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center h-96">
            <div className="flex items-center gap-2">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span>Loading chart data...</span>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground mb-2">{error}</p>
              <Button onClick={fetchHistoricalData} variant="outline" size="sm">
                Retry
              </Button>
            </div>
          </div>
        )}

        {/* Chart Container */}
        {!isLoading && !error && (
          <div
            ref={chartContainerRef}
            className="w-full"
            style={{ height: `${height}px` }}
          />
        )}

        {/* No Instrument Selected */}
        {!normalizedInstrument && !isLoading && !error && (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">
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
