import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  Search, 
  Plus, 
  Minus, 
  TrendingUp, 
  TrendingDown,
  X,
  BarChart3,
  DollarSign,
  Activity,
  Zap,
  Target,
  Eye,
  Bell,
  Settings,
  RefreshCw,
  PlayCircle,
  PauseCircle,
  Volume2,
  Wifi,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  Sparkles,
  Monitor,
  CandlestickChart,
  LineChart,
  Maximize2,
  MoreHorizontal,
  Filter,
  Star,
  BookOpen,
  Download,
  Share,
  Calculator,
  AlertCircle,
  CheckCircle,
  History,
  Bookmark,
  MousePointer,
  Crosshair,
  Move,
  RotateCcw,
  Layers,
  TrendingUpIcon,
  Grid,
  Palette,
  Gauge,
  Percent,
  IndianRupee,
  ExternalLink,
  ChevronUp,
  ChevronDown,
  ChevronRight,
  Wallet,
  PieChart,
  BarChart2
} from "lucide-react";
import { usePageTitle } from "@/hooks/use-page-title";

const PaperTrading = () => {
  usePageTitle("Paper Trading");

  const [selectedSymbol, setSelectedSymbol] = useState("RELIANCE");
  const [isOrderModalOpen, setIsOrderModalOpen] = useState(false);
  const [orderType, setOrderType] = useState("buy");
  const [productType, setProductType] = useState("intraday");
  const [executionType, setExecutionType] = useState("market");
  const [quantity, setQuantity] = useState(1);
  const [limitPrice, setLimitPrice] = useState(2456.30);
  const [stopPrice, setStopPrice] = useState(2400.00);
  const [isLiveMode, setIsLiveMode] = useState(true);
  const [marketStatus, setMarketStatus] = useState("OPEN");
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [selectedTimeframe, setSelectedTimeframe] = useState("1D");
  const [chartType, setChartType] = useState("candlestick");
  const [activeTab, setActiveTab] = useState("positions");

  const [watchlist] = useState([
    { 
      symbol: "RELIANCE", 
      ltp: 2456.30, 
      change: -15.20, 
      changePercent: "-0.61%", 
      volume: "1.8M", 
      dayHigh: 2485.60, 
      dayLow: 2441.20,
      marketCap: "16.63L Cr",
      pe: 25.4,
      sector: "Energy"
    },
    { 
      symbol: "TCS", 
      ltp: 3890.45, 
      change: 48.15, 
      changePercent: "+1.25%", 
      volume: "892K", 
      dayHigh: 3910.80, 
      dayLow: 3842.30,
      marketCap: "14.2L Cr",
      pe: 28.7,
      sector: "IT"
    },
    { 
      symbol: "HDFCBANK", 
      ltp: 1520.10, 
      change: 23.05, 
      changePercent: "+1.54%", 
      volume: "1.2M", 
      dayHigh: 1535.75, 
      dayLow: 1497.05,
      marketCap: "11.5L Cr",
      pe: 19.2,
      sector: "Banking"
    },
    { 
      symbol: "INFY", 
      ltp: 1456.75, 
      change: -8.90, 
      changePercent: "-0.61%", 
      volume: "756K", 
      dayHigh: 1475.20, 
      dayLow: 1448.30,
      marketCap: "6.1L Cr",
      pe: 26.1,
      sector: "IT"
    },
    { 
      symbol: "ICICIBANK", 
      ltp: 789.30, 
      change: 12.80, 
      changePercent: "+1.65%", 
      volume: "2.1M", 
      dayHigh: 795.45, 
      dayLow: 776.50,
      marketCap: "5.5L Cr",
      pe: 15.8,
      sector: "Banking"
    },
    { 
      symbol: "WIPRO", 
      ltp: 445.85, 
      change: 7.20, 
      changePercent: "+1.64%", 
      volume: "1.4M", 
      dayHigh: 448.90, 
      dayLow: 438.65,
      marketCap: "2.4L Cr",
      pe: 21.3,
      sector: "IT"
    },
  ]);
  
  const [positions] = useState([
    { 
      symbol: "TCS", 
      qty: 50, 
      side: "BUY",
      avgPrice: 3842.30, 
      ltp: 3890.45, 
      pnl: 2407.50, 
      pnlPercent: "+1.25%", 
      dayPnl: 1250.50,
      marketValue: 194522.50,
      product: "MIS"
    },
    { 
      symbol: "HDFCBANK", 
      qty: 100, 
      side: "BUY",
      avgPrice: 1497.05, 
      ltp: 1520.10, 
      pnl: 2305.00, 
      pnlPercent: "+1.54%", 
      dayPnl: 1845.75,
      marketValue: 152010.00,
      product: "CNC"
    },
    { 
      symbol: "RELIANCE", 
      qty: 25, 
      side: "BUY",
      avgPrice: 2471.50, 
      ltp: 2456.30, 
      pnl: -380.00, 
      pnlPercent: "-0.61%", 
      dayPnl: -180.25,
      marketValue: 61407.50,
      product: "MIS"
    },
  ]);

  const [orders] = useState([
    {
      id: "ORD001",
      symbol: "INFY",
      side: "BUY",
      qty: 75,
      orderType: "LIMIT",
      price: 1450.00,
      status: "PENDING",
      product: "MIS",
      timestamp: "09:32:45",
      validity: "DAY"
    },
    {
      id: "ORD002", 
      symbol: "WIPRO",
      side: "SELL",
      qty: 100,
      orderType: "MARKET",
      price: 445.85,
      status: "EXECUTED",
      product: "CNC",
      timestamp: "09:28:12",
      validity: "DAY"
    },
    {
      id: "ORD003",
      symbol: "ICICIBANK", 
      side: "BUY",
      qty: 150,
      orderType: "SL",
      price: 785.00,
      triggerPrice: 790.00,
      status: "PENDING",
      product: "MIS",
      timestamp: "09:15:30",
      validity: "DAY"
    }
  ]);

  const currentSymbolData = watchlist.find(item => item.symbol === selectedSymbol);
  const currentPrice = currentSymbolData?.ltp || 0;
  
  const estimatedCost = orderType === "buy" 
    ? quantity * (executionType === "market" ? currentPrice : limitPrice)
    : -(quantity * (executionType === "market" ? currentPrice : limitPrice));

  const totalPnL = positions.reduce((sum, pos) => sum + pos.pnl, 0);
  const dayPnL = positions.reduce((sum, pos) => sum + pos.dayPnl, 0);
  const totalMarketValue = positions.reduce((sum, pos) => sum + pos.marketValue, 0);
  const availableBalance = 850000;
  const totalPortfolioValue = availableBalance + totalMarketValue;

  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdate(new Date());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleWatchlistClick = (symbol) => {
    setSelectedSymbol(symbol);
    const item = watchlist.find(w => w.symbol === symbol);
    if (item) {
      setLimitPrice(item.ltp);
    }
  };

  const handlePlaceTrade = () => {
    console.log("Placing trade:", {
      symbol: selectedSymbol,
      orderType,
      productType,
      executionType,
      quantity,
      limitPrice: executionType === "limit" ? limitPrice : currentPrice
    });
    setIsOrderModalOpen(false);
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  const OrderModal = () => (
    <Dialog open={isOrderModalOpen} onOpenChange={setIsOrderModalOpen}>
      <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-qn-light-cyan">
            <Zap className="h-5 w-5" />
            Place Order - {selectedSymbol}
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Current Price Display */}
          <div className="bg-gray-800/50 p-3 rounded-lg border border-gray-700/50">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Current Price</span>
              <div className="text-right">
                <div className="text-lg font-bold text-white">₹{currentPrice.toLocaleString()}</div>
                <div className={`text-sm ${currentSymbolData?.change >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {currentSymbolData?.changePercent}
                </div>
              </div>
            </div>
          </div>

          {/* Order Type */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Transaction Type</Label>
            <div className="grid grid-cols-2 gap-2">
              <Button
                variant={orderType === "buy" ? "default" : "outline"}
                onClick={() => setOrderType("buy")}
                className={`${orderType === "buy" 
                  ? "bg-green-600 hover:bg-green-700 text-white" 
                  : "border-gray-600 text-gray-300 hover:bg-gray-800"}`}
              >
                <ArrowUpRight className="h-4 w-4 mr-2" />
                BUY
              </Button>
              <Button
                variant={orderType === "sell" ? "default" : "outline"}
                onClick={() => setOrderType("sell")}
                className={`${orderType === "sell" 
                  ? "bg-red-600 hover:bg-red-700 text-white" 
                  : "border-gray-600 text-gray-300 hover:bg-gray-800"}`}
              >
                <ArrowDownRight className="h-4 w-4 mr-2" />
                SELL
              </Button>
            </div>
          </div>

          {/* Quantity */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Quantity</Label>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setQuantity(Math.max(1, quantity - 1))}
                className="border-gray-600 text-gray-300 hover:bg-gray-800 h-10 w-10 p-0"
              >
                <Minus className="h-4 w-4" />
              </Button>
              <Input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                className="text-center bg-gray-800 border-gray-600 text-white h-10"
                min="1"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => setQuantity(quantity + 1)}
                className="border-gray-600 text-gray-300 hover:bg-gray-800 h-10 w-10 p-0"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Product Type */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Product</Label>
            <Select value={productType} onValueChange={setProductType}>
              <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-gray-800 border-gray-700">
                <SelectItem value="intraday">Intraday (MIS)</SelectItem>
                <SelectItem value="delivery">Delivery (CNC)</SelectItem>
                <SelectItem value="cover">Cover Order (CO)</SelectItem>
                <SelectItem value="bracket">Bracket Order (BO)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Order Type */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Order Type</Label>
            <Select value={executionType} onValueChange={setExecutionType}>
              <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-gray-800 border-gray-700">
                <SelectItem value="market">Market</SelectItem>
                <SelectItem value="limit">Limit</SelectItem>
                <SelectItem value="sl">Stop Loss</SelectItem>
                <SelectItem value="sl-m">Stop Loss Market</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Price Fields */}
          {executionType === "limit" && (
            <div className="space-y-2">
              <Label className="text-sm font-medium">Limit Price</Label>
              <Input
                type="number"
                value={limitPrice}
                onChange={(e) => setLimitPrice(parseFloat(e.target.value) || 0)}
                className="bg-gray-800 border-gray-600 text-white"
                step="0.05"
              />
            </div>
          )}

          {(executionType === "sl" || executionType === "sl-m") && (
            <div className="space-y-2">
              <Label className="text-sm font-medium">Trigger Price</Label>
              <Input
                type="number"
                value={stopPrice}
                onChange={(e) => setStopPrice(parseFloat(e.target.value) || 0)}
                className="bg-gray-800 border-gray-600 text-white"
                step="0.05"
              />
            </div>
          )}

          {/* Estimated Cost */}
          <div className="bg-gray-800/50 p-3 rounded-lg border border-gray-700/50">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Estimated {orderType === "buy" ? "Cost" : "Credit"}</span>
              <span className={`text-lg font-bold ${orderType === "buy" ? "text-red-400" : "text-green-400"}`}>
                ₹{Math.abs(estimatedCost).toLocaleString()}
              </span>
            </div>
          </div>

          {/* Place Order Button */}
          <Button 
            onClick={handlePlaceTrade}
            className="w-full bg-gradient-to-r from-qn-light-cyan to-blue-400 text-black hover:from-qn-light-cyan/80 hover:to-blue-400/80 font-semibold py-3"
          >
            <Sparkles className="h-4 w-4 mr-2" />
            Place {orderType.toUpperCase()} Order
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );

  return (
    <div className="h-screen bg-gradient-to-br from-slate-950 via-gray-950 to-slate-900 text-white overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-800/50 bg-gray-900/30 backdrop-blur-xl">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-qn-light-cyan to-blue-400 rounded-lg flex items-center justify-center">
                <CandlestickChart className="h-5 w-5 text-black" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Paper Trading Terminal</h1>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full animate-pulse ${marketStatus === 'OPEN' ? 'bg-green-400' : 'bg-red-400'}`}></div>
                  <span className="text-sm font-medium text-green-400">Market {marketStatus}</span>
                  <span className="text-xs text-gray-400">• Last updated: {formatTime(lastUpdate)}</span>
                </div>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <Badge className="bg-green-600/20 text-green-400 border-green-600/30">
              <Activity className="h-3 w-3 mr-1" />
              Live Data
            </Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsLiveMode(!isLiveMode)}
              className="border-qn-light-cyan/30 text-qn-light-cyan hover:bg-qn-light-cyan hover:text-black"
            >
              {isLiveMode ? <PauseCircle className="h-4 w-4 mr-2" /> : <PlayCircle className="h-4 w-4 mr-2" />}
              {isLiveMode ? 'Pause' : 'Resume'}
            </Button>
            <Button variant="outline" size="sm" className="border-gray-600 text-gray-300">
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      <div className="flex h-[calc(100vh-4rem)]">
        {/* Left Sidebar - Watchlist */}
        <div className="w-80 border-r border-gray-800/50 bg-gray-900/20 backdrop-blur-xl flex flex-col">
          <div className="p-4 border-b border-gray-800/50">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-white">Watchlist</h3>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white h-8 w-8 p-0">
                  <RefreshCw className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white h-8 w-8 p-0">
                  <Settings className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search symbols..."
                className="pl-10 bg-gray-800/50 border-gray-700 text-white text-sm"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {watchlist.map((item) => (
              <div
                key={item.symbol}
                onClick={() => handleWatchlistClick(item.symbol)}
                className={`p-4 cursor-pointer hover:bg-gray-800/30 transition-all duration-200 border-b border-gray-800/30 ${
                  selectedSymbol === item.symbol ? "bg-qn-light-cyan/10 border-l-2 border-l-qn-light-cyan" : ""
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white">{item.symbol}</span>
                      <Badge variant="outline" className="text-xs border-gray-600 text-gray-400">
                        {item.sector}
                      </Badge>
                    </div>
                    <div className="text-xs text-gray-400">MCap: {item.marketCap}</div>
                  </div>
                  <Badge 
                    variant={item.change >= 0 ? "default" : "destructive"} 
                    className={`text-xs ${item.change >= 0 ? "bg-green-600/20 text-green-400 border-green-600/30" : "bg-red-600/20 text-red-400 border-red-600/30"}`}
                  >
                    {item.changePercent}
                  </Badge>
                </div>
                
                <div className="flex justify-between items-center mb-2">
                  <span className="text-lg font-bold text-white">₹{item.ltp.toLocaleString()}</span>
                  <span className={`text-sm ${item.change >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {item.change >= 0 ? "+" : ""}₹{item.change}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 text-xs text-gray-400">
                  <div>
                    <span className="block">High</span>
                    <span className="text-white">₹{item.dayHigh}</span>
                  </div>
                  <div>
                    <span className="block">Low</span>
                    <span className="text-white">₹{item.dayLow}</span>
                  </div>
                  <div>
                    <span className="block">Vol</span>
                    <span className="text-white">{item.volume}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="p-4 border-t border-gray-800/50">
            <Dialog open={isOrderModalOpen} onOpenChange={setIsOrderModalOpen}>
              <DialogTrigger asChild>
                <Button className="w-full bg-gradient-to-r from-qn-light-cyan to-blue-400 text-black hover:from-qn-light-cyan/80 hover:to-blue-400/80 font-semibold">
                  <Plus className="h-4 w-4 mr-2" />
                  Place Order
                </Button>
              </DialogTrigger>
            </Dialog>
          </div>
        </div>

        {/* Main Chart Area */}
        <div className="flex-1 flex flex-col">
          {/* Chart Header */}
          <div className="p-4 border-b border-gray-800/50 bg-gray-900/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-3">
                  <span className="text-xl font-bold text-white">{selectedSymbol}</span>
                  <Badge variant="outline" className="border-qn-light-cyan/30 text-qn-light-cyan">
                    ₹{currentPrice?.toLocaleString()}
                  </Badge>
                  <Badge 
                    variant={currentSymbolData?.change >= 0 ? "default" : "destructive"}
                    className={`${currentSymbolData?.change >= 0 ? "bg-green-600/20 text-green-400" : "bg-red-600/20 text-red-400"}`}
                  >
                    {currentSymbolData?.changePercent}
                  </Badge>
                </div>
              </div>

              <div className="flex items-center gap-3">
                {/* Timeframe Selector */}
                <div className="flex gap-1">
                  {["1M", "5M", "15M", "1H", "1D", "1W"].map((tf) => (
                    <Button
                      key={tf}
                      variant={selectedTimeframe === tf ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSelectedTimeframe(tf)}
                      className={`text-xs h-8 ${selectedTimeframe === tf 
                        ? "bg-qn-light-cyan text-black" 
                        : "border-gray-600 text-gray-300"}`}
                    >
                      {tf}
                    </Button>
                  ))}
                </div>

                {/* Chart Tools */}
                <div className="flex gap-1">
                  <Button variant="outline" size="sm" className="border-gray-600 text-gray-300 h-8 w-8 p-0">
                    <MousePointer className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="sm" className="border-gray-600 text-gray-300 h-8 w-8 p-0">
                    <Crosshair className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="sm" className="border-gray-600 text-gray-300 h-8 w-8 p-0">
                    <TrendingUpIcon className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="sm" className="border-gray-600 text-gray-300 h-8 w-8 p-0">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          </div>

          {/* Chart Area */}
          <div className="flex-1 bg-gray-900/20">
            <div className="h-full flex items-center justify-center bg-gradient-to-br from-gray-800/20 to-gray-700/10 border border-gray-600/20">
              <div className="text-center">
                <div className="mb-6">
                  <Monitor className="h-24 w-24 mx-auto mb-4 text-gray-500" />
                  <div className="space-y-2">
                    <p className="text-2xl font-bold text-gray-300">Advanced TradingView Chart</p>
                    <p className="text-gray-400">Professional-grade charting with real-time data</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 bg-gray-800/30 p-6 rounded-xl max-w-2xl">
                  <div className="text-center">
                    <p className="text-xs text-gray-400 mb-1">Open</p>
                    <p className="font-semibold text-white">₹{currentSymbolData?.dayLow}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-gray-400 mb-1">High</p>
                    <p className="font-semibold text-green-400">₹{currentSymbolData?.dayHigh}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-gray-400 mb-1">Low</p>
                    <p className="font-semibold text-red-400">₹{currentSymbolData?.dayLow}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-gray-400 mb-1">Volume</p>
                    <p className="font-semibold text-blue-400">{currentSymbolData?.volume}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Sidebar - Positions & Orders */}
        <div className="w-96 border-l border-gray-800/50 bg-gray-900/20 backdrop-blur-xl flex flex-col">
          {/* Portfolio Summary */}
          <div className="p-4 border-b border-gray-800/50">
            <h3 className="font-medium text-white mb-3">Portfolio Summary</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">Total Value</span>
                <span className="font-semibold text-white">₹{totalPortfolioValue.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">Available Cash</span>
                <span className="font-semibold text-white">₹{availableBalance.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">Today's P&L</span>
                <span className={`font-semibold ${dayPnL >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {dayPnL >= 0 ? "+" : ""}₹{dayPnL.toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">Total P&L</span>
                <span className={`font-semibold ${totalPnL >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {totalPnL >= 0 ? "+" : ""}₹{totalPnL.toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-gray-800/50">
            {[
              { id: "positions", label: "Positions", count: positions.length },
              { id: "orders", label: "Orders", count: orders.length }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? "text-qn-light-cyan border-b-2 border-qn-light-cyan bg-qn-light-cyan/5"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                {tab.label} ({tab.count})
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto">
            {activeTab === "positions" ? (
              <div className="space-y-1">
                {positions.length === 0 ? (
                  <div className="p-6 text-center text-gray-400">
                    <Target className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">No open positions</p>
                  </div>
                ) : (
                  positions.map((position, index) => (
                    <div key={index} className="p-4 border-b border-gray-800/30 hover:bg-gray-800/20 transition-colors">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-white">{position.symbol}</span>
                          <Badge 
                            variant="outline" 
                            className={`text-xs ${position.side === "BUY" ? "border-green-600/30 text-green-400" : "border-red-600/30 text-red-400"}`}
                          >
                            {position.side}
                          </Badge>
                          <Badge variant="outline" className="text-xs border-gray-600 text-gray-400">
                            {position.product}
                          </Badge>
                        </div>
                        <Button variant="ghost" size="sm" className="text-red-400 hover:bg-red-600/10 h-6 w-6 p-0">
                          <X className="h-3 w-3" />
                        </Button>
                      </div>

                      <div className="grid grid-cols-2 gap-3 text-xs mb-3">
                        <div>
                          <span className="text-gray-400 block">Qty</span>
                          <span className="text-white font-medium">{position.qty}</span>
                        </div>
                        <div>
                          <span className="text-gray-400 block">Avg Price</span>
                          <span className="text-white font-medium">₹{position.avgPrice}</span>
                        </div>
                        <div>
                          <span className="text-gray-400 block">LTP</span>
                          <span className="text-white font-medium">₹{position.ltp}</span>
                        </div>
                        <div>
                          <span className="text-gray-400 block">Market Value</span>
                          <span className="text-white font-medium">₹{position.marketValue.toLocaleString()}</span>
                        </div>
                      </div>

                      <div className="flex justify-between items-center">
                        <div>
                          <span className="text-xs text-gray-400">P&L:</span>
                          <div className={`text-sm font-medium ${position.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                            {position.pnl >= 0 ? "+" : ""}₹{position.pnl.toLocaleString()}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`text-xs ${position.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                            {position.pnlPercent}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div className="space-y-1">
                {orders.length === 0 ? (
                  <div className="p-6 text-center text-gray-400">
                    <Clock className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">No pending orders</p>
                  </div>
                ) : (
                  orders.map((order, index) => (
                    <div key={index} className="p-4 border-b border-gray-800/30 hover:bg-gray-800/20 transition-colors">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-white">{order.symbol}</span>
                          <Badge 
                            variant="outline" 
                            className={`text-xs ${order.side === "BUY" ? "border-green-600/30 text-green-400" : "border-red-600/30 text-red-400"}`}
                          >
                            {order.side}
                          </Badge>
                        </div>
                        <Badge 
                          variant="outline" 
                          className={`text-xs ${
                            order.status === "EXECUTED" ? "border-green-600/30 text-green-400" :
                            order.status === "PENDING" ? "border-yellow-600/30 text-yellow-400" :
                            "border-red-600/30 text-red-400"
                          }`}
                        >
                          {order.status}
                        </Badge>
                      </div>

                      <div className="grid grid-cols-2 gap-3 text-xs mb-2">
                        <div>
                          <span className="text-gray-400 block">Qty</span>
                          <span className="text-white font-medium">{order.qty}</span>
                        </div>
                        <div>
                          <span className="text-gray-400 block">Type</span>
                          <span className="text-white font-medium">{order.orderType}</span>
                        </div>
                        <div>
                          <span className="text-gray-400 block">Price</span>
                          <span className="text-white font-medium">₹{order.price}</span>
                        </div>
                        <div>
                          <span className="text-gray-400 block">Time</span>
                          <span className="text-white font-medium">{order.timestamp}</span>
                        </div>
                      </div>

                      {order.status === "PENDING" && (
                        <div className="flex gap-2 mt-3">
                          <Button variant="outline" size="sm" className="flex-1 border-gray-600 text-gray-300 hover:bg-gray-800 text-xs">
                            Modify
                          </Button>
                          <Button variant="outline" size="sm" className="flex-1 border-red-600 text-red-400 hover:bg-red-600/10 text-xs">
                            Cancel
                          </Button>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <OrderModal />
    </div>
  );
};

export default PaperTrading;
