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
  const [filterStatus, setFilterStatus] = useState("all");

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
      pe: 25.4
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
      pe: 28.7
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
      pe: 19.2
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
      pe: 26.1
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
      pe: 15.8
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
      validity: "DAY",
      avgFillPrice: 0,
      filledQty: 0,
      pendingQty: 75
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
      validity: "DAY",
      avgFillPrice: 445.85,
      filledQty: 100,
      pendingQty: 0
    },
    {
      id: "ORD003",
      symbol: "HDFCBANK",
      side: "BUY",
      qty: 50,
      orderType: "SL",
      price: 1495.00,
      status: "TRIGGERED",
      product: "CNC",
      timestamp: "10:15:28",
      validity: "DAY",
      avgFillPrice: 1496.25,
      filledQty: 50,
      pendingQty: 0
    },
    {
      id: "ORD004",
      symbol: "TCS",
      side: "SELL",
      qty: 25,
      orderType: "BRACKET",
      price: 3900.00,
      status: "PENDING",
      product: "BO",
      timestamp: "11:45:16",
      validity: "DAY",
      avgFillPrice: 0,
      filledQty: 0,
      pendingQty: 25
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
    // Defensive check to prevent multiple rapid calls
    if (isOrderModalOpen) return;

    setOrderType(side);
    setTimeout(() => {
      setIsOrderModalOpen(true);
    }, 50);
  };

  const handlePositionClick = (position) => {
    setSelectedPosition(position);
    setIsPositionModalOpen(true);
  };

  const handleCancelOrder = (orderId) => {
    setOrders(prev => prev.filter(order => order.id !== orderId));
  };

  const handleSquareOffPosition = (symbol) => {
    setPositions(prev => prev.filter(pos => pos.symbol !== symbol));
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
    <Dialog
      open={isOrderModalOpen}
      onOpenChange={(open) => {
        if (!open) {
          setIsOrderModalOpen(false);
        }
      }}
      modal={true}
    >
      <DialogContent className="bg-slate-950 border-emerald-400/30 text-white max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-emerald-400">
            <Zap className="h-5 w-5" />
            Place Order - {selectedSymbol}
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Current Price Display */}
          <div className="bg-slate-900 p-3 rounded-lg border border-emerald-400/30">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Current Price</span>
              <div className="text-right">
                <div className="text-lg font-bold text-white">₹{currentPrice.toLocaleString()}</div>
                <div className={`text-sm ${currentSymbolData?.change >= 0 ? "text-emerald-400" : "text-red-400"}`}>
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
                  ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                  : "bg-slate-800 border-emerald-400/40 text-emerald-400 hover:bg-emerald-400/20 hover:text-emerald-300"}`}
              >
                <ArrowUpRight className="h-4 w-4 mr-2" />
                BUY
              </Button>
              <Button
                variant={orderType === "sell" ? "default" : "outline"}
                onClick={() => setOrderType("sell")}
                className={`${orderType === "sell"
                  ? "bg-red-600 hover:bg-red-700 text-white"
                  : "bg-slate-800 border-red-400/40 text-red-400 hover:bg-red-400/20 hover:text-red-300"}`}
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
                className="bg-slate-800 border-emerald-400/40 text-emerald-400 hover:bg-emerald-400/20 hover:text-emerald-300 h-10 w-10 p-0"
              >
                <Minus className="h-4 w-4" />
              </Button>
              <Input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                className="text-center bg-slate-800 border-slate-600 text-white h-10"
                min="1"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => setQuantity(quantity + 1)}
                className="bg-slate-800 border-emerald-400/40 text-emerald-400 hover:bg-emerald-400/20 hover:text-emerald-300 h-10 w-10 p-0"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Product Type */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Product</Label>
            <Select value={productType} onValueChange={setProductType}>
              <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-emerald-400/30 text-white">
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
              <SelectTrigger className="bg-slate-800 border-slate-600 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-emerald-400/30 text-white">
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
                className="bg-slate-800 border-slate-600 text-white"
                step="0.05"
              />
            </div>
          )}

          {/* Advanced Options Toggle */}
          <div className="space-y-2">
            <Button
              variant="outline"
              onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
              className="w-full bg-slate-800 border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white justify-between"
            >
              Advanced Options
              <ChevronDown className={`h-4 w-4 ${showAdvancedOptions ? 'rotate-180' : ''}`} />
            </Button>

            {showAdvancedOptions && (
              <div className="space-y-3">
                {/* Stop Loss */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Stop Loss</Label>
                  <Input
                    type="number"
                    value={stopLoss}
                    onChange={(e) => setStopLoss(e.target.value)}
                    placeholder="Stop loss price"
                    className="bg-slate-800 border-slate-600 text-white"
                    step="0.05"
                  />
                </div>

                {/* Take Profit */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Take Profit</Label>
                  <Input
                    type="number"
                    value={takeProfit}
                    onChange={(e) => setTakeProfit(e.target.value)}
                    placeholder="Take profit price"
                    className="bg-slate-800 border-slate-600 text-white"
                    step="0.05"
                  />
                </div>

                {/* Alert Price */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Price Alert</Label>
                  <Input
                    type="number"
                    value={alertPrice}
                    onChange={(e) => setAlertPrice(e.target.value)}
                    placeholder="Alert price"
                    className="bg-slate-800 border-slate-600 text-white"
                    step="0.05"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Place Order Button */}
          <Button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setIsOrderModalOpen(false);
            }}
            className="w-full bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-900 hover:from-emerald-600 hover:to-cyan-600 font-semibold py-3"
          >
            <Sparkles className="h-4 w-4 mr-2" />
            Place {orderType.toUpperCase()} Order
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );

  const TradingInterface = () => (
    <div className="w-full h-full">
      {/* Main Trading Content with Tabs */}
      <Card className="bg-gradient-to-br from-slate-950/95 to-slate-900/95 border-emerald-400/20 backdrop-blur-xl shadow-2xl h-full">
        <CardContent className="p-3 sm:p-4 h-full">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full h-full flex flex-col">
            <TabsList className="grid w-full grid-cols-4 bg-slate-900/80 border border-emerald-400/30 mb-4 backdrop-blur-sm">
              <TabsTrigger
                value="trading"
                className="data-[state=active]:bg-emerald-400/20 data-[state=active]:text-emerald-400 text-xs sm:text-sm text-slate-300 hover:text-white"
              >
                <Monitor className="h-4 w-4 mr-1 sm:mr-2" />
                <span className="hidden sm:inline">Trading</span>
                <span className="sm:hidden">Trade</span>
              </TabsTrigger>
              <TabsTrigger
                value="positions"
                className="data-[state=active]:bg-emerald-400/20 data-[state=active]:text-emerald-400 text-xs sm:text-sm text-slate-300 hover:text-white"
              >
                <Target className="h-4 w-4 mr-1 sm:mr-2" />
                <span className="hidden sm:inline">Positions</span>
                <span className="sm:hidden">Pos</span>
              </TabsTrigger>
              <TabsTrigger
                value="orders"
                className="data-[state=active]:bg-emerald-400/20 data-[state=active]:text-emerald-400 text-xs sm:text-sm text-slate-300 hover:text-white"
              >
                <Clock className="h-4 w-4 mr-1 sm:mr-2" />
                <span className="hidden sm:inline">Orders</span>
                <span className="sm:hidden">Orders</span>
              </TabsTrigger>
              <TabsTrigger
                value="account"
                className="data-[state=active]:bg-emerald-400/20 data-[state=active]:text-emerald-400 text-xs sm:text-sm text-slate-300 hover:text-white"
              >
                <Wallet className="h-4 w-4 mr-1 sm:mr-2" />
                <span className="hidden sm:inline">Account</span>
                <span className="sm:hidden">Acc</span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="trading" className="flex-1 space-y-3">
              {/* Trading Interface */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 h-full">
                {/* Watchlist */}
                <div className="lg:col-span-1">
                  <Card className="bg-slate-900/80 border-emerald-400/30 backdrop-blur-sm h-full">
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-emerald-400 text-lg">Market Watch</CardTitle>
                        <Button variant="ghost" size="sm" className="text-emerald-400 hover:text-emerald-300 hover:bg-emerald-400/10 h-8 w-8 p-0">
                          <RefreshCw className="h-4 w-4" />
                        </Button>
                      </div>
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                        <Input
                          placeholder="Search symbols..."
                          className="pl-10 bg-slate-800/50 border-emerald-400/30 text-white text-sm focus:border-emerald-400 focus:ring-emerald-400/20"
                        />
                      </div>
                    </CardHeader>
                    <CardContent className="p-0 flex-1">
                      <div className="space-y-1 max-h-80 overflow-y-auto">
                        {watchlist.map((item) => (
                          <div
                            key={item.symbol}
                            onClick={() => handleWatchlistClick(item.symbol)}
                            className={`p-3 cursor-pointer hover:bg-emerald-400/10 ${
                              selectedSymbol === item.symbol ? "bg-emerald-400/15 border-l-3 border-l-emerald-400" : ""
                            }`}
                          >
                            <div className="flex justify-between items-center mb-2">
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-white text-base">{item.symbol}</span>
                              </div>
                              <Badge
                                variant={item.change >= 0 ? "default" : "destructive"}
                                className={`text-xs ${item.change >= 0 ? "bg-emerald-500/20 text-emerald-400 border-emerald-400/30" : "bg-red-500/20 text-red-400 border-red-400/30"}`}
                              >
                                {item.changePercent}
                              </Badge>
                            </div>

                            <div className="flex justify-between items-center">
                              <span className="text-lg font-bold text-white">₹{item.ltp.toLocaleString()}</span>
                              <span className={`text-sm font-medium ${item.change >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                                {item.change >= 0 ? "+" : ""}₹{item.change}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Chart Area */}
                <div className="lg:col-span-2">
                  <Card className="bg-slate-900/80 border-emerald-400/30 backdrop-blur-sm h-full">
                    <CardHeader className="pb-2">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl font-bold text-white">{selectedSymbol}</span>
                        <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-400/40 px-3 py-1">
                          ₹{currentPrice?.toLocaleString()}
                        </Badge>
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
                          <span className="text-sm text-emerald-400 font-medium">Live</span>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="p-4 flex-1">
                      <div className="h-80 sm:h-96 bg-gradient-to-br from-slate-800/40 to-slate-900/40 rounded-xl flex flex-col items-center justify-center relative border border-emerald-400/20">
                        {/* Chart Placeholder */}
                        <div className="text-center mb-6">
                          <Monitor className="h-16 w-16 mx-auto mb-4 text-emerald-400/60" />
                          <p className="text-xl font-bold text-white mb-2">TradingView Chart</p>
                          <p className="text-sm text-emerald-400/80 mb-6">Professional charting interface</p>

                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-slate-950/70 p-6 rounded-xl max-w-lg border border-emerald-400/20">
                            {[
                              { label: "Open", value: currentSymbolData?.dayLow, color: "text-cyan-400" },
                              { label: "High", value: currentSymbolData?.dayHigh, color: "text-emerald-400" },
                              { label: "Low", value: currentSymbolData?.dayLow, color: "text-red-400" },
                              { label: "Volume", value: currentSymbolData?.volume, color: "text-emerald-400" }
                            ].map((stat, index) => (
                              <div key={index} className="text-center">
                                <p className="text-xs text-slate-300 mb-1">{stat.label}</p>
                                <p className={`text-sm font-semibold ${stat.color}`}>
                                  {stat.label === "Volume" ? stat.value : `₹${stat.value}`}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Buy/Sell Buttons */}
                        <div className="absolute bottom-6 right-6 flex gap-4">
                          <Button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              handlePlaceOrder("buy");
                            }}
                            className="bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white px-6 py-3 font-semibold shadow-lg hover:shadow-xl transition-all duration-200"
                          >
                            <ArrowUpRight className="h-4 w-4 mr-2" />
                            BUY
                          </Button>
                          <Button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              handlePlaceOrder("sell");
                            }}
                            className="bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white px-6 py-3 font-semibold shadow-lg hover:shadow-xl transition-all duration-200"
                          >
                            <ArrowDownRight className="h-4 w-4 mr-2" />
                            SELL
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </TabsContent>

            {/* Positions Tab */}
            <TabsContent value="positions" className="flex-1 space-y-3">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
                <Card className="bg-gradient-to-br from-slate-900/80 to-slate-950/80 border-emerald-400/30 backdrop-blur-sm hover:scale-105 transition-all duration-200">
                  <CardContent className="p-4 text-center">
                    <TrendingUp className="h-6 w-6 mx-auto mb-2 text-emerald-400" />
                    <p className="text-xs text-emerald-300 mb-1">Total P&L</p>
                    <p className="text-lg font-bold text-emerald-400">+₹4,332</p>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-slate-900/80 to-slate-950/80 border-cyan-400/30 backdrop-blur-sm hover:scale-105 transition-all duration-200">
                  <CardContent className="p-4 text-center">
                    <Activity className="h-6 w-6 mx-auto mb-2 text-cyan-400" />
                    <p className="text-xs text-cyan-300 mb-1">Day P&L</p>
                    <p className="text-lg font-bold text-cyan-400">+₹2,196</p>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-slate-900/80 to-slate-950/80 border-purple-400/30 backdrop-blur-sm hover:scale-105 transition-all duration-200">
                  <CardContent className="p-4 text-center">
                    <Wallet className="h-6 w-6 mx-auto mb-2 text-purple-400" />
                    <p className="text-xs text-purple-300 mb-1">Market Value</p>
                    <p className="text-lg font-bold text-white">₹4,95,347</p>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-slate-900/80 to-slate-950/80 border-orange-400/30 backdrop-blur-sm hover:scale-105 transition-all duration-200">
                  <CardContent className="p-4 text-center">
                    <Target className="h-6 w-6 mx-auto mb-2 text-orange-400" />
                    <p className="text-xs text-orange-300 mb-1">Positions</p>
                    <p className="text-lg font-bold text-white">{positions.length}</p>
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-2">
                {positions.length === 0 ? (
                  <div className="text-center py-12 text-slate-400">
                    <Target className="h-16 w-16 mx-auto mb-4 opacity-30" />
                    <p className="text-lg font-medium mb-2">No positions</p>
                    <p className="text-sm">Start trading to see your positions here</p>
                  </div>
                ) : (
                  positions.map((position, index) => (
                    <Card
                      key={index}
                      className="bg-slate-900/70 border-emerald-400/30 hover:bg-slate-900/90 hover:border-emerald-400/50 cursor-pointer backdrop-blur-sm"
                      onClick={() => handlePositionClick(position)}
                    >
                      <CardContent className="p-3">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                          <div className="flex items-center gap-3 min-w-0 flex-1">
                            <div className="flex-shrink-0">
                              <Badge
                                variant="outline"
                                className={`${position.side === "BUY"
                                  ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                                  : "border-red-500/30 text-red-400 bg-red-500/10"} font-medium`}
                              >
                                {position.side === "BUY" ? <ArrowUpRight className="h-3 w-3 mr-1" /> : <ArrowDownRight className="h-3 w-3 mr-1" />}
                                {position.side}
                              </Badge>
                            </div>

                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-semibold text-white">{position.symbol}</span>
                                <Badge variant="outline" className="text-xs border-slate-600/50 text-slate-400">
                                  {position.product}
                                </Badge>
                              </div>
                              <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                                <span>Qty: {position.qty}</span>
                                <span>•</span>
                                <span>Avg: ₹{position.avgPrice}</span>
                                <span>•</span>
                                <span>LTP: ₹{position.ltp}</span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center justify-between sm:justify-end gap-3">
                            <div className="text-right">
                              <div className={`text-base font-bold ${position.pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                                {position.pnl >= 0 ? "+" : ""}₹{position.pnl.toLocaleString()}
                              </div>
                              <div className={`text-xs ${position.pnl >= 0 ? "text-emerald-400/70" : "text-red-400/70"}`}>
                                {position.pnlPercent}
                              </div>
                            </div>

                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-400 hover:bg-red-600/20 hover:text-red-300 h-8 w-8 p-0"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSquareOffPosition(position.symbol);
                              }}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))
                )}
              </div>
            </TabsContent>

            {/* Orders Tab */}
            <TabsContent value="orders" className="flex-1 space-y-3">
              <div className="flex flex-wrap gap-2 mb-4">
                <Select value={filterStatus} onValueChange={setFilterStatus}>
                  <SelectTrigger className="w-32 bg-slate-800 border-emerald-400/30 text-white focus:border-emerald-400 data-[state=open]:border-emerald-400">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent
                    className="bg-slate-900 border-emerald-400/30 text-white shadow-lg"
                    position="popper"
                    sideOffset={4}
                  >
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="executed">Executed</SelectItem>
                    <SelectItem value="rejected">Rejected</SelectItem>
                  </SelectContent>
                </Select>

                <Button variant="outline" size="sm" className="bg-slate-800 border-emerald-400/40 text-emerald-400 hover:bg-emerald-400/20 hover:border-emerald-400 hover:text-emerald-300">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
              </div>

              <div className="space-y-2">
                {orders.filter(order => filterStatus === "all" || order.status.toLowerCase() === filterStatus).length === 0 ? (
                  <div className="text-center py-12 text-slate-400">
                    <Clock className="h-16 w-16 mx-auto mb-4 opacity-30" />
                    <p className="text-lg font-medium mb-2">No orders found</p>
                    <p className="text-sm">Your orders will appear here</p>
                  </div>
                ) : (
                  orders.filter(order => filterStatus === "all" || order.status.toLowerCase() === filterStatus).map((order, index) => (
                    <Card
                      key={index}
                      className="bg-slate-900/70 border-emerald-400/30 hover:bg-slate-900/90 hover:border-emerald-400/50 backdrop-blur-sm"
                    >
                      <CardContent className="p-3">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                          <div className="flex items-center gap-3 min-w-0 flex-1">
                            <div className="flex-shrink-0">
                              <Badge
                                variant="outline"
                                className={`${order.side === "BUY" ? "border-emerald-600/30 text-emerald-400" : "border-red-600/30 text-red-400"}`}
                              >
                                {order.side}
                              </Badge>
                            </div>

                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-semibold text-white">{order.symbol}</span>
                                <Badge
                                  variant="outline"
                                  className={`text-xs ${
                                    order.status === "EXECUTED" ? "border-emerald-600/30 text-emerald-400" :
                                    order.status === "PENDING" ? "border-yellow-600/30 text-yellow-400" :
                                    "border-red-600/30 text-red-400"
                                  }`}
                                >
                                  {order.status}
                                </Badge>
                              </div>
                              <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                                <span>Qty: {order.qty}</span>
                                <span>•</span>
                                <span>Type: {order.orderType}</span>
                                <span>��</span>
                                <span>Price: ₹{order.price}</span>
                                <span>•</span>
                                <span>Time: {order.timestamp}</span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            {order.status === "PENDING" && (
                              <>
                                <Button variant="outline" size="sm" className="bg-slate-800/60 border-emerald-400/40 text-emerald-400 hover:bg-emerald-400/10 hover:border-emerald-400 hover:text-emerald-300 text-xs">
                                  <Edit className="h-3 w-3 mr-1" />
                                  Modify
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="bg-slate-800/60 border-red-400/40 text-red-400 hover:bg-red-500/20 hover:border-red-400 hover:text-red-300 text-xs"
                                  onClick={() => handleCancelOrder(order.id)}
                                >
                                  <X className="h-3 w-3 mr-1" />
                                  Cancel
                                </Button>
                              </>
                            )}
                          </div>
                        </div>

                        {order.filledQty > 0 && order.filledQty < order.qty && (
                          <div className="mt-3 pt-3 border-t border-slate-700/50">
                            <div className="flex justify-between text-xs text-slate-400 mb-2">
                              <span>Filled: {order.filledQty}/{order.qty}</span>
                              <span>Avg: ₹{order.avgFillPrice}</span>
                            </div>
                            <div className="w-full bg-slate-700 rounded-full h-1.5">
                              <div
                                className="bg-emerald-400 h-1.5 rounded-full transition-all"
                                style={{ width: `${(order.filledQty / order.qty) * 100}%` }}
                              ></div>
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))
                )}
              </div>
            </TabsContent>

            {/* Account Tab */}
            <TabsContent value="account" className="flex-1 space-y-3">
              {/* Account Overview */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <Card className="bg-gradient-to-br from-slate-900/80 to-slate-950/80 border-emerald-400/30 backdrop-blur-sm hover:scale-105 transition-all duration-200">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-emerald-500/20 rounded-lg">
                        <Wallet className="h-5 w-5 text-emerald-400" />
                      </div>
                      <div>
                        <p className="text-xs text-emerald-300">Total Capital</p>
                        <p className="text-lg font-bold text-white">₹{accountInfo.totalCapital.toLocaleString()}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-gradient-to-br from-slate-900/80 to-slate-950/80 border-cyan-400/30 backdrop-blur-sm hover:scale-105 transition-all duration-200">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-cyan-500/20 rounded-lg">
                        <DollarSign className="h-5 w-5 text-cyan-400" />
                      </div>
                      <div>
                        <p className="text-xs text-cyan-300">Available Balance</p>
                        <p className="text-lg font-bold text-white">��{accountInfo.availableBalance.toLocaleString()}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-gradient-to-br from-slate-900/80 to-slate-950/80 border-purple-400/30 backdrop-blur-sm hover:scale-105 transition-all duration-200">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-purple-500/20 rounded-lg">
                        <TrendingUp className="h-5 w-5 text-purple-400" />
                      </div>
                      <div>
                        <p className="text-xs text-purple-300">Total P&L</p>
                        <p className="text-lg font-bold text-emerald-400">+₹{accountInfo.totalPnL.toLocaleString()}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-gradient-to-br from-slate-900/80 to-slate-950/80 border-orange-400/30 backdrop-blur-sm hover:scale-105 transition-all duration-200">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-orange-500/20 rounded-lg">
                        <Activity className="h-5 w-5 text-orange-400" />
                      </div>
                      <div>
                        <p className="text-xs text-orange-300">Day P&L</p>
                        <p className="text-lg font-bold text-emerald-400">+₹{accountInfo.dayPnL.toLocaleString()}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Account Details & Holdings */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Account Information */}
                <Card className="bg-slate-900/80 border-emerald-400/30 backdrop-blur-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-emerald-400 text-sm">Account Information</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-slate-400 text-xs">Account ID</Label>
                        <p className="text-white font-mono text-sm">{accountInfo.accountId}</p>
                      </div>
                      <div>
                        <Label className="text-slate-400 text-xs">Account Type</Label>
                        <p className="text-white text-sm">{accountInfo.accountType}</p>
                      </div>
                      <div>
                        <Label className="text-slate-400 text-xs">Status</Label>
                        <Badge className="bg-emerald-600/20 text-emerald-400">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          {accountInfo.status}
                        </Badge>
                      </div>
                      <div>
                        <Label className="text-slate-400 text-xs">Opening Date</Label>
                        <p className="text-white text-sm">{accountInfo.openingDate}</p>
                      </div>
                    </div>

                    <div className="border-t border-slate-700/50 pt-3">
                      <h4 className="text-white font-semibold mb-2 text-sm">Trading Limits</h4>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-slate-400 text-xs">Exposure Limit</span>
                          <span className="text-white text-xs">₹{accountInfo.exposureLimit.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400 text-xs">Day Trading Power</span>
                          <span className="text-white text-xs">₹{accountInfo.dayTradingBuyingPower.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400 text-xs">Overnight Power</span>
                          <span className="text-white text-xs">₹{accountInfo.overnightBuyingPower.toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* P&L Breakdown */}
                <Card className="bg-slate-900/80 border-emerald-400/30 backdrop-blur-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-emerald-400 text-sm">P&L Breakdown</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400 text-xs">Realized P&L</span>
                        <span className="text-emerald-400 font-semibold text-sm">+₹{accountInfo.realizedPnL.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400 text-xs">Unrealized P&L</span>
                        <span className="text-emerald-400 font-semibold text-sm">+₹{accountInfo.unrealizedPnL.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400 text-xs">Brokerage</span>
                        <span className="text-red-400 text-sm">-₹{accountInfo.brokerage.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400 text-xs">Taxes & Charges</span>
                        <span className="text-red-400 text-sm">-₹{accountInfo.taxes.toLocaleString()}</span>
                      </div>
                      <div className="border-t border-slate-700/50 pt-2">
                        <div className="flex justify-between items-center">
                          <span className="text-white font-semibold text-sm">Net P&L</span>
                          <span className="text-emerald-400 font-bold text-lg">+₹{accountInfo.netPnL.toLocaleString()}</span>
                        </div>
                      </div>
                    </div>

                    <div className="bg-gradient-to-r from-slate-800/60 to-slate-900/60 p-3 rounded-lg border border-emerald-400/30 backdrop-blur-sm">
                      <div className="flex items-center gap-2 mb-2">
                        <Award className="h-4 w-4 text-emerald-400" />
                        <span className="text-emerald-400 font-medium text-sm">Performance Metrics</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-slate-400">Return: </span>
                          <span className="text-emerald-400 font-semibold">+4.19%</span>
                        </div>
                        <div>
                          <span className="text-slate-400">Max Profit: </span>
                          <span className="text-emerald-400">₹8,450</span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );


  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white">
      {/* Main Trading Interface - Full Screen */}
      <div className="h-screen w-full overflow-hidden">
        <TradingInterface />
      </div>

      <OrderModal />

      {/* Position Details Modal */}
      <Dialog open={isPositionModalOpen} onOpenChange={setIsPositionModalOpen}>
        <DialogContent className="bg-slate-950/95 border-slate-700 text-white max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-emerald-400">
              <Target className="h-5 w-5" />
              Position Details - {selectedPosition?.symbol}
            </DialogTitle>
          </DialogHeader>

          {selectedPosition && (
            <div className="space-y-4">
              {/* Position Summary */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-800/50 p-3 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">Quantity</p>
                  <p className="text-lg font-bold text-white">{selectedPosition.qty}</p>
                  <p className="text-xs text-slate-400">{selectedPosition.side}</p>
                </div>
                <div className="bg-slate-800/50 p-3 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">Current P&L</p>
                  <p className={`text-lg font-bold ${selectedPosition.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {selectedPosition.pnl >= 0 ? '+' : ''}₹{selectedPosition.pnl.toLocaleString()}
                  </p>
                  <p className={`text-xs ${selectedPosition.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {selectedPosition.pnlPercent}
                  </p>
                </div>
              </div>

              {/* Price Details */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Average Price:</span>
                  <span className="text-white font-medium">₹{selectedPosition.avgPrice}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Current Price:</span>
                  <span className="text-white font-medium">₹{selectedPosition.ltp}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Market Value:</span>
                  <span className="text-white font-medium">₹{selectedPosition.marketValue.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Product Type:</span>
                  <span className="text-white font-medium">{selectedPosition.product}</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-3 pt-4">
                <Button
                  variant="outline"
                  className="border-emerald-400/30 text-emerald-400 hover:bg-emerald-400/10 hover:text-emerald-300"
                  onClick={() => {
                    setIsPositionModalOpen(false);
                    handlePlaceOrder(selectedPosition.side === 'BUY' ? 'sell' : 'buy');
                  }}
                >
                  <ArrowUpRight className="h-4 w-4 mr-2" />
                  Exit Position
                </Button>
                <Button
                  variant="outline"
                  className="border-red-600/30 text-red-400 hover:bg-red-600/20 hover:text-red-300"
                  onClick={() => {
                    handleSquareOffPosition(selectedPosition.symbol);
                    setIsPositionModalOpen(false);
                  }}
                >
                  <X className="h-4 w-4 mr-2" />
                  Square Off
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PaperTrading;
