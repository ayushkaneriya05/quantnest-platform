import React, { useState, useEffect } from "react";
import { cn } from "@/shared/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { Badge } from "@/shared/components/ui/badge";
import { Separator } from "@/shared/components/ui/separator";
import {
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Edit3,
  X,
  DollarSign,
  Clock,
  Info,
  Loader2,
} from "lucide-react";
import { useWebSocket } from "@/shared/hooks/useWebSocket";
import api from "@/shared/services/api";
import toast from "react-hot-toast";

// Constants for order type selection
const ORDER_TYPES = [
  {
    value: "MARKET",
    label: "Market",
    description: "Execute immediately at current market price",
  },
  {
    value: "LIMIT",
    label: "Limit",
    description: "Execute only at specified price or better",
  },
  {
    value: "STOP",
    label: "Stop Loss",
    description: "Market order triggered at stop price",
  },
  {
    value: "STOP_LIMIT",
    label: "Stop Limit",
    description: "Limit order triggered at stop price",
  },
];

// Helper functions for safe number operations and formatting
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

export default function ModifyOrderModal({
  isOpen,
  onClose,
  order,
  onOrderModified,
}) {
  // Component State
  const [formData, setFormData] = useState({
    order_type: "",
    quantity: "",
    price: "",
    trigger_price: "",
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentMarketPrice, setCurrentMarketPrice] = useState(null);
  const [estimatedValue, setEstimatedValue] = useState(0);

  // WebSocket Context Hooks
  const { getTickData, subscribe } = useWebSocket();

  // Effect to reset form data when a new order is passed in
  useEffect(() => {
    if (order) {
      setFormData({
        order_type: order.order_type || "MARKET",
        quantity: safeNumber(order.quantity).toString() || "",
        price: safeNumber(order.price).toString() || "",
        trigger_price: safeNumber(order.trigger_price).toString() || "",
      });
      setErrors({});
    }
  }, [order]);

  // Effect to subscribe to live price updates when the modal is open
  useEffect(() => {
    if (!isOpen || !order?.instrument?.symbol) {
      setCurrentMarketPrice(null);
      return;
    }
    const symbol = order.instrument.symbol;

    const initialTick = getTickData(symbol);
    if (initialTick) {
      setCurrentMarketPrice(initialTick.price);
    }

    const unsubscribe = subscribe(symbol, (tick) => {
      setCurrentMarketPrice(tick.price);
    });

    return () => unsubscribe();
  }, [isOpen, order, getTickData, subscribe]);

  // Effect to calculate the estimated order value
  useEffect(() => {
    const quantity = safeNumber(formData.quantity);
    let price = 0;
    if (formData.order_type === "MARKET") {
      price = currentMarketPrice || 0;
    } else if (formData.price) {
      price = safeNumber(formData.price);
    }
    setEstimatedValue(quantity * price);
  }, [formData, currentMarketPrice]);

  const validateForm = () => {
    const newErrors = {};
    if (safeNumber(formData.quantity) <= 0) {
      newErrors.quantity = "Quantity must be greater than 0";
    }
    if (
      (formData.order_type === "LIMIT" ||
        formData.order_type === "STOP_LIMIT") &&
      safeNumber(formData.price) <= 0
    ) {
      newErrors.price = "Price must be greater than 0";
    }
    if (
      (formData.order_type === "STOP" ||
        formData.order_type === "STOP_LIMIT") &&
      safeNumber(formData.trigger_price) <= 0
    ) {
      newErrors.trigger_price = "Trigger price must be greater than 0";
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      const updateData = {
        order_type: formData.order_type,
        quantity: safeNumber(formData.quantity),
        price:
          formData.order_type === "LIMIT" ||
          formData.order_type === "STOP_LIMIT"
            ? safeNumber(formData.price)
            : null,
        trigger_price:
          formData.order_type === "STOP" || formData.order_type === "STOP_LIMIT"
            ? safeNumber(formData.trigger_price)
            : null,
      };

      const response = await api.put(
        `/trading/orders/${order.id}/`,
        updateData
      );
      toast.success("Order modified successfully");
      if (onOrderModified) onOrderModified(response.data);
      onClose();
    } catch (err) {
      const errorData = err.response?.data;
      const errorMsg = errorData?.detail || 
                       (errorData && typeof errorData === 'object' ? Object.values(errorData).flat()[0] : null) ||
                       "Failed to modify order.";
      toast.error(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: "" }));
  };

  if (!order) return null;

  const requiresPrice =
    formData.order_type === "LIMIT" || formData.order_type === "STOP_LIMIT";
  const requiresTriggerPrice =
    formData.order_type === "STOP" || formData.order_type === "STOP_LIMIT";
  const timeSinceCreated = new Date() - new Date(order.created_at);
  const minutesAgo = Math.floor(timeSinceCreated / 60000);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[700px] bg-slate-950/95 border-slate-800/80 backdrop-blur-2xl text-white rounded-[2rem] overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.5)] animate-in zoom-in-95 duration-300 px-0 py-0">
        <div className="p-6">
          <DialogHeader className="mb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-sky-500/10 text-sky-400 border border-sky-500/20">
                  <Edit3 className="h-4 w-4" />
                </div>
                <div>
                  <DialogTitle className="text-lg font-black tracking-tight leading-none">Modify Order</DialogTitle>
                  <p className="text-[10px] text-slate-500 font-medium mt-1">Adjust parameters before execution</p>
                </div>
              </div>
              <div className="text-right flex items-center gap-2">
                <Badge variant="outline" className="bg-slate-900 border-slate-800 text-[8px] h-4 tracking-widest px-1.5 uppercase text-slate-500">
                  ID: #{order.id.toString().slice(-4)}
                </Badge>
              </div>
            </div>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Asset Info Card */}
            <div className="bg-slate-900/60 p-4 rounded-2xl border border-white/5 shadow-inner">
              <div className="flex items-center justify-between mb-3">
                <div className="min-w-0">
                  <h3 className="font-black text-base text-slate-100 truncate leading-none">
                    {order.instrument?.symbol}
                  </h3>
                  <p className="text-[9px] text-slate-500 font-medium truncate mt-1">
                    {order.instrument?.company_name}
                  </p>
                </div>
                <div className="text-right flex flex-col items-end gap-1">
                  <div className="flex items-center gap-1.5">
                    <Badge
                      className={cn(
                        "text-[9px] font-black h-4 px-1.5",
                        order.transaction_type === "BUY" ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"
                      )}
                    >
                      {order.transaction_type}
                    </Badge>
                    <Badge
                      variant="outline"
                      className="text-[8px] font-bold h-4 border-slate-700 text-slate-400 capitalize"
                    >
                      {order.status.toLowerCase()}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1 text-[8px] text-slate-600 font-bold uppercase tracking-tighter">
                    <Clock className="h-2.5 w-2.5" />
                    Created {minutesAgo}m ago
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-3 border-t border-white/[0.03]">
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Market</span>
                  <div className="font-mono text-white text-xs font-bold">
                    {currentMarketPrice
                      ? formatCurrency(currentMarketPrice)
                      : "..."}
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest pl-4">Original</span>
                  <div className="font-mono text-slate-300 text-xs font-bold">
                    {order.order_type === "MARKET"
                      ? "MARKET"
                      : formatCurrency(order.price)}
                  </div>
                </div>
              </div>
            </div>

            {/* Inputs Panel */}
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="order_type" className="text-[9px] font-black text-slate-500 uppercase ml-1 tracking-wider text-opacity-70">Execution Mode</Label>
                  <Select
                    value={formData.order_type}
                    onValueChange={(value) => handleInputChange("order_type", value)}
                  >
                    <SelectTrigger className="bg-slate-900 border-slate-800 rounded-xl h-10 text-xs focus:ring-sky-500/20 transition-all">
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-950 border-slate-800 rounded-xl">
                      {ORDER_TYPES.map((type) => (
                        <SelectItem
                          key={type.value}
                          value={type.value}
                          className="text-white hover:bg-white/5 py-2"
                        >
                          <div className="flex flex-col">
                            <span className="font-bold text-xs">{type.label}</span>
                            <span className="text-[9px] text-slate-500">{type.description}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="quantity" className="text-[9px] font-black text-slate-500 uppercase ml-1 tracking-wider text-opacity-70">Quantity</Label>
                  <Input
                    id="quantity"
                    type="number"
                    value={formData.quantity}
                    onChange={(e) => handleInputChange("quantity", e.target.value)}
                    className="bg-slate-900 border-slate-800 rounded-xl h-10 text-xs focus-visible:ring-sky-500/20 font-mono"
                    min="1"
                    step="1"
                  />
                </div>
              </div>

              {(requiresPrice || requiresTriggerPrice) && (
                <div className="grid grid-cols-2 gap-3 animate-in fade-in slide-in-from-top-1 duration-200">
                  {requiresPrice ? (
                    <div className="space-y-1.5">
                      <Label htmlFor="price" className="text-[9px] font-black text-slate-500 uppercase ml-1 tracking-wider text-opacity-70">Limit Price</Label>
                      <Input
                        id="price"
                        type="number"
                        value={formData.price}
                        onChange={(e) => handleInputChange("price", e.target.value)}
                        className="bg-slate-900 border-slate-800 rounded-xl h-10 text-xs focus-visible:ring-sky-500/20 font-mono"
                        min="0"
                        step="0.01"
                      />
                    </div>
                  ) : <div />}

                  {requiresTriggerPrice && (
                    <div className="space-y-1.5">
                      <Label htmlFor="trigger_price" className="text-[9px] font-black text-slate-500 uppercase ml-1 tracking-wider text-opacity-70">Trigger Price</Label>
                      <Input
                        id="trigger_price"
                        type="number"
                        value={formData.trigger_price}
                        onChange={(e) =>
                          handleInputChange("trigger_price", e.target.value)
                        }
                        className="bg-slate-900 border-slate-800 rounded-xl h-10 text-xs focus-visible:ring-sky-500/20 font-mono"
                        min="0"
                        step="0.01"
                      />
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Total Indicator */}
            <div className="flex items-center justify-between px-4 py-2.5 bg-sky-500/5 rounded-xl border border-sky-500/10">
              <div className="flex items-center gap-2">
                <DollarSign className="h-3 w-3 text-sky-400" />
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">Revised Order Value</span>
              </div>
              <span className="font-mono font-black text-white text-sm">
                {formatCurrency(estimatedValue)}
              </span>
            </div>

            <div className="flex gap-3 pt-1">
              <Button
                type="button"
                variant="ghost"
                onClick={onClose}
                disabled={isSubmitting}
                className="flex-1 h-10 rounded-xl font-bold text-[10px] text-slate-500 hover:text-white hover:bg-white/5 transition-colors uppercase tracking-widest"
              >
                Discard
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting}
                className="flex-[2] h-10 rounded-xl font-black text-[10px] bg-sky-500 hover:bg-sky-600 text-white shadow-lg shadow-sky-500/20 transition-all active:scale-95 uppercase tracking-widest"
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  "Update Order"
                )}
              </Button>
            </div>
          </form>
        </div>
      </DialogContent>
    </Dialog>
  );
}

