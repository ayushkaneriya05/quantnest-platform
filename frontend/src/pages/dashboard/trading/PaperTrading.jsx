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

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  const TradingInterface = () => (
    <div className="grid grid-cols-12 gap-6 h-full">
      {/* Watchlist */}
      <div className="col-span-3">
        <Card className="bg-black/40 border-white/10 backdrop-blur-xl h-full">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-cyan-400">Market Watch</CardTitle>
              <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white h-8 w-8 p-0">
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search symbols..."
                className="pl-10 bg-white/5 border-white/10 text-white"
              />
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="space-y-1 max-h-96 overflow-y-auto">
              {watchlist.map((item) => (
                <div
                  key={item.symbol}
                  onClick={() => setSelectedSymbol(item.symbol)}
                  className={`p-4 cursor-pointer hover:bg-white/10 transition-all ${
                    selectedSymbol === item.symbol ? "bg-cyan-500/20 border-l-2 border-l-cyan-400" : ""
                  }`}
                >
                  <div className="flex justify-between items-center mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white">{item.symbol}</span>
                      <Badge variant="outline" className="text-xs border-gray-600 text-gray-400">
                        {item.sector}
                      </Badge>
                    </div>
                    <Badge 
                      variant={item.change >= 0 ? "default" : "destructive"} 
                      className={`text-xs ${item.change >= 0 ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}
                    >
                      {item.changePercent}
                    </Badge>
                  </div>
                  
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xl font-bold text-white">₹{item.ltp.toLocaleString()}</span>
                    <span className={`text-sm ${item.change >= 0 ? "text-emerald-400" : "text-red-400"}`}>
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
        <Card className="bg-black/40 border-white/10 backdrop-blur-xl h-full">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl font-bold text-white">{selectedSymbol}</span>
                <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
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
                      ? "bg-cyan-500 text-black" 
                      : "border-white/20 text-gray-300"}`}
                  >
                    {tf}
                  </Button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent className="h-full">
            <div className="h-full bg-gradient-to-br from-gray-800/20 to-gray-700/10 rounded-xl flex items-center justify-center">
              <div className="text-center">
                <Monitor className="h-20 w-20 mx-auto mb-4 text-gray-500" />
                <p className="text-xl font-bold text-gray-300 mb-2">Professional Chart</p>
                <p className="text-gray-400 mb-6">TradingView integration ready</p>
                
                <div className="grid grid-cols-4 gap-4 bg-black/30 p-6 rounded-xl max-w-lg">
                  {[
                    { label: "Open", value: currentSymbolData?.dayLow, color: "text-blue-400" },
                    { label: "High", value: currentSymbolData?.dayHigh, color: "text-emerald-400" },
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
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Order Panel */}
      <div className="col-span-3">
        <Card className="bg-black/40 border-white/10 backdrop-blur-xl h-full">
          <CardHeader>
            <CardTitle className="text-cyan-400">Quick Order</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-2">
              <Button className="bg-emerald-600 hover:bg-emerald-700 text-white">
                <ArrowUpRight className="h-4 w-4 mr-2" />
                BUY
              </Button>
              <Button className="bg-red-600 hover:bg-red-700 text-white">
                <ArrowDownRight className="h-4 w-4 mr-2" />
                SELL
              </Button>
            </div>

            <div className="space-y-3">
              <div>
                <Label className="text-gray-400 text-sm">Quantity</Label>
                <Input 
                  type="number" 
                  defaultValue="1" 
                  className="bg-white/5 border-white/10 text-white"
                />
              </div>
              
              <div>
                <Label className="text-gray-400 text-sm">Order Type</Label>
                <Select defaultValue="market">
                  <SelectTrigger className="bg-white/5 border-white/10 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 border-white/10">
                    <SelectItem value="market">Market</SelectItem>
                    <SelectItem value="limit">Limit</SelectItem>
                    <SelectItem value="stop">Stop Loss</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="bg-white/5 p-3 rounded-lg">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Est. Cost:</span>
                  <span className="text-white font-semibold">₹{currentPrice?.toLocaleString()}</span>
                </div>
              </div>

              <Button className="w-full bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white">
                <Zap className="h-4 w-4 mr-2" />
                Place Order
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );

  const AccountDashboard = () => (
    <div className="space-y-6">
      {/* Account Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="bg-gradient-to-br from-emerald-500/20 to-green-500/10 border-emerald-500/30">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-emerald-500/20 rounded-xl">
                <Wallet className="h-6 w-6 text-emerald-400" />
              </div>
              <div>
                <p className="text-sm text-emerald-300">Total Capital</p>
                <p className="text-2xl font-bold text-white">₹{accountInfo.totalCapital.toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-blue-500/20 to-cyan-500/10 border-blue-500/30">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-500/20 rounded-xl">
                <DollarSign className="h-6 w-6 text-blue-400" />
              </div>
              <div>
                <p className="text-sm text-blue-300">Available Balance</p>
                <p className="text-2xl font-bold text-white">₹{accountInfo.availableBalance.toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-purple-500/20 to-pink-500/10 border-purple-500/30">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-purple-500/20 rounded-xl">
                <TrendingUp className="h-6 w-6 text-purple-400" />
              </div>
              <div>
                <p className="text-sm text-purple-300">Total P&L</p>
                <p className="text-2xl font-bold text-emerald-400">+₹{accountInfo.totalPnL.toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-orange-500/20 to-red-500/10 border-orange-500/30">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-orange-500/20 rounded-xl">
                <Activity className="h-6 w-6 text-orange-400" />
              </div>
              <div>
                <p className="text-sm text-orange-300">Day P&L</p>
                <p className="text-2xl font-bold text-emerald-400">+₹{accountInfo.dayPnL.toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Account Details & Holdings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Account Information */}
        <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="text-cyan-400">Account Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-gray-400 text-sm">Account ID</Label>
                <p className="text-white font-mono">{accountInfo.accountId}</p>
              </div>
              <div>
                <Label className="text-gray-400 text-sm">Account Type</Label>
                <p className="text-white">{accountInfo.accountType}</p>
              </div>
              <div>
                <Label className="text-gray-400 text-sm">Status</Label>
                <Badge className="bg-emerald-500/20 text-emerald-400">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  {accountInfo.status}
                </Badge>
              </div>
              <div>
                <Label className="text-gray-400 text-sm">Opening Date</Label>
                <p className="text-white">{accountInfo.openingDate}</p>
              </div>
            </div>

            <div className="border-t border-white/10 pt-4">
              <h4 className="text-white font-semibold mb-3">Trading Limits</h4>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Exposure Limit</span>
                  <span className="text-white">₹{accountInfo.exposureLimit.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Day Trading Power</span>
                  <span className="text-white">₹{accountInfo.dayTradingBuyingPower.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Overnight Power</span>
                  <span className="text-white">₹{accountInfo.overnightBuyingPower.toLocaleString()}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* P&L Breakdown */}
        <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="text-cyan-400">P&L Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Realized P&L</span>
                <span className="text-emerald-400 font-semibold">+₹{accountInfo.realizedPnL.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Unrealized P&L</span>
                <span className="text-emerald-400 font-semibold">+₹{accountInfo.unrealizedPnL.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Brokerage</span>
                <span className="text-red-400">-₹{accountInfo.brokerage.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Taxes & Charges</span>
                <span className="text-red-400">-₹{accountInfo.taxes.toLocaleString()}</span>
              </div>
              <div className="border-t border-white/10 pt-3">
                <div className="flex justify-between items-center">
                  <span className="text-white font-semibold">Net P&L</span>
                  <span className="text-emerald-400 font-bold text-lg">+₹{accountInfo.netPnL.toLocaleString()}</span>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-r from-emerald-500/10 to-green-500/10 p-4 rounded-lg border border-emerald-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Award className="h-5 w-5 text-emerald-400" />
                <span className="text-emerald-400 font-medium">Performance Metrics</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-gray-400">Return: </span>
                  <span className="text-emerald-400 font-semibold">+4.19%</span>
                </div>
                <div>
                  <span className="text-gray-400">Max Profit: </span>
                  <span className="text-emerald-400">₹8,450</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Positions & Orders */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Current Positions */}
        <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="text-cyan-400">Current Positions ({positions.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {positions.map((position, index) => (
                <div key={index} className="bg-white/5 p-4 rounded-lg border border-white/10">
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white">{position.symbol}</span>
                      <Badge className={`${position.side === "BUY" ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}>
                        {position.side}
                      </Badge>
                      <Badge variant="outline" className="text-xs border-gray-600 text-gray-400">
                        {position.product}
                      </Badge>
                    </div>
                    <Button variant="ghost" size="sm" className="text-red-400 hover:bg-red-500/20 h-6 w-6 p-0">
                      <X className="h-3 w-3" />
                    </Button>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-sm mb-3">
                    <div>
                      <span className="text-gray-400">Qty: </span>
                      <span className="text-white font-medium">{position.qty}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Avg: </span>
                      <span className="text-white font-medium">₹{position.avgPrice}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">LTP: </span>
                      <span className="text-white font-medium">₹{position.ltp}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Value: </span>
                      <span className="text-white font-medium">₹{position.marketValue.toLocaleString()}</span>
                    </div>
                  </div>

                  <div className="flex justify-between items-center pt-2 border-t border-white/10">
                    <div>
                      <span className="text-xs text-gray-400">P&L: </span>
                      <span className={`text-sm font-semibold ${position.pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                        {position.pnl >= 0 ? "+" : ""}₹{position.pnl.toLocaleString()}
                      </span>
                    </div>
                    <span className={`text-xs ${position.pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                      {position.pnlPercent}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Orders */}
        <Card className="bg-black/40 border-white/10 backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="text-cyan-400">Recent Orders ({orders.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {orders.map((order, index) => (
                <div key={index} className="bg-white/5 p-4 rounded-lg border border-white/10">
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white">{order.symbol}</span>
                      <Badge className={`${order.side === "BUY" ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}>
                        {order.side}
                      </Badge>
                    </div>
                    <Badge className={`${
                      order.status === "EXECUTED" ? "bg-emerald-500/20 text-emerald-400" :
                      order.status === "PENDING" ? "bg-yellow-500/20 text-yellow-400" :
                      "bg-red-500/20 text-red-400"
                    }`}>
                      {order.status}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-gray-400">Qty: </span>
                      <span className="text-white font-medium">{order.qty}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Type: </span>
                      <span className="text-white font-medium">{order.orderType}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Price: </span>
                      <span className="text-white font-medium">₹{order.price}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Time: </span>
                      <span className="text-white font-medium">{order.timestamp}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );

  return (
    <div className="h-screen bg-gradient-to-br from-slate-950 via-gray-950 to-slate-900 text-white overflow-hidden">
      {/* Premium Header */}
      <div className="border-b border-white/10 bg-black/20 backdrop-blur-xl">
        <div className="flex items-center justify-between p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-cyan-400 to-blue-500 rounded-xl flex items-center justify-center shadow-xl">
              <CandlestickChart className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
                Paper Trading Terminal
              </h1>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
                <span className="text-sm text-emerald-400 font-medium">Market {marketStatus}</span>
                <span className="text-xs text-gray-400">• {formatTime(lastUpdate)}</span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
              <Activity className="h-3 w-3 mr-1" />
              Live Data
            </Badge>
            <Button variant="outline" size="sm" className="border-white/20 text-gray-300 hover:bg-white/10">
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6 overflow-hidden">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
          <TabsList className="grid w-full grid-cols-2 bg-black/20 border border-white/10">
            <TabsTrigger 
              value="trading" 
              className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400"
            >
              <CandlestickChart className="h-4 w-4 mr-2" />
              Trading Interface
            </TabsTrigger>
            <TabsTrigger 
              value="account" 
              className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400"
            >
              <Briefcase className="h-4 w-4 mr-2" />
              Account Dashboard
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="trading" className="h-full mt-6">
            <TradingInterface />
          </TabsContent>
          
          <TabsContent value="account" className="h-full mt-6 overflow-y-auto">
            <AccountDashboard />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default PaperTrading;
