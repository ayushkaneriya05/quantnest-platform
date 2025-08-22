import React, { useState, useEffect, useCallback, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  TrendingDown,
  Package,
  FileText,
  DollarSign,
  BarChart3,
  Settings,
  MoreVertical,
  XCircle,
  Edit3,
  X,
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
import { useWebSocket } from "@/contexts/websocket-context";
import api from "@/services/api";
import toast from "react-hot-toast";

// A reusable card component for displaying key statistics.
const StatCard = ({
  icon: Icon,
  title,
  value,
  subtitle,
  variant = "default",
}) => (
  <Card className="bg-[#161b22] border-gray-700/50">
    <CardContent className="p-4">
      <div className="flex items-center gap-3">
        <div
          className={`p-2 rounded-xl ${
            variant === "positive"
              ? "bg-emerald-500/20"
              : variant === "negative"
              ? "bg-red-500/20"
              : "bg-[#0969da]/20"
          }`}
        >
          <Icon
            className={`h-5 w-5 ${
              variant === "positive"
                ? "text-emerald-400"
                : variant === "negative"
                ? "text-red-400"
                : "text-[#58a6ff]"
            }`}
          />
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

// Helper function to safely parse numbers, returning a default value if parsing fails.
const safeNumber = (value, defaultValue = 0) => {
  const num = parseFloat(value);
  return isNaN(num) ? defaultValue : num;
};

// Helper function to format a number as a price string.
const formatPrice = (value, decimals = 2) => {
  const num = safeNumber(value);
  return num.toFixed(decimals);
};

export default function PortfolioDisplay() {
  // Component State
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [selectedPosition, setSelectedPosition] = useState(null);
  const [isOrderModalOpen, setIsOrderModalOpen] = useState(false);
  const [isPositionModalOpen, setIsPositionModalOpen] = useState(false);

  // WebSocket Context Hooks
  const {
    getLatestPrice,
    subscribe,
    isConnected,
    orderUpdates,
    positionUpdates,
    tickData,
  } = useWebSocket();

  // Fetches the initial state of positions and orders from the API.
  const fetchData = useCallback(async () => {
    try {
      const [posRes, ordRes] = await Promise.all([
        api.get("/trading/positions/"),
        api.get("/trading/orders/"),
      ]);
      setPositions(posRes.data || []);
      setOrders(ordRes.data || []);
    } catch (error) {
      console.error("Failed to fetch portfolio data:", error);
      toast.error("Failed to load portfolio data");
    } finally {
      setLoading(false);
    }
  }, []);

  // Effect to run the initial data fetch when the component mounts.
  useEffect(() => {
    setLoading(true);
    fetchData();
  }, [fetchData]);

  // Memoize the list of symbols to prevent re-subscribing on every render.
  const positionSymbols = useMemo(
    () => new Set(positions.map((p) => p.instrument?.symbol).filter(Boolean)),
    [positions]
  );

  // Decoupled effect for managing WebSocket subscriptions.
  useEffect(() => {
    if (!isConnected || positionSymbols.size === 0) return;

    const unsubscribers = Array.from(positionSymbols).map((symbol) => {
      return subscribe(symbol, () => {});
    });

    return () => {
      unsubscribers.forEach((unsub) => unsub());
    };
  }, [positionSymbols, isConnected, subscribe]);

  // Effect to fetch initial prices for any new positions.
  useEffect(() => {
    if (positions.length === 0) return;
    positions.forEach((pos) => {
      if (pos.instrument?.symbol && !tickData.has(pos.instrument.symbol)) {
        getLatestPrice(pos.instrument.symbol);
      }
    });
  }, [positions, tickData, getLatestPrice]);

  // Effect to handle live order updates from the WebSocket.
  useEffect(() => {
    if (orderUpdates.length > 0) {
      const latestUpdate = orderUpdates[0];
      setOrders((prevOrders) => {
        const index = prevOrders.findIndex((o) => o.id === latestUpdate.id);
        if (index !== -1) {
          const updatedOrders = [...prevOrders];
          updatedOrders[index] = latestUpdate;
          return updatedOrders;
        }
        return [latestUpdate, ...prevOrders];
      });
      if (["COMPLETE", "CANCELLED", "REJECTED"].includes(latestUpdate.status)) {
        fetchData();
      }
    }
  }, [orderUpdates, fetchData]);

  // Effect to handle live position updates from the WebSocket.
  useEffect(() => {
    if (positionUpdates.length > 0) {
      const latestUpdate = positionUpdates[0];
      setPositions((prevPositions) => {
        const index = prevPositions.findIndex((p) => p.id === latestUpdate.id);
        if (safeNumber(latestUpdate.quantity) === 0) {
          return prevPositions.filter((p) => p.id !== latestUpdate.id);
        }
        if (index !== -1) {
          const updatedPositions = [...prevPositions];
          updatedPositions[index] = latestUpdate;
          return updatedPositions;
        }
        return [latestUpdate, ...prevPositions];
      });
    }
  }, [positionUpdates]);

  // Handlers for user actions, which trigger API calls.
  const handleCancelOrder = async (orderId) => {
    try {
      await api.delete(`/trading/orders/${orderId}/`);
      toast.success("Order cancellation request sent");
    } catch (error) {
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
      const quantity = safeNumber(position.quantity);
      const transaction_type = quantity > 0 ? "SELL" : "BUY";
      const absQuantity = Math.abs(quantity);

      // FIX: Send `instrument_symbol` instead of `instrument_id` to match the serializer.
      await api.post("/trading/orders/", {
        instrument_symbol: position.instrument.symbol,
        order_type: "MARKET",
        transaction_type,
        quantity: absQuantity,
      });

      toast.success("Position close order placed successfully");
    } catch (error) {
      toast.error("Failed to close position");
    }
  };

  // Callback for modals to refresh data after a successful action.
  const onActionSuccess = () => {
    fetchData();
    setIsOrderModalOpen(false);
    setIsPositionModalOpen(false);
  };

  // Memoized calculations for performance.
  const { totalInvestment, totalPnl } = useMemo(() => {
    return positions.reduce(
      (acc, pos) => {
        const avgPrice = safeNumber(pos.average_price);
        const quantity = safeNumber(pos.quantity);
        const currentPrice =
          tickData.get(pos.instrument?.symbol)?.price || avgPrice;
        acc.totalInvestment += avgPrice * Math.abs(quantity);
        acc.totalPnl += (currentPrice - avgPrice) * quantity;
        return acc;
      },
      { totalInvestment: 0, totalPnl: 0 }
    );
  }, [positions, tickData]);

  const openOrders = useMemo(
    () => orders.filter((o) => o.status === "OPEN"),
    [orders]
  );

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-24 bg-[#161b22] rounded-lg animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <StatCard
            icon={DollarSign}
            title="Total Investment"
            value={`₹${totalInvestment.toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}`}
            subtitle="Across all positions"
          />
          <StatCard
            icon={BarChart3}
            title="Total P&L"
            value={`₹${formatPrice(totalPnl)}`}
            subtitle={
              totalInvestment > 0
                ? `${((totalPnl / totalInvestment) * 100).toFixed(2)}% return`
                : "0% return"
            }
            variant={totalPnl >= 0 ? "positive" : "negative"}
          />
          <StatCard
            icon={Package}
            title="Active Positions"
            value={positions.length.toString()}
            subtitle={`${openOrders.length} pending orders`}
          />
        </div>

        {/* Active Positions Table */}
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
                    <TableRow className="border-gray-700/50 hover:bg-gray-800/20">
                      <TableHead className="text-gray-300">Symbol</TableHead>
                      <TableHead className="text-gray-300">Qty</TableHead>
                      <TableHead className="text-gray-300">Avg Price</TableHead>
                      <TableHead className="text-gray-300">
                        Current Price
                      </TableHead>
                      <TableHead className="text-gray-300">P&L</TableHead>
                      <TableHead className="text-gray-300">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {positions.map((position) => {
                      const avgPrice = safeNumber(position.average_price);
                      const quantity = safeNumber(position.quantity);
                      const currentPrice =
                        tickData.get(position.instrument?.symbol)?.price ||
                        avgPrice;
                      const pnl = (currentPrice - avgPrice) * quantity;
                      const pnlPercentage =
                        avgPrice > 0
                          ? (pnl / (avgPrice * Math.abs(quantity))) * 100
                          : 0;
                      const isLongPosition = quantity > 0;

                      return (
                        <TableRow
                          key={position.id}
                          className="border-gray-700/50 hover:bg-gray-800/30"
                        >
                          <TableCell className="font-medium text-white">
                            <div>
                              <div className="flex items-center gap-2">
                                {position.instrument?.symbol || "N/A"}
                                <Badge
                                  variant={
                                    isLongPosition ? "default" : "secondary"
                                  }
                                  className="text-xs"
                                >
                                  {isLongPosition ? "LONG" : "SHORT"}
                                </Badge>
                              </div>
                              <div className="text-xs text-gray-400">
                                {position.instrument?.company_name || "N/A"}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell className="text-white">
                            {Math.abs(quantity)}
                          </TableCell>
                          <TableCell className="text-white font-mono">
                            ₹{formatPrice(avgPrice)}
                          </TableCell>
                          <TableCell className="text-white font-mono">
                            ₹{formatPrice(currentPrice)}
                          </TableCell>
                          <TableCell
                            className={`font-mono ${
                              pnl >= 0 ? "text-emerald-400" : "text-red-400"
                            }`}
                          >
                            <div>
                              <div>
                                {pnl >= 0 ? "+" : ""}₹{formatPrice(pnl)}
                              </div>
                              <div className="text-xs">
                                ({pnl >= 0 ? "+" : ""}
                                {formatPrice(pnlPercentage)}%)
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-gray-300 hover:text-white hover:bg-gray-700"
                                >
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent
                                align="end"
                                className="bg-gray-800 border-gray-700"
                              >
                                <DropdownMenuItem
                                  onClick={() => handleModifyPosition(position)}
                                  className="text-white hover:bg-gray-700"
                                >
                                  <Settings className="h-4 w-4 mr-2" /> Modify
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={() => handleClosePosition(position)}
                                  className="text-red-400 hover:bg-gray-700"
                                >
                                  <XCircle className="h-4 w-4 mr-2" /> Close
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
                <h3 className="text-lg font-medium text-gray-300 mb-2">
                  No Active Positions
                </h3>
                <p className="text-sm text-gray-500">
                  Your positions will appear here once you start trading.
                </p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Pending Orders Table */}
        <div>
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-orange-500/20">
              <FileText className="h-5 w-5 text-orange-400" />
            </div>
            <h2 className="text-xl font-bold text-white">Pending Orders</h2>
          </div>
          {openOrders.length > 0 ? (
            <Card className="bg-[#161b22] border-gray-700/50">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="border-gray-700/50 hover:bg-gray-800/20">
                      <TableHead className="text-gray-300">Symbol</TableHead>
                      <TableHead className="text-gray-300">Type</TableHead>
                      <TableHead className="text-gray-300">Side</TableHead>
                      <TableHead className="text-gray-300">Qty</TableHead>
                      <TableHead className="text-gray-300">Price</TableHead>
                      <TableHead className="text-gray-300">Created</TableHead>
                      <TableHead className="text-gray-300">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {openOrders.map((order) => (
                      <TableRow
                        key={order.id}
                        className="border-gray-700/50 hover:bg-gray-800/30"
                      >
                        <TableCell className="font-medium text-white">
                          <div>
                            <div>{order.instrument?.symbol || "N/A"}</div>
                            <div className="text-xs text-gray-400">
                              {order.instrument?.company_name || "N/A"}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className="text-xs border-gray-600 text-gray-400"
                          >
                            {order.order_type}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge
                            className={`text-xs ${
                              order.transaction_type === "BUY"
                                ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                                : "bg-red-500/20 text-red-400 border-red-500/30"
                            }`}
                          >
                            {order.transaction_type}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-white">
                          {safeNumber(order.quantity)}
                        </TableCell>
                        <TableCell className="text-white font-mono">
                          {order.order_type === "MARKET"
                            ? "Market"
                            : `₹${formatPrice(safeNumber(order.price))}`}
                        </TableCell>
                        <TableCell className="text-gray-400 text-sm">
                          {new Date(order.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-gray-300 hover:text-white hover:bg-gray-700"
                              >
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent
                              align="end"
                              className="bg-gray-800 border-gray-700"
                            >
                              <DropdownMenuItem
                                onClick={() => handleModifyOrder(order)}
                                className="text-white hover:bg-gray-700"
                              >
                                <Edit3 className="h-4 w-4 mr-2" /> Modify
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => handleCancelOrder(order.id)}
                                className="text-red-400 hover:bg-gray-700"
                              >
                                <X className="h-4 w-4 mr-2" /> Cancel
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-[#161b22] border-gray-700/50">
              <CardContent className="p-12 text-center">
                <FileText className="h-12 w-12 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-300 mb-2">
                  No Pending Orders
                </h3>
                <p className="text-sm text-gray-500">
                  Your pending orders will appear here.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Modals */}
      <ModifyOrderModal
        isOpen={isOrderModalOpen}
        onClose={() => setIsOrderModalOpen(false)}
        order={selectedOrder}
        onOrderModified={onActionSuccess}
      />
      <ModifyPositionModal
        isOpen={isPositionModalOpen}
        onClose={() => setIsPositionModalOpen(false)}
        position={selectedPosition}
        onPositionModified={onActionSuccess}
      />
    </>
  );
}
