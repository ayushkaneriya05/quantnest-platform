import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Settings,
  X,
  DollarSign,
  Shield,
  Target,
  Calculator,
  Info,
} from "lucide-react";
import { useWebSocket } from "@/contexts/websocket-context";
import api from "@/services/api";
import toast from "react-hot-toast";

const TRANSACTION_TYPES = [
  { value: "BUY", label: "Buy More", description: "Add to existing position" },
  { value: "SELL", label: "Sell Partial", description: "Reduce position size" },
];

const ORDER_TYPES = [
  { value: "MARKET", label: "Market", description: "Execute immediately" },
  { value: "LIMIT", label: "Limit", description: "Execute at specified price" },
];

// Helper functions for safe number operations
const safeNumber = (value, defaultValue = 0) => {
  if (value === null || value === undefined || value === "")
    return defaultValue;
  const num = parseFloat(value);
  return isNaN(num) ? defaultValue : num;
};

const formatPrice = (value, decimals = 2) => {
  const num = safeNumber(value);
  return num.toFixed(decimals);
};

const formatCurrency = (value, decimals = 2) => {
  return `₹${formatPrice(value, decimals)}`;
};

export default function ModifyPositionModal({
  isOpen,
  onClose,
  position,
  onPositionModified,
}) {
  const [formData, setFormData] = useState({
    action: "",
    order_type: "MARKET",
    quantity: "",
    price: "",
    stop_loss: "",
    take_profit: "",
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentMarketPrice, setCurrentMarketPrice] = useState(null);
  const [estimatedValue, setEstimatedValue] = useState(0);
  const [profitLoss, setProfitLoss] = useState({ amount: 0, percentage: 0 });
  const [riskReward, setRiskReward] = useState({
    risk: 0,
    reward: 0,
    ratio: 0,
  });

  const { getLatestPrice } = useWebSocket();

  // Initialize form data and calculations when position changes
  useEffect(() => {
    if (position) {
      const marketPrice = getLatestPrice(position.instrument?.symbol) || 0;
      setCurrentMarketPrice(marketPrice);

      if (marketPrice > 0) {
        const quantity = safeNumber(position.quantity);
        const avgPrice = safeNumber(position.average_price);

        const currentValue = quantity * marketPrice;
        const investedValue = quantity * avgPrice;
        const pnl = currentValue - investedValue;
        const pnlPercentage =
          investedValue > 0 ? (pnl / investedValue) * 100 : 0;

        setProfitLoss({
          amount: pnl,
          percentage: pnlPercentage,
        });
      }

      // Reset form
      setFormData({
        action: "",
        order_type: "MARKET",
        quantity: "",
        price: "",
        stop_loss: "",
        take_profit: "",
      });
      setErrors({});
    }
  }, [position, getLatestPrice]);

  // Calculate estimated value and risk/reward when form data changes
  useEffect(() => {
    if (!formData.quantity || !currentMarketPrice) {
      setEstimatedValue(0);
      setRiskReward({ risk: 0, reward: 0, ratio: 0 });
      return;
    }

    const quantity = safeNumber(formData.quantity);
    const price =
      formData.order_type === "LIMIT" && formData.price
        ? safeNumber(formData.price)
        : currentMarketPrice;

    setEstimatedValue(quantity * price);

    // Calculate risk/reward if stop loss and take profit are set
    if (formData.stop_loss && formData.take_profit && position) {
      const stopLoss = safeNumber(formData.stop_loss);
      const takeProfit = safeNumber(formData.take_profit);
      const entryPrice = safeNumber(position.average_price);
      const positionQuantity = safeNumber(position.quantity);

      const risk = Math.abs(entryPrice - stopLoss) * Math.abs(positionQuantity);
      const reward =
        Math.abs(takeProfit - entryPrice) * Math.abs(positionQuantity);
      const ratio = risk > 0 ? reward / risk : 0;

      setRiskReward({ risk, reward, ratio });
    }
  }, [formData, currentMarketPrice, position]);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.action) {
      newErrors.action = "Please select an action";
    }

    const quantity = safeNumber(formData.quantity);
    if (quantity <= 0) {
      newErrors.quantity = "Quantity must be greater than 0";
    }

    // Check if trying to sell more than available
    if (formData.action === "SELL" && position) {
      const positionQuantity = safeNumber(position.quantity);
      if (quantity > Math.abs(positionQuantity)) {
        newErrors.quantity = `Cannot sell more than available quantity (${Math.abs(
          positionQuantity
        )})`;
      }
    }

    if (formData.order_type === "LIMIT") {
      const price = safeNumber(formData.price);
      if (price <= 0) {
        newErrors.price = "Price must be greater than 0";
      }
    }

    // Validate stop loss and take profit
    const stopLoss = safeNumber(formData.stop_loss);
    const takeProfit = safeNumber(formData.take_profit);

    if (formData.stop_loss && stopLoss <= 0) {
      newErrors.stop_loss = "Stop loss must be greater than 0";
    }

    if (formData.take_profit && takeProfit <= 0) {
      newErrors.take_profit = "Take profit must be greater than 0";
    }

    if (formData.stop_loss && formData.take_profit && position) {
      const avgPrice = safeNumber(position.average_price);
      const positionQuantity = safeNumber(position.quantity);
      const isLong = positionQuantity > 0;

      if (isLong) {
        if (stopLoss >= avgPrice) {
          newErrors.stop_loss =
            "Stop loss should be below average price for long positions";
        }
        if (takeProfit <= avgPrice) {
          newErrors.take_profit =
            "Take profit should be above average price for long positions";
        }
      } else {
        if (stopLoss <= avgPrice) {
          newErrors.stop_loss =
            "Stop loss should be above average price for short positions";
        }
        if (takeProfit >= avgPrice) {
          newErrors.take_profit =
            "Take profit should be below average price for short positions";
        }
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) return;

    setIsSubmitting(true);

    try {
      let transaction_type = formData.action;
      let quantity = safeNumber(formData.quantity);

      const orderData = {
        instrument_id: position.instrument?.id,
        order_type: formData.order_type,
        transaction_type: transaction_type,
        quantity: quantity,
      };

      // Add price for limit orders
      if (formData.order_type === "LIMIT") {
        orderData.price = safeNumber(formData.price);
      }

      // Add stop loss and take profit if provided
      if (formData.stop_loss) {
        orderData.stop_loss = safeNumber(formData.stop_loss);
      }

      if (formData.take_profit) {
        orderData.take_profit = safeNumber(formData.take_profit);
      }

      const response = await api.post("/api/v1/trading/orders/", orderData);

      toast.success("Position modification order placed successfully");

      if (onPositionModified) {
        onPositionModified(response.data);
      }

      onClose();
    } catch (err) {
      console.error("Failed to modify position:", err);

      if (err.response?.data?.error) {
        toast.error(err.response.data.error);
      } else if (err.response?.data) {
        // Handle field-specific errors
        const fieldErrors = {};
        Object.keys(err.response.data).forEach((field) => {
          if (Array.isArray(err.response.data[field])) {
            fieldErrors[field] = err.response.data[field][0];
          }
        });
        setErrors(fieldErrors);
      } else {
        toast.error("Failed to modify position. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));

    // Clear error when user starts typing
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: "" }));
    }
  };

  const handleCancel = () => {
    setFormData({
      action: "",
      order_type: "MARKET",
      quantity: "",
      price: "",
      stop_loss: "",
      take_profit: "",
    });
    setErrors({});
    onClose();
  };

  const requiresPrice = formData.order_type === "LIMIT";

  if (!position) return null;

  const positionQuantity = safeNumber(position.quantity);
  const avgPrice = safeNumber(position.average_price);
  const isLongPosition = positionQuantity > 0;
  const positionValue =
    Math.abs(positionQuantity) * (currentMarketPrice || avgPrice);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px] bg-slate-900 border-slate-700 text-white max-h-[90vh] overflow-y-auto [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-slate-800 [&::-webkit-scrollbar-thumb]:bg-slate-600 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-slate-500">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Settings className="h-5 w-5 text-blue-400" />
            Modify Position
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Position Info */}
          <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700/50">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="font-semibold text-lg">
                  {position.instrument?.symbol || "N/A"}
                </h3>
                <p className="text-sm text-gray-400">
                  {position.instrument?.company_name || "N/A"}
                </p>
              </div>
              <div className="text-right">
                <Badge
                  variant={isLongPosition ? "default" : "secondary"}
                  className="mb-1"
                >
                  {isLongPosition ? "LONG" : "SHORT"}
                </Badge>
                <div className="text-sm text-gray-400 mt-1">
                  {Math.abs(positionQuantity)} shares
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Avg Price:</span>
                <div className="font-mono text-white">
                  {formatCurrency(avgPrice)}
                </div>
              </div>
              <div>
                <span className="text-gray-400">Current Price:</span>
                <div className="font-mono text-white">
                  {currentMarketPrice
                    ? formatCurrency(currentMarketPrice)
                    : "---"}
                </div>
              </div>
              <div>
                <span className="text-gray-400">Position Value:</span>
                <div className="font-mono text-white">
                  {formatCurrency(positionValue)}
                </div>
              </div>
              <div>
                <span className="text-gray-400">P&L:</span>
                <div
                  className={`font-mono flex items-center gap-1 ${
                    profitLoss.amount >= 0 ? "text-emerald-400" : "text-red-400"
                  }`}
                >
                  {profitLoss.amount >= 0 ? (
                    <TrendingUp className="h-3 w-3" />
                  ) : (
                    <TrendingDown className="h-3 w-3" />
                  )}
                  {formatCurrency(profitLoss.amount)} (
                  {formatPrice(profitLoss.percentage)}%)
                </div>
              </div>
            </div>
          </div>

          {/* Action Selection */}
          <div className="space-y-2">
            <Label htmlFor="action">Action</Label>
            <Select
              value={formData.action}
              onValueChange={(value) => handleInputChange("action", value)}
            >
              <SelectTrigger className="bg-slate-800 border-slate-700">
                <SelectValue placeholder="Select action" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                {TRANSACTION_TYPES.map((type) => (
                  <SelectItem
                    key={type.value}
                    value={type.value}
                    className="text-white hover:bg-slate-700"
                  >
                    <div>
                      <div className="font-medium">{type.label}</div>
                      <div className="text-xs text-gray-400">
                        {type.description}
                      </div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.action && (
              <p className="text-red-400 text-sm flex items-center gap-1">
                <AlertCircle className="h-4 w-4" />
                {errors.action}
              </p>
            )}
          </div>

          {/* Order Type and Quantity */}
          {formData.action && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="order_type">Order Type</Label>
                <Select
                  value={formData.order_type}
                  onValueChange={(value) =>
                    handleInputChange("order_type", value)
                  }
                >
                  <SelectTrigger className="bg-slate-800 border-slate-700">
                    <SelectValue placeholder="Select order type" />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-700">
                    {ORDER_TYPES.map((type) => (
                      <SelectItem
                        key={type.value}
                        value={type.value}
                        className="text-white hover:bg-slate-700"
                      >
                        <div>
                          <div className="font-medium">{type.label}</div>
                          <div className="text-xs text-gray-400">
                            {type.description}
                          </div>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="quantity">
                  Quantity
                  {formData.action === "SELL" && (
                    <span className="text-sm text-gray-400 ml-2">
                      (Available: {Math.abs(positionQuantity)})
                    </span>
                  )}
                </Label>
                <Input
                  id="quantity"
                  type="number"
                  value={formData.quantity}
                  onChange={(e) =>
                    handleInputChange("quantity", e.target.value)
                  }
                  placeholder="Enter quantity"
                  className="bg-slate-800 border-slate-700"
                  min="1"
                  step="1"
                />
                {errors.quantity && (
                  <p className="text-red-400 text-sm flex items-center gap-1">
                    <AlertCircle className="h-4 w-4" />
                    {errors.quantity}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Price (for LIMIT orders) */}
          {requiresPrice && formData.action && (
            <div className="space-y-2">
              <Label htmlFor="price">Limit Price</Label>
              <Input
                id="price"
                type="number"
                value={formData.price}
                onChange={(e) => handleInputChange("price", e.target.value)}
                placeholder="Enter limit price"
                className="bg-slate-800 border-slate-700"
                min="0"
                step="0.01"
              />
              {errors.price && (
                <p className="text-red-400 text-sm flex items-center gap-1">
                  <AlertCircle className="h-4 w-4" />
                  {errors.price}
                </p>
              )}
            </div>
          )}

          <Separator className="bg-slate-700" />

          {/* Risk Management Section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-blue-400" />
              <h3 className="font-semibold text-white">Risk Management</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="stop_loss" className="flex items-center gap-1">
                  <Shield className="h-4 w-4 text-red-400" />
                  Stop Loss
                </Label>
                <Input
                  id="stop_loss"
                  type="number"
                  value={formData.stop_loss}
                  onChange={(e) =>
                    handleInputChange("stop_loss", e.target.value)
                  }
                  placeholder="Enter stop loss price"
                  className="bg-slate-800 border-slate-700"
                  min="0"
                  step="0.01"
                />
                {errors.stop_loss && (
                  <p className="text-red-400 text-sm flex items-center gap-1">
                    <AlertCircle className="h-4 w-4" />
                    {errors.stop_loss}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label
                  htmlFor="take_profit"
                  className="flex items-center gap-1"
                >
                  <Target className="h-4 w-4 text-emerald-400" />
                  Take Profit
                </Label>
                <Input
                  id="take_profit"
                  type="number"
                  value={formData.take_profit}
                  onChange={(e) =>
                    handleInputChange("take_profit", e.target.value)
                  }
                  placeholder="Enter take profit price"
                  className="bg-slate-800 border-slate-700"
                  min="0"
                  step="0.01"
                />
                {errors.take_profit && (
                  <p className="text-red-400 text-sm flex items-center gap-1">
                    <AlertCircle className="h-4 w-4" />
                    {errors.take_profit}
                  </p>
                )}
              </div>
            </div>

            {/* Risk/Reward Ratio */}
            {riskReward.ratio > 0 && (
              <div className="bg-blue-900/20 p-3 rounded-lg border border-blue-700/30">
                <div className="flex items-center gap-2 mb-2">
                  <Calculator className="h-4 w-4 text-blue-400" />
                  <span className="text-sm font-medium text-blue-300">
                    Risk/Reward Analysis
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <div className="text-gray-400">Risk</div>
                    <div className="text-red-400 font-mono">
                      {formatCurrency(riskReward.risk)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400">Reward</div>
                    <div className="text-emerald-400 font-mono">
                      {formatCurrency(riskReward.reward)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400">Ratio</div>
                    <div
                      className={`font-mono ${
                        riskReward.ratio >= 2
                          ? "text-emerald-400"
                          : riskReward.ratio >= 1
                          ? "text-yellow-400"
                          : "text-red-400"
                      }`}
                    >
                      1:{formatPrice(riskReward.ratio)}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Estimated Value */}
          {estimatedValue > 0 && (
            <div className="bg-emerald-900/20 p-3 rounded-lg border border-emerald-700/30">
              <div className="flex items-center gap-2 text-emerald-300">
                <DollarSign className="h-4 w-4" />
                <span className="text-sm font-medium">
                  Estimated Order Value: {formatCurrency(estimatedValue)}
                </span>
              </div>
            </div>
          )}

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
              disabled={isSubmitting}
              className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white hover:border-slate-500"
            >
              <X className="h-4 w-4 mr-2" />
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || !formData.action}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isSubmitting ? (
                <div className="flex items-center gap-2">
                  <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                  Processing...
                </div>
              ) : (
                <>
                  <Settings className="h-4 w-4 mr-2" />
                  Place Order
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
