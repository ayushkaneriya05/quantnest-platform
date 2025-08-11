import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Avatar } from "@/components/ui/avatar";
import { 
  Send, 
  Mic,
  MicOff,
  Paperclip,
  MoreVertical,
  Brain,
  User,
  Sparkles,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Clock,
  CheckCircle,
  Copy,
  ThumbsUp,
  ThumbsDown,
  RefreshCw,
  Zap,
  Bot,
  MessageSquare,
  Activity,
  DollarSign,
  AlertTriangle,
  Lightbulb,
  Target,
  Search,
  Filter,
  Settings,
  Star,
  Bookmark,
  Share,
  Download,
  ChevronRight,
  Circle,
  Dot,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  X,
  Calendar,
  Flame,
  Eye,
  Globe,
  PieChart,
  LineChart
} from "lucide-react";
import { usePageTitle } from "@/hooks/use-page-title";

const AIResearchAssistant = () => {
  usePageTitle("AI Research Assistant");

  const [message, setMessage] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const [chatHistory, setChatHistory] = useState([
    {
      id: 1,
      type: "assistant",
      content: "Hello! I'm QuantNest AI, your personal trading research assistant. I can help you with market analysis, stock insights, portfolio recommendations, and trading strategies. What would you like to explore today?",
      timestamp: new Date(Date.now() - 60000),
      suggestions: [
        { text: "Analyze NIFTY 50 trend", icon: TrendingUp },
        { text: "Top gainers today", icon: Activity },
        { text: "Portfolio risk assessment", icon: AlertTriangle },
        { text: "Sector opportunities", icon: Target }
      ]
    },
    {
      id: 2,
      type: "user",
      content: "What's the market outlook for banking stocks this week?",
      timestamp: new Date(Date.now() - 45000)
    },
    {
      id: 3,
      type: "assistant",
      content: "Based on my analysis of banking sector trends, here's the outlook for this week:",
      timestamp: new Date(Date.now() - 40000),
      insights: [
        {
          type: "BULLISH SIGNAL",
          color: "from-emerald-500 to-green-400",
          title: "Strong Q3 Earnings Momentum",
          content: "Major private banks like HDFC Bank and ICICI Bank have shown robust earnings growth with improved asset quality.",
          confidence: 85,
          symbols: ["HDFCBANK", "ICICIBANK", "AXISBANK"]
        },
        {
          type: "TECHNICAL ANALYSIS",
          color: "from-blue-500 to-cyan-400",
          title: "Bank Nifty Breaking Resistance",
          content: "Bank Nifty has broken above 47,500 resistance with strong volume. Next target at 48,200-48,500 range.",
          confidence: 78,
          symbols: ["BANKNIFTY"]
        },
        {
          type: "RISK FACTOR",
          color: "from-orange-500 to-red-400",
          title: "RBI Policy Meeting",
          content: "Upcoming RBI monetary policy meeting could impact banking stocks. Watch for any changes in repo rates or liquidity measures.",
          confidence: 72,
          symbols: ["BANKNIFTY"]
        }
      ]
    }
  ]);

  const quickActions = [
    { icon: TrendingUp, label: "Market Analysis", color: "from-emerald-500 to-teal-400" },
    { icon: BarChart3, label: "Stock Research", color: "from-blue-500 to-cyan-400" },
    { icon: Target, label: "Portfolio Review", color: "from-purple-500 to-pink-400" },
    { icon: AlertTriangle, label: "Risk Assessment", color: "from-orange-500 to-red-400" },
    { icon: Lightbulb, label: "Trading Ideas", color: "from-yellow-500 to-orange-400" },
    { icon: DollarSign, label: "Earnings Calendar", color: "from-teal-500 to-green-400" }
  ];

  const suggestedQueries = [
    "What are the top performing sectors this month?",
    "Show me oversold stocks with good fundamentals",
    "Analyze RELIANCE technical chart",
    "Best dividend paying stocks under ₹500",
    "Options strategies for current market conditions",
    "FII and DII flow analysis for this week"
  ];

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSendMessage = async () => {
    if (!message.trim()) return;

    const userMessage = {
      id: chatHistory.length + 1,
      type: "user",
      content: message,
      timestamp: new Date()
    };

    setChatHistory(prev => [...prev, userMessage]);
    setMessage("");
    setIsTyping(true);
    setIsLoading(true);

    // Simulate AI response
    setTimeout(() => {
      const aiResponse = {
        id: chatHistory.length + 2,
        type: "assistant",
        content: generateAIResponse(message),
        timestamp: new Date(),
        confidence: 92
      };
      setChatHistory(prev => [...prev, aiResponse]);
      setIsTyping(false);
      setIsLoading(false);
    }, 2000);
  };

  const generateAIResponse = (query) => {
    return `I've analyzed your query about "${query}". Here's what I found based on current market data and trends. This analysis considers technical indicators, fundamental metrics, and market sentiment.`;
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleVoiceToggle = () => {
    setIsRecording(!isRecording);
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const MessageBubble = ({ msg }) => {
    const isUser = msg.type === "user";
    
    return (
      <div className={`flex gap-4 mb-8 ${isUser ? "justify-end" : "justify-start"}`}>
        {!isUser && (
          <Avatar className="w-12 h-12 bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center shadow-lg">
            <Brain className="h-6 w-6 text-white" />
          </Avatar>
        )}
        
        <div className={`max-w-[75%] ${isUser ? "order-first" : ""}`}>
          <div className={`rounded-3xl px-6 py-4 ${
            isUser 
              ? "bg-gradient-to-r from-cyan-500 to-blue-500 text-white ml-auto shadow-lg" 
              : "bg-white/5 text-white border border-white/10 backdrop-blur-xl shadow-xl"
          }`}>
            <p className="text-sm leading-relaxed">{msg.content}</p>
            
            {msg.insights && (
              <div className="mt-6 space-y-4">
                {msg.insights.map((insight, index) => (
                  <Card key={index} className="bg-black/20 border-white/10 backdrop-blur-sm">
                    <CardContent className="p-5">
                      <div className="flex items-start gap-4">
                        <Badge className={`bg-gradient-to-r ${insight.color} text-white px-3 py-1 text-xs font-medium shadow-md`}>
                          {insight.type}
                        </Badge>
                        <div className="flex-1">
                          <h4 className="font-semibold text-white mb-3 text-base">{insight.title}</h4>
                          <p className="text-sm text-gray-200 mb-4 leading-relaxed">{insight.content}</p>
                          <div className="flex items-center justify-between">
                            <div className="flex gap-2">
                              {insight.symbols.map(symbol => (
                                <Badge key={symbol} variant="outline" className="text-xs border-cyan-400/40 text-cyan-300 hover:bg-cyan-400/10 transition-colors">
                                  {symbol}
                                </Badge>
                              ))}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-400">Confidence:</span>
                              <span className="text-xs font-semibold text-cyan-300">{insight.confidence}%</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {msg.suggestions && (
              <div className="mt-6 grid grid-cols-2 gap-3">
                {msg.suggestions.map((suggestion, index) => {
                  const IconComponent = suggestion.icon;
                  return (
                    <Button
                      key={index}
                      variant="outline"
                      size="sm"
                      onClick={() => setMessage(suggestion.text)}
                      className="justify-start text-left border-white/20 text-gray-200 hover:bg-white/10 h-auto py-3 backdrop-blur-sm"
                    >
                      <IconComponent className="h-4 w-4 mr-3 text-cyan-400" />
                      <span className="text-xs">{suggestion.text}</span>
                    </Button>
                  );
                })}
              </div>
            )}
          </div>
          
          <div className={`flex items-center gap-3 mt-3 text-xs text-gray-400 ${isUser ? "justify-end" : ""}`}>
            <span>{formatTime(msg.timestamp)}</span>
            {!isUser && (
              <>
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 hover:bg-white/10">
                  <Copy className="h-3 w-3" />
                </Button>
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 hover:bg-white/10">
                  <ThumbsUp className="h-3 w-3" />
                </Button>
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 hover:bg-white/10">
                  <ThumbsDown className="h-3 w-3" />
                </Button>
              </>
            )}
          </div>
        </div>

        {isUser && (
          <Avatar className="w-12 h-12 bg-gradient-to-br from-gray-600 to-gray-700 flex items-center justify-center shadow-lg">
            <User className="h-6 w-6 text-white" />
          </Avatar>
        )}
      </div>
    );
  };

  return (
    <div className="h-screen bg-gradient-to-br from-slate-950 via-gray-950 to-slate-900 flex flex-col overflow-hidden">
      {/* Premium Header */}
      <div className="border-b border-white/10 bg-black/20 backdrop-blur-xl">
        <div className="flex items-center justify-between p-6">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="w-14 h-14 bg-gradient-to-br from-cyan-400 to-blue-500 rounded-2xl flex items-center justify-center shadow-xl">
                  <Brain className="h-7 w-7 text-white" />
                </div>
                <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-emerald-500 rounded-full border-3 border-gray-900 flex items-center justify-center">
                  <Circle className="h-2 w-2 fill-current text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
                  QuantNest AI
                </h1>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
                  <span className="text-sm text-emerald-400 font-medium">Online</span>
                  <span className="text-xs text-gray-400">• GPT-4 Powered</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Badge className="bg-cyan-500/20 text-cyan-400 border-cyan-500/30 shadow-lg">
              <Zap className="h-3 w-3 mr-1" />
              AI Active
            </Badge>
            <Button variant="outline" size="sm" className="border-white/20 text-gray-300 hover:bg-white/10">
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Chat Area - Single Column */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {chatHistory.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            
            {isTyping && (
              <div className="flex gap-4 mb-8">
                <Avatar className="w-12 h-12 bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center shadow-lg">
                  <Brain className="h-6 w-6 text-white" />
                </Avatar>
                <div className="bg-white/5 border border-white/10 backdrop-blur-xl rounded-3xl px-6 py-4 shadow-xl">
                  <div className="flex items-center gap-3">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                      <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                    </div>
                    <span className="text-sm text-gray-300">AI is thinking...</span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className="border-t border-white/10 bg-black/20 backdrop-blur-xl p-6">
          <div className="max-w-4xl mx-auto">
            {/* Quick Actions */}
            <div className="mb-6">
              <div className="flex gap-3 overflow-x-auto pb-2">
                {quickActions.map((action, index) => {
                  const IconComponent = action.icon;
                  return (
                    <Button
                      key={index}
                      variant="outline"
                      size="sm"
                      className="border-white/20 text-gray-300 hover:bg-white/10 whitespace-nowrap backdrop-blur-sm"
                    >
                      <div className={`h-4 w-4 mr-2 bg-gradient-to-r ${action.color} rounded p-0.5`}>
                        <IconComponent className="h-full w-full text-white" />
                      </div>
                      {action.label}
                    </Button>
                  );
                })}
              </div>
            </div>

            {/* Message Input */}
            <div className="relative">
              <div className="flex items-end gap-4">
                <div className="flex-1 relative">
                  <textarea
                    ref={inputRef}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask me anything about markets, stocks, trading strategies..."
                    className="w-full max-h-32 p-5 pr-20 bg-white/5 border border-white/20 rounded-3xl text-white placeholder-gray-400 resize-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all duration-200 backdrop-blur-xl"
                    rows="1"
                    style={{ minHeight: '60px' }}
                  />
                  
                  <div className="absolute right-4 bottom-4 flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleVoiceToggle}
                      className={`h-8 w-8 p-0 ${isRecording ? 'text-red-400 bg-red-400/20' : 'text-gray-400 hover:text-white hover:bg-white/10'}`}
                    >
                      {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                    </Button>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-gray-400 hover:text-white hover:bg-white/10">
                      <Paperclip className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                <Button
                  onClick={handleSendMessage}
                  disabled={!message.trim() || isLoading}
                  className="h-[60px] w-[60px] bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white rounded-3xl p-0 shadow-xl"
                >
                  {isLoading ? (
                    <RefreshCw className="h-6 w-6 animate-spin" />
                  ) : (
                    <Send className="h-6 w-6" />
                  )}
                </Button>
              </div>
            </div>

            {/* Suggested Queries */}
            <div className="mt-4">
              <div className="flex gap-2 overflow-x-auto">
                {suggestedQueries.slice(0, 3).map((query, index) => (
                  <Button
                    key={index}
                    variant="ghost"
                    size="sm"
                    onClick={() => setMessage(query)}
                    className="text-xs text-gray-400 hover:text-white hover:bg-white/10 whitespace-nowrap"
                  >
                    <MessageSquare className="h-3 w-3 mr-2" />
                    {query}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIResearchAssistant;
