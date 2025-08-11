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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
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
  BarChart2,
  User,
  Shield,
  CreditCard,
  Building2,
  MapPin,
  Phone,
  Mail,
  Calendar,
  Award,
  Flame,
  Signal,
  Timer,
  Lightbulb,
  Briefcase,
  FileText,
  Copy,
  Edit,
  LogOut,
  Power
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
  const [activeTab, setActiveTab] = useState("trading");
  const [selectedPosition, setSelectedPosition] = useState(null);
  const [isPositionModalOpen, setIsPositionModalOpen] = useState(false);
  const [alertPrice, setAlertPrice] = useState("");
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);

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
  ]);
  
  const [positions, setPositions] = useState([
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
    {
      symbol: "INFY",
      qty: 60,
      side: "SELL",
      avgPrice: 1465.20,
      ltp: 1456.75,
      pnl: 507.00,
      pnlPercent: "+0.57%",
      dayPnl: 280.15,
      marketValue: 87405.00,
      product: "MIS"
    },
  ]);

  const [orders, setOrders] = useState([
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
  ]);

  const accountInfo = {
    accountId: "PAP001234567",
    accountType: "Paper Trading",
    status: "Active",
    openingDate: "15 Jan 2024",
    totalCapital: 1000000,
    availableBalance: 850000,
    usedMargin: 150000,
    exposureLimit: 500000,
    dayTradingBuyingPower: 400000,
    overnightBuyingPower: 850000,
    maintenanceMargin: 25000,
    totalPnL: 45650,
    dayPnL: 2850,
    unrealizedPnL: 4332.50,
    realizedPnL: 41317.50,
    brokerage: 2456.75,
    taxes: 1205.30,
    netPnL: 41894.45
  };

  const currentSymbolData = watchlist.find(item => item.symbol === selectedSymbol);
  const currentPrice = currentSymbolData?.ltp || 0;

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

  const handlePlaceOrder = (side) => {
    setOrderType(side);
    setIsOrderModalOpen(true);
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

          {/* Place Order Button */}
          <Button 
            onClick={() => setIsOrderModalOpen(false)}
            className="w-full bg-gradient-to-r from-qn-light-cyan to-blue-400 text-black hover:from-qn-light-cyan/80 hover:to-blue-400/80 font-semibold py-3"
          >
            <Sparkles className="h-4 w-4 mr-2" />
            Place {orderType.toUpperCase()} Order
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );

  const TradingInterface = () => (
    <div className="grid grid-cols-12 gap-4 h-full">
      {/* Watchlist */}
      <div className="col-span-3">
        <Card className="bg-gray-900/50 border-gray-800/50 backdrop-blur-xl h-full">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-qn-light-cyan">Market Watch</CardTitle>
              <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white h-8 w-8 p-0">
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search symbols..."
                className="pl-10 bg-gray-800/50 border-gray-700/50 text-white text-sm"
              />
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="space-y-1 max-h-[calc(100vh-300px)] overflow-y-auto">
              {watchlist.map((item) => (
                <div
                  key={item.symbol}
                  onClick={() => handleWatchlistClick(item.symbol)}
                  className={`p-3 cursor-pointer hover:bg-gray-800/30 transition-all ${
                    selectedSymbol === item.symbol ? "bg-qn-light-cyan/10 border-l-2 border-l-qn-light-cyan" : ""
                  }`}
                >
                  <div className="flex justify-between items-center mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white text-sm">{item.symbol}</span>
                      <Badge variant="outline" className="text-xs border-gray-600 text-gray-400">
                        {item.sector}
                      </Badge>
                    </div>
                    <Badge 
                      variant={item.change >= 0 ? "default" : "destructive"} 
                      className={`text-xs ${item.change >= 0 ? "bg-green-600/20 text-green-400" : "bg-red-600/20 text-red-400"}`}
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
                      <span className="text-white font-medium">₹{item.dayHigh}</span>
                    </div>
                    <div>
                      <span className="block">Low</span>
                      <span className="text-white font-medium">₹{item.dayLow}</span>
                    </div>
                    <div>
                      <span className="block">Vol</span>
                      <span className="text-white font-medium">{item.volume}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Chart Area */}
      <div className="col-span-6">
        <Card className="bg-gray-900/50 border-gray-800/50 backdrop-blur-xl h-full">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xl font-bold text-white">{selectedSymbol}</span>
                <Badge className="bg-green-600/20 text-green-400 border-green-600/30">
                  ₹{currentPrice?.toLocaleString()}
                </Badge>
              </div>
              <div className="flex gap-1">
                {["1M", "5M", "15M", "1H", "1D", "1W"].map((tf) => (
                  <Button
                    key={tf}
                    variant={selectedTimeframe === tf ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedTimeframe(tf)}
                    className={`text-xs h-8 ${selectedTimeframe === tf 
                      ? "bg-qn-light-cyan text-black" 
                      : "border-gray-700/50 text-gray-300"}`}
                  >
                    {tf}
                  </Button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent className="h-full p-4">
            <div className="h-full bg-gray-800/30 rounded-lg flex flex-col items-center justify-center relative">
              {/* Chart Placeholder */}
              <div className="text-center mb-6">
                <Monitor className="h-16 w-16 mx-auto mb-4 text-gray-500" />
                <p className="text-xl font-bold text-gray-300 mb-2">TradingView Chart</p>
                <p className="text-gray-400 mb-6">Professional charting interface</p>
                
                <div className="grid grid-cols-4 gap-4 bg-gray-900/50 p-6 rounded-xl max-w-lg">
                  {[
                    { label: "Open", value: currentSymbolData?.dayLow, color: "text-blue-400" },
                    { label: "High", value: currentSymbolData?.dayHigh, color: "text-green-400" },
                    { label: "Low", value: currentSymbolData?.dayLow, color: "text-red-400" },
                    { label: "Volume", value: currentSymbolData?.volume, color: "text-purple-400" }
                  ].map((stat, index) => (
                    <div key={index} className="text-center">
                      <p className="text-xs text-gray-400 mb-1">{stat.label}</p>
                      <p className={`text-sm font-semibold ${stat.color}`}>
                        {stat.label === "Volume" ? stat.value : `₹${stat.value}`}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Buy/Sell Buttons */}
              <div className="absolute bottom-4 right-4 flex gap-3">
                <Button 
                  onClick={() => handlePlaceOrder("buy")}
                  className="bg-green-600 hover:bg-green-700 text-white px-6 py-2"
                >
                  <ArrowUpRight className="h-4 w-4 mr-2" />
                  BUY
                </Button>
                <Button 
                  onClick={() => handlePlaceOrder("sell")}
                  className="bg-red-600 hover:bg-red-700 text-white px-6 py-2"
                >
                  <ArrowDownRight className="h-4 w-4 mr-2" />
                  SELL
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Positions & Orders */}
      <div className="col-span-3">
        <div className="space-y-4 h-full">
          {/* Positions */}
          <Card className="bg-gray-900/50 border-gray-800/50 backdrop-blur-xl flex-1">
            <CardHeader className="pb-3">
              <CardTitle className="text-qn-light-cyan text-sm">Positions ({positions.length})</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="space-y-1 max-h-[calc(50vh-150px)] overflow-y-auto">
                {positions.length === 0 ? (
                  <div className="p-6 text-center text-gray-400">
                    <Target className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No positions</p>
                  </div>
                ) : (
                  positions.map((position, index) => (
                    <div key={index} className="p-3 border-b border-gray-800/30 last:border-b-0 hover:bg-gray-800/20 transition-colors">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <span className="font-medium text-sm text-white">{position.symbol}</span>
                          <div className="text-xs text-gray-400">Qty: {position.qty}</div>
                        </div>
                        <Button variant="ghost" size="sm" className="text-red-400 hover:bg-red-600/10 h-6 w-6 p-0">
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs mb-2">
                        <div>
                          <span className="text-gray-400">Avg: </span>
                          <span className="text-white">₹{position.avgPrice}</span>
                        </div>
                        <div>
                          <span className="text-gray-400">LTP: </span>
                          <span className="text-white">₹{position.ltp}</span>
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

          {/* Orders */}
          <Card className="bg-gray-900/50 border-gray-800/50 backdrop-blur-xl flex-1">
            <CardHeader className="pb-3">
              <CardTitle className="text-qn-light-cyan text-sm">Orders ({orders.length})</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="space-y-1 max-h-[calc(50vh-150px)] overflow-y-auto">
                {orders.length === 0 ? (
                  <div className="p-6 text-center text-gray-400">
                    <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No orders</p>
                  </div>
                ) : (
                  orders.map((order, index) => (
                    <div key={index} className="p-3 border-b border-gray-800/30 last:border-b-0 hover:bg-gray-800/20 transition-colors">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm text-white">{order.symbol}</span>
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

                      <div className="grid grid-cols-2 gap-2 text-xs mb-2">
                        <div>
                          <span className="text-gray-400">Qty: </span>
                          <span className="text-white">{order.qty}</span>
                        </div>
                        <div>
                          <span className="text-gray-400">Type: </span>
                          <span className="text-white">{order.orderType}</span>
                        </div>
                        <div>
                          <span className="text-gray-400">Price: </span>
                          <span className="text-white">₹{order.price}</span>
                        </div>
                        <div>
                          <span className="text-gray-400">Time: </span>
                          <span className="text-white">{order.timestamp}</span>
                        </div>
                      </div>

                      {order.status === "PENDING" && (
                        <div className="flex gap-2 mt-2">
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
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );

  const AccountDashboard = () => (
    <div className="space-y-4 h-full overflow-y-auto">
      {/* Account Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-green-900/20 to-emerald-800/10 border-green-700/30">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-600/20 rounded-lg">
                <Wallet className="h-5 w-5 text-green-400" />
              </div>
              <div>
                <p className="text-xs text-green-300">Total Capital</p>
                <p className="text-lg font-bold text-white">₹{accountInfo.totalCapital.toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-blue-900/20 to-cyan-800/10 border-blue-700/30">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-600/20 rounded-lg">
                <DollarSign className="h-5 w-5 text-blue-400" />
              </div>
              <div>
                <p className="text-xs text-blue-300">Available Balance</p>
                <p className="text-lg font-bold text-white">₹{accountInfo.availableBalance.toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-purple-900/20 to-pink-800/10 border-purple-700/30">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-600/20 rounded-lg">
                <TrendingUp className="h-5 w-5 text-purple-400" />
              </div>
              <div>
                <p className="text-xs text-purple-300">Total P&L</p>
                <p className="text-lg font-bold text-green-400">+₹{accountInfo.totalPnL.toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-orange-900/20 to-red-800/10 border-orange-700/30">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-600/20 rounded-lg">
                <Activity className="h-5 w-5 text-orange-400" />
              </div>
              <div>
                <p className="text-xs text-orange-300">Day P&L</p>
                <p className="text-lg font-bold text-green-400">+₹{accountInfo.dayPnL.toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Account Details & Holdings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Account Information */}
        <Card className="bg-gray-900/50 border-gray-800/50 backdrop-blur-xl">
          <CardHeader className="pb-3">
            <CardTitle className="text-qn-light-cyan text-sm">Account Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-gray-400 text-xs">Account ID</Label>
                <p className="text-white font-mono text-sm">{accountInfo.accountId}</p>
              </div>
              <div>
                <Label className="text-gray-400 text-xs">Account Type</Label>
                <p className="text-white text-sm">{accountInfo.accountType}</p>
              </div>
              <div>
                <Label className="text-gray-400 text-xs">Status</Label>
                <Badge className="bg-green-600/20 text-green-400">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  {accountInfo.status}
                </Badge>
              </div>
              <div>
                <Label className="text-gray-400 text-xs">Opening Date</Label>
                <p className="text-white text-sm">{accountInfo.openingDate}</p>
              </div>
            </div>

            <div className="border-t border-gray-700/50 pt-3">
              <h4 className="text-white font-semibold mb-2 text-sm">Trading Limits</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400 text-xs">Exposure Limit</span>
                  <span className="text-white text-xs">₹{accountInfo.exposureLimit.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400 text-xs">Day Trading Power</span>
                  <span className="text-white text-xs">₹{accountInfo.dayTradingBuyingPower.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400 text-xs">Overnight Power</span>
                  <span className="text-white text-xs">₹{accountInfo.overnightBuyingPower.toLocaleString()}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* P&L Breakdown */}
        <Card className="bg-gray-900/50 border-gray-800/50 backdrop-blur-xl">
          <CardHeader className="pb-3">
            <CardTitle className="text-qn-light-cyan text-sm">P&L Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-gray-400 text-xs">Realized P&L</span>
                <span className="text-green-400 font-semibold text-sm">+₹{accountInfo.realizedPnL.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400 text-xs">Unrealized P&L</span>
                <span className="text-green-400 font-semibold text-sm">+₹{accountInfo.unrealizedPnL.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400 text-xs">Brokerage</span>
                <span className="text-red-400 text-sm">-₹{accountInfo.brokerage.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400 text-xs">Taxes & Charges</span>
                <span className="text-red-400 text-sm">-₹{accountInfo.taxes.toLocaleString()}</span>
              </div>
              <div className="border-t border-gray-700/50 pt-2">
                <div className="flex justify-between items-center">
                  <span className="text-white font-semibold text-sm">Net P&L</span>
                  <span className="text-green-400 font-bold text-lg">+₹{accountInfo.netPnL.toLocaleString()}</span>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-r from-green-900/20 to-emerald-800/10 p-3 rounded-lg border border-green-700/30">
              <div className="flex items-center gap-2 mb-2">
                <Award className="h-4 w-4 text-green-400" />
                <span className="text-green-400 font-medium text-sm">Performance Metrics</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-400">Return: </span>
                  <span className="text-green-400 font-semibold">+4.19%</span>
                </div>
                <div>
                  <span className="text-gray-400">Max Profit: </span>
                  <span className="text-green-400">₹8,450</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );

  return (
    <div className="h-[calc(100vh-80px)] bg-gradient-to-br from-slate-950 via-gray-950 to-slate-900 text-white flex flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-800/50 bg-gray-900/30 backdrop-blur-xl flex-shrink-0">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-gradient-to-br from-qn-light-cyan to-blue-500 rounded-lg flex items-center justify-center">
              <CandlestickChart className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-qn-light-cyan to-blue-400 bg-clip-text text-transparent">
                Paper Trading Terminal
              </h1>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-sm text-green-400 font-medium">Market {marketStatus}</span>
                <span className="text-xs text-gray-400">• {formatTime(lastUpdate)}</span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <Badge className="bg-green-600/20 text-green-400 border-green-600/30">
              <Activity className="h-3 w-3 mr-1" />
              Live Data
            </Badge>
            <Button variant="outline" size="sm" className="border-gray-700/50 text-gray-300 hover:bg-gray-800/50">
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-4 overflow-hidden">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
          <TabsList className="grid w-full grid-cols-2 bg-gray-900/50 border border-gray-800/50 flex-shrink-0">
            <TabsTrigger 
              value="trading" 
              className="data-[state=active]:bg-qn-light-cyan/20 data-[state=active]:text-qn-light-cyan"
            >
              <CandlestickChart className="h-4 w-4 mr-2" />
              Trading Interface
            </TabsTrigger>
            <TabsTrigger 
              value="account" 
              className="data-[state=active]:bg-qn-light-cyan/20 data-[state=active]:text-qn-light-cyan"
            >
              <Briefcase className="h-4 w-4 mr-2" />
              Account Dashboard
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="trading" className="flex-1 mt-4 overflow-hidden">
            <TradingInterface />
          </TabsContent>
          
          <TabsContent value="account" className="flex-1 mt-4 overflow-hidden">
            <AccountDashboard />
          </TabsContent>
        </Tabs>
      </div>

      <OrderModal />
    </div>
  );
};

export default PaperTrading;
