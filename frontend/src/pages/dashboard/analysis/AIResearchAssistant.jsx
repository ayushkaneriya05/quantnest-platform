import { useState } from "react";
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
  Filter
} from "lucide-react";
import { usePageTitle } from "@/hooks/use-page-title";

const AIResearchAssistant = () => {
  usePageTitle("AI Research Assistant");

  const [query, setQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [bookmarkedItems, setBookmarkedItems] = useState(new Set());

  const categories = [
    { id: "all", label: "All Insights", count: 24 },
    { id: "market", label: "Market Summaries", count: 8 },
    { id: "stocks", label: "Stock Analysis", count: 12 },
    { id: "portfolio", label: "Portfolio Alerts", count: 3 },
    { id: "bookmarks", label: "My Bookmarks", count: bookmarkedItems.size },
  ];

  const insights = [
    {
      id: 1,
      type: "MARKET MOVER",
      typeColor: "bg-green-600",
      title: "NIFTY 50 breaks above key resistance at 19,800",
      summary: "Strong buying interest in banking and IT sectors pushes the index to new highs. Technical indicators suggest further upside momentum with next target at 20,200.",
      relatedSymbols: ["NIFTY50", "HDFCBANK", "TCS", "INFY"],
      confidence: 92,
      source: "QuantNest AI",
      timestamp: "15 minutes ago",
      category: "market"
    },
    {
      id: 2,
      type: "STOCK ALERT",
      typeColor: "bg-blue-600",
      title: "RELIANCE shows strong reversal pattern",
      summary: "After testing support at ₹2,400, RELIANCE has formed a bullish engulfing pattern with high volume. RSI oversold conditions present a good buying opportunity.",
      relatedSymbols: ["RELIANCE"],
      confidence: 87,
      source: "Technical Analysis Engine",
      timestamp: "32 minutes ago",
      category: "stocks"
    },
    {
      id: 3,
      type: "EARNINGS INSIGHT",
      typeColor: "bg-purple-600",
      title: "TCS Q3 results exceed expectations",
      summary: "Revenue growth of 13.2% YoY and improved margin guidance boost investor confidence. Strong dollar revenue and deal wins in BFSI segment highlight robust fundamentals.",
      relatedSymbols: ["TCS", "INFY", "WIPRO"],
      confidence: 95,
      source: "Earnings Analysis",
      timestamp: "1 hour ago",
      category: "stocks"
    },
    {
      id: 4,
      type: "PORTFOLIO ALERT",
      typeColor: "bg-orange-600",
      title: "Your portfolio concentration risk increasing",
      summary: "Banking sector exposure has reached 35% of your portfolio. Consider rebalancing to reduce sector-specific risks and improve diversification.",
      relatedSymbols: ["HDFCBANK", "ICICIBANK", "AXISBANK"],
      confidence: 88,
      source: "Portfolio Analyzer",
      timestamp: "2 hours ago",
      category: "portfolio"
    },
    {
      id: 5,
      type: "SECTOR ROTATION",
      typeColor: "bg-cyan-600",
      title: "IT sector gaining momentum over pharma",
      summary: "Relative strength rotation favors IT stocks as global tech spending recovers. Pharma sector showing signs of fatigue after recent outperformance.",
      relatedSymbols: ["TCS", "INFY", "HCLTECH", "DRREDDY", "SUNPHARMA"],
      confidence: 84,
      source: "Sector Analysis",
      timestamp: "3 hours ago",
      category: "market"
    },
    {
      id: 6,
      type: "MOMENTUM PLAY",
      typeColor: "bg-red-600",
      title: "HDFC Bank showing weakness below ₹1,500",
      summary: "Failed breakout attempt and increasing selling pressure suggest further downside. Key support at ₹1,450 crucial for preventing deeper correction.",
      relatedSymbols: ["HDFCBANK"],
      confidence: 78,
      source: "Momentum Scanner",
      timestamp: "4 hours ago",
      category: "stocks"
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

  const handleSearch = () => {
    if (query.trim()) {
      console.log("Searching for:", query);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  return (
    <div className="h-screen bg-black text-white p-6 overflow-hidden">
      <div className="flex gap-6 h-full">
        {/* Left Column - Control Panel (33%) */}
        <div className="w-1/3 space-y-6">
          {/* Query Input */}
          <Card className="bg-gray-900/50 border-gray-800/50">
            <CardContent className="p-6">
              <div className="space-y-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <Input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="pl-12 pr-4 py-3 bg-gray-800 border-gray-700 text-white text-lg placeholder:text-gray-400"
                    placeholder="Ask QuantNest anything... (e.g., 'Why is NIFTY BANK volatile today?')"
                  />
                </div>
                <Button 
                  onClick={handleSearch}
                  className="w-full bg-qn-light-cyan text-black hover:bg-qn-light-cyan/80 font-semibold"
                >
                  <Search className="h-4 w-4 mr-2" />
                  Ask AI Assistant
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Quick Suggestions */}
          <Card className="bg-gray-900/50 border-gray-800/50">
            <CardHeader>
              <CardTitle className="text-qn-light-cyan text-sm">Quick Suggestions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {[
                "Market outlook for next week",
                "Best performing sectors today",
                "NIFTY technical analysis",
                "Portfolio rebalancing advice"
              ].map((suggestion, index) => (
                <Button
                  key={index}
                  variant="outline"
                  onClick={() => setQuery(suggestion)}
                  className="w-full justify-start text-left border-gray-700 text-gray-300 hover:bg-gray-800 text-xs"
                >
                  <Lightbulb className="h-3 w-3 mr-2" />
                  {suggestion}
                </Button>
              ))}
            </CardContent>
          </Card>

          {/* Insight Categories */}
          <Card className="bg-gray-900/50 border-gray-800/50 flex-1">
            <CardHeader>
              <CardTitle className="text-qn-light-cyan">Categories</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {categories.map((category) => (
                <Button
                  key={category.id}
                  variant={activeCategory === category.id ? "default" : "outline"}
                  onClick={() => setActiveCategory(category.id)}
                  className={`w-full justify-between ${
                    activeCategory === category.id
                      ? "bg-qn-light-cyan text-black hover:bg-qn-light-cyan/80"
                      : "border-gray-700 text-gray-300 hover:bg-gray-800"
                  }`}
                >
                  <span>{category.label}</span>
                  <Badge variant="secondary" className="bg-gray-700 text-gray-300">
                    {category.count}
                  </Badge>
                </Button>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Insight Display (67%) */}
        <div className="w-2/3">
          <Card className="bg-gray-900/50 border-gray-800/50 h-full">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle className="text-qn-light-cyan">AI Insights Feed</CardTitle>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="bg-gray-700 text-gray-300">
                    {filteredInsights.length} insights
                  </Badge>
                  <Button variant="outline" size="sm" className="border-gray-700 text-gray-300">
                    <Filter className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="h-full overflow-hidden">
              <div className="h-full overflow-y-auto space-y-4 pr-2">
                {filteredInsights.map((insight) => (
                  <Card key={insight.id} className="bg-gray-800/50 border-gray-700/50 hover:bg-gray-800/70 transition-colors">
                    <CardContent className="p-6">
                      {/* Header */}
                      <div className="flex justify-between items-start mb-4">
                        <div className="flex items-center gap-3">
                          <Badge className={`${insight.typeColor} text-white text-xs px-2 py-1`}>
                            {insight.type}
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
                            className={`h-8 w-8 p-0 ${
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
                      <h3 className="text-lg font-semibold text-white mb-3">{insight.title}</h3>

                      {/* Content */}
                      <p className="text-gray-300 mb-4 leading-relaxed">{insight.summary}</p>

                      {/* Data Fields */}
                      <div className="space-y-3">
                        {/* Related Symbols */}
                        <div>
                          <span className="text-sm text-gray-400 block mb-2">Related Symbols:</span>
                          <div className="flex flex-wrap gap-2">
                            {insight.relatedSymbols.map((symbol) => (
                              <Badge
                                key={symbol}
                                variant="outline"
                                className="border-qn-light-cyan text-qn-light-cyan hover:bg-qn-light-cyan hover:text-black cursor-pointer transition-colors"
                              >
                                {symbol}
                                <ExternalLink className="h-3 w-3 ml-1" />
                              </Badge>
                            ))}
                          </div>
                        </div>

                        {/* Confidence Score and Source */}
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-gray-400">Confidence:</span>
                            <div className="flex items-center gap-2">
                              <Progress value={insight.confidence} className="w-20 h-2" />
                              <span className="text-sm font-medium text-qn-light-cyan">{insight.confidence}%</span>
                            </div>
                          </div>
                          <div className="text-sm text-gray-400">
                            Source: <span className="text-gray-300">{insight.source}</span>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}

                {filteredInsights.length === 0 && (
                  <div className="text-center text-gray-400 py-12">
                    <Target className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p className="text-lg font-medium">No insights found</p>
                    <p className="text-sm">Try adjusting your filters or search query</p>
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
