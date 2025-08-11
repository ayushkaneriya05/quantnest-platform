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
  Search
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
  const [viewMode, setViewMode] = useState("table");

  // Enhanced KPI Data with trends
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
    consecutiveLosses: 2
  };

  // Enhanced trade data with more fields
  const trades = [
    {
      id: 1,
      symbol: "TCS",
      entryDate: "2024-01-15",
      exitDate: "2024-01-18",
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
      notes: "Clean breakout above resistance with good volume. Entry was perfect at the breakout level. Exit could have been better - sold too early due to profit booking mindset.",
      commission: 25.50,
      slippage: 1.20,
      marketCap: "Large",
      sector: "IT",
      holdingPeriod: 3,
      riskReward: 1.8,
      maxFavorable: 3.2,
      maxAdverse: -0.8
    },
    {
      id: 2,
      symbol: "RELIANCE",
      entryDate: "2024-01-12",
      exitDate: "2024-01-16",
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
      notes: "Support level held initially but weak follow-through. Should have waited for stronger confirmation. Exit was premature due to fear of larger losses.",
      commission: 18.75,
      slippage: 2.10,
      marketCap: "Large",
      sector: "Energy",
      holdingPeriod: 4,
      riskReward: 0.9,
      maxFavorable: 0.8,
      maxAdverse: -1.2
    },
    {
      id: 3,
      symbol: "HDFCBANK",
      entryDate: "2024-01-10",
      exitDate: "2024-01-14",
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
      notes: "Perfect setup with 50 EMA crossing above 200 EMA. Strong momentum and volume confirmation. Held position well despite intraday volatility.",
      commission: 35.20,
      slippage: 0.80,
      marketCap: "Large",
      sector: "Banking",
      holdingPeriod: 4,
      riskReward: 2.1,
      maxFavorable: 2.8,
      maxAdverse: -0.5
    },
    {
      id: 4,
      symbol: "INFY",
      entryDate: "2024-01-08",
      exitDate: "2024-01-09",
      quantity: 75,
      direction: "Short",
      entryPrice: 1465.65,
      exitPrice: 1456.75,
      pnl: 667.50,
      pnlPercent: 0.61,
      strategy: "Gap Down",
      setupRating: 3,
      executionRating: 3,
      emotion: "Neutral",
      notes: "Quick gap down trade. Entry was okay but could have been more patient. Exit was well-timed before any reversal.",
      commission: 22.40,
      slippage: 1.50,
      marketCap: "Large",
      sector: "IT",
      holdingPeriod: 1,
      riskReward: 1.2,
      maxFavorable: 1.1,
      maxAdverse: -0.3
    },
    {
      id: 5,
      symbol: "ICICIBANK",
      entryDate: "2024-01-05",
      exitDate: "2024-01-08",
      quantity: 150,
      direction: "Long",
      entryPrice: 776.50,
      exitPrice: 789.30,
      pnl: 1920.00,
      pnlPercent: 1.65,
      strategy: "Earnings Play",
      setupRating: 4,
      executionRating: 4,
      emotion: "Optimistic",
      notes: "Good earnings expectations setup. Results were better than expected. Could have held longer for more gains but took profits at resistance.",
      commission: 28.80,
      slippage: 1.20,
      marketCap: "Large",
      sector: "Banking",
      holdingPeriod: 3,
      riskReward: 1.6,
      maxFavorable: 2.1,
      maxAdverse: -0.7
    }
  ];

  const filteredTrades = trades.filter(trade => {
    if (symbolFilter !== "all" && trade.symbol !== symbolFilter) return false;
    if (strategyFilter !== "all" && trade.strategy !== strategyFilter) return false;
    return true;
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

  const getEmotionColor = (emotion) => {
    switch (emotion.toLowerCase()) {
      case "confident": return "from-green-600 to-emerald-500";
      case "fearful": return "from-red-600 to-pink-500";
      case "greedy": return "from-orange-600 to-yellow-500";
      case "optimistic": return "from-blue-600 to-cyan-500";
      case "neutral": return "from-gray-600 to-slate-500";
      default: return "from-gray-600 to-slate-500";
    }
  };

  const renderStars = (rating) => {
    return Array.from({ length: 5 }, (_, i) => (
      <Star
        key={i}
        className={`h-4 w-4 ${
          i < rating ? "text-yellow-400 fill-current" : "text-gray-600"
        }`}
      />
    ));
  };

  const getTrendIcon = (trend) => {
    if (trend > 0) return <TrendingUp className="h-4 w-4 text-green-400" />;
    if (trend < 0) return <TrendingDown className="h-4 w-4 text-red-400" />;
    return <Activity className="h-4 w-4 text-gray-400" />;
  };

  const getTrendColor = (trend) => {
    if (trend > 0) return "text-green-400";
    if (trend < 0) return "text-red-400";
    return "text-gray-400";
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-black to-gray-900 text-white p-4 lg:p-6">
      {/* Enhanced Header */}
      <div className="mb-8">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-gradient-to-br from-qn-light-cyan/20 to-blue-500/20 rounded-xl border border-qn-light-cyan/30">
                <FileText className="h-8 w-8 text-qn-light-cyan" />
              </div>
              <div>
                <h1 className="text-2xl lg:text-3xl font-bold bg-gradient-to-r from-qn-light-cyan to-blue-400 bg-clip-text text-transparent">
                  Trade Journal
                </h1>
                <p className="text-sm text-gray-400">Advanced trading performance analytics</p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="flex gap-1">
              {["1W", "1M", "3M", "6M", "1Y"].map((range) => (
                <Button
                  key={range}
                  variant={selectedTimeRange === range ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSelectedTimeRange(range)}
                  className={`text-xs ${selectedTimeRange === range 
                    ? "bg-qn-light-cyan text-black" 
                    : "border-gray-600 text-gray-300"}`}
                >
                  {range}
                </Button>
              ))}
            </div>
            <Button variant="outline" size="sm" className="border-qn-light-cyan/30 text-qn-light-cyan hover:bg-qn-light-cyan hover:text-black">
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </div>
      </div>

      {/* Enhanced KPI Dashboard */}
      <div className="grid grid-cols-2 lg:grid-cols-5 xl:grid-cols-6 gap-4 mb-8">
        {/* Total P&L */}
        <Card className="col-span-2 bg-gradient-to-br from-green-900/20 to-emerald-800/10 border-green-700/30 backdrop-blur-xl">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-full bg-green-600/20">
                  <DollarSign className="h-6 w-6 text-green-400" />
                </div>
                <div>
                  <p className="text-sm text-green-300">Total P&L</p>
                  <p className="text-2xl font-bold text-green-400">
                    {kpiData.totalPnL >= 0 ? "+" : ""}₹{kpiData.totalPnL.toLocaleString()}
                  </p>
                  <div className="flex items-center gap-1 mt-1">
                    {getTrendIcon(kpiData.totalPnLTrend)}
                    <span className={`text-xs ${getTrendColor(kpiData.totalPnLTrend)}`}>
                      {kpiData.totalPnLTrend >= 0 ? "+" : ""}{kpiData.totalPnLTrend}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Win Rate */}
        <Card className="bg-gradient-to-br from-cyan-900/20 to-blue-800/10 border-cyan-700/30 backdrop-blur-xl">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-full bg-cyan-600/20">
                <Target className="h-6 w-6 text-cyan-400" />
              </div>
              <div className="flex-1">
                <p className="text-sm text-cyan-300">Win Rate</p>
                <div className="flex items-center gap-2 mb-1">
                  <Progress value={kpiData.winRate} className="flex-1 h-2" />
                  <span className="text-lg font-bold text-cyan-400">{kpiData.winRate}%</span>
                </div>
                <div className="flex items-center gap-1">
                  {getTrendIcon(kpiData.winRateTrend)}
                  <span className={`text-xs ${getTrendColor(kpiData.winRateTrend)}`}>
                    {kpiData.winRateTrend >= 0 ? "+" : ""}{kpiData.winRateTrend}%
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Profit Factor */}
        <Card className="bg-gradient-to-br from-purple-900/20 to-indigo-800/10 border-purple-700/30 backdrop-blur-xl">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-full bg-purple-600/20">
                <Gauge className="h-6 w-6 text-purple-400" />
              </div>
              <div>
                <p className="text-sm text-purple-300">Profit Factor</p>
                <p className="text-2xl font-bold text-purple-400">{kpiData.profitFactor}</p>
                <div className="flex items-center gap-1 mt-1">
                  {getTrendIcon(kpiData.profitFactorTrend)}
                  <span className={`text-xs ${getTrendColor(kpiData.profitFactorTrend)}`}>
                    {kpiData.profitFactorTrend >= 0 ? "+" : ""}{kpiData.profitFactorTrend}%
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Avg Winning Trade */}
        <Card className="bg-gradient-to-br from-emerald-900/20 to-green-800/10 border-emerald-700/30 backdrop-blur-xl">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-full bg-emerald-600/20">
                <TrendingUp className="h-6 w-6 text-emerald-400" />
              </div>
              <div>
                <p className="text-sm text-emerald-300">Avg Win</p>
                <p className="text-xl font-bold text-emerald-400">+₹{kpiData.avgWinningTrade.toLocaleString()}</p>
                <div className="flex items-center gap-1 mt-1">
                  {getTrendIcon(kpiData.avgWinningTradeTrend)}
                  <span className={`text-xs ${getTrendColor(kpiData.avgWinningTradeTrend)}`}>
                    {kpiData.avgWinningTradeTrend >= 0 ? "+" : ""}{kpiData.avgWinningTradeTrend}%
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Avg Losing Trade */}
        <Card className="bg-gradient-to-br from-red-900/20 to-pink-800/10 border-red-700/30 backdrop-blur-xl">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-full bg-red-600/20">
                <TrendingDown className="h-6 w-6 text-red-400" />
              </div>
              <div>
                <p className="text-sm text-red-300">Avg Loss</p>
                <p className="text-xl font-bold text-red-400">₹{kpiData.avgLosingTrade.toLocaleString()}</p>
                <div className="flex items-center gap-1 mt-1">
                  {getTrendIcon(-kpiData.avgLosingTradeTrend)}
                  <span className={`text-xs ${getTrendColor(-kpiData.avgLosingTradeTrend)}`}>
                    {kpiData.avgLosingTradeTrend >= 0 ? "+" : ""}{kpiData.avgLosingTradeTrend}%
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Secondary KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4 mb-8">
        <Card className="bg-gray-900/40 border-gray-700/50 backdrop-blur-xl">
          <CardContent className="p-4 text-center">
            <Trophy className="h-6 w-6 text-yellow-400 mx-auto mb-2" />
            <p className="text-xs text-gray-400 mb-1">Sharpe Ratio</p>
            <p className="text-lg font-bold text-white">{kpiData.sharpeRatio}</p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/40 border-gray-700/50 backdrop-blur-xl">
          <CardContent className="p-4 text-center">
            <AlertTriangle className="h-6 w-6 text-orange-400 mx-auto mb-2" />
            <p className="text-xs text-gray-400 mb-1">Max Drawdown</p>
            <p className="text-lg font-bold text-orange-400">-₹{kpiData.maxDrawdown.toLocaleString()}</p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/40 border-gray-700/50 backdrop-blur-xl">
          <CardContent className="p-4 text-center">
            <Clock className="h-6 w-6 text-blue-400 mx-auto mb-2" />
            <p className="text-xs text-gray-400 mb-1">Avg Hold Period</p>
            <p className="text-lg font-bold text-blue-400">{kpiData.avgHoldingPeriod}d</p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/40 border-gray-700/50 backdrop-blur-xl">
          <CardContent className="p-4 text-center">
            <Flame className="h-6 w-6 text-green-400 mx-auto mb-2" />
            <p className="text-xs text-gray-400 mb-1">Largest Win</p>
            <p className="text-lg font-bold text-green-400">+₹{kpiData.largestWin.toLocaleString()}</p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/40 border-gray-700/50 backdrop-blur-xl">
          <CardContent className="p-4 text-center">
            <CheckCircle className="h-6 w-6 text-cyan-400 mx-auto mb-2" />
            <p className="text-xs text-gray-400 mb-1">Win Streak</p>
            <p className="text-lg font-bold text-cyan-400">{kpiData.consecutiveWins}</p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/40 border-gray-700/50 backdrop-blur-xl">
          <CardContent className="p-4 text-center">
            <Calculator className="h-6 w-6 text-qn-light-cyan mx-auto mb-2" />
            <p className="text-xs text-gray-400 mb-1">Total Trades</p>
            <p className="text-lg font-bold text-qn-light-cyan">{kpiData.totalTrades}</p>
          </CardContent>
        </Card>
      </div>

      {/* Enhanced Trade History Table */}
      <Card className="bg-gradient-to-br from-gray-900/50 to-gray-800/30 border-gray-700/50 backdrop-blur-xl shadow-2xl">
        <CardHeader className="pb-4">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <CardTitle className="flex items-center gap-2 text-qn-light-cyan">
              <BarChart3 className="h-5 w-5" />
              Trade History & Analytics
            </CardTitle>
            <div className="flex flex-wrap gap-3">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input 
                  placeholder="Search trades..." 
                  className="pl-10 w-48 bg-gray-800/50 border-gray-600 text-white text-sm"
                />
              </div>

              {/* Filters */}
              <Select value={symbolFilter} onValueChange={setSymbolFilter}>
                <SelectTrigger className="w-32 bg-gray-800/50 border-gray-600 text-white">
                  <SelectValue placeholder="Symbol" />
                </SelectTrigger>
                <SelectContent className="bg-gray-800 border-gray-700">
                  <SelectItem value="all">All Symbols</SelectItem>
                  <SelectItem value="TCS">TCS</SelectItem>
                  <SelectItem value="RELIANCE">RELIANCE</SelectItem>
                  <SelectItem value="HDFCBANK">HDFCBANK</SelectItem>
                  <SelectItem value="INFY">INFY</SelectItem>
                  <SelectItem value="ICICIBANK">ICICIBANK</SelectItem>
                </SelectContent>
              </Select>

              <Select value={strategyFilter} onValueChange={setStrategyFilter}>
                <SelectTrigger className="w-40 bg-gray-800/50 border-gray-600 text-white">
                  <SelectValue placeholder="Strategy" />
                </SelectTrigger>
                <SelectContent className="bg-gray-800 border-gray-700">
                  <SelectItem value="all">All Strategies</SelectItem>
                  <SelectItem value="Breakout">Breakout</SelectItem>
                  <SelectItem value="Support Bounce">Support Bounce</SelectItem>
                  <SelectItem value="Moving Average Crossover">MA Crossover</SelectItem>
                  <SelectItem value="Gap Down">Gap Down</SelectItem>
                  <SelectItem value="Earnings Play">Earnings Play</SelectItem>
                </SelectContent>
              </Select>

              <Button variant="outline" size="sm" className="border-gray-600 text-gray-300">
                <Settings className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left p-3 text-gray-400">
                    <Button variant="ghost" onClick={() => handleSort("symbol")} className="text-gray-400 hover:text-white p-0 font-medium">
                      Symbol
                      {sortField === "symbol" && (sortDirection === "asc" ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />)}
                    </Button>
                  </th>
                  <th className="text-left p-3 text-gray-400">
                    <Button variant="ghost" onClick={() => handleSort("entryDate")} className="text-gray-400 hover:text-white p-0 font-medium">
                      Entry Date
                      {sortField === "entryDate" && (sortDirection === "asc" ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />)}
                    </Button>
                  </th>
                  <th className="text-left p-3 text-gray-400">Direction</th>
                  <th className="text-left p-3 text-gray-400">Strategy</th>
                  <th className="text-left p-3 text-gray-400">
                    <Button variant="ghost" onClick={() => handleSort("pnl")} className="text-gray-400 hover:text-white p-0 font-medium">
                      P&L (₹)
                      {sortField === "pnl" && (sortDirection === "asc" ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />)}
                    </Button>
                  </th>
                  <th className="text-left p-3 text-gray-400">R:R</th>
                  <th className="text-left p-3 text-gray-400">Hold</th>
                  <th className="text-center p-3 text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedTrades.map((trade) => (
                  <React.Fragment key={trade.id}>
                    <tr
                      className="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer transition-all duration-200"
                      onClick={() => setExpandedRow(expandedRow === trade.id ? null : trade.id)}
                    >
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{trade.symbol}</span>
                          <Badge variant="outline" className="text-xs border-gray-600 text-gray-400">
                            {trade.sector}
                          </Badge>
                        </div>
                      </td>
                      <td className="p-3 text-gray-300 text-sm">{trade.entryDate}</td>
                      <td className="p-3">
                        <Badge 
                          variant={trade.direction === "Long" ? "default" : "destructive"} 
                          className={`text-xs ${trade.direction === "Long" ? "bg-green-600" : "bg-red-600"}`}
                        >
                          {trade.direction === "Long" ? (
                            <ArrowUpRight className="h-3 w-3 mr-1" />
                          ) : (
                            <ArrowDownRight className="h-3 w-3 mr-1" />
                          )}
                          {trade.direction}
                        </Badge>
                      </td>
                      <td className="p-3 text-gray-300 text-sm">{trade.strategy}</td>
                      <td className="p-3">
                        <div className="flex flex-col">
                          <span className={`font-medium ${trade.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                            {trade.pnl >= 0 ? "+" : ""}₹{trade.pnl.toLocaleString()}
                          </span>
                          <span className={`text-xs ${trade.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                            {trade.pnl >= 0 ? "+" : ""}{trade.pnlPercent}%
                          </span>
                        </div>
                      </td>
                      <td className="p-3">
                        <Badge 
                          variant="outline" 
                          className={`text-xs ${trade.riskReward >= 1.5 ? "border-green-600 text-green-400" : trade.riskReward >= 1 ? "border-yellow-600 text-yellow-400" : "border-red-600 text-red-400"}`}
                        >
                          1:{trade.riskReward}
                        </Badge>
                      </td>
                      <td className="p-3 text-gray-300 text-sm">{trade.holdingPeriod}d</td>
                      <td className="p-3 text-center">
                        <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
                          {expandedRow === trade.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        </Button>
                      </td>
                    </tr>
                    {expandedRow === trade.id && (
                      <tr>
                        <td colSpan="8" className="p-0">
                          <div className="bg-gradient-to-br from-gray-800/50 to-gray-700/30 p-6 border-t border-gray-600/30 backdrop-blur-sm">
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                              {/* Chart Placeholder */}
                              <div className="lg:col-span-1">
                                <Card className="bg-gray-700/30 border-gray-600/30 h-48">
                                  <CardContent className="p-4 h-full flex flex-col items-center justify-center">
                                    <BarChart3 className="h-12 w-12 text-gray-400 opacity-50 mb-3" />
                                    <p className="text-sm font-medium text-gray-300 mb-2">Trade Analysis</p>
                                    <div className="text-xs text-gray-400 space-y-1 text-center">
                                      <p>Entry: ₹{trade.entryPrice}</p>
                                      <p>Exit: ₹{trade.exitPrice}</p>
                                      <p>Max Favorable: +{trade.maxFavorable}%</p>
                                      <p>Max Adverse: {trade.maxAdverse}%</p>
                                    </div>
                                  </CardContent>
                                </Card>
                              </div>

                              {/* Trade Details */}
                              <div className="lg:col-span-2 space-y-6">
                                {/* Performance Metrics */}
                                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                                  <div className="bg-gray-800/30 p-3 rounded-lg border border-gray-600/30">
                                    <p className="text-xs text-gray-400 mb-1">Commission</p>
                                    <p className="text-sm font-medium text-red-400">₹{trade.commission}</p>
                                  </div>
                                  <div className="bg-gray-800/30 p-3 rounded-lg border border-gray-600/30">
                                    <p className="text-xs text-gray-400 mb-1">Slippage</p>
                                    <p className="text-sm font-medium text-orange-400">₹{trade.slippage}</p>
                                  </div>
                                  <div className="bg-gray-800/30 p-3 rounded-lg border border-gray-600/30">
                                    <p className="text-xs text-gray-400 mb-1">Market Cap</p>
                                    <p className="text-sm font-medium text-blue-400">{trade.marketCap}</p>
                                  </div>
                                  <div className="bg-gray-800/30 p-3 rounded-lg border border-gray-600/30">
                                    <p className="text-xs text-gray-400 mb-1">Quantity</p>
                                    <p className="text-sm font-medium text-cyan-400">{trade.quantity}</p>
                                  </div>
                                </div>

                                {/* Ratings */}
                                <div className="grid grid-cols-2 gap-6">
                                  <div>
                                    <Label className="text-sm text-gray-400 mb-2 block">Setup Rating</Label>
                                    <div className="flex gap-1">
                                      {renderStars(trade.setupRating)}
                                    </div>
                                  </div>
                                  <div>
                                    <Label className="text-sm text-gray-400 mb-2 block">Execution Rating</Label>
                                    <div className="flex gap-1">
                                      {renderStars(trade.executionRating)}
                                    </div>
                                  </div>
                                </div>

                                {/* Emotion Tag */}
                                <div>
                                  <Label className="text-sm text-gray-400 mb-2 block">Emotional State</Label>
                                  <Badge className={`bg-gradient-to-r ${getEmotionColor(trade.emotion)} text-white px-3 py-1`}>
                                    <Circle className="h-3 w-3 mr-2 fill-current" />
                                    {trade.emotion}
                                  </Badge>
                                </div>

                                {/* Notes */}
                                <div>
                                  <Label className="text-sm text-gray-400 mb-2 block">Trade Notes</Label>
                                  <div className="bg-gradient-to-br from-gray-700/40 to-gray-600/30 rounded-lg p-4 border border-gray-600/30 backdrop-blur-sm">
                                    <p className="text-sm text-gray-300 leading-relaxed">{trade.notes}</p>
                                  </div>
                                </div>

                                {/* Action Buttons */}
                                <div className="flex gap-3 pt-2">
                                  <Button variant="outline" className="border-qn-light-cyan text-qn-light-cyan hover:bg-qn-light-cyan hover:text-black">
                                    <Edit className="h-4 w-4 mr-2" />
                                    Edit Journal
                                  </Button>
                                  <Button variant="outline" className="border-gray-600 text-gray-300 hover:bg-gray-800/50">
                                    <Bookmark className="h-4 w-4 mr-2" />
                                    Bookmark
                                  </Button>
                                  <Button variant="outline" className="border-gray-600 text-gray-300 hover:bg-gray-800/50">
                                    <Share className="h-4 w-4 mr-2" />
                                    Share
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
              <div className="text-center text-gray-400 py-12">
                <Target className="h-16 w-16 mx-auto mb-4 opacity-50" />
                <p className="text-xl font-medium mb-2">No trades found</p>
                <p className="text-sm">Try adjusting your filters to see more results</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default TradeJournal;
