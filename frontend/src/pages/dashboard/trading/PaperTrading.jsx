import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { 
  Search, 
  Plus, 
  Minus, 
  TrendingUp, 
  TrendingDown,
  X,
  BarChart3,
  DollarSign,
  Activity
} from "lucide-react";
import { usePageTitle } from "@/hooks/use-page-title";

const PaperTrading = () => {
  usePageTitle("Paper Trading");

  const [selectedSymbol, setSelectedSymbol] = useState("NIFTY 50");
  const [orderType, setOrderType] = useState("buy");
  const [productType, setProductType] = useState("intraday");
  const [executionType, setExecutionType] = useState("market");
  const [quantity, setQuantity] = useState(1);
  const [limitPrice, setLimitPrice] = useState(19850.50);
  const [watchlist] = useState([
    { symbol: "NIFTY 50", ltp: 19850.50, change: 1.52, changePercent: "+0.08%" },
    { symbol: "RELIANCE", ltp: 2456.30, change: -15.20, changePercent: "-0.61%" },
    { symbol: "TCS", ltp: 3890.45, change: 48.15, changePercent: "+1.25%" },
    { symbol: "HDFCBANK", ltp: 1520.10, change: 23.05, changePercent: "+1.54%" },
    { symbol: "INFY", ltp: 1456.75, change: -8.90, changePercent: "-0.61%" },
    { symbol: "ICICIBANK", ltp: 789.30, change: 12.80, changePercent: "+1.65%" },
  ]);
  const [positions] = useState([
    { symbol: "TCS", qty: 50, avgPrice: 3842.30, ltp: 3890.45, pnl: 2407.50, pnlPercent: "+1.25%" },
    { symbol: "RELIANCE", qty: 25, avgPrice: 2471.50, ltp: 2456.30, pnl: -380.00, pnlPercent: "-0.61%" },
    { symbol: "HDFCBANK", qty: 100, qty: 100, avgPrice: 1497.05, ltp: 1520.10, pnl: 2305.00, pnlPercent: "+1.54%" },
  ]);

  const currentPrice = watchlist.find(item => item.symbol === selectedSymbol)?.ltp || 0;
  const estimatedCost = orderType === "buy" 
    ? quantity * (executionType === "market" ? currentPrice : limitPrice)
    : -(quantity * (executionType === "market" ? currentPrice : limitPrice));

  const totalPnL = positions.reduce((sum, pos) => sum + pos.pnl, 0);
  const availableBalance = 850000;
  const holdingsValue = 150000;
  const totalPortfolioValue = availableBalance + holdingsValue;

  const handleWatchlistClick = (symbol) => {
    setSelectedSymbol(symbol);
    const item = watchlist.find(w => w.symbol === symbol);
    if (item) {
      setLimitPrice(item.ltp);
    }
  };

  const handlePlaceTrade = () => {
    console.log("Placing trade:", {
      symbol: selectedSymbol,
      orderType,
      productType,
      executionType,
      quantity,
      limitPrice: executionType === "limit" ? limitPrice : currentPrice
    });
  };

  return (
    <div className="h-screen bg-black text-white p-6 overflow-hidden">
      <div className="flex gap-6 h-full">
        {/* Left Panel - Action Zone (25%) */}
        <div className="w-1/4 space-y-6">
          {/* Order Entry Form */}
          <Card className="bg-gray-900/50 border-gray-800/50">
            <CardHeader>
              <CardTitle className="text-qn-light-cyan">Place Order</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Stock Symbol */}
              <div className="space-y-2">
                <Label>Stock Symbol</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    value={selectedSymbol}
                    onChange={(e) => setSelectedSymbol(e.target.value)}
                    className="pl-10 bg-gray-800 border-gray-700 text-white"
                    placeholder="e.g., RELIANCE, TCS"
                  />
                </div>
              </div>

              {/* Order Type */}
              <div className="space-y-2">
                <Label>Order Type</Label>
                <div className="flex gap-2">
                  <Button
                    variant={orderType === "buy" ? "default" : "outline"}
                    onClick={() => setOrderType("buy")}
                    className={`flex-1 ${orderType === "buy" 
                      ? "bg-green-600 hover:bg-green-700" 
                      : "border-gray-700 text-gray-300 hover:bg-gray-800"}`}
                  >
                    Buy
                  </Button>
                  <Button
                    variant={orderType === "sell" ? "default" : "outline"}
                    onClick={() => setOrderType("sell")}
                    className={`flex-1 ${orderType === "sell" 
                      ? "bg-red-600 hover:bg-red-700" 
                      : "border-gray-700 text-gray-300 hover:bg-gray-800"}`}
                  >
                    Sell
                  </Button>
                </div>
              </div>

              {/* Product Type */}
              <div className="space-y-2">
                <Label>Product Type</Label>
                <div className="flex gap-2">
                  <Button
                    variant={productType === "intraday" ? "default" : "outline"}
                    onClick={() => setProductType("intraday")}
                    className={`flex-1 ${productType === "intraday" 
                      ? "bg-blue-600 hover:bg-blue-700" 
                      : "border-gray-700 text-gray-300 hover:bg-gray-800"}`}
                  >
                    Intraday (MIS)
                  </Button>
                  <Button
                    variant={productType === "delivery" ? "default" : "outline"}
                    onClick={() => setProductType("delivery")}
                    className={`flex-1 ${productType === "delivery" 
                      ? "bg-blue-600 hover:bg-blue-700" 
                      : "border-gray-700 text-gray-300 hover:bg-gray-800"}`}
                  >
                    Delivery (CNC)
                  </Button>
                </div>
              </div>

              {/* Quantity */}
              <div className="space-y-2">
                <Label>Quantity</Label>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setQuantity(Math.max(1, quantity - 1))}
                    className="border-gray-700 text-gray-300 hover:bg-gray-800"
                  >
                    <Minus className="h-4 w-4" />
                  </Button>
                  <Input
                    type="number"
                    value={quantity}
                    onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                    className="text-center bg-gray-800 border-gray-700 text-white"
                    min="1"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setQuantity(quantity + 1)}
                    className="border-gray-700 text-gray-300 hover:bg-gray-800"
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Execution Type */}
              <div className="space-y-2">
                <Label>Execution Type</Label>
                <div className="flex gap-2">
                  <Button
                    variant={executionType === "market" ? "default" : "outline"}
                    onClick={() => setExecutionType("market")}
                    className={`flex-1 ${executionType === "market" 
                      ? "bg-qn-light-cyan text-black hover:bg-qn-light-cyan/80" 
                      : "border-gray-700 text-gray-300 hover:bg-gray-800"}`}
                  >
                    Market
                  </Button>
                  <Button
                    variant={executionType === "limit" ? "default" : "outline"}
                    onClick={() => setExecutionType("limit")}
                    className={`flex-1 ${executionType === "limit" 
                      ? "bg-qn-light-cyan text-black hover:bg-qn-light-cyan/80" 
                      : "border-gray-700 text-gray-300 hover:bg-gray-800"}`}
                  >
                    Limit
                  </Button>
                </div>
              </div>

              {/* Limit Price */}
              {executionType === "limit" && (
                <div className="space-y-2">
                  <Label>Limit Price</Label>
                  <Input
                    type="number"
                    value={limitPrice}
                    onChange={(e) => setLimitPrice(parseFloat(e.target.value) || 0)}
                    className="bg-gray-800 border-gray-700 text-white"
                    step="0.01"
                  />
                </div>
              )}

              {/* Estimated Cost */}
              <div className="bg-gray-800/50 p-3 rounded-lg">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Estimated {orderType === "buy" ? "Cost" : "Credit"}:</span>
                  <span className={`font-semibold ${orderType === "buy" ? "text-red-400" : "text-green-400"}`}>
                    ₹{Math.abs(estimatedCost).toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Place Trade Button */}
              <Button 
                onClick={handlePlaceTrade}
                className="w-full bg-qn-light-cyan text-black hover:bg-qn-light-cyan/80 font-semibold"
              >
                Place Paper Trade
              </Button>
            </CardContent>
          </Card>

          {/* Watchlist */}
          <Card className="bg-gray-900/50 border-gray-800/50 flex-1">
            <CardHeader>
              <CardTitle className="text-qn-light-cyan">Watchlist</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="space-y-1 max-h-80 overflow-y-auto">
                {watchlist.map((item) => (
                  <div
                    key={item.symbol}
                    onClick={() => handleWatchlistClick(item.symbol)}
                    className={`p-3 cursor-pointer hover:bg-gray-800/50 transition-colors ${
                      selectedSymbol === item.symbol ? "bg-gray-800" : ""
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-medium">{item.symbol}</span>
                      <Badge variant={item.change >= 0 ? "default" : "destructive"} className="text-xs">
                        {item.changePercent}
                      </Badge>
                    </div>
                    <div className="text-sm text-gray-400 mt-1">
                      ₹{item.ltp.toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Center Panel - Analysis Zone (50%) */}
        <div className="w-1/2">
          <Card className="bg-gray-900/50 border-gray-800/50 h-full">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle className="text-qn-light-cyan">{selectedSymbol} Chart</CardTitle>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="border-gray-700 text-gray-300">5m</Button>
                  <Button variant="outline" size="sm" className="border-gray-700 text-gray-300">15m</Button>
                  <Button variant="outline" size="sm" className="border-gray-700 text-gray-300">1H</Button>
                  <Button variant="default" size="sm" className="bg-qn-light-cyan text-black">1D</Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="h-full">
              <div className="h-full bg-gray-800/30 rounded-lg flex items-center justify-center">
                <div className="text-center text-gray-400">
                  <BarChart3 className="h-16 w-16 mx-auto mb-4 opacity-50" />
                  <p className="text-lg font-medium">Chart Integration</p>
                  <p className="text-sm">TradingView chart will be integrated here</p>
                  <p className="text-xs mt-2">Showing: {selectedSymbol} • Current: ₹{currentPrice.toLocaleString()}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Panel - Status Zone (25%) */}
        <div className="w-1/4 space-y-6">
          {/* Account Summary */}
          <Card className="bg-gray-900/50 border-gray-800/50">
            <CardHeader>
              <CardTitle className="text-qn-light-cyan">Account Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Available Balance</span>
                <span className="font-semibold">₹{availableBalance.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Holdings Value</span>
                <span className="font-semibold">₹{holdingsValue.toLocaleString()}</span>
              </div>
              <div className="border-t border-gray-700 pt-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Total Portfolio</span>
                  <span className="text-xl font-bold text-qn-light-cyan">
                    ₹{totalPortfolioValue.toLocaleString()}
                  </span>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Today's P&L</span>
                <span className={`font-semibold ${totalPnL >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {totalPnL >= 0 ? "+" : ""}₹{totalPnL.toLocaleString()}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Current Positions */}
          <Card className="bg-gray-900/50 border-gray-800/50 flex-1">
            <CardHeader>
              <CardTitle className="text-qn-light-cyan">Open Positions</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="space-y-1 max-h-96 overflow-y-auto">
                {positions.length === 0 ? (
                  <div className="p-6 text-center text-gray-400">
                    <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No open positions</p>
                  </div>
                ) : (
                  positions.map((position, index) => (
                    <div key={index} className="p-3 border-b border-gray-800/50 last:border-b-0">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <span className="font-medium text-sm">{position.symbol}</span>
                          <div className="text-xs text-gray-400">Qty: {position.qty}</div>
                        </div>
                        <Button variant="outline" size="sm" className="border-red-600 text-red-400 hover:bg-red-600/10">
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-gray-400">Avg: </span>
                          <span>₹{position.avgPrice}</span>
                        </div>
                        <div>
                          <span className="text-gray-400">LTP: </span>
                          <span>₹{position.ltp}</span>
                        </div>
                      </div>
                      <div className="mt-2 flex justify-between items-center">
                        <span className="text-xs text-gray-400">P&L:</span>
                        <div className="text-right">
                          <div className={`text-sm font-medium ${position.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                            {position.pnl >= 0 ? "+" : ""}₹{position.pnl.toLocaleString()}
                          </div>
                          <div className={`text-xs ${position.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                            {position.pnlPercent}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default PaperTrading;
