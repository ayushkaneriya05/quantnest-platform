import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { 
  TrendingUp, 
  TrendingDown,
  Target,
  Filter,
  Calendar,
  ChevronDown,
  ChevronUp,
  Edit,
  Star,
  BarChart3,
  DollarSign,
  Percent,
  Award,
  Gauge,
  Activity,
  Eye,
  Zap,
  Brain,
  PieChart,
  LineChart,
  Lightbulb,
  Download,
  Share,
  RefreshCw,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  Sparkles,
  Trophy,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Circle,
  BarChart2,
  Flame,
  Bookmark,
  Settings,
  Calculator,
  FileText,
  Search,
  Plus,
  MoreHorizontal,
  TrendingUpIcon,
  Minus,
  X,
  PlayCircle,
  StopCircle,
  Hash,
  Calendar as CalendarIcon,
  Timer,
  MapPin,
  Layers,
  Grid,
  Users,
  Briefcase,
  ThumbsUp,
  ThumbsDown,
  MessageSquare,
  BookOpen,
  RotateCcw,
  Copy,
  ExternalLink,
  Maximize2,
  BarChart4,
  Signal
} from "lucide-react";
import { usePageTitle } from "@/hooks/use-page-title";

const TradeJournal = () => {
  usePageTitle("Trade Journal");

  const [expandedRow, setExpandedRow] = useState(null);
  const [dateFilter, setDateFilter] = useState("all");
  const [symbolFilter, setSymbolFilter] = useState("all");
  const [strategyFilter, setStrategyFilter] = useState("all");
  const [sortField, setSortField] = useState("entryDate");
  const [sortDirection, setSortDirection] = useState("desc");
  const [selectedTimeRange, setSelectedTimeRange] = useState("1M");
  const [searchTerm, setSearchTerm] = useState("");
  const [isAnalyticsOpen, setIsAnalyticsOpen] = useState(false);

  // Enhanced KPI Data with better contrast colors
  const kpiData = {
    totalPnL: 45650,
    totalPnLTrend: 12.5,
    winRate: 67.5,
    winRateTrend: 3.2,
    profitFactor: 1.85,
    profitFactorTrend: -2.1,
    avgWinningTrade: 2500,
    avgWinningTradeTrend: 8.7,
    avgLosingTrade: -1200,
    avgLosingTradeTrend: 15.3,
    totalTrades: 42,
    winningTrades: 28,
    losingTrades: 14,
    maxDrawdown: 8750,
    sharpeRatio: 1.42,
    avgHoldingPeriod: 3.2,
    largestWin: 4200,
    largestLoss: -2800,
    consecutiveWins: 5,
    consecutiveLosses: 2,
    returnOnCapital: 18.5,
    calmarRatio: 2.1,
    maxConsecutiveWins: 7,
    maxConsecutiveLosses: 3
  };

  // Enhanced trade data
  const trades = [
    {
      id: 1,
      symbol: "TCS",
      entryDate: "2024-01-15",
      exitDate: "2024-01-18", 
      entryTime: "09:32:45",
      exitTime: "15:24:12",
      quantity: 50,
      direction: "Long",
      entryPrice: 3842.30,
      exitPrice: 3890.45,
      pnl: 2407.50,
      pnlPercent: 1.25,
      strategy: "Breakout",
      setupRating: 4,
      executionRating: 5,
      emotion: "Confident",
      notes: "Clean breakout above resistance with good volume. Entry was perfect at the breakout level. Exit could have been better - sold too early due to profit booking mindset. Need to work on holding winning positions longer.",
      commission: 25.50,
      slippage: 1.20,
      marketCap: "Large",
      sector: "Technology",
      holdingPeriod: 3,
      riskReward: 1.8,
      maxFavorable: 3.2,
      maxAdverse: -0.8,
      tags: ["Momentum", "Volume Breakout", "Tech Rally"],
      learnings: "Trust the setup when all confirmations align",
      improvements: "Hold longer on strong momentum"
    },
    {
      id: 2,
      symbol: "RELIANCE",
      entryDate: "2024-01-12",
      exitDate: "2024-01-16",
      entryTime: "10:15:30",
      exitTime: "14:45:22",
      quantity: 25,
      direction: "Long",
      entryPrice: 2471.50,
      exitPrice: 2456.30,
      pnl: -380.00,
      pnlPercent: -0.61,
      strategy: "Support Bounce",
      setupRating: 3,
      executionRating: 2,
      emotion: "Fearful",
      notes: "Support level held initially but weak follow-through. Should have waited for stronger confirmation signals. Exit was premature due to fear of larger losses. Risk management needs improvement.",
      commission: 18.75,
      slippage: 2.10,
      marketCap: "Large",
      sector: "Energy",
      holdingPeriod: 4,
      riskReward: 0.9,
      maxFavorable: 0.8,
      maxAdverse: -1.2,
      tags: ["Support Trade", "Weak Follow-through", "Energy Sector"],
      learnings: "Wait for stronger confirmation on support bounces",
      improvements: "Better risk management and stop loss placement"
    },
    {
      id: 3,
      symbol: "HDFCBANK",
      entryDate: "2024-01-10", 
      exitDate: "2024-01-14",
      entryTime: "09:45:15",
      exitTime: "15:10:30",
      quantity: 100,
      direction: "Long",
      entryPrice: 1497.05,
      exitPrice: 1520.10,
      pnl: 2305.00,
      pnlPercent: 1.54,
      strategy: "Moving Average Crossover",
      setupRating: 5,
      executionRating: 4,
      emotion: "Confident",
      notes: "Perfect setup with 50 EMA crossing above 200 EMA. Strong momentum and volume confirmation. Held position well despite intraday volatility. Good example of following the system.",
      commission: 35.20,
      slippage: 0.80,
      marketCap: "Large",
      sector: "Banking",
      holdingPeriod: 4,
      riskReward: 2.1,
      maxFavorable: 2.8,
      maxAdverse: -0.5,
      tags: ["EMA Crossover", "Banking Strength", "System Trade"],
      learnings: "EMA crossovers work well in trending markets",
      improvements: "Consider pyramiding on strong trends"
    }
  ];

  const filteredTrades = trades.filter(trade => {
    const matchesSearch = trade.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         trade.strategy.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         trade.notes.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSymbol = symbolFilter === "all" || trade.symbol === symbolFilter;
    const matchesStrategy = strategyFilter === "all" || trade.strategy === strategyFilter;
    
    return matchesSearch && matchesSymbol && matchesStrategy;
  });

  const sortedTrades = [...filteredTrades].sort((a, b) => {
    const aValue = a[sortField];
    const bValue = b[sortField];
    const direction = sortDirection === "asc" ? 1 : -1;
    
    if (typeof aValue === "string") {
      return direction * aValue.localeCompare(bValue);
    }
    return direction * (aValue - bValue);
  });

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const getEmotionData = (emotion) => {
    const emotionMap = {
      confident: { color: "from-emerald-400 to-green-300", bg: "bg-emerald-400/20", border: "border-emerald-400/30", text: "text-emerald-300" },
      fearful: { color: "from-red-400 to-pink-300", bg: "bg-red-400/20", border: "border-red-400/30", text: "text-red-300" },
      greedy: { color: "from-orange-400 to-yellow-300", bg: "bg-orange-400/20", border: "border-orange-400/30", text: "text-orange-300" },
      optimistic: { color: "from-blue-400 to-cyan-300", bg: "bg-blue-400/20", border: "border-blue-400/30", text: "text-blue-300" },
      neutral: { color: "from-gray-400 to-slate-300", bg: "bg-gray-400/20", border: "border-gray-400/30", text: "text-gray-300" }
    };
    return emotionMap[emotion.toLowerCase()] || emotionMap.neutral;
  };

  const renderStars = (rating) => {
    return Array.from({ length: 5 }, (_, i) => (
      <Star
        key={i}
        className={`h-4 w-4 ${
          i < rating ? "text-yellow-300 fill-current" : "text-gray-600"
        }`}
      />
    ));
  };

  const getTrendIcon = (trend) => {
    if (trend > 0) return <TrendingUp className="h-4 w-4 text-emerald-300" />;
    if (trend < 0) return <TrendingDown className="h-4 w-4 text-red-300" />;
    return <Activity className="h-4 w-4 text-gray-400" />;
  };

  const getTrendColor = (trend) => {
    if (trend > 0) return "text-emerald-300";
    if (trend < 0) return "text-red-300";
    return "text-gray-400";
  };

  const StatCard = ({ icon: Icon, title, value, trend, trendValue, color, bgGradient }) => (
    <Card className={`${bgGradient} border-white/20 backdrop-blur-xl hover:scale-105 transition-transform duration-200 shadow-xl`}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className={`p-3 rounded-xl ${color.bg} ${color.border} border backdrop-blur-sm`}>
            <Icon className={`h-6 w-6 ${color.text}`} />
          </div>
          {trend !== undefined && (
            <div className="flex items-center gap-1">
              {getTrendIcon(trend)}
              <span className={`text-sm font-medium ${getTrendColor(trend)}`}>
                {trend >= 0 ? "+" : ""}{trend}%
              </span>
            </div>
          )}
        </div>
        <div>
          <p className="text-sm text-gray-300 mb-1">{title}</p>
          <p className={`text-2xl font-bold ${color.text}`}>{value}</p>
          {trendValue && (
            <p className={`text-sm ${getTrendColor(trendValue)}`}>
              {trendValue >= 0 ? "+" : ""}{trendValue}% from last month
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-gray-950 to-slate-900 text-white">
      {/* Enhanced Header */}
      <div className="border-b border-white/20 bg-black/40 backdrop-blur-xl">
        <div className="p-6">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-gradient-to-br from-cyan-400/30 to-blue-500/20 rounded-xl border border-cyan-400/40 backdrop-blur-sm">
                  <BarChart4 className="h-8 w-8 text-cyan-300" />
                </div>
                <div>
                  <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-300 to-blue-300 bg-clip-text text-transparent">
                    Trade Journal
                  </h1>
                  <p className="text-gray-300">Professional performance analytics & insights</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <div className="flex gap-1">
                {["7D", "1M", "3M", "6M", "1Y", "ALL"].map((range) => (
                  <Button
                    key={range}
                    variant={selectedTimeRange === range ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedTimeRange(range)}
                    className={`text-xs h-9 ${selectedTimeRange === range 
                      ? "bg-cyan-500 text-black hover:bg-cyan-400 font-semibold" 
                      : "border-white/30 text-gray-200 hover:bg-white/10 hover:text-white"}`}
                  >
                    {range}
                  </Button>
                ))}
              </div>
              
              <Button 
                variant="outline" 
                size="sm" 
                className="border-cyan-400/40 text-cyan-300 hover:bg-cyan-400/20 hover:text-cyan-200"
                onClick={() => setIsAnalyticsOpen(true)}
              >
                <Brain className="h-4 w-4 mr-2" />
                AI Insights
              </Button>
              
              <Button variant="outline" size="sm" className="border-white/30 text-gray-200 hover:bg-white/10 hover:text-white">
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Enhanced KPI Dashboard */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            icon={DollarSign}
            title="Total P&L"
            value={`${kpiData.totalPnL >= 0 ? "+" : ""}₹${kpiData.totalPnL.toLocaleString()}`}
            trend={kpiData.totalPnLTrend}
            color={{ bg: "bg-emerald-400/20", border: "border-emerald-400/40", text: "text-emerald-300" }}
            bgGradient="bg-gradient-to-br from-emerald-500/20 to-green-400/10"
          />
          
          <StatCard
            icon={Target}
            title="Win Rate"
            value={`${kpiData.winRate}%`}
            trend={kpiData.winRateTrend}
            color={{ bg: "bg-cyan-400/20", border: "border-cyan-400/40", text: "text-cyan-300" }}
            bgGradient="bg-gradient-to-br from-cyan-500/20 to-blue-400/10"
          />
          
          <StatCard
            icon={Gauge}
            title="Profit Factor"
            value={kpiData.profitFactor}
            trend={kpiData.profitFactorTrend}
            color={{ bg: "bg-purple-400/20", border: "border-purple-400/40", text: "text-purple-300" }}
            bgGradient="bg-gradient-to-br from-purple-500/20 to-indigo-400/10"
          />
          
          <StatCard
            icon={Trophy}
            title="Sharpe Ratio"
            value={kpiData.sharpeRatio}
            color={{ bg: "bg-yellow-400/20", border: "border-yellow-400/40", text: "text-yellow-300" }}
            bgGradient="bg-gradient-to-br from-yellow-500/20 to-orange-400/10"
          />
        </div>

        {/* Secondary Metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
          {[
            { icon: TrendingUp, label: "Avg Win", value: `+₹${kpiData.avgWinningTrade.toLocaleString()}`, color: "text-emerald-300" },
            { icon: TrendingDown, label: "Avg Loss", value: `₹${kpiData.avgLosingTrade.toLocaleString()}`, color: "text-red-300" },
            { icon: AlertTriangle, label: "Max Drawdown", value: `-₹${kpiData.maxDrawdown.toLocaleString()}`, color: "text-orange-300" },
            { icon: Timer, label: "Avg Hold", value: `${kpiData.avgHoldingPeriod}d`, color: "text-blue-300" },
            { icon: Flame, label: "Best Trade", value: `+₹${kpiData.largestWin.toLocaleString()}`, color: "text-green-300" },
            { icon: Calculator, label: "Total Trades", value: kpiData.totalTrades, color: "text-cyan-300" }
          ].map((metric, index) => (
            <Card key={index} className="bg-black/40 border-white/20 backdrop-blur-xl hover:bg-black/50 transition-all duration-200">
              <CardContent className="p-4 text-center">
                <metric.icon className={`h-6 w-6 mx-auto mb-2 ${metric.color}`} />
                <p className="text-xs text-gray-300 mb-1">{metric.label}</p>
                <p className={`text-lg font-bold ${metric.color}`}>{metric.value}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Enhanced Trade History */}
        <Card className="bg-black/40 border-white/20 backdrop-blur-xl shadow-2xl">
          <CardHeader className="pb-4">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              <CardTitle className="flex items-center gap-2 text-cyan-300">
                <BookOpen className="h-5 w-5" />
                Trade History & Analysis
              </CardTitle>
              
              <div className="flex flex-wrap gap-3">
                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input 
                    placeholder="Search trades, strategies, notes..." 
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10 w-64 bg-white/10 border-white/20 text-white placeholder-gray-400 focus:border-cyan-400"
                  />
                </div>

                {/* Filters */}
                <Select value={symbolFilter} onValueChange={setSymbolFilter}>
                  <SelectTrigger className="w-32 bg-white/10 border-white/20 text-white">
                    <SelectValue placeholder="Symbol" />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 border-white/20">
                    <SelectItem value="all">All Symbols</SelectItem>
                    <SelectItem value="TCS">TCS</SelectItem>
                    <SelectItem value="RELIANCE">RELIANCE</SelectItem>
                    <SelectItem value="HDFCBANK">HDFCBANK</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={strategyFilter} onValueChange={setStrategyFilter}>
                  <SelectTrigger className="w-40 bg-white/10 border-white/20 text-white">
                    <SelectValue placeholder="Strategy" />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 border-white/20">
                    <SelectItem value="all">All Strategies</SelectItem>
                    <SelectItem value="Breakout">Breakout</SelectItem>
                    <SelectItem value="Support Bounce">Support Bounce</SelectItem>
                    <SelectItem value="Moving Average Crossover">MA Crossover</SelectItem>
                  </SelectContent>
                </Select>

                <Button variant="outline" size="sm" className="border-white/20 text-gray-200 hover:bg-white/10">
                  <Settings className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
          
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/20">
                    {[
                      { key: "symbol", label: "Symbol" },
                      { key: "entryDate", label: "Date" },
                      { key: "direction", label: "Side" },
                      { key: "strategy", label: "Strategy" },
                      { key: "pnl", label: "P&L (₹)" },
                      { key: "riskReward", label: "R:R" },
                      { key: "holdingPeriod", label: "Hold" },
                      { key: "actions", label: "Actions" }
                    ].map((header) => (
                      <th key={header.key} className="text-left p-4 text-gray-200 font-semibold">
                        {header.key !== "actions" ? (
                          <Button 
                            variant="ghost" 
                            onClick={() => handleSort(header.key)} 
                            className="text-gray-200 hover:text-white p-0 font-semibold"
                          >
                            {header.label}
                            {sortField === header.key && (
                              sortDirection === "asc" ? 
                              <ChevronUp className="h-4 w-4 ml-1" /> : 
                              <ChevronDown className="h-4 w-4 ml-1" />
                            )}
                          </Button>
                        ) : (
                          header.label
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sortedTrades.map((trade) => (
                    <React.Fragment key={trade.id}>
                      <tr
                        className="border-b border-white/10 hover:bg-white/5 cursor-pointer transition-all duration-200"
                        onClick={() => setExpandedRow(expandedRow === trade.id ? null : trade.id)}
                      >
                        <td className="p-4">
                          <div className="flex items-center gap-3">
                            <span className="font-semibold text-white">{trade.symbol}</span>
                            <Badge variant="outline" className="text-xs border-white/30 text-gray-300">
                              {trade.sector}
                            </Badge>
                          </div>
                        </td>
                        <td className="p-4">
                          <div className="text-sm">
                            <div className="text-white font-medium">{trade.entryDate}</div>
                            <div className="text-gray-300 text-xs">{trade.entryTime}</div>
                          </div>
                        </td>
                        <td className="p-4">
                          <Badge 
                            variant="outline"
                            className={`${trade.direction === "Long" 
                              ? "border-emerald-400/40 text-emerald-300 bg-emerald-400/20" 
                              : "border-red-400/40 text-red-300 bg-red-400/20"} font-medium`}
                          >
                            {trade.direction === "Long" ? <ArrowUpRight className="h-3 w-3 mr-1" /> : <ArrowDownRight className="h-3 w-3 mr-1" />}
                            {trade.direction}
                          </Badge>
                        </td>
                        <td className="p-4 text-gray-200 text-sm font-medium">{trade.strategy}</td>
                        <td className="p-4">
                          <div className="flex flex-col">
                            <span className={`font-bold ${trade.pnl >= 0 ? "text-emerald-300" : "text-red-300"}`}>
                              {trade.pnl >= 0 ? "+" : ""}₹{trade.pnl.toLocaleString()}
                            </span>
                            <span className={`text-xs ${trade.pnl >= 0 ? "text-emerald-400/70" : "text-red-400/70"}`}>
                              {trade.pnl >= 0 ? "+" : ""}{trade.pnlPercent}%
                            </span>
                          </div>
                        </td>
                        <td className="p-4">
                          <Badge 
                            variant="outline" 
                            className={`text-xs font-medium ${
                              trade.riskReward >= 2 ? "border-emerald-400/40 text-emerald-300" : 
                              trade.riskReward >= 1.5 ? "border-yellow-400/40 text-yellow-300" : 
                              "border-red-400/40 text-red-300"
                            }`}
                          >
                            1:{trade.riskReward}
                          </Badge>
                        </td>
                        <td className="p-4 text-gray-200 text-sm font-medium">{trade.holdingPeriod}d</td>
                        <td className="p-4 text-center">
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="text-gray-300 hover:text-white h-8 w-8 p-0"
                          >
                            {expandedRow === trade.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </Button>
                        </td>
                      </tr>
                      
                      {expandedRow === trade.id && (
                        <tr>
                          <td colSpan="8" className="p-0">
                            <div className="bg-white/5 backdrop-blur-sm border-t border-white/20">
                              <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
                                {/* Trade Chart Placeholder */}
                                <div className="lg:col-span-1">
                                  <Card className="bg-black/40 border-white/20 h-56">
                                    <CardContent className="p-4 h-full flex flex-col items-center justify-center">
                                      <BarChart3 className="h-16 w-16 text-gray-400 opacity-50 mb-3" />
                                      <p className="text-sm font-medium text-gray-200 mb-3">Trade Performance Chart</p>
                                      <div className="text-xs text-gray-300 space-y-2 text-center w-full">
                                        <div className="flex justify-between">
                                          <span>Entry:</span>
                                          <span className="text-white font-medium">₹{trade.entryPrice}</span>
                                        </div>
                                        <div className="flex justify-between">
                                          <span>Exit:</span>
                                          <span className="text-white font-medium">₹{trade.exitPrice}</span>
                                        </div>
                                        <div className="flex justify-between">
                                          <span>Max Favorable:</span>
                                          <span className="text-emerald-300 font-medium">+{trade.maxFavorable}%</span>
                                        </div>
                                        <div className="flex justify-between">
                                          <span>Max Adverse:</span>
                                          <span className="text-red-300 font-medium">{trade.maxAdverse}%</span>
                                        </div>
                                      </div>
                                    </CardContent>
                                  </Card>
                                </div>

                                {/* Trade Details */}
                                <div className="lg:col-span-2 space-y-6">
                                  {/* Performance Metrics Grid */}
                                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                                    {[
                                      { label: "Commission", value: `₹${trade.commission}`, color: "text-red-300" },
                                      { label: "Slippage", value: `₹${trade.slippage}`, color: "text-orange-300" },
                                      { label: "Quantity", value: trade.quantity, color: "text-cyan-300" },
                                      { label: "Market Cap", value: trade.marketCap, color: "text-blue-300" }
                                    ].map((metric, index) => (
                                      <div key={index} className="bg-white/5 p-3 rounded-lg border border-white/20">
                                        <p className="text-xs text-gray-300 mb-1">{metric.label}</p>
                                        <p className={`text-sm font-medium ${metric.color}`}>{metric.value}</p>
                                      </div>
                                    ))}
                                  </div>

                                  {/* Trade Tags */}
                                  <div>
                                    <Label className="text-sm text-gray-300 mb-2 block">Trade Tags</Label>
                                    <div className="flex flex-wrap gap-2">
                                      {trade.tags.map((tag, index) => (
                                        <Badge key={index} variant="outline" className="text-xs border-cyan-400/40 text-cyan-300 bg-cyan-400/10">
                                          <Hash className="h-3 w-3 mr-1" />
                                          {tag}
                                        </Badge>
                                      ))}
                                    </div>
                                  </div>

                                  {/* Ratings */}
                                  <div className="grid grid-cols-2 gap-6">
                                    <div>
                                      <Label className="text-sm text-gray-300 mb-2 block">Setup Quality</Label>
                                      <div className="flex items-center gap-2">
                                        <div className="flex gap-1">
                                          {renderStars(trade.setupRating)}
                                        </div>
                                        <span className="text-sm text-gray-200">({trade.setupRating}/5)</span>
                                      </div>
                                    </div>
                                    <div>
                                      <Label className="text-sm text-gray-300 mb-2 block">Execution Quality</Label>
                                      <div className="flex items-center gap-2">
                                        <div className="flex gap-1">
                                          {renderStars(trade.executionRating)}
                                        </div>
                                        <span className="text-sm text-gray-200">({trade.executionRating}/5)</span>
                                      </div>
                                    </div>
                                  </div>

                                  {/* Emotion & Psychology */}
                                  <div>
                                    <Label className="text-sm text-gray-300 mb-2 block">Emotional State</Label>
                                    <div className="flex items-center gap-3">
                                      <Badge 
                                        className={`bg-gradient-to-r ${getEmotionData(trade.emotion).color} text-white px-3 py-1 shadow-lg font-medium`}
                                      >
                                        <Circle className="h-3 w-3 mr-2 fill-current" />
                                        {trade.emotion}
                                      </Badge>
                                    </div>
                                  </div>

                                  {/* Trade Notes */}
                                  <div>
                                    <Label className="text-sm text-gray-300 mb-2 block">Trade Notes</Label>
                                    <div className="bg-white/5 rounded-lg p-4 border border-white/20">
                                      <p className="text-sm text-gray-200 leading-relaxed mb-3">{trade.notes}</p>
                                      
                                      {/* Key Learnings */}
                                      <div className="space-y-2">
                                        <div className="flex items-start gap-2">
                                          <Lightbulb className="h-4 w-4 text-yellow-300 mt-0.5 flex-shrink-0" />
                                          <div>
                                            <span className="text-xs text-yellow-300 font-medium">Key Learning: </span>
                                            <span className="text-xs text-gray-200">{trade.learnings}</span>
                                          </div>
                                        </div>
                                        <div className="flex items-start gap-2">
                                          <Target className="h-4 w-4 text-blue-300 mt-0.5 flex-shrink-0" />
                                          <div>
                                            <span className="text-xs text-blue-300 font-medium">Improvement: </span>
                                            <span className="text-xs text-gray-200">{trade.improvements}</span>
                                          </div>
                                        </div>
                                      </div>
                                    </div>
                                  </div>

                                  {/* Action Buttons */}
                                  <div className="flex gap-3 pt-2">
                                    <Button 
                                      variant="outline" 
                                      className="border-cyan-400/40 text-cyan-300 hover:bg-cyan-400/20 hover:text-cyan-200"
                                    >
                                      <Edit className="h-4 w-4 mr-2" />
                                      Edit Journal
                                    </Button>
                                    <Button variant="outline" className="border-white/20 text-gray-200 hover:bg-white/10 hover:text-white">
                                      <Copy className="h-4 w-4 mr-2" />
                                      Duplicate
                                    </Button>
                                    <Button variant="outline" className="border-white/20 text-gray-200 hover:bg-white/10 hover:text-white">
                                      <Share className="h-4 w-4 mr-2" />
                                      Share
                                    </Button>
                                    <Button variant="outline" className="border-white/20 text-gray-200 hover:bg-white/10 hover:text-white">
                                      <Bookmark className="h-4 w-4 mr-2" />
                                      Bookmark
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>

              {sortedTrades.length === 0 && (
                <div className="text-center text-gray-300 py-16">
                  <BookOpen className="h-20 w-20 mx-auto mb-4 opacity-30" />
                  <p className="text-xl font-medium mb-2">No trades found</p>
                  <p className="text-sm">Try adjusting your search criteria or filters</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* AI Insights Modal */}
      <Dialog open={isAnalyticsOpen} onOpenChange={setIsAnalyticsOpen}>
        <DialogContent className="bg-gray-900 border-white/20 text-white max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-cyan-300">
              <Brain className="h-5 w-5" />
              AI Performance Insights
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="bg-gradient-to-br from-cyan-400/20 to-blue-500/10 p-4 rounded-lg border border-cyan-400/40">
              <h4 className="font-medium text-cyan-300 mb-2">Performance Summary</h4>
              <p className="text-sm text-gray-200">
                Your trading performance shows strong momentum with a {kpiData.winRate}% win rate and {kpiData.profitFactor} profit factor. 
                Focus on extending holding periods for winning trades to maximize gains.
              </p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-emerald-400/20 p-4 rounded-lg border border-emerald-400/40">
                <h5 className="font-medium text-emerald-300 mb-2">Strengths</h5>
                <ul className="text-sm text-gray-200 space-y-1">
                  <li>• Excellent setup identification</li>
                  <li>• Strong risk management</li>
                  <li>• Consistent execution</li>
                </ul>
              </div>
              
              <div className="bg-orange-400/20 p-4 rounded-lg border border-orange-400/40">
                <h5 className="font-medium text-orange-300 mb-2">Areas to Improve</h5>
                <ul className="text-sm text-gray-200 space-y-1">
                  <li>• Hold winning positions longer</li>
                  <li>• Reduce emotional trading</li>
                  <li>• Better position sizing</li>
                </ul>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TradeJournal;
