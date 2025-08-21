import React, { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  TrendingUp, 
  TrendingDown, 
  Package, 
  FileText, 
  X, 
  Clock,
  DollarSign,
  Activity,
  BarChart3,
  Settings,
  Edit3,
  MoreVertical,
  XCircle
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import ModifyOrderModal from "./ModifyOrderModal";
import ModifyPositionModal from "./ModifyPositionModal";
import { useWebSocketContext } from "@/contexts/websocket-context";
import api from "@/services/api";
import toast from "react-hot-toast";

const StatCard = ({ icon: Icon, title, value, subtitle, variant = "default" }) => (
  <Card className="bg-[#161b22] border-gray-700/50">
    <CardContent className="p-4">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-xl ${
          variant === 'positive' ? 'bg-emerald-500/20' :
          variant === 'negative' ? 'bg-red-500/20' :
          'bg-[#0969da]/20'
        }`}>
          <Icon className={`h-5 w-5 ${
            variant === 'positive' ? 'text-emerald-400' :
            variant === 'negative' ? 'text-red-400' :
            'text-[#58a6ff]'
          }`} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">
            {title}
          </p>
          <p className="text-lg font-bold text-white truncate">{value}</p>
          {subtitle && (
            <p className="text-xs text-gray-500 truncate">{subtitle}</p>
          )}
        </div>
      </div>
    </CardContent>
  </Card>
);

export default function PortfolioDisplay() {
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [selectedPosition, setSelectedPosition] = useState(null);
  const [isOrderModalOpen, setIsOrderModalOpen] = useState(false);
  const [isPositionModalOpen, setIsPositionModalOpen] = useState(false);

  const { getLatestPrice } = useWebSocketContext();

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
      const [posRes, ordRes] = await Promise.all([
        api.get("/api/v1/trading/positions/"),
        api.get("/api/v1/trading/orders/")
      ]);

      if (posRes.data && Array.isArray(posRes.data)) {
        setPositions(posRes.data);
      } else {
        setPositions([]);
      }

      if (ordRes.data && Array.isArray(ordRes.data)) {
        setOrders(ordRes.data.filter((o) => o.status === "OPEN"));
      } else {
        setOrders([]);
      }
    } catch (error) {
      console.error("Failed to fetch portfolio data:", error);
      toast.error("Failed to load portfolio data");
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
      await api.delete(`/api/v1/trading/orders/${orderId}/`);
      toast.success("Order cancelled successfully");
      fetchData(); // Refresh data
    } catch (error) {
      console.error("Failed to cancel order:", error);
      toast.error("Failed to cancel order");
    }
  };

  const handleModifyOrder = (order) => {
    setSelectedOrder(order);
    setIsOrderModalOpen(true);
  };

  const handleModifyPosition = (position) => {
    setSelectedPosition(position);
    setIsPositionModalOpen(true);
  };

  const handleClosePosition = async (position) => {
    try {
      const transaction_type = position.quantity > 0 ? 'SELL' : 'BUY';
      const quantity = Math.abs(position.quantity);

      await api.post('/api/v1/trading/orders/', {
        instrument_id: position.instrument.id,
        order_type: 'MARKET',
        transaction_type: transaction_type,
        quantity: quantity,
      });

      toast.success("Position close order placed successfully");
      fetchData(); // Refresh data
    } catch (error) {
      console.error("Failed to close position:", error);
      toast.error("Failed to close position");
    }
  };

  const onOrderModified = () => {
    fetchData();
    setIsOrderModalOpen(false);
    setSelectedOrder(null);
  };

  const onPositionModified = () => {
    fetchData();
    setIsPositionModalOpen(false);
    setSelectedPosition(null);
  };

  const getCurrentPrice = (symbol) => {
    return getLatestPrice(symbol) || mockLivePrices[symbol] || 0;
  };

  const calculateTotalPnl = () => {
    return positions.reduce((total, pos) => {
      const currentPrice = getCurrentPrice(pos.instrument.symbol);
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
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 bg-[#161b22] rounded-lg animate-pulse" />
          ))}
        </div>
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 bg-[#161b22] rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-6">
        {/* Portfolio Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
            subtitle={totalInvestment > 0 ? `${((totalPnl / totalInvestment) * 100).toFixed(2)}% return` : '0% return'}
            variant={totalPnl >= 0 ? 'positive' : 'negative'}
          />
          <StatCard
            icon={Activity}
            title="Active Positions"
            value={positions.length.toString()}
            subtitle={`${orders.length} pending orders`}
          />
        </div>

        {/* Positions Table */}
        <div>
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-[#0969da]/20">
              <Package className="h-5 w-5 text-[#58a6ff]" />
            </div>
            <h2 className="text-xl font-bold text-white">Active Positions</h2>
          </div>
          
          {positions.length > 0 ? (
            <Card className="bg-[#161b22] border-gray-700/50">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="border-gray-700/50">
                      <TableHead className="text-gray-400">Symbol</TableHead>
                      <TableHead className="text-gray-400">Qty</TableHead>
                      <TableHead className="text-gray-400">Avg Price</TableHead>
                      <TableHead className="text-gray-400">Current Price</TableHead>
                      <TableHead className="text-gray-400">P&L</TableHead>
                      <TableHead className="text-gray-400">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {positions.map((position) => {
                      const currentPrice = getCurrentPrice(position.instrument.symbol);
                      const pnl = (currentPrice - position.average_price) * position.quantity;
                      const pnlPercentage = ((currentPrice - position.average_price) / position.average_price) * 100;
                      const isLongPosition = position.quantity > 0;
                      
                      return (
                        <TableRow key={position.id} className="border-gray-700/50 hover:bg-gray-800/30">
                          <TableCell className="font-medium text-white">
                            <div>
                              <div className="flex items-center gap-2">
                                {position.instrument.symbol}
                                <Badge variant={isLongPosition ? "default" : "secondary"} className="text-xs">
                                  {isLongPosition ? "LONG" : "SHORT"}
                                </Badge>
                              </div>
                              <div className="text-xs text-gray-400">{position.instrument.company_name}</div>
                            </div>
                          </TableCell>
                          <TableCell className="text-white">{Math.abs(position.quantity)}</TableCell>
                          <TableCell className="text-white font-mono">₹{position.average_price.toFixed(2)}</TableCell>
                          <TableCell className="text-white font-mono">₹{currentPrice.toFixed(2)}</TableCell>
                          <TableCell className={`font-mono ${pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            <div>
                              <div>{pnl >= 0 ? '+' : ''}₹{pnl.toFixed(2)}</div>
                              <div className="text-xs">({pnl >= 0 ? '+' : ''}{pnlPercentage.toFixed(2)}%)</div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="sm">
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end" className="bg-gray-800 border-gray-700">
                                <DropdownMenuItem onClick={() => handleModifyPosition(position)} className="text-white hover:bg-gray-700">
                                  <Settings className="h-4 w-4 mr-2" />
                                  Modify Position
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleClosePosition(position)} className="text-red-400 hover:bg-gray-700">
                                  <XCircle className="h-4 w-4 mr-2" />
                                  Close Position
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-[#161b22] border-gray-700/50">
              <CardContent className="p-12 text-center">
                <Package className="h-12 w-12 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-300 mb-2">No Active Positions</h3>
                <p className="text-sm text-gray-500">Your positions will appear here once you start trading</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Orders Table */}
        <div>
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-orange-500/20">
              <FileText className="h-5 w-5 text-orange-400" />
            </div>
            <h2 className="text-xl font-bold text-white">Pending Orders</h2>
          </div>
          
          {orders.length > 0 ? (
            <Card className="bg-[#161b22] border-gray-700/50">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="border-gray-700/50">
                      <TableHead className="text-gray-400">Symbol</TableHead>
                      <TableHead className="text-gray-400">Type</TableHead>
                      <TableHead className="text-gray-400">Side</TableHead>
                      <TableHead className="text-gray-400">Qty</TableHead>
                      <TableHead className="text-gray-400">Price</TableHead>
                      <TableHead className="text-gray-400">Created</TableHead>
                      <TableHead className="text-gray-400">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {orders.map((order) => {
                      const isBuy = order.transaction_type === 'BUY';
                      const isMarket = order.order_type === 'MARKET';
                      
                      return (
                        <TableRow key={order.id} className="border-gray-700/50 hover:bg-gray-800/30">
                          <TableCell className="font-medium text-white">
                            <div>
                              <div>{order.instrument.symbol}</div>
                              <div className="text-xs text-gray-400">{order.instrument.company_name}</div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-xs border-gray-600 text-gray-400">
                              {order.order_type}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge className={`text-xs ${
                              isBuy 
                                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' 
                                : 'bg-red-500/20 text-red-400 border-red-500/30'
                            }`}>
                              {order.transaction_type}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-white">{order.quantity}</TableCell>
                          <TableCell className="text-white font-mono">
                            {isMarket ? "Market" : `₹${order.price}`}
                          </TableCell>
                          <TableCell className="text-gray-400 text-sm">
                            {new Date(order.created_at).toLocaleDateString()}
                          </TableCell>
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="sm">
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end" className="bg-gray-800 border-gray-700">
                                <DropdownMenuItem onClick={() => handleModifyOrder(order)} className="text-white hover:bg-gray-700">
                                  <Edit3 className="h-4 w-4 mr-2" />
                                  Modify Order
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleCancelOrder(order.id)} className="text-red-400 hover:bg-gray-700">
                                  <X className="h-4 w-4 mr-2" />
                                  Cancel Order
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-[#161b22] border-gray-700/50">
              <CardContent className="p-12 text-center">
                <FileText className="h-12 w-12 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-300 mb-2">No Pending Orders</h3>
                <p className="text-sm text-gray-500">Your pending orders will appear here</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Modals */}
      <ModifyOrderModal
        isOpen={isOrderModalOpen}
        onClose={() => {
          setIsOrderModalOpen(false);
          setSelectedOrder(null);
        }}
        order={selectedOrder}
        onOrderModified={onOrderModified}
      />

      <ModifyPositionModal
        isOpen={isPositionModalOpen}
        onClose={() => {
          setIsPositionModalOpen(false);
          setSelectedPosition(null);
        }}
        position={selectedPosition}
        onPositionModified={onPositionModified}
      />
    </>
  );
}
