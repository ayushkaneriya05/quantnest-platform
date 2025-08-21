import React, { useEffect, useRef, useState, useCallback } from "react";
import { TrendingUp, Volume2, AlertCircle, BarChart3, Activity, Eye, Calendar } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

const TradingChart = ({ symbol, timeframe, lastPrice, priceChange, volume24h, isConnected }) => {
  return (
    <div className="w-full h-full min-h-[300px] lg:min-h-[400px] bg-slate-950 relative overflow-hidden">
      {/* Trading Grid Background */}
      <div className="absolute inset-0 opacity-10">
        <div 
          className="w-full h-full"
          style={{
            backgroundImage: `
              linear-gradient(to right, #374151 1px, transparent 1px),
              linear-gradient(to bottom, #374151 1px, transparent 1px)
            `,
            backgroundSize: '40px 20px'
          }}
        />
      </div>

      {/* Price Info Overlay */}
      <div className="absolute top-4 left-4 right-4 z-10">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <div className="text-xl lg:text-2xl font-bold text-white">
              ₹{lastPrice.toFixed(2)}
            </div>
            <div className={`flex items-center gap-1 text-sm lg:text-base ${
              priceChange.change >= 0 ? 'text-emerald-400' : 'text-red-400'
            }`}>
              <TrendingUp className={`h-4 w-4 ${priceChange.change < 0 ? 'rotate-180' : ''}`} />
              {priceChange.change >= 0 ? '+' : ''}{priceChange.change.toFixed(2)} 
              ({priceChange.percentage.toFixed(2)}%)
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs lg:text-sm text-gray-400">
            <div className="flex items-center gap-1">
              <Volume2 className="h-3 w-3 lg:h-4 lg:w-4" />
              <span>{volume24h.toLocaleString()}</span>
            </div>
            <div className="flex items-center gap-1">
              <Eye className="h-3 w-3 lg:h-4 lg:w-4" />
              <span>{timeframe}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Chart Area */}
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4 mt-16">
          {/* Simulated Candlestick Pattern */}
          <div className="flex items-end justify-center gap-1 lg:gap-2 h-32 lg:h-40">
            {[...Array(20)].map((_, i) => {
              const height = Math.random() * 80 + 20;
              const isGreen = Math.random() > 0.5;
              return (
                <div
                  key={i}
                  className={`w-2 lg:w-3 ${
                    isGreen ? 'bg-emerald-500' : 'bg-red-500'
                  } opacity-70 hover:opacity-100 transition-opacity`}
                  style={{ height: `${height}%` }}
                />
              );
            })}
          </div>
          
          <div className="space-y-2">
            <h3 className="text-lg lg:text-xl font-bold text-white">{symbol}</h3>
            <div className="flex items-center justify-center gap-2 text-sm text-gray-400">
              <BarChart3 className="h-4 w-4" />
              <span>Live {timeframe} Chart</span>
              {isConnected && (
                <Badge className="bg-emerald-500/20 text-emerald-400 text-xs">
                  <div className="w-1 h-1 bg-emerald-400 rounded-full mr-1 animate-pulse" />
                  Live
                </Badge>
              )}
            </div>
          </div>

          {/* Trading Indicators */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4 mt-6 text-xs lg:text-sm">
            <div className="text-center p-2 bg-gray-900/50 rounded">
              <div className="text-gray-400">Open</div>
              <div className="text-white font-mono">₹{(lastPrice * 0.998).toFixed(2)}</div>
            </div>
            <div className="text-center p-2 bg-gray-900/50 rounded">
              <div className="text-gray-400">High</div>
              <div className="text-emerald-400 font-mono">₹{(lastPrice * 1.015).toFixed(2)}</div>
            </div>
            <div className="text-center p-2 bg-gray-900/50 rounded">
              <div className="text-gray-400">Low</div>
              <div className="text-red-400 font-mono">₹{(lastPrice * 0.985).toFixed(2)}</div>
            </div>
            <div className="text-center p-2 bg-gray-900/50 rounded">
              <div className="text-gray-400">Volume</div>
              <div className="text-blue-400 font-mono">{(volume24h / 1000).toFixed(0)}K</div>
            </div>
          </div>
        </div>
      </div>

      {/* Time Axis */}
      <div className="absolute bottom-2 left-4 right-4">
        <div className="flex justify-between text-xs text-gray-500">
          <span>09:15</span>
          <span>12:00</span>
          <span>15:30</span>
        </div>
      </div>
    </div>
  );
};

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

  return (
    <Card className="w-full bg-gray-900/50 border-gray-700/50 overflow-hidden">
      <CardHeader className="pb-3 lg:pb-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 lg:gap-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3 lg:gap-4">
            <CardTitle className="text-lg lg:text-xl font-bold text-white flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-blue-400" />
              {symbol}
            </CardTitle>
            
            <div className="flex items-center gap-2 text-xs lg:text-sm">
              {useMockData && (
                <Badge variant="outline" className="border-yellow-600 text-yellow-400 bg-yellow-500/10">
                  <Activity className="h-3 w-3 mr-1" />
                  Demo Data
                </Badge>
              )}
              
              <Badge variant="outline" className="border-gray-600 text-gray-300">
                <Calendar className="h-3 w-3 mr-1" />
                Market Hours
              </Badge>
            </div>
          </div>

          <div className="flex items-center justify-between lg:justify-end gap-3">
            <TimeframeSelector
              timeframes={TIMEFRAMES}
              selectedTimeframe={timeframe}
              onTimeframeChange={handleTimeframeChange}
            />
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <div className="relative w-full">
          {isLoading && (
            <div className="absolute inset-0 bg-gray-900/80 flex items-center justify-center z-10">
              <div className="flex items-center gap-3 text-slate-300">
                <div className="animate-spin h-6 w-6 border-2 border-emerald-400 border-t-transparent rounded-full" />
                <span className="text-sm lg:text-base">Loading chart data...</span>
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

          <div className="aspect-[16/9] lg:aspect-[21/9] max-h-[400px] lg:max-h-[500px] w-full">
            <TradingChart 
              symbol={symbol}
              timeframe={timeframe}
              lastPrice={lastPrice}
              priceChange={priceChange}
              volume24h={volume24h}
              isConnected={isConnected}
            />
          </div>
        </div>
      </CardContent>

      {/* Chart Controls */}
      <div className="border-t border-gray-700/50 p-3 lg:p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs lg:text-sm text-gray-400">
          <div className="flex items-center gap-4">
            <span>Indicators:</span>
            <Button variant="ghost" size="sm" className="h-6 px-2 text-gray-400 hover:text-white">
              RSI
            </Button>
            <Button variant="ghost" size="sm" className="h-6 px-2 text-gray-400 hover:text-white">
              MACD
            </Button>
            <Button variant="ghost" size="sm" className="h-6 px-2 text-gray-400 hover:text-white">
              BB
            </Button>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-xs">Data:</span>
            <span className={`text-xs ${isConnected ? 'text-emerald-400' : 'text-yellow-400'}`}>
              {isConnected ? 'Live' : 'Simulated'}
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}
