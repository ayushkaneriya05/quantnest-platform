import React, { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { 
  TrendingUp, 
  TrendingDown, 
  Package, 
  FileText, 
  X, 
  Clock,
  DollarSign,
  Activity,
  BarChart3
} from "lucide-react";
import api from "@/services/api";

const PositionCard = ({ position, currentPrice, onClose }) => {
  const pnl = (currentPrice - position.average_price) * position.quantity;
  const pnlPercent = ((currentPrice - position.average_price) / position.average_price * 100).toFixed(2);
  const isProfit = pnl >= 0;

  return (
    <Card className="bg-[#161b22] border-gray-700/50 hover:border-gray-600/60 transition-all duration-300 hover:shadow-lg group">
      <CardContent className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold text-white mb-1">
              {position.instrument.symbol}
            </h3>
            <p className="text-sm text-gray-400">
              {position.instrument.company_name || "Company Name Ltd."}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={isProfit ? "default" : "destructive"} className={`text-xs ${
              position.quantity > 0 
                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' 
                : 'bg-red-500/20 text-red-400 border-red-500/30'
            }`}>
              {position.quantity > 0 ? "LONG" : "SHORT"}
            </Badge>
            {onClose && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-red-400"
                onClick={() => onClose(position.id)}
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-xs text-gray-500 mb-1">Quantity</p>
            <p className="text-sm font-semibold text-gray-200">
              {Math.abs(position.quantity)} shares
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Avg Price</p>
            <p className="text-sm font-semibold text-gray-200">
              ₹{position.average_price.toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Current Price</p>
            <p className="text-sm font-semibold text-gray-200">
              ₹{currentPrice.toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Investment</p>
            <p className="text-sm font-semibold text-gray-200">
              ₹{(position.average_price * Math.abs(position.quantity)).toLocaleString()}
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between p-3 rounded-lg bg-[#0d1117]">
          <div className="flex items-center gap-2">
            {isProfit ? (
              <TrendingUp className="h-4 w-4 text-emerald-400" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-400" />
            )}
            <span className="text-sm font-medium text-gray-300">P&L</span>
          </div>
          <div className="text-right">
            <p className={`text-lg font-bold ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>
              {isProfit ? '+' : ''}₹{pnl.toFixed(2)}
            </p>
            <p className={`text-sm ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>
              ({isProfit ? '+' : ''}{pnlPercent}%)
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const OrderCard = ({ order, onCancel }) => {
  const isMarket = order.order_type === "MARKET";
  const isBuy = order.transaction_type === "BUY";

  return (
    <Card className="bg-[#161b22] border-gray-700/50 hover:border-gray-600/60 transition-all duration-300 hover:shadow-lg group">
      <CardContent className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${
              isBuy 
                ? 'bg-emerald-500/20 text-emerald-400' 
                : 'bg-red-500/20 text-red-400'
            }`}>
              {isBuy ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">
                {order.instrument.symbol}
              </h3>
              <p className="text-sm text-gray-400">
                {order.instrument.company_name || "Company Name Ltd."}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={`text-xs ${
              isBuy 
                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' 
                : 'bg-red-500/20 text-red-400 border-red-500/30'
            }`}>
              {order.transaction_type}
            </Badge>
            <Badge variant="outline" className="text-xs border-gray-600 text-gray-400">
              {order.order_type}
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <p className="text-xs text-gray-500 mb-1">Quantity</p>
            <p className="text-sm font-semibold text-gray-200">
              {order.quantity} shares
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Price</p>
            <p className="text-sm font-semibold text-gray-200">
              {isMarket ? "Market" : `₹${order.price}`}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Value</p>
            <p className="text-sm font-semibold text-gray-200">
              {isMarket ? "Market" : `₹${(order.price * order.quantity).toLocaleString()}`}
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-gray-400">
            <Clock className="h-4 w-4" />
            <span className="text-sm">Pending</span>
          </div>
          <Button
            size="sm"
            variant="destructive"
            onClick={() => onCancel(order.id)}
            className="opacity-0 group-hover:opacity-100 transition-opacity bg-red-600 hover:bg-red-700"
          >
            Cancel Order
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

const StatCard = ({ icon: Icon, title, value, subtitle, variant = "default" }) => (
  <Card className="bg-[#161b22] border-gray-700/50">
    <CardContent className="p-6">
      <div className="flex items-center gap-3">
        <div className={`p-3 rounded-xl ${
          variant === 'positive' ? 'bg-emerald-500/20' :
          variant === 'negative' ? 'bg-red-500/20' :
          'bg-[#0969da]/20'
        }`}>
          <Icon className={`h-6 w-6 ${
            variant === 'positive' ? 'text-emerald-400' :
            variant === 'negative' ? 'text-red-400' :
            'text-[#58a6ff]'
          }`} />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-400 uppercase tracking-wider">
            {title}
          </p>
          <p className="text-2xl font-bold text-white">{value}</p>
          {subtitle && (
            <p className="text-sm text-gray-500">{subtitle}</p>
          )}
        </div>
      </div>
    </CardContent>
  </Card>
);

export default function PortfolioDisplay() {
  const { toast } = useToast();
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [livePrices, setLivePrices] = useState({});
  const [loading, setLoading] = useState(true);

  // Mock live prices for demo
  const mockLivePrices = {
    "RELIANCE": 2458.50,
    "TCS": 3245.80,
    "INFY": 1456.30,
    "HDFCBANK": 1678.90,
    "ICICIBANK": 934.20,
  };

  const fetchData = useCallback(async () => {
    try {
      const posRes = await api.get("/trading/positions/");
      if (posRes.data && Array.isArray(posRes.data)) {
        setPositions(posRes.data);
      } else {
        setPositions([]);
      }

      const ordRes = await api.get("/trading/orders/");
      if (ordRes.data && Array.isArray(ordRes.data)) {
        setOrders(ordRes.data.filter((o) => o.status === "OPEN"));
      } else {
        setOrders([]);
      }

      // Mock live prices
      setLivePrices(mockLivePrices);
    } catch (error) {
      console.error("Failed to fetch portfolio data:", error);
      setPositions([]);
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCancelOrder = async (orderId) => {
    try {
      await api.delete(`/trading/orders/${orderId}/`);
      toast({ 
        title: "Success", 
        description: "Order cancelled successfully.",
        className: "bg-[#161b22] border-gray-700 text-white"
      });
      fetchData(); // Refresh data
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to cancel order.",
        className: "bg-red-900 border-red-700 text-white"
      });
    }
  };

  const calculateTotalPnl = () => {
    return positions.reduce((total, pos) => {
      const currentPrice = livePrices[pos.instrument.symbol] || pos.average_price;
      const pnl = (currentPrice - pos.average_price) * pos.quantity;
      return total + pnl;
    }, 0);
  };

  const totalInvestment = positions.reduce((total, pos) => {
    return total + (pos.average_price * Math.abs(pos.quantity));
  }, 0);

  const totalPnl = calculateTotalPnl();

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 bg-[#161b22] rounded-lg animate-pulse" />
          ))}
        </div>
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-32 bg-[#161b22] rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Portfolio Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          icon={DollarSign}
          title="Total Investment"
          value={`₹${totalInvestment.toLocaleString()}`}
          subtitle="Across all positions"
        />
        <StatCard
          icon={BarChart3}
          title="Total P&L"
          value={`₹${totalPnl.toFixed(2)}`}
          subtitle={`${((totalPnl / totalInvestment) * 100).toFixed(2)}% return`}
          variant={totalPnl >= 0 ? 'positive' : 'negative'}
        />
        <StatCard
          icon={Activity}
          title="Active Positions"
          value={positions.length.toString()}
          subtitle={`${orders.length} pending orders`}
        />
      </div>

      {/* Positions */}
      <div>
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-[#0969da]/20">
            <Package className="h-5 w-5 text-[#58a6ff]" />
          </div>
          <h2 className="text-2xl font-bold text-white">Active Positions</h2>
        </div>
        
        {positions.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {positions.map((pos) => (
              <PositionCard
                key={pos.id}
                position={pos}
                currentPrice={livePrices[pos.instrument.symbol] || pos.average_price}
              />
            ))}
          </div>
        ) : (
          <Card className="bg-[#161b22] border-gray-700/50">
            <CardContent className="p-12 text-center">
              <div className="p-4 rounded-full bg-[#0d1117] w-fit mx-auto mb-4">
                <Package className="h-8 w-8 text-gray-600" />
              </div>
              <h3 className="text-lg font-medium text-gray-300 mb-2">
                No Active Positions
              </h3>
              <p className="text-sm text-gray-500">
                Your positions will appear here once you start trading
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Orders */}
      <div>
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-orange-500/20">
            <FileText className="h-5 w-5 text-orange-400" />
          </div>
          <h2 className="text-2xl font-bold text-white">Pending Orders</h2>
        </div>
        
        {orders.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {orders.map((order) => (
              <OrderCard
                key={order.id}
                order={order}
                onCancel={handleCancelOrder}
              />
            ))}
          </div>
        ) : (
          <Card className="bg-[#161b22] border-gray-700/50">
            <CardContent className="p-12 text-center">
              <div className="p-4 rounded-full bg-[#0d1117] w-fit mx-auto mb-4">
                <FileText className="h-8 w-8 text-gray-600" />
              </div>
              <h3 className="text-lg font-medium text-gray-300 mb-2">
                No Pending Orders
              </h3>
              <p className="text-sm text-gray-500">
                Your pending orders will appear here
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
