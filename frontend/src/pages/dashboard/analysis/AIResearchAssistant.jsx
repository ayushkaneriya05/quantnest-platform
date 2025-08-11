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
          color: "from-green-500 to-emerald-400",
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
    { icon: TrendingUp, label: "Market Analysis", color: "from-green-500 to-emerald-400" },
    { icon: BarChart3, label: "Stock Research", color: "from-blue-500 to-cyan-400" },
    { icon: Target, label: "Portfolio Review", color: "from-purple-500 to-pink-400" },
    { icon: AlertTriangle, label: "Risk Assessment", color: "from-orange-500 to-red-400" },
    { icon: Lightbulb, label: "Trading Ideas", color: "from-yellow-500 to-orange-400" },
    { icon: DollarSign, label: "Earnings Calendar", color: "from-teal-500 to-green-400" }
  ];

  const suggestedQueries = [
    "What are the top performing sectors this month?",
    "Show me oversold stocks with good fundamentals",
    "Analyze RELIANCE technical chart"
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
      <div className={`flex gap-4 mb-6 ${isUser ? "justify-end" : "justify-start"}`}>
        {!isUser && (
          <Avatar className="w-10 h-10 bg-gradient-to-br from-qn-light-cyan to-blue-500 flex items-center justify-center shadow-lg flex-shrink-0">
            <Brain className="h-5 w-5 text-white" />
          </Avatar>
        )}
        
        <div className={`max-w-[75%] ${isUser ? "order-first" : ""}`}>
          <div className={`rounded-3xl px-5 py-3 ${
            isUser 
              ? "bg-gradient-to-r from-qn-light-cyan to-blue-500 text-white ml-auto shadow-lg" 
              : "bg-gray-800/50 text-white border border-gray-700/50 backdrop-blur-xl shadow-xl"
          }`}>
            <p className="text-sm leading-relaxed">{msg.content}</p>
            
            {msg.insights && (
              <div className="mt-4 space-y-3">
                {msg.insights.map((insight, index) => (
                  <Card key={index} className="bg-gray-900/50 border-gray-600/30">
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3">
                        <Badge className={`bg-gradient-to-r ${insight.color} text-white px-2 py-1 text-xs font-medium shadow-md`}>
                          {insight.type}
                        </Badge>
                        <div className="flex-1">
                          <h4 className="font-semibold text-white mb-2 text-sm">{insight.title}</h4>
                          <p className="text-xs text-gray-200 mb-3 leading-relaxed">{insight.content}</p>
                          <div className="flex items-center justify-between">
                            <div className="flex gap-1">
                              {insight.symbols.map(symbol => (
                                <Badge key={symbol} variant="outline" className="text-xs border-qn-light-cyan/40 text-qn-light-cyan hover:bg-qn-light-cyan/10 transition-colors">
                                  {symbol}
                                </Badge>
                              ))}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-400">Confidence:</span>
                              <span className="text-xs font-semibold text-qn-light-cyan">{insight.confidence}%</span>
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
              <div className="mt-4 grid grid-cols-2 gap-2">
                {msg.suggestions.map((suggestion, index) => {
                  const IconComponent = suggestion.icon;
                  return (
                    <Button
                      key={index}
                      variant="outline"
                      size="sm"
                      onClick={() => setMessage(suggestion.text)}
                      className="justify-start text-left border-gray-600/50 text-gray-200 hover:bg-gray-700/50 h-auto py-2 backdrop-blur-sm"
                    >
                      <IconComponent className="h-3 w-3 mr-2 text-qn-light-cyan" />
                      <span className="text-xs">{suggestion.text}</span>
                    </Button>
                  );
                })}
              </div>
            )}
          </div>
          
          <div className={`flex items-center gap-2 mt-2 text-xs text-gray-400 ${isUser ? "justify-end" : ""}`}>
            <span>{formatTime(msg.timestamp)}</span>
            {!isUser && (
              <>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0 hover:bg-gray-700/50">
                  <Copy className="h-3 w-3" />
                </Button>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0 hover:bg-gray-700/50">
                  <ThumbsUp className="h-3 w-3" />
                </Button>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0 hover:bg-gray-700/50">
                  <ThumbsDown className="h-3 w-3" />
                </Button>
              </>
            )}
          </div>
        </div>

        {isUser && (
          <Avatar className="w-10 h-10 bg-gradient-to-br from-gray-600 to-gray-700 flex items-center justify-center shadow-lg flex-shrink-0">
            <User className="h-5 w-5 text-white" />
          </Avatar>
        )}
      </div>
    );
  };

  return (
    <div className="h-[calc(100vh-80px)] bg-gradient-to-br from-slate-950 via-gray-950 to-slate-900 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-800/50 bg-gray-900/30 backdrop-blur-xl flex-shrink-0">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-12 h-12 bg-gradient-to-br from-qn-light-cyan to-blue-500 rounded-2xl flex items-center justify-center shadow-xl">
                  <Brain className="h-6 w-6 text-white" />
                </div>
                <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-gray-900 flex items-center justify-center">
                  <Circle className="h-2 w-2 fill-current text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-qn-light-cyan to-blue-400 bg-clip-text text-transparent">
                  QuantNest AI
                </h1>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                  <span className="text-sm text-green-400 font-medium">Online</span>
                  <span className="text-xs text-gray-400">• GPT-4 Powered</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Badge className="bg-qn-light-cyan/20 text-qn-light-cyan border-qn-light-cyan/30 shadow-lg">
              <Zap className="h-3 w-3 mr-1" />
              AI Active
            </Badge>
            <Button variant="outline" size="sm" className="border-gray-700/50 text-gray-300 hover:bg-gray-800/50">
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          <div className="max-w-4xl mx-auto space-y-4">
            {chatHistory.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            
            {isTyping && (
              <div className="flex gap-4 mb-6">
                <Avatar className="w-10 h-10 bg-gradient-to-br from-qn-light-cyan to-blue-500 flex items-center justify-center shadow-lg">
                  <Brain className="h-5 w-5 text-white" />
                </Avatar>
                <div className="bg-gray-800/50 border border-gray-700/50 backdrop-blur-xl rounded-3xl px-5 py-3 shadow-xl">
                  <div className="flex items-center gap-3">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-qn-light-cyan rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-qn-light-cyan rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                      <div className="w-2 h-2 bg-qn-light-cyan rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
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
        <div className="border-t border-gray-800/50 bg-gray-900/30 backdrop-blur-xl p-4 flex-shrink-0">
          <div className="max-w-4xl mx-auto">
            {/* Quick Actions */}
            <div className="mb-4">
              <div className="flex gap-2 overflow-x-auto pb-2">
                {quickActions.map((action, index) => {
                  const IconComponent = action.icon;
                  return (
                    <Button
                      key={index}
                      variant="outline"
                      size="sm"
                      className="border-gray-700/50 text-gray-300 hover:bg-gray-800/50 whitespace-nowrap backdrop-blur-sm"
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
              <div className="flex items-end gap-3">
                <div className="flex-1 relative">
                  <textarea
                    ref={inputRef}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask me anything about markets, stocks, trading strategies..."
                    className="w-full max-h-24 p-4 pr-16 bg-gray-800/50 border border-gray-700/50 rounded-3xl text-white placeholder-gray-400 resize-none focus:border-qn-light-cyan focus:ring-2 focus:ring-qn-light-cyan/20 transition-all duration-200 backdrop-blur-xl"
                    rows="1"
                    style={{ minHeight: '52px' }}
                  />
                  
                  <div className="absolute right-3 bottom-3 flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleVoiceToggle}
                      className={`h-8 w-8 p-0 ${isRecording ? 'text-red-400 bg-red-400/20' : 'text-gray-400 hover:text-white hover:bg-gray-700/50'}`}
                    >
                      {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                    </Button>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-gray-400 hover:text-white hover:bg-gray-700/50">
                      <Paperclip className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                <Button
                  onClick={handleSendMessage}
                  disabled={!message.trim() || isLoading}
                  className="h-[52px] w-[52px] bg-gradient-to-r from-qn-light-cyan to-blue-500 hover:from-qn-light-cyan/80 hover:to-blue-500/80 text-white rounded-3xl p-0 shadow-xl"
                >
                  {isLoading ? (
                    <RefreshCw className="h-5 w-5 animate-spin" />
                  ) : (
                    <Send className="h-5 w-5" />
                  )}
                </Button>
              </div>
            </div>

            {/* Suggested Queries */}
            <div className="mt-3">
              <div className="flex gap-2 overflow-x-auto">
                {suggestedQueries.map((query, index) => (
                  <Button
                    key={index}
                    variant="ghost"
                    size="sm"
                    onClick={() => setMessage(query)}
                    className="text-xs text-gray-400 hover:text-white hover:bg-gray-800/50 whitespace-nowrap"
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
