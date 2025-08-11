import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
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
  Monitor
} from "lucide-react";
import { usePageTitle } from "@/hooks/use-page-title";

const PaperTrading = () => {
  usePageTitle("Paper Trading");

  const [selectedSymbol, setSelectedSymbol] = useState("NIFTY 50");
  const [orderType, setOrderType] = useState("buy");
  const [productType, setProductType] = useState("intraday");
  const [executionType, setExecutionType] = useState("market");
  const [quantity, setQuantity] = useState(1);
  const [limitPrice, setLimitPrice] = useState(19850.50);
  const [isLiveMode, setIsLiveMode] = useState(true);
  const [marketStatus, setMarketStatus] = useState("OPEN");
  const [lastUpdate, setLastUpdate] = useState(new Date());

  const [watchlist] = useState([
    { symbol: "NIFTY 50", ltp: 19850.50, change: 1.52, changePercent: "+0.08%", volume: "2.4M", dayHigh: 19920.30, dayLow: 19780.15 },
    { symbol: "RELIANCE", ltp: 2456.30, change: -15.20, changePercent: "-0.61%", volume: "1.8M", dayHigh: 2485.60, dayLow: 2441.20 },
    { symbol: "TCS", ltp: 3890.45, change: 48.15, changePercent: "+1.25%", volume: "892K", dayHigh: 3910.80, dayLow: 3842.30 },
    { symbol: "HDFCBANK", ltp: 1520.10, change: 23.05, changePercent: "+1.54%", volume: "1.2M", dayHigh: 1535.75, dayLow: 1497.05 },
    { symbol: "INFY", ltp: 1456.75, change: -8.90, changePercent: "-0.61%", volume: "756K", dayHigh: 1475.20, dayLow: 1448.30 },
    { symbol: "ICICIBANK", ltp: 789.30, change: 12.80, changePercent: "+1.65%", volume: "2.1M", dayHigh: 795.45, dayLow: 776.50 },
  ]);
  
  const [positions] = useState([
    { symbol: "TCS", qty: 50, avgPrice: 3842.30, ltp: 3890.45, pnl: 2407.50, pnlPercent: "+1.25%", dayPnl: 1250.50 },
    { symbol: "RELIANCE", qty: 25, avgPrice: 2471.50, ltp: 2456.30, pnl: -380.00, pnlPercent: "-0.61%", dayPnl: -180.25 },
    { symbol: "HDFCBANK", qty: 100, avgPrice: 1497.05, ltp: 1520.10, pnl: 2305.00, pnlPercent: "+1.54%", dayPnl: 1845.75 },
  ]);

  const [alerts] = useState([
    { symbol: "NIFTY 50", type: "BREAKOUT", message: "Breaking above 19,800 resistance" },
    { symbol: "TCS", type: "VOLUME_SPIKE", message: "Unusual volume activity detected" },
  ]);

  const currentPrice = watchlist.find(item => item.symbol === selectedSymbol)?.ltp || 0;
  const estimatedCost = orderType === "buy" 
    ? quantity * (executionType === "market" ? currentPrice : limitPrice)
    : -(quantity * (executionType === "market" ? currentPrice : limitPrice));

  const totalPnL = positions.reduce((sum, pos) => sum + pos.pnl, 0);
  const dayPnL = positions.reduce((sum, pos) => sum + pos.dayPnl, 0);
  const availableBalance = 850000;
  const holdingsValue = 150000;
  const totalPortfolioValue = availableBalance + holdingsValue;

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
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-black to-gray-900 text-white p-4 lg:p-6 overflow-hidden">
      {/* Header with Live Status */}
      <div className="mb-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl lg:text-3xl font-bold bg-gradient-to-r from-qn-light-cyan to-blue-400 bg-clip-text text-transparent">
              Paper Trading Terminal
            </h1>
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full animate-pulse ${marketStatus === 'OPEN' ? 'bg-green-400' : 'bg-red-400'}`}></div>
              <span className="text-sm font-medium">{marketStatus}</span>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Clock className="h-4 w-4" />
              <span>Last updated: {formatTime(lastUpdate)}</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsLiveMode(!isLiveMode)}
              className={`border-qn-light-cyan text-qn-light-cyan hover:bg-qn-light-cyan hover:text-black ${isLiveMode ? 'bg-qn-light-cyan/10' : ''}`}
            >
              {isLiveMode ? <PlayCircle className="h-4 w-4 mr-2" /> : <PauseCircle className="h-4 w-4 mr-2" />}
              {isLiveMode ? 'Live' : 'Paused'}
            </Button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 h-[calc(100vh-8rem)]">
        {/* Left Panel - Action Zone */}
        <div className="xl:col-span-3 space-y-6 overflow-y-auto">
          {/* Quick Stats */}
          <div className="grid grid-cols-2 gap-3">
            <Card className="bg-gradient-to-br from-green-900/20 to-green-800/10 border-green-700/30 backdrop-blur-xl">
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-400" />
                  <div>
                    <p className="text-xs text-green-300">Day P&L</p>
                    <p className="text-lg font-bold text-green-400">+₹{dayPnL.toLocaleString()}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-gradient-to-br from-blue-900/20 to-blue-800/10 border-blue-700/30 backdrop-blur-xl">
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <Activity className="h-5 w-5 text-blue-400" />
                  <div>
                    <p className="text-xs text-blue-300">Open Positions</p>
                    <p className="text-lg font-bold text-blue-400">{positions.length}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Order Entry Form */}
          <Card className="bg-gray-900/40 border-gray-700/50 backdrop-blur-xl shadow-2xl">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-qn-light-cyan">
                <Zap className="h-5 w-5" />
                Quick Order
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Stock Symbol */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Symbol</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    value={selectedSymbol}
                    onChange={(e) => setSelectedSymbol(e.target.value)}
                    className="pl-10 bg-gray-800/50 border-gray-600 text-white backdrop-blur-sm focus:border-qn-light-cyan transition-all duration-200"
                    placeholder="Search symbol..."
                  />
                </div>
                <div className="text-xs text-gray-400">
                  LTP: ₹{currentPrice.toLocaleString()}
                </div>
              </div>

              {/* Order Type Toggle */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Order Type</Label>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    variant={orderType === "buy" ? "default" : "outline"}
                    onClick={() => setOrderType("buy")}
                    className={`relative overflow-hidden ${orderType === "buy" 
                      ? "bg-gradient-to-r from-green-600 to-green-500 hover:from-green-700 hover:to-green-600 border-green-500" 
                      : "border-gray-600 text-gray-300 hover:bg-gray-800/50"}`}
                  >
                    <ArrowUpRight className="h-4 w-4 mr-2" />
                    Buy
                  </Button>
                  <Button
                    variant={orderType === "sell" ? "default" : "outline"}
                    onClick={() => setOrderType("sell")}
                    className={`relative overflow-hidden ${orderType === "sell" 
                      ? "bg-gradient-to-r from-red-600 to-red-500 hover:from-red-700 hover:to-red-600 border-red-500" 
                      : "border-gray-600 text-gray-300 hover:bg-gray-800/50"}`}
                  >
                    <ArrowDownRight className="h-4 w-4 mr-2" />
                    Sell
                  </Button>
                </div>
              </div>

              {/* Product Type */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Product</Label>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    variant={productType === "intraday" ? "default" : "outline"}
                    onClick={() => setProductType("intraday")}
                    className={`text-xs ${productType === "intraday" 
                      ? "bg-qn-light-cyan text-black hover:bg-qn-light-cyan/80" 
                      : "border-gray-600 text-gray-300 hover:bg-gray-800/50"}`}
                  >
                    Intraday
                  </Button>
                  <Button
                    variant={productType === "delivery" ? "default" : "outline"}
                    onClick={() => setProductType("delivery")}
                    className={`text-xs ${productType === "delivery" 
                      ? "bg-qn-light-cyan text-black hover:bg-qn-light-cyan/80" 
                      : "border-gray-600 text-gray-300 hover:bg-gray-800/50"}`}
                  >
                    Delivery
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
                    className="border-gray-600 text-gray-300 hover:bg-gray-800/50 h-9 w-9 p-0"
                  >
                    <Minus className="h-4 w-4" />
                  </Button>
                  <Input
                    type="number"
                    value={quantity}
                    onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                    className="text-center bg-gray-800/50 border-gray-600 text-white h-9"
                    min="1"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setQuantity(quantity + 1)}
                    className="border-gray-600 text-gray-300 hover:bg-gray-800/50 h-9 w-9 p-0"
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Execution Type */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Execution</Label>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    variant={executionType === "market" ? "default" : "outline"}
                    onClick={() => setExecutionType("market")}
                    className={`text-xs ${executionType === "market" 
                      ? "bg-orange-600 hover:bg-orange-700" 
                      : "border-gray-600 text-gray-300 hover:bg-gray-800/50"}`}
                  >
                    Market
                  </Button>
                  <Button
                    variant={executionType === "limit" ? "default" : "outline"}
                    onClick={() => setExecutionType("limit")}
                    className={`text-xs ${executionType === "limit" 
                      ? "bg-orange-600 hover:bg-orange-700" 
                      : "border-gray-600 text-gray-300 hover:bg-gray-800/50"}`}
                  >
                    Limit
                  </Button>
                </div>
              </div>

              {/* Limit Price */}
              {executionType === "limit" && (
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Limit Price</Label>
                  <Input
                    type="number"
                    value={limitPrice}
                    onChange={(e) => setLimitPrice(parseFloat(e.target.value) || 0)}
                    className="bg-gray-800/50 border-gray-600 text-white"
                    step="0.01"
                  />
                </div>
              )}

              {/* Estimated Cost */}
              <div className="bg-gradient-to-r from-gray-800/50 to-gray-700/50 p-4 rounded-lg border border-gray-600/50 backdrop-blur-sm">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-300">Estimated {orderType === "buy" ? "Cost" : "Credit"}:</span>
                  <span className={`text-lg font-bold ${orderType === "buy" ? "text-red-400" : "text-green-400"}`}>
                    ₹{Math.abs(estimatedCost).toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Place Trade Button */}
              <Button 
                onClick={handlePlaceTrade}
                className="w-full bg-gradient-to-r from-qn-light-cyan to-blue-400 text-black hover:from-qn-light-cyan/80 hover:to-blue-400/80 font-semibold py-3 relative overflow-hidden group"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent transform -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
                <Sparkles className="h-4 w-4 mr-2" />
                Place Paper Trade
              </Button>
            </CardContent>
          </Card>

          {/* Market Alerts */}
          <Card className="bg-gradient-to-br from-yellow-900/20 to-orange-800/10 border-yellow-700/30 backdrop-blur-xl">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-yellow-400 text-sm">
                <Bell className="h-4 w-4" />
                Live Alerts
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {alerts.map((alert, index) => (
                <div key={index} className="bg-yellow-900/20 p-3 rounded-lg border border-yellow-700/30">
                  <div className="flex items-start gap-2">
                    <Badge variant="outline" className="border-yellow-500 text-yellow-400 text-xs">
                      {alert.type}
                    </Badge>
                  </div>
                  <p className="text-xs text-yellow-200 mt-1">{alert.symbol}: {alert.message}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Center Panel - Chart Zone */}
        <div className="xl:col-span-6">
          <Card className="bg-gray-900/40 border-gray-700/50 backdrop-blur-xl h-full shadow-2xl">
            <CardHeader className="pb-4">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                <div className="flex items-center gap-3">
                  <CardTitle className="text-qn-light-cyan text-lg">{selectedSymbol}</CardTitle>
                  <Badge variant="outline" className="border-green-500 text-green-400">
                    ₹{currentPrice.toLocaleString()}
                  </Badge>
                  <Badge variant={watchlist.find(w => w.symbol === selectedSymbol)?.change >= 0 ? "default" : "destructive"} className="text-xs">
                    {watchlist.find(w => w.symbol === selectedSymbol)?.changePercent}
                  </Badge>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="border-gray-600 text-gray-300 text-xs">1M</Button>
                  <Button variant="outline" size="sm" className="border-gray-600 text-gray-300 text-xs">5M</Button>
                  <Button variant="outline" size="sm" className="border-gray-600 text-gray-300 text-xs">15M</Button>
                  <Button variant="outline" size="sm" className="border-gray-600 text-gray-300 text-xs">1H</Button>
                  <Button variant="default" size="sm" className="bg-qn-light-cyan text-black text-xs">1D</Button>
                  <Button variant="outline" size="sm" className="border-gray-600 text-gray-300">
                    <Settings className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="h-[calc(100%-5rem)]">
              <div className="h-full bg-gradient-to-br from-gray-800/30 to-gray-700/20 rounded-lg flex flex-col items-center justify-center border border-gray-600/30 backdrop-blur-sm">
                <div className="text-center text-gray-400">
                  <div className="mb-6">
                    <Monitor className="h-20 w-20 mx-auto mb-4 opacity-50" />
                    <div className="space-y-2">
                      <p className="text-xl font-medium">Advanced TradingView Chart</p>
                      <p className="text-sm">Real-time candlestick chart with technical indicators</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm bg-gray-800/20 p-4 rounded-lg">
                    <div>
                      <p className="text-gray-500">Day High</p>
                      <p className="font-semibold text-green-400">₹{watchlist.find(w => w.symbol === selectedSymbol)?.dayHigh}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Day Low</p>
                      <p className="font-semibold text-red-400">₹{watchlist.find(w => w.symbol === selectedSymbol)?.dayLow}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Volume</p>
                      <p className="font-semibold text-blue-400">{watchlist.find(w => w.symbol === selectedSymbol)?.volume}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">LTP</p>
                      <p className="font-semibold text-qn-light-cyan">₹{currentPrice.toLocaleString()}</p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Panel - Status Zone */}
        <div className="xl:col-span-3 space-y-6 overflow-y-auto">
          {/* Account Summary */}
          <Card className="bg-gradient-to-br from-purple-900/20 to-indigo-800/10 border-purple-700/30 backdrop-blur-xl">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-purple-400">
                <DollarSign className="h-5 w-5" />
                Portfolio
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-400">Available Balance</span>
                  <span className="font-semibold text-white">₹{availableBalance.toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-400">Holdings Value</span>
                  <span className="font-semibold text-white">₹{holdingsValue.toLocaleString()}</span>
                </div>
                <div className="border-t border-purple-700/30 pt-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-400">Total Portfolio</span>
                    <span className="text-xl font-bold text-purple-400">
                      ₹{totalPortfolioValue.toLocaleString()}
                    </span>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-400">Total P&L</span>
                  <span className={`font-semibold ${totalPnL >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {totalPnL >= 0 ? "+" : ""}₹{totalPnL.toLocaleString()}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Watchlist */}
          <Card className="bg-gray-900/40 border-gray-700/50 backdrop-blur-xl flex-1">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-qn-light-cyan">
                  <Eye className="h-5 w-5" />
                  Watchlist
                </CardTitle>
                <Button variant="outline" size="sm" className="border-gray-600 text-gray-300">
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {watchlist.map((item) => (
                  <div
                    key={item.symbol}
                    onClick={() => handleWatchlistClick(item.symbol)}
                    className={`p-3 cursor-pointer hover:bg-gray-800/50 transition-all duration-200 ${
                      selectedSymbol === item.symbol ? "bg-qn-light-cyan/10 border-l-2 border-qn-light-cyan" : ""
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-medium text-sm">{item.symbol}</span>
                      <Badge 
                        variant={item.change >= 0 ? "default" : "destructive"} 
                        className={`text-xs ${item.change >= 0 ? "bg-green-600" : "bg-red-600"}`}
                      >
                        {item.changePercent}
                      </Badge>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-gray-400">₹{item.ltp.toLocaleString()}</span>
                      <span className="text-gray-500">{item.volume}</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Current Positions */}
          <Card className="bg-gray-900/40 border-gray-700/50 backdrop-blur-xl">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-qn-light-cyan">
                <Target className="h-5 w-5" />
                Positions
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="space-y-1 max-h-80 overflow-y-auto">
                {positions.length === 0 ? (
                  <div className="p-6 text-center text-gray-400">
                    <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No open positions</p>
                  </div>
                ) : (
                  positions.map((position, index) => (
                    <div key={index} className="p-3 border-b border-gray-800/50 last:border-b-0 hover:bg-gray-800/30 transition-colors">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <span className="font-medium text-sm">{position.symbol}</span>
                          <div className="text-xs text-gray-400">Qty: {position.qty}</div>
                        </div>
                        <Button variant="outline" size="sm" className="border-red-600 text-red-400 hover:bg-red-600/10 h-6 w-6 p-0">
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs mb-2">
                        <div>
                          <span className="text-gray-400">Avg: </span>
                          <span>₹{position.avgPrice}</span>
                        </div>
                        <div>
                          <span className="text-gray-400">LTP: </span>
                          <span>₹{position.ltp}</span>
                        </div>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-400">P&L:</span>
                        <div className="text-right">
                          <div className={`text-sm font-medium ${position.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                            {position.pnl >= 0 ? "+" : ""}₹{position.pnl.toLocaleString()}
                          </div>
                          <div className={`text-xs ${position.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                            {position.pnlPercent}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default PaperTrading;
