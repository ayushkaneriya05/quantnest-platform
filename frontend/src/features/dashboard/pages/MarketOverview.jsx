/**
 * Market Overview Dashboard - market status and key indices
 */
import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { 
  TrendingUp, TrendingDown, Activity, Clock, 
  Globe, BarChart2, Zap
} from 'lucide-react';

// Mock data
const MOCK_INDICES = [
  { name: 'NIFTY 50', value: 22450.50, change: 125.30, changePercent: 0.56 },
  { name: 'BANK NIFTY', value: 47890.25, change: -180.45, changePercent: -0.38 },
  { name: 'SENSEX', value: 73890.15, change: 420.80, changePercent: 0.57 },
  { name: 'NIFTY IT', value: 35420.00, change: 210.50, changePercent: 0.60 },
];

const MOCK_TOP_GAINERS = [
  { symbol: 'TATASTEEL', price: 145.50, change: 8.5 },
  { symbol: 'RELIANCE', price: 2480.00, change: 4.2 },
  { symbol: 'HDFC', price: 1650.00, change: 3.8 },
];

const MOCK_TOP_LOSERS = [
  { symbol: 'ICICIBANK', price: 980.00, change: -3.2 },
  { symbol: 'INFY', price: 1520.00, change: -2.8 },
  { symbol: 'TCS', price: 3850.00, change: -1.5 },
];

const MOCK_MARKET_STATUS = {
  isOpen: true,
  session: 'Regular',
  nextEvent: 'Market Close',
  nextEventTime: '15:30',
};

export default function MarketOverview() {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', { 
      maximumFractionDigits: 2,
      minimumFractionDigits: 2
    }).format(val);
  };

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      {/* Indices */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {MOCK_INDICES.map((index) => (
          <Card key={index.name} className="bg-gray-900/50 border-gray-800">
            <CardContent className="py-4">
              <p className="text-sm text-gray-400">{index.name}</p>
              <p className="text-xl font-bold text-white mt-1">
                {formatCurrency(index.value)}
              </p>
              <div className={`flex items-center gap-1 mt-1 ${
                index.changePercent >= 0 ? 'text-green-400' : 'text-red-400'
              }`}>
                {index.changePercent >= 0 
                  ? <TrendingUp className="h-4 w-4" />
                  : <TrendingDown className="h-4 w-4" />}
                <span className="text-sm font-medium">
                  {index.changePercent >= 0 ? '+' : ''}{index.changePercent.toFixed(2)}%
                </span>
                <span className="text-xs">
                  ({index.change >= 0 ? '+' : ''}{formatCurrency(index.change)})
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Gainers & Losers */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Top Gainers */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-400" />
              Top Gainers
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {MOCK_TOP_GAINERS.map((stock) => (
              <div 
                key={stock.symbol}
                className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg"
              >
                <div>
                  <p className="text-white font-medium">{stock.symbol}</p>
                  <p className="text-sm text-gray-400">₹{formatCurrency(stock.price)}</p>
                </div>
                <Badge className="bg-green-600">+{stock.change}%</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Top Losers */}
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <TrendingDown className="h-5 w-5 text-red-400" />
              Top Losers
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {MOCK_TOP_LOSERS.map((stock) => (
              <div 
                key={stock.symbol}
                className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg"
              >
                <div>
                  <p className="text-white font-medium">{stock.symbol}</p>
                  <p className="text-sm text-gray-400">₹{formatCurrency(stock.price)}</p>
                </div>
                <Badge className="bg-red-600">{stock.change}%</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Market Breadth */}
      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <BarChart2 className="h-5 w-5 text-indigo-400" />
            Market Breadth
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="p-4 bg-green-900/20 rounded-lg">
              <p className="text-3xl font-bold text-green-400">1,245</p>
              <p className="text-sm text-gray-400">Advances</p>
            </div>
            <div className="p-4 bg-red-900/20 rounded-lg">
              <p className="text-3xl font-bold text-red-400">856</p>
              <p className="text-sm text-gray-400">Declines</p>
            </div>
            <div className="p-4 bg-gray-800/50 rounded-lg">
              <p className="text-3xl font-bold text-gray-300">124</p>
              <p className="text-sm text-gray-400">Unchanged</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
