import React, { useState } from "react";
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
  Gauge
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

  // KPI Data
  const kpiData = {
    totalPnL: 45650,
    winRate: 67.5,
    profitFactor: 1.85,
    avgWinningTrade: 2500,
    avgLosingTrade: -1200,
    totalTrades: 42,
    winningTrades: 28,
    losingTrades: 14
  };

  // Trade History Data
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
      notes: "Clean breakout above resistance with good volume. Entry was perfect at the breakout level. Exit could have been better - sold too early due to profit booking mindset."
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
      notes: "Support level held initially but weak follow-through. Should have waited for stronger confirmation. Exit was premature due to fear of larger losses."
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
      notes: "Perfect setup with 50 EMA crossing above 200 EMA. Strong momentum and volume confirmation. Held position well despite intraday volatility."
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
      notes: "Quick gap down trade. Entry was okay but could have been more patient. Exit was well-timed before any reversal."
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
      notes: "Good earnings expectations setup. Results were better than expected. Could have held longer for more gains but took profits at resistance."
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
      case "confident": return "bg-green-600";
      case "fearful": return "bg-red-600";
      case "greedy": return "bg-orange-600";
      case "optimistic": return "bg-blue-600";
      default: return "bg-gray-600";
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

  return (
    <div className="min-h-screen bg-black text-white p-6">
      <div className="space-y-6">
        {/* KPI Dashboard */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
          {/* Total P&L */}
          <Card className="bg-gray-900/50 border-gray-800/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className={`p-3 rounded-full ${kpiData.totalPnL >= 0 ? "bg-green-600/20" : "bg-red-600/20"}`}>
                  <DollarSign className={`h-6 w-6 ${kpiData.totalPnL >= 0 ? "text-green-400" : "text-red-400"}`} />
                </div>
                <div>
                  <p className="text-sm text-gray-400">Total P&L</p>
                  <p className={`text-2xl font-bold ${kpiData.totalPnL >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {kpiData.totalPnL >= 0 ? "+" : ""}₹{kpiData.totalPnL.toLocaleString()}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Win Rate */}
          <Card className="bg-gray-900/50 border-gray-800/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-full bg-qn-light-cyan/20">
                  <Percent className="h-6 w-6 text-qn-light-cyan" />
                </div>
                <div className="flex-1">
                  <p className="text-sm text-gray-400">Win Rate</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1">
                      <Progress value={kpiData.winRate} className="h-2" />
                    </div>
                    <span className="text-lg font-bold text-qn-light-cyan">{kpiData.winRate}%</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Profit Factor */}
          <Card className="bg-gray-900/50 border-gray-800/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-full bg-blue-600/20">
                  <Gauge className="h-6 w-6 text-blue-400" />
                </div>
                <div>
                  <p className="text-sm text-gray-400">Profit Factor</p>
                  <p className="text-2xl font-bold text-white">{kpiData.profitFactor}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Average Winning Trade */}
          <Card className="bg-gray-900/50 border-gray-800/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-full bg-green-600/20">
                  <TrendingUp className="h-6 w-6 text-green-400" />
                </div>
                <div>
                  <p className="text-sm text-gray-400">Avg Winning Trade</p>
                  <p className="text-2xl font-bold text-green-400">+₹{kpiData.avgWinningTrade.toLocaleString()}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Average Losing Trade */}
          <Card className="bg-gray-900/50 border-gray-800/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-full bg-red-600/20">
                  <TrendingDown className="h-6 w-6 text-red-400" />
                </div>
                <div>
                  <p className="text-sm text-gray-400">Avg Losing Trade</p>
                  <p className="text-2xl font-bold text-red-400">₹{kpiData.avgLosingTrade.toLocaleString()}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Trade History Table */}
        <Card className="bg-gray-900/50 border-gray-800/50">
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle className="text-qn-light-cyan">Trade History</CardTitle>
              <div className="flex gap-3">
                {/* Filters */}
                <Select value={symbolFilter} onValueChange={setSymbolFilter}>
                  <SelectTrigger className="w-32 bg-gray-800 border-gray-700">
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
                  <SelectTrigger className="w-40 bg-gray-800 border-gray-700">
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
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left p-3 text-gray-400">
                      <Button variant="ghost" onClick={() => handleSort("symbol")} className="text-gray-400 hover:text-white p-0">
                        Symbol
                        {sortField === "symbol" && (sortDirection === "asc" ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />)}
                      </Button>
                    </th>
                    <th className="text-left p-3 text-gray-400">
                      <Button variant="ghost" onClick={() => handleSort("entryDate")} className="text-gray-400 hover:text-white p-0">
                        Entry Date
                        {sortField === "entryDate" && (sortDirection === "asc" ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />)}
                      </Button>
                    </th>
                    <th className="text-left p-3 text-gray-400">Exit Date</th>
                    <th className="text-left p-3 text-gray-400">Qty</th>
                    <th className="text-left p-3 text-gray-400">Direction</th>
                    <th className="text-left p-3 text-gray-400">
                      <Button variant="ghost" onClick={() => handleSort("pnl")} className="text-gray-400 hover:text-white p-0">
                        P&L (₹)
                        {sortField === "pnl" && (sortDirection === "asc" ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />)}
                      </Button>
                    </th>
                    <th className="text-left p-3 text-gray-400">Strategy</th>
                    <th className="text-center p-3 text-gray-400">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedTrades.map((trade) => (
                    <React.Fragment key={trade.id}>
                      <tr
                        key={trade.id}
                        className="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer"
                        onClick={() => setExpandedRow(expandedRow === trade.id ? null : trade.id)}
                      >
                        <td className="p-3 font-medium">{trade.symbol}</td>
                        <td className="p-3 text-gray-300">{trade.entryDate}</td>
                        <td className="p-3 text-gray-300">{trade.exitDate}</td>
                        <td className="p-3 text-gray-300">{trade.quantity}</td>
                        <td className="p-3">
                          <Badge variant={trade.direction === "Long" ? "default" : "destructive"} className="text-xs">
                            {trade.direction}
                          </Badge>
                        </td>
                        <td className="p-3">
                          <span className={`font-medium ${trade.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                            {trade.pnl >= 0 ? "+" : ""}₹{trade.pnl.toLocaleString()}
                          </span>
                          <div className={`text-xs ${trade.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                            {trade.pnl >= 0 ? "+" : ""}{trade.pnlPercent}%
                          </div>
                        </td>
                        <td className="p-3 text-gray-300">{trade.strategy}</td>
                        <td className="p-3 text-center">
                          <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
                            {expandedRow === trade.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </Button>
                        </td>
                      </tr>
                      {expandedRow === trade.id && (
                        <tr>
                          <td colSpan="8" className="p-0">
                            <div className="bg-gray-800/30 p-6 border-t border-gray-700">
                              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                {/* Mini Chart Placeholder */}
                                <div className="lg:col-span-1">
                                  <div className="bg-gray-700/30 rounded-lg p-4 h-48 flex items-center justify-center">
                                    <div className="text-center text-gray-400">
                                      <BarChart3 className="h-8 w-8 mx-auto mb-2 opacity-50" />
                                      <p className="text-sm">Trade Chart</p>
                                      <p className="text-xs">Entry: ₹{trade.entryPrice}</p>
                                      <p className="text-xs">Exit: ₹{trade.exitPrice}</p>
                                    </div>
                                  </div>
                                </div>

                                {/* Trade Details */}
                                <div className="lg:col-span-2 space-y-4">
                                  {/* Ratings */}
                                  <div className="grid grid-cols-2 gap-4">
                                    <div>
                                      <Label className="text-sm text-gray-400">Setup Rating</Label>
                                      <div className="flex gap-1 mt-1">
                                        {renderStars(trade.setupRating)}
                                      </div>
                                    </div>
                                    <div>
                                      <Label className="text-sm text-gray-400">Execution Rating</Label>
                                      <div className="flex gap-1 mt-1">
                                        {renderStars(trade.executionRating)}
                                      </div>
                                    </div>
                                  </div>

                                  {/* Emotion Tag */}
                                  <div>
                                    <Label className="text-sm text-gray-400">Emotion</Label>
                                    <div className="mt-1">
                                      <Badge className={`${getEmotionColor(trade.emotion)} text-white`}>
                                        {trade.emotion}
                                      </Badge>
                                    </div>
                                  </div>

                                  {/* Notes */}
                                  <div>
                                    <Label className="text-sm text-gray-400">Trade Notes</Label>
                                    <div className="mt-1 bg-gray-700/30 rounded-lg p-3 text-sm text-gray-300 leading-relaxed max-h-32 overflow-y-auto">
                                      {trade.notes}
                                    </div>
                                  </div>

                                  {/* Action Button */}
                                  <div className="flex justify-end">
                                    <Button variant="outline" className="border-qn-light-cyan text-qn-light-cyan hover:bg-qn-light-cyan hover:text-black">
                                      <Edit className="h-4 w-4 mr-2" />
                                      Edit Journal
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
                  <Target className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p className="text-lg font-medium">No trades found</p>
                  <p className="text-sm">Try adjusting your filters</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default TradeJournal;
