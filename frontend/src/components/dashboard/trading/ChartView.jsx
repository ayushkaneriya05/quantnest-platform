import React, { useEffect, useRef, useState, useCallback } from "react";
import { TrendingUp, Volume2, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import TimeframeSelector from "./TimeframeSelector";
import { useWebSocketContext } from "@/contexts/websocket-context";
import api from "@/services/api";

const TIMEFRAMES = [
  { label: '1m', value: '1m' },
  { label: '5m', value: '5m' },
  { label: '15m', value: '15m' },
  { label: '1h', value: '1h' },
  { label: '4h', value: '4h' },
  { label: '1D', value: '1D' },
];

export default function ChartView({ symbol = "RELIANCE" }) {
  const [timeframe, setTimeframe] = useState('5m');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastPrice, setLastPrice] = useState(2458.50);
  const [priceChange, setPriceChange] = useState({ change: 12.50, percentage: 0.51 });
  const [volume24h, setVolume24h] = useState(1250000);

  const { 
    isConnected, 
    subscribe, 
    unsubscribe, 
    getLatestPrice,
    useMockData
  } = useWebSocketContext();

  // Load historical data
  const loadHistoricalData = useCallback(async (symbolToLoad, timeframeToLoad) => {
    if (!symbolToLoad) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get('/api/v1/market/historical/', {
        params: {
          symbol: symbolToLoad,
          timeframe: timeframeToLoad,
          limit: 100,
        },
      });

      // Simulate successful data load
      setTimeout(() => {
        setIsLoading(false);
      }, 1000);

    } catch (err) {
      console.error('Failed to load historical data:', err);
      setError('Chart data temporarily unavailable');
      setIsLoading(false);
    }
  }, []);

  // Handle live tick data updates
  useEffect(() => {
    if (!symbol) return;

    const handleTickUpdate = (tickData) => {
      if (tickData.symbol === symbol && tickData.ltp) {
        setLastPrice(tickData.ltp);
        
        // Update price change
        const change = tickData.ltp - 2458.00; // Mock base price
        const percentage = (change / 2458.00) * 100;
        setPriceChange({ change, percentage });
      }
    };

    const unsubscribeFunc = subscribe(symbol, handleTickUpdate);
    
    return () => {
      if (unsubscribeFunc) unsubscribeFunc();
    };
  }, [symbol, subscribe]);

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
    <Card className="w-full bg-gray-800/50 border-gray-700/50">
      <CardHeader className="pb-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex items-center gap-4">
            <CardTitle className="text-xl font-bold text-white">
              {symbol}
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
      </CardHeader>

      <CardContent className="p-0">
        <div className="relative">
          {isLoading && (
            <div className="absolute inset-0 bg-gray-900/80 flex items-center justify-center z-10">
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

          {/* Simple Chart Placeholder */}
          <div className="w-full h-[400px] bg-gray-900 flex items-center justify-center">
            <div className="text-center p-8">
              <div className="mb-6">
                <div className="w-16 h-16 bg-emerald-400/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <TrendingUp className="h-8 w-8 text-emerald-400" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">{symbol}</h3>
                <div className="text-2xl font-mono text-white mb-2">
                  {formatPrice(lastPrice)}
                </div>
                <div className={`text-lg ${priceChange.change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {priceChange.change >= 0 ? '+' : ''}{priceChange.change.toFixed(2)} 
                  ({priceChange.percentage.toFixed(2)}%)
                </div>
              </div>
              <div className="text-gray-400 text-sm">
                <p>Chart visualization for {timeframe} timeframe</p>
                <p>Live price updates {isConnected ? 'active' : 'simulated'}</p>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
