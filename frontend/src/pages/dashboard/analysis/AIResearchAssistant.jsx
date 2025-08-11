import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  Search, 
  Bookmark, 
  Share, 
  TrendingUp, 
  AlertTriangle,
  Lightbulb,
  Target,
  Clock,
  Star,
  ExternalLink,
  Filter,
  Brain,
  Zap,
  Globe,
  MessageSquare,
  Calendar,
  ThumbsUp,
  ThumbsDown,
  Copy,
  Download,
  Sparkles,
  Activity,
  TrendingDown,
  BarChart3,
  DollarSign,
  Users,
  Flame,
  Eye,
  ArrowRight,
  ChevronRight,
  Bot,
  Mic,
  Send,
  RefreshCw
} from "lucide-react";
import { usePageTitle } from "@/hooks/use-page-title";

const AIResearchAssistant = () => {
  usePageTitle("AI Research Assistant");

  const [query, setQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [bookmarkedItems, setBookmarkedItems] = useState(new Set([1, 3]));
  const [isLoading, setIsLoading] = useState(false);
  const [likedInsights, setLikedInsights] = useState(new Set());
  const [searchHistory] = useState([
    "Market outlook for next week",
    "NIFTY technical analysis", 
    "Best performing sectors",
    "Portfolio rebalancing advice"
  ]);

  const categories = [
    { id: "all", label: "All Insights", count: 24, icon: Globe, color: "text-blue-400" },
    { id: "market", label: "Market Analysis", count: 8, icon: TrendingUp, color: "text-green-400" },
    { id: "stocks", label: "Stock Insights", count: 12, icon: BarChart3, color: "text-purple-400" },
    { id: "portfolio", label: "Portfolio Alerts", count: 3, icon: Target, color: "text-orange-400" },
    { id: "bookmarks", label: "Bookmarked", count: bookmarkedItems.size, icon: Bookmark, color: "text-yellow-400" },
  ];

  const quickSuggestions = [
    { text: "Analyze NIFTY 50 trend", icon: TrendingUp, category: "Technical Analysis" },
    { text: "Top gainers today", icon: Flame, category: "Market Movers" },
    { text: "Sector rotation opportunities", icon: Activity, category: "Sector Analysis" },
    { text: "Risk assessment for my portfolio", icon: AlertTriangle, category: "Risk Management" },
    { text: "Earnings calendar this week", icon: Calendar, category: "Fundamental Analysis" },
    { text: "Options strategy suggestions", icon: Target, category: "Options Trading" }
  ];

  const insights = [
    {
      id: 1,
      type: "MARKET MOVER",
      typeColor: "from-green-600 to-emerald-500",
      title: "NIFTY 50 breaks above key resistance at 19,800",
      summary: "Strong buying interest in banking and IT sectors pushes the index to new highs. Technical indicators suggest further upside momentum with next target at 20,200. Volume confirmation supports the breakout pattern.",
      relatedSymbols: ["NIFTY50", "HDFCBANK", "TCS", "INFY"],
      confidence: 92,
      source: "QuantNest AI",
      timestamp: "15 minutes ago",
      category: "market",
      views: 1247,
      likes: 89,
      aiInsight: "High probability breakout with strong momentum indicators",
      tags: ["Bullish", "Breakout", "High Volume"],
      riskLevel: "Medium"
    },
    {
      id: 2,
      type: "STOCK ALERT",
      typeColor: "from-blue-600 to-cyan-500",
      title: "RELIANCE shows strong reversal pattern",
      summary: "After testing support at ₹2,400, RELIANCE has formed a bullish engulfing pattern with high volume. RSI oversold conditions present a good buying opportunity with target at ₹2,550.",
      relatedSymbols: ["RELIANCE"],
      confidence: 87,
      source: "Technical Analysis Engine",
      timestamp: "32 minutes ago",
      category: "stocks",
      views: 892,
      likes: 64,
      aiInsight: "Strong reversal pattern with volume confirmation",
      tags: ["Reversal", "Support", "RSI Oversold"],
      riskLevel: "Low"
    },
    {
      id: 3,
      type: "EARNINGS INSIGHT",
      typeColor: "from-purple-600 to-pink-500",
      title: "TCS Q3 results exceed expectations",
      summary: "Revenue growth of 13.2% YoY and improved margin guidance boost investor confidence. Strong dollar revenue and deal wins in BFSI segment highlight robust fundamentals. Stock price target revised upward.",
      relatedSymbols: ["TCS", "INFY", "WIPRO"],
      confidence: 95,
      source: "Earnings Analysis",
      timestamp: "1 hour ago",
      category: "stocks",
      views: 2156,
      likes: 143,
      aiInsight: "Exceptional earnings beat with strong forward guidance",
      tags: ["Earnings Beat", "Revenue Growth", "IT Sector"],
      riskLevel: "Low"
    },
    {
      id: 4,
      type: "PORTFOLIO ALERT",
      typeColor: "from-orange-600 to-red-500",
      title: "Portfolio concentration risk increasing",
      summary: "Banking sector exposure has reached 35% of your portfolio. Consider rebalancing to reduce sector-specific risks and improve diversification across different market segments.",
      relatedSymbols: ["HDFCBANK", "ICICIBANK", "AXISBANK"],
      confidence: 88,
      source: "Portfolio Analyzer",
      timestamp: "2 hours ago",
      category: "portfolio",
      views: 445,
      likes: 23,
      aiInsight: "Immediate attention required for risk management",
      tags: ["Risk Alert", "Diversification", "Banking"],
      riskLevel: "High"
    },
    {
      id: 5,
      type: "SECTOR ROTATION",
      typeColor: "from-cyan-600 to-blue-500",
      title: "IT sector gaining momentum over pharma",
      summary: "Relative strength rotation favors IT stocks as global tech spending recovers. Pharma sector showing signs of fatigue after recent outperformance. Consider rotating positions strategically.",
      relatedSymbols: ["TCS", "INFY", "HCLTECH", "DRREDDY", "SUNPHARMA"],
      confidence: 84,
      source: "Sector Analysis",
      timestamp: "3 hours ago",
      category: "market",
      views: 1078,
      likes: 67,
      aiInsight: "Strong sector rotation signals detected",
      tags: ["Sector Rotation", "IT Outperformance", "Strategy"],
      riskLevel: "Medium"
    },
    {
      id: 6,
      type: "MOMENTUM PLAY",
      typeColor: "from-red-600 to-pink-500",
      title: "HDFC Bank showing weakness below ₹1,500",
      summary: "Failed breakout attempt and increasing selling pressure suggest further downside. Key support at ₹1,450 crucial for preventing deeper correction. Consider defensive strategies.",
      relatedSymbols: ["HDFCBANK"],
      confidence: 78,
      source: "Momentum Scanner",
      timestamp: "4 hours ago",
      category: "stocks",
      views: 734,
      likes: 31,
      aiInsight: "Bearish momentum with key support test ahead",
      tags: ["Bearish", "Support Test", "Banking"],
      riskLevel: "High"
    }
  ];

  const filteredInsights = insights.filter(insight => {
    if (activeCategory === "all") return true;
    if (activeCategory === "bookmarks") return bookmarkedItems.has(insight.id);
    return insight.category === activeCategory;
  });

  const handleBookmark = (insightId) => {
    const newBookmarks = new Set(bookmarkedItems);
    if (newBookmarks.has(insightId)) {
      newBookmarks.delete(insightId);
    } else {
      newBookmarks.add(insightId);
    }
    setBookmarkedItems(newBookmarks);
  };

  const handleLike = (insightId) => {
    const newLikes = new Set(likedInsights);
    if (newLikes.has(insightId)) {
      newLikes.delete(insightId);
    } else {
      newLikes.add(insightId);
    }
    setLikedInsights(newLikes);
  };

  const handleSearch = () => {
    if (query.trim()) {
      setIsLoading(true);
      setTimeout(() => {
        setIsLoading(false);
        console.log("Searching for:", query);
      }, 2000);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const getRiskColor = (risk) => {
    switch (risk) {
      case "Low": return "text-green-400 bg-green-900/20 border-green-700/30";
      case "Medium": return "text-yellow-400 bg-yellow-900/20 border-yellow-700/30";
      case "High": return "text-red-400 bg-red-900/20 border-red-700/30";
      default: return "text-gray-400 bg-gray-900/20 border-gray-700/30";
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-black to-gray-900 text-white p-4 lg:p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-gradient-to-br from-qn-light-cyan/20 to-blue-500/20 rounded-xl border border-qn-light-cyan/30">
                <Brain className="h-8 w-8 text-qn-light-cyan" />
              </div>
              <div>
                <h1 className="text-2xl lg:text-3xl font-bold bg-gradient-to-r from-qn-light-cyan to-blue-400 bg-clip-text text-transparent">
                  AI Research Assistant
                </h1>
                <p className="text-sm text-gray-400">Powered by advanced market intelligence</p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <Badge className="bg-green-600/20 text-green-400 border-green-600/30">
              <Bot className="h-3 w-3 mr-1" />
              AI Online
            </Badge>
            <Button variant="outline" size="sm" className="border-qn-light-cyan/30 text-qn-light-cyan hover:bg-qn-light-cyan hover:text-black">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column - Control Panel */}
        <div className="lg:col-span-4 space-y-6">
          {/* AI Query Input */}
          <Card className="bg-gradient-to-br from-gray-900/50 to-gray-800/30 border-gray-700/50 backdrop-blur-xl shadow-2xl">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-qn-light-cyan">
                <MessageSquare className="h-5 w-5" />
                Ask AI Assistant
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="pl-12 pr-12 py-4 bg-gray-800/50 border-gray-600 text-white text-lg placeholder:text-gray-400 focus:border-qn-light-cyan transition-all duration-200"
                  placeholder="Ask anything about markets, stocks, or your portfolio..."
                />
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex gap-2">
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-gray-400 hover:text-white">
                    <Mic className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              
              <Button 
                onClick={handleSearch}
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-qn-light-cyan to-blue-400 text-black hover:from-qn-light-cyan/80 hover:to-blue-400/80 font-semibold py-3 relative overflow-hidden group"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent transform -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
                {isLoading ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Ask AI Assistant
                  </>
                )}
              </Button>

              {isLoading && (
                <div className="bg-gray-800/30 p-4 rounded-lg border border-qn-light-cyan/30 animate-pulse">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-qn-light-cyan rounded-full animate-pulse"></div>
                    <div className="w-2 h-2 bg-qn-light-cyan rounded-full animate-pulse" style={{animationDelay: '0.1s'}}></div>
                    <div className="w-2 h-2 bg-qn-light-cyan rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
                    <span className="text-sm text-qn-light-cyan">AI is thinking...</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick Suggestions */}
          <Card className="bg-gradient-to-br from-purple-900/20 to-indigo-800/10 border-purple-700/30 backdrop-blur-xl">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-purple-400 text-sm">
                <Lightbulb className="h-4 w-4" />
                Quick Suggestions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {quickSuggestions.map((suggestion, index) => (
                <Button
                  key={index}
                  variant="outline"
                  onClick={() => setQuery(suggestion.text)}
                  className="w-full justify-start text-left border-purple-700/30 text-gray-300 hover:bg-purple-800/20 hover:border-purple-600/50 transition-all duration-200 group"
                >
                  <suggestion.icon className="h-4 w-4 mr-3 text-purple-400 group-hover:text-purple-300" />
                  <div className="flex-1">
                    <div className="text-sm">{suggestion.text}</div>
                    <div className="text-xs text-gray-500">{suggestion.category}</div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-gray-500 group-hover:text-purple-400" />
                </Button>
              ))}
            </CardContent>
          </Card>

          {/* Categories */}
          <Card className="bg-gradient-to-br from-gray-900/50 to-gray-800/30 border-gray-700/50 backdrop-blur-xl">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-qn-light-cyan">
                <Filter className="h-5 w-5" />
                Categories
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {categories.map((category) => {
                const IconComponent = category.icon;
                return (
                  <Button
                    key={category.id}
                    variant={activeCategory === category.id ? "default" : "outline"}
                    onClick={() => setActiveCategory(category.id)}
                    className={`w-full justify-between group transition-all duration-200 ${
                      activeCategory === category.id
                        ? "bg-gradient-to-r from-qn-light-cyan to-blue-400 text-black hover:from-qn-light-cyan/80 hover:to-blue-400/80"
                        : "border-gray-700/50 text-gray-300 hover:bg-gray-800/50 hover:border-gray-600"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <IconComponent className={`h-4 w-4 ${activeCategory === category.id ? "text-black" : category.color}`} />
                      <span>{category.label}</span>
                    </div>
                    <Badge 
                      variant="secondary" 
                      className={`${activeCategory === category.id ? "bg-black/20 text-black" : "bg-gray-700 text-gray-300"}`}
                    >
                      {category.count}
                    </Badge>
                  </Button>
                );
              })}
            </CardContent>
          </Card>

          {/* Search History */}
          <Card className="bg-gradient-to-br from-gray-900/30 to-gray-800/20 border-gray-700/30 backdrop-blur-xl">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-gray-400 text-sm">
                <Clock className="h-4 w-4" />
                Recent Searches
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {searchHistory.map((search, index) => (
                <button
                  key={index}
                  onClick={() => setQuery(search)}
                  className="w-full text-left text-xs text-gray-500 hover:text-gray-300 py-1 px-2 rounded hover:bg-gray-800/30 transition-colors"
                >
                  {search}
                </button>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Insights Feed */}
        <div className="lg:col-span-8">
          <Card className="bg-gradient-to-br from-gray-900/50 to-gray-800/30 border-gray-700/50 backdrop-blur-xl h-[calc(100vh-12rem)] shadow-2xl">
            <CardHeader className="pb-4">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                <CardTitle className="flex items-center gap-2 text-qn-light-cyan">
                  <Sparkles className="h-5 w-5" />
                  AI Insights Feed
                </CardTitle>
                <div className="flex items-center gap-3">
                  <Badge variant="secondary" className="bg-gray-700 text-gray-300">
                    {filteredInsights.length} insights
                  </Badge>
                  <Button variant="outline" size="sm" className="border-gray-600 text-gray-300">
                    <Download className="h-4 w-4 mr-2" />
                    Export
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="h-full overflow-hidden">
              <div className="h-full overflow-y-auto space-y-6 pr-2">
                {filteredInsights.map((insight) => (
                  <Card key={insight.id} className="bg-gradient-to-br from-gray-800/50 to-gray-700/30 border-gray-600/50 hover:border-gray-500/50 transition-all duration-300 hover:shadow-xl group">
                    <CardContent className="p-6">
                      {/* Header */}
                      <div className="flex justify-between items-start mb-4">
                        <div className="flex items-center gap-3">
                          <Badge className={`bg-gradient-to-r ${insight.typeColor} text-white text-xs px-3 py-1 shadow-lg`}>
                            {insight.type}
                          </Badge>
                          <Badge variant="outline" className={`text-xs px-2 py-1 ${getRiskColor(insight.riskLevel)}`}>
                            {insight.riskLevel} Risk
                          </Badge>
                          <span className="text-xs text-gray-400 flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {insight.timestamp}
                          </span>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleBookmark(insight.id)}
                            className={`h-8 w-8 p-0 transition-colors ${
                              bookmarkedItems.has(insight.id) 
                                ? "text-yellow-400 hover:text-yellow-300" 
                                : "text-gray-400 hover:text-gray-300"
                            }`}
                          >
                            <Bookmark className={`h-4 w-4 ${bookmarkedItems.has(insight.id) ? "fill-current" : ""}`} />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-gray-400 hover:text-gray-300"
                          >
                            <Share className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>

                      {/* Title */}
                      <h3 className="text-xl font-semibold text-white mb-3 group-hover:text-qn-light-cyan transition-colors">
                        {insight.title}
                      </h3>

                      {/* AI Insight Badge */}
                      <div className="mb-3">
                        <Badge className="bg-gradient-to-r from-qn-light-cyan/20 to-blue-500/20 text-qn-light-cyan border-qn-light-cyan/30">
                          <Bot className="h-3 w-3 mr-1" />
                          {insight.aiInsight}
                        </Badge>
                      </div>

                      {/* Content */}
                      <p className="text-gray-300 mb-4 leading-relaxed">{insight.summary}</p>

                      {/* Tags */}
                      <div className="flex flex-wrap gap-2 mb-4">
                        {insight.tags.map((tag, index) => (
                          <Badge key={index} variant="outline" className="text-xs border-gray-600 text-gray-400">
                            {tag}
                          </Badge>
                        ))}
                      </div>

                      {/* Data Fields */}
                      <div className="space-y-4">
                        {/* Related Symbols */}
                        <div>
                          <span className="text-sm text-gray-400 block mb-2">Related Symbols:</span>
                          <div className="flex flex-wrap gap-2">
                            {insight.relatedSymbols.map((symbol) => (
                              <Badge
                                key={symbol}
                                variant="outline"
                                className="border-qn-light-cyan/30 text-qn-light-cyan hover:bg-qn-light-cyan hover:text-black cursor-pointer transition-all duration-200 group"
                              >
                                {symbol}
                                <ExternalLink className="h-3 w-3 ml-1 group-hover:scale-110 transition-transform" />
                              </Badge>
                            ))}
                          </div>
                        </div>

                        {/* Bottom Row */}
                        <div className="flex items-center justify-between pt-3 border-t border-gray-600/30">
                          <div className="flex items-center gap-4">
                            {/* Confidence Score */}
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-gray-400">Confidence:</span>
                              <div className="flex items-center gap-2">
                                <Progress value={insight.confidence} className="w-16 h-2" />
                                <span className="text-sm font-medium text-qn-light-cyan">{insight.confidence}%</span>
                              </div>
                            </div>
                            
                            {/* Engagement */}
                            <div className="flex items-center gap-3 text-sm text-gray-400">
                              <div className="flex items-center gap-1">
                                <Eye className="h-3 w-3" />
                                <span>{insight.views}</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <ThumbsUp className="h-3 w-3" />
                                <span>{insight.likes}</span>
                              </div>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-gray-400">Source:</span>
                            <span className="text-sm text-gray-300 font-medium">{insight.source}</span>
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex gap-2 pt-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleLike(insight.id)}
                            className={`flex-1 ${likedInsights.has(insight.id) ? "border-green-600 text-green-400" : "border-gray-600 text-gray-400"} hover:bg-gray-800/50`}
                          >
                            <ThumbsUp className="h-3 w-3 mr-2" />
                            {likedInsights.has(insight.id) ? "Liked" : "Like"}
                          </Button>
                          <Button variant="outline" size="sm" className="border-gray-600 text-gray-400 hover:bg-gray-800/50">
                            <Copy className="h-3 w-3 mr-2" />
                            Copy
                          </Button>
                          <Button variant="outline" size="sm" className="border-gray-600 text-gray-400 hover:bg-gray-800/50">
                            <ArrowRight className="h-3 w-3 mr-2" />
                            Details
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}

                {filteredInsights.length === 0 && (
                  <div className="text-center text-gray-400 py-12">
                    <Target className="h-16 w-16 mx-auto mb-4 opacity-50" />
                    <p className="text-xl font-medium mb-2">No insights found</p>
                    <p className="text-sm">Try adjusting your filters or search for specific topics</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AIResearchAssistant;
