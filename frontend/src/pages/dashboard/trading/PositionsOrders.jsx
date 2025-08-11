import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
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
  Target, 
  Clock,
  X,
  Activity,
  RefreshCw,
  ArrowUpRight,
  ArrowDownRight,
  Filter,
  Download,
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  AlertCircle,
  CheckCircle,
  Wallet,
  CreditCard,
  PieChart,
  Edit,
  Copy,
  ExternalLink,
  Settings,
  Bell,
  Calculator,
  Timer,
  Award,
  Flame,
  Eye,
  Share,
  Bookmark,
  MoreHorizontal,
  ChevronDown,
  ChevronUp
} from "lucide-react";
import { usePageTitle } from "@/hooks/use-page-title";

const PositionsOrders = () => {
  usePageTitle("Positions & Orders");

  const [activeTab, setActiveTab] = useState("positions");
  const [selectedPosition, setSelectedPosition] = useState(null);
  const [isPositionModalOpen, setIsPositionModalOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [sortField, setSortField] = useState("symbol");
  const [sortDirection, setSortDirection] = useState("asc");

  // Enhanced positions data
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
      product: "MIS",
      exchange: "NSE",
      entryTime: "09:32:45",
      exitTime: null,
      stopLoss: 3800.00,
      target: 3950.00,
      riskReward: 1.8,
      unrealizedPnl: 2407.50,
      realizedPnl: 0,
      fees: 45.60,
      taxes: 12.30
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
      product: "CNC",
      exchange: "NSE",
      entryTime: "09:45:15",
      exitTime: null,
      stopLoss: 1480.00,
      target: 1550.00,
      riskReward: 2.1,
      unrealizedPnl: 2305.00,
      realizedPnl: 0,
      fees: 35.20,
      taxes: 18.45
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
      product: "MIS",
      exchange: "NSE",
      entryTime: "10:15:30",
      exitTime: null,
      stopLoss: 2420.00,
      target: 2520.00,
      riskReward: 0.9,
      unrealizedPnl: -380.00,
      realizedPnl: 0,
      fees: 28.75,
      taxes: 15.20
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
      product: "MIS",
      exchange: "NSE",
      entryTime: "11:20:45",
      exitTime: null,
      stopLoss: 1480.00,
      target: 1440.00,
      riskReward: 1.5,
      unrealizedPnl: 507.00,
      realizedPnl: 0,
      fees: 32.40,
      taxes: 14.85
    },
  ]);

  // Enhanced orders data
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
      pendingQty: 75,
      exchange: "NSE",
      orderNumber: "220124000001",
      rejectionReason: null,
      lastModified: "09:32:45",
      fees: 0,
      triggerPrice: null
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
      pendingQty: 0,
      exchange: "NSE",
      orderNumber: "220124000002",
      rejectionReason: null,
      lastModified: "09:28:15",
      fees: 25.30,
      triggerPrice: null
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
      pendingQty: 0,
      exchange: "NSE",
      orderNumber: "220124000003",
      rejectionReason: null,
      lastModified: "10:16:02",
      fees: 35.80,
      triggerPrice: 1495.00
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
      pendingQty: 25,
      exchange: "NSE",
      orderNumber: "220124000004",
      rejectionReason: null,
      lastModified: "11:45:16",
      fees: 0,
      triggerPrice: 3895.00
    },
    {
      id: "ORD005",
      symbol: "ICICIBANK",
      side: "BUY",
      qty: 80,
      orderType: "LIMIT",
      price: 785.00,
      status: "REJECTED",
      product: "MIS",
      timestamp: "12:30:22",
      validity: "DAY",
      avgFillPrice: 0,
      filledQty: 0,
      pendingQty: 0,
      exchange: "NSE",
      orderNumber: "220124000005",
      rejectionReason: "Insufficient margin",
      lastModified: "12:30:25",
      fees: 0,
      triggerPrice: null
    },
  ]);

  const handlePositionClick = (position) => {
    setSelectedPosition(position);
    setIsPositionModalOpen(true);
  };

  const handleSquareOffPosition = (symbol) => {
    setPositions(prev => prev.filter(pos => pos.symbol !== symbol));
  };

  const handleCancelOrder = (orderId) => {
    setOrders(prev => prev.filter(order => order.id !== orderId));
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "EXECUTED":
      case "TRIGGERED":
        return "border-green-500/30 text-green-400 bg-green-500/10";
      case "PENDING":
        return "border-yellow-500/30 text-yellow-400 bg-yellow-500/10";
      case "REJECTED":
      case "CANCELLED":
        return "border-red-500/30 text-red-400 bg-red-500/10";
      default:
        return "border-gray-500/30 text-gray-400 bg-gray-500/10";
    }
  };

  const filteredPositions = positions.filter(position => {
    const matchesSearch = position.symbol.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  const filteredOrders = orders.filter(order => {
    const matchesSearch = order.symbol.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = filterStatus === "all" || order.status.toLowerCase() === filterStatus.toLowerCase();
    return matchesSearch && matchesStatus;
  });

  const totalPnL = positions.reduce((sum, pos) => sum + pos.pnl, 0);
  const totalDayPnL = positions.reduce((sum, pos) => sum + pos.dayPnl, 0);
  const totalMarketValue = positions.reduce((sum, pos) => sum + pos.marketValue, 0);

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-950 via-gray-950 to-slate-900 text-white p-2 sm:p-4 lg:p-6">
      <div className="max-w-7xl mx-auto space-y-4 sm:space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <Card className="bg-gradient-to-br from-gray-900/80 to-gray-800/60 border-green-500/30 backdrop-blur-xl hover:scale-105 transition-transform duration-200">
            <CardContent className="p-3 sm:p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-600/20 rounded-lg">
                  <TrendingUp className="h-4 w-4 sm:h-5 sm:w-5 text-green-400" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-green-300">Total P&L</p>
                  <p className={`text-sm sm:text-lg font-bold truncate ${totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {totalPnL >= 0 ? '+' : ''}₹{totalPnL.toLocaleString()}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-gray-900/80 to-gray-800/60 border-blue-500/30 backdrop-blur-xl hover:scale-105 transition-transform duration-200">
            <CardContent className="p-3 sm:p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-600/20 rounded-lg">
                  <Activity className="h-4 w-4 sm:h-5 sm:w-5 text-blue-400" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-blue-300">Day P&L</p>
                  <p className={`text-sm sm:text-lg font-bold truncate ${totalDayPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {totalDayPnL >= 0 ? '+' : ''}₹{totalDayPnL.toLocaleString()}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-gray-900/80 to-gray-800/60 border-purple-500/30 backdrop-blur-xl hover:scale-105 transition-transform duration-200">
            <CardContent className="p-3 sm:p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-600/20 rounded-lg">
                  <Wallet className="h-4 w-4 sm:h-5 sm:w-5 text-purple-400" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-purple-300">Market Value</p>
                  <p className="text-sm sm:text-lg font-bold text-white truncate">₹{totalMarketValue.toLocaleString()}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-gray-900/80 to-gray-800/60 border-yellow-500/30 backdrop-blur-xl hover:scale-105 transition-transform duration-200">
            <CardContent className="p-3 sm:p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-600/20 rounded-lg">
                  <Target className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-400" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-yellow-300">Positions</p>
                  <p className="text-sm sm:text-lg font-bold text-white truncate">{positions.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <Card className="bg-gray-900/80 border-gray-700/50 backdrop-blur-xl">
          <CardHeader className="pb-3">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <CardTitle className="text-qn-light-cyan text-lg sm:text-xl">Portfolio Management</CardTitle>
              
              <div className="flex flex-wrap gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input 
                    placeholder="Search..." 
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10 w-full sm:w-48 bg-gray-800/50 border-gray-700/50 text-white text-sm"
                  />
                </div>
                
                <Button variant="outline" size="sm" className="border-gray-700/50 text-gray-300 hover:bg-gray-800/50">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
                
                <Button variant="outline" size="sm" className="border-gray-700/50 text-gray-300 hover:bg-gray-800/50">
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </Button>
              </div>
            </div>
          </CardHeader>
          
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-2 bg-gray-900/50 border border-gray-800/50 mb-4">
                <TabsTrigger 
                  value="positions" 
                  className="data-[state=active]:bg-qn-light-cyan/20 data-[state=active]:text-qn-light-cyan"
                >
                  <Target className="h-4 w-4 mr-2" />
                  Positions ({positions.length})
                </TabsTrigger>
                <TabsTrigger 
                  value="orders" 
                  className="data-[state=active]:bg-qn-light-cyan/20 data-[state=active]:text-qn-light-cyan"
                >
                  <Clock className="h-4 w-4 mr-2" />
                  Orders ({orders.length})
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="positions" className="space-y-4">
                {/* Positions List */}
                <div className="space-y-3">
                  {filteredPositions.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                      <Target className="h-16 w-16 mx-auto mb-4 opacity-30" />
                      <p className="text-lg font-medium mb-2">No positions found</p>
                      <p className="text-sm">Start trading to see your positions here</p>
                    </div>
                  ) : (
                    filteredPositions.map((position, index) => (
                      <Card 
                        key={index} 
                        className="bg-gray-800/60 border-gray-700/50 hover:bg-gray-800/80 transition-all duration-200 cursor-pointer"
                        onClick={() => handlePositionClick(position)}
                      >
                        <CardContent className="p-3 sm:p-4">
                          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                            <div className="flex items-center gap-3 min-w-0 flex-1">
                              <div className="flex-shrink-0">
                                <Badge 
                                  variant="outline"
                                  className={`${position.side === "BUY" 
                                    ? "border-green-500/30 text-green-400 bg-green-500/10" 
                                    : "border-red-500/30 text-red-400 bg-red-500/10"} font-medium text-xs`}
                                >
                                  {position.side === "BUY" ? <ArrowUpRight className="h-3 w-3 mr-1" /> : <ArrowDownRight className="h-3 w-3 mr-1" />}
                                  {position.side}
                                </Badge>
                              </div>
                              
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="font-semibold text-white text-sm sm:text-base">{position.symbol}</span>
                                  <Badge variant="outline" className="text-xs border-gray-600/50 text-gray-400">
                                    {position.product}
                                  </Badge>
                                </div>
                                <div className="flex flex-wrap gap-2 text-xs text-gray-400">
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
                                <div className={`text-sm sm:text-base font-bold ${position.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                                  {position.pnl >= 0 ? "+" : ""}₹{position.pnl.toLocaleString()}
                                </div>
                                <div className={`text-xs ${position.pnl >= 0 ? "text-green-400/70" : "text-red-400/70"}`}>
                                  {position.pnlPercent}
                                </div>
                              </div>
                              
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                className="text-red-400 hover:bg-red-600/20 h-8 w-8 p-0"
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
              
              <TabsContent value="orders" className="space-y-4">
                {/* Orders Filter */}
                <div className="flex flex-wrap gap-2">
                  <Select value={filterStatus} onValueChange={setFilterStatus}>
                    <SelectTrigger className="w-32 bg-gray-800/50 border-gray-700/50 text-white text-sm">
                      <SelectValue placeholder="Status" />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-900 border-gray-700">
                      <SelectItem value="all">All Status</SelectItem>
                      <SelectItem value="pending">Pending</SelectItem>
                      <SelectItem value="executed">Executed</SelectItem>
                      <SelectItem value="rejected">Rejected</SelectItem>
                      <SelectItem value="cancelled">Cancelled</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Orders List */}
                <div className="space-y-3">
                  {filteredOrders.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                      <Clock className="h-16 w-16 mx-auto mb-4 opacity-30" />
                      <p className="text-lg font-medium mb-2">No orders found</p>
                      <p className="text-sm">Your orders will appear here</p>
                    </div>
                  ) : (
                    filteredOrders.map((order, index) => (
                      <Card 
                        key={index} 
                        className="bg-gray-800/60 border-gray-700/50 hover:bg-gray-800/80 transition-all duration-200"
                      >
                        <CardContent className="p-3 sm:p-4">
                          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                            <div className="flex items-center gap-3 min-w-0 flex-1">
                              <div className="flex-shrink-0">
                                <Badge 
                                  variant="outline" 
                                  className={`${order.side === "BUY" ? "border-green-600/30 text-green-400" : "border-red-600/30 text-red-400"} text-xs`}
                                >
                                  {order.side}
                                </Badge>
                              </div>
                              
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="font-semibold text-white text-sm sm:text-base">{order.symbol}</span>
                                  <Badge variant="outline" className={`text-xs ${getStatusColor(order.status)}`}>
                                    {order.status}
                                  </Badge>
                                </div>
                                <div className="flex flex-wrap gap-2 text-xs text-gray-400">
                                  <span>Qty: {order.qty}</span>
                                  <span>•</span>
                                  <span>Type: {order.orderType}</span>
                                  <span>•</span>
                                  <span>Price: ₹{order.price}</span>
                                  <span>•</span>
                                  <span>Time: {order.timestamp}</span>
                                </div>
                              </div>
                            </div>
                            
                            <div className="flex items-center gap-2">
                              {order.status === "PENDING" && (
                                <>
                                  <Button variant="outline" size="sm" className="border-gray-600 text-gray-300 hover:bg-gray-800 text-xs">
                                    <Edit className="h-3 w-3 mr-1" />
                                    Modify
                                  </Button>
                                  <Button 
                                    variant="outline" 
                                    size="sm" 
                                    className="border-red-600 text-red-400 hover:bg-red-600/10 text-xs"
                                    onClick={() => handleCancelOrder(order.id)}
                                  >
                                    <X className="h-3 w-3 mr-1" />
                                    Cancel
                                  </Button>
                                </>
                              )}
                              
                              {order.rejectionReason && (
                                <div className="text-xs text-red-400">
                                  Rejected: {order.rejectionReason}
                                </div>
                              )}
                            </div>
                          </div>
                          
                          {order.filledQty > 0 && order.filledQty < order.qty && (
                            <div className="mt-3 pt-3 border-t border-gray-700/50">
                              <div className="flex justify-between text-xs text-gray-400 mb-2">
                                <span>Filled: {order.filledQty}/{order.qty}</span>
                                <span>Avg: ₹{order.avgFillPrice}</span>
                              </div>
                              <div className="w-full bg-gray-700 rounded-full h-1.5">
                                <div 
                                  className="bg-qn-light-cyan h-1.5 rounded-full transition-all" 
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
            </Tabs>
          </CardContent>
        </Card>
      </div>

      {/* Position Details Modal */}
      <Dialog open={isPositionModalOpen} onOpenChange={setIsPositionModalOpen}>
        <DialogContent className="bg-gray-900/95 border-gray-700 text-white max-w-2xl backdrop-blur-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-qn-light-cyan">
              <Target className="h-5 w-5" />
              Position Details - {selectedPosition?.symbol}
            </DialogTitle>
          </DialogHeader>
          
          {selectedPosition && (
            <div className="space-y-6">
              {/* Position Summary */}
              <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="bg-gray-800/80 p-4 rounded-lg">
                  <p className="text-sm text-gray-400 mb-1">Quantity</p>
                  <p className="text-xl font-bold text-white">{selectedPosition.qty}</p>
                  <p className="text-sm text-gray-400">{selectedPosition.side}</p>
                </div>
                <div className="bg-gray-800/80 p-4 rounded-lg">
                  <p className="text-sm text-gray-400 mb-1">Current P&L</p>
                  <p className={`text-xl font-bold ${selectedPosition.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {selectedPosition.pnl >= 0 ? '+' : ''}₹{selectedPosition.pnl.toLocaleString()}
                  </p>
                  <p className={`text-sm ${selectedPosition.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {selectedPosition.pnlPercent}
                  </p>
                </div>
                <div className="bg-gray-800/80 p-4 rounded-lg">
                  <p className="text-sm text-gray-400 mb-1">Risk:Reward</p>
                  <p className="text-xl font-bold text-qn-light-cyan">1:{selectedPosition.riskReward}</p>
                  <p className="text-sm text-gray-400">Ratio</p>
                </div>
              </div>
              
              {/* Detailed Information */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="space-y-3">
                  <h4 className="font-semibold text-white">Price Information</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Average Price:</span>
                      <span className="text-white font-medium">₹{selectedPosition.avgPrice}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Current Price:</span>
                      <span className="text-white font-medium">₹{selectedPosition.ltp}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Market Value:</span>
                      <span className="text-white font-medium">₹{selectedPosition.marketValue.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Stop Loss:</span>
                      <span className="text-red-400 font-medium">₹{selectedPosition.stopLoss}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Target:</span>
                      <span className="text-green-400 font-medium">₹{selectedPosition.target}</span>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-3">
                  <h4 className="font-semibold text-white">Trade Details</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Product Type:</span>
                      <span className="text-white font-medium">{selectedPosition.product}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Exchange:</span>
                      <span className="text-white font-medium">{selectedPosition.exchange}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Entry Time:</span>
                      <span className="text-white font-medium">{selectedPosition.entryTime}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Fees:</span>
                      <span className="text-red-400 font-medium">₹{selectedPosition.fees}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Taxes:</span>
                      <span className="text-red-400 font-medium">₹{selectedPosition.taxes}</span>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-3 pt-4 border-t border-gray-700/50">
                <Button 
                  variant="outline" 
                  className="border-qn-light-cyan/30 text-qn-light-cyan hover:bg-qn-light-cyan/20"
                >
                  <ArrowUpRight className="h-4 w-4 mr-2" />
                  Exit Position
                </Button>
                <Button 
                  variant="outline" 
                  className="border-red-600/30 text-red-400 hover:bg-red-600/20"
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

export default PositionsOrders;
