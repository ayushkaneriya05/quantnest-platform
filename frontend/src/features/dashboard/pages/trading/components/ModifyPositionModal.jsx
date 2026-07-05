import React, { useState, useEffect } from "react";
import { cn } from "@/shared/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
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
  TrendingUp,
  TrendingDown,
  Settings,
  Loader2,
} from "lucide-react";
import { useWebSocket } from "@/shared/hooks/useWebSocket";
import api from "@/shared/services/api";
import toast from "react-hot-toast";

// Constants for form selections
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
  // Form and UI State
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

  const { getTickData, subscribe } = useWebSocket();

  // Effect to subscribe to live price updates when the modal is open
  useEffect(() => {
    if (!isOpen || !position?.instrument?.symbol) {
      setCurrentMarketPrice(null);
      return;
    }
    const symbol = position.instrument.symbol;

    const initialTick = getTickData(symbol);
    if (initialTick) {
      setCurrentMarketPrice(initialTick.price);
    }

    const unsubscribe = subscribe(symbol, (tick) => {
      setCurrentMarketPrice(tick.price);
    });

    return () => unsubscribe();
  }, [isOpen, position, getTickData, subscribe]);

  // Effect to calculate P&L whenever the live price changes
  useEffect(() => {
    if (position && currentMarketPrice !== null) {
      const quantity = safeNumber(position.quantity);
      const avgPrice = safeNumber(position.average_price);
      const investedValue = Math.abs(quantity * avgPrice);
      const pnl = (currentMarketPrice - avgPrice) * quantity;
      const pnlPercentage = investedValue > 0 ? (pnl / investedValue) * 100 : 0;
      setProfitLoss({ amount: pnl, percentage: pnlPercentage });
    }
  }, [position, currentMarketPrice]);

  useEffect(() => {
    if (position) {
      setFormData({
        action: "",
        order_type: "MARKET",
        quantity: "",
        price: "",
        stop_loss: position.stop_loss?.toString() || "",
        take_profit: position.take_profit?.toString() || "",
      });
      setErrors({});
    }
  }, [position?.id]);

  // Effect to calculate estimated order value and risk/reward
  useEffect(() => {
    if (!formData.quantity || currentMarketPrice === null) {
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

    // If no action is selected, we are only updating SL/TP
    if (formData.action) {
      const quantity = safeNumber(formData.quantity);
      if (quantity <= 0) newErrors.quantity = "Quantity must be greater than 0";

      if (formData.action === "SELL" && position) {
        if (quantity > Math.abs(safeNumber(position.quantity))) {
          newErrors.quantity = `Cannot sell more than available quantity (${Math.abs(
            safeNumber(position.quantity)
          )})`;
        }
      }

      if (formData.order_type === "LIMIT" && safeNumber(formData.price) <= 0) {
        newErrors.price = "Price must be greater than 0";
      }
    } else {
      // If no action, ensure SL or TP has been modified
      const slChanged = formData.stop_loss !== (position.stop_loss?.toString() || "");
      const tpChanged = formData.take_profit !== (position.take_profit?.toString() || "");
      
      if (!slChanged && !tpChanged) {
        newErrors.action = "Please select an action or update risk parameters";
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
      if (formData.action) {
        // Create an Order (BUY MORE or SELL PARTIAL)
        const orderData = {
          instrument_symbol: position.instrument?.symbol,
          order_type: formData.order_type,
          transaction_type: formData.action,
          quantity: safeNumber(formData.quantity),
          price:
            formData.order_type === "LIMIT" ? safeNumber(formData.price) : null,
        };

        await api.post("/trading/orders/", orderData);

        const slChanged = formData.stop_loss !== (position.stop_loss?.toString() || "");
        const tpChanged = formData.take_profit !== (position.take_profit?.toString() || "");
        if (slChanged || tpChanged) {
          await api.patch(`/trading/positions/${position.id}/`, {
            stop_loss: formData.stop_loss ? safeNumber(formData.stop_loss) : null,
            take_profit: formData.take_profit ? safeNumber(formData.take_profit) : null,
          });
        }
        toast.success("Trade order placed successfully");
      } else {
        // Direct Position Parameter Update (SL/TP Only)
        const positionData = {
          stop_loss: formData.stop_loss ? safeNumber(formData.stop_loss) : null,
          take_profit: formData.take_profit ? safeNumber(formData.take_profit) : null,
        };
        await api.patch(`/trading/positions/${position.id}/`, positionData);
        toast.success("Risk parameters updated successfully");
      }

      if (onPositionModified) onPositionModified();
      onClose();
    } catch (err) {
      const errorData = err.response?.data;
      const errorMsg =
        errorData?.detail ||
        (errorData && typeof errorData === "object" ? Object.values(errorData).flat()[0] : null) ||
        "Failed to update position.";
      toast.error(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: "" }));
  };

  if (!position) return null;

  const positionQuantity = safeNumber(position.quantity);
  const avgPrice = safeNumber(position.average_price);
  const isLongPosition = positionQuantity > 0;
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose} modal={true}>
      <DialogContent className="sm:max-w-[750px] bg-slate-950/95 border-slate-800/80 backdrop-blur-2xl text-white rounded-[2rem] overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.5)] animate-in zoom-in-95 duration-300 px-0 py-0">
        <div className="p-6">
          <DialogHeader className="mb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-amber-500/10 text-amber-500 border border-amber-500/20">
                  <Settings className="h-4 w-4" />
                </div>
                <div>
                  <DialogTitle className="text-lg font-black tracking-tight leading-none">Manage Position</DialogTitle>
                  <p className="text-[10px] text-slate-500 font-medium mt-1">Adjust size or update risk parameters</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge
                  className={cn(
                    "font-black text-[9px] h-4.5 px-2",
                    isLongPosition ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"
                  )}
                >
                  {isLongPosition ? "LONG" : "SHORT"}
                </Badge>
              </div>
            </div>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Split layout: Info | Parameters */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Left Column: Position Summary */}
              <div className="bg-slate-900/60 p-4 rounded-2xl border border-white/5 shadow-inner flex flex-col justify-between">
                <div>
                   <div className="flex items-center justify-between mb-2">
                    <h3 className="font-black text-base text-slate-100 truncate leading-none">
                      {position.instrument?.symbol}
                    </h3>
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-tight">
                      {Math.abs(positionQuantity)} Shares
                    </span>
                  </div>
                  <p className="text-[9px] text-slate-500 font-medium leading-none mb-4 truncate">
                    {position.instrument?.company_name}
                  </p>
                </div>

                <div className="space-y-3 pt-3 border-t border-white/[0.03]">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Entry Avg</span>
                    <div className="font-mono text-slate-300 text-xs font-bold">
                       {formatCurrency(avgPrice)}
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Current Market</span>
                    <div className="font-mono text-white text-xs font-bold">
                       {currentMarketPrice ? formatCurrency(currentMarketPrice) : "..."}
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Live P&L</span>
                    <div className={cn(
                      "font-mono text-xs font-black flex items-center gap-1",
                      profitLoss.amount >= 0 ? "text-emerald-400" : "text-rose-400"
                    )}>
                      {profitLoss.amount >= 0 ? <TrendingUp className="h-2.5 w-2.5" /> : <TrendingDown className="h-2.5 w-2.5" />}
                      {formatCurrency(profitLoss.amount)}
                      <span className="text-[10px] opacity-70">({profitLoss.percentage.toFixed(2)}%)</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column: Trade Actions */}
              <div className="bg-slate-900/40 p-4 rounded-2xl border border-white/5 space-y-3">
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center px-1">
                    <Label htmlFor="action" className="text-[9px] font-black text-slate-500 uppercase tracking-wider opacity-70">Trade Modification</Label>
                    {formData.action && (
                      <button 
                        type="button" 
                        onClick={() => { setFormData(p => ({ ...p, action: "" })); setErrors(e => ({ ...e, action: "" })); }}
                        className="text-[8px] font-bold text-sky-500 hover:text-sky-400 uppercase tracking-tighter"
                      >
                        Reset
                      </button>
                    )}
                  </div>
                  <Select
                    value={formData.action}
                    onValueChange={(value) => handleInputChange("action", value)}
                  >
                    <SelectTrigger className="bg-slate-900 border-slate-800 rounded-xl h-10 text-xs focus:ring-sky-500/20">
                      <SelectValue placeholder="Add/Reduce Position (Optional)" />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-950 border-slate-800 rounded-xl">
                      {TRANSACTION_TYPES.map((type) => (
                        <SelectItem key={type.value} value={type.value} className="text-white hover:bg-white/5 py-2">
                           <div className="flex flex-col">
                            <span className="font-bold text-xs">{type.label}</span>
                            <span className="text-[9px] text-slate-500">{type.description}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.action && <p className="text-[9px] text-rose-500 font-bold ml-1">{errors.action}</p>}
                </div>

                {formData.action && (
                  <div className="grid grid-cols-2 gap-3 animate-in fade-in slide-in-from-top-1 duration-200">
                    <div className="space-y-1.5">
                      <Label htmlFor="order_type" className="text-[9px] font-black text-slate-500 uppercase">Mode</Label>
                      <Select
                        value={formData.order_type}
                        onValueChange={(value) => handleInputChange("order_type", value)}
                      >
                        <SelectTrigger className="bg-slate-900 border-slate-800 rounded-xl h-9 text-[11px]">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-slate-950 border-slate-800">
                          {ORDER_TYPES.map((type) => (
                            <SelectItem key={type.value} value={type.value} className="text-white text-[11px] py-1.5">
                              {type.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="quantity" className="text-[9px] font-black text-slate-500 uppercase">Qty</Label>
                      <Input
                        id="quantity"
                        type="number"
                        value={formData.quantity}
                        onChange={(e) => handleInputChange("quantity", e.target.value)}
                        className="bg-slate-900 border-slate-800 rounded-xl h-9 text-[11px] font-mono"
                        placeholder="Shares..."
                      />
                      {errors.quantity && <p className="text-[8px] text-rose-500 font-bold">{errors.quantity}</p>}
                    </div>
                    {formData.order_type === "LIMIT" && (
                      <div className="space-y-1.5 col-span-2">
                        <Label htmlFor="price" className="text-[9px] font-black text-slate-500 uppercase">Limit Price</Label>
                        <Input
                          id="price"
                          type="number"
                          value={formData.price}
                          onChange={(e) => handleInputChange("price", e.target.value)}
                          className="bg-slate-900 border-slate-800 rounded-xl h-9 text-[11px] font-mono"
                          placeholder="Price..."
                        />
                         {errors.price && <p className="text-[8px] text-rose-500 font-bold">{errors.price}</p>}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            <Separator className="bg-slate-800/50" />

            {/* Risk Management Panel - Now in Horizontal Layout */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
              <div className="md:col-span-2 grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="stop_loss" className="text-[9px] font-black text-slate-500 uppercase ml-1 flex items-center gap-1 opacity-70">
                    <div className="h-1 w-1 rounded-full bg-rose-500" /> Stop Loss
                  </Label>
                  <Input
                    id="stop_loss"
                    type="number"
                    value={formData.stop_loss}
                    onChange={(e) => handleInputChange("stop_loss", e.target.value)}
                    className="bg-slate-900/40 border-slate-800 rounded-xl h-10 text-xs font-mono text-rose-400 focus-visible:ring-rose-500/20"
                    placeholder="Exit price..."
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="take_profit" className="text-[9px] font-black text-slate-500 uppercase ml-1 flex items-center gap-1 opacity-70">
                     <div className="h-1 w-1 rounded-full bg-emerald-500" /> Take Profit
                  </Label>
                  <Input
                    id="take_profit"
                    type="number"
                    value={formData.take_profit}
                    onChange={(e) => handleInputChange("take_profit", e.target.value)}
                    className="bg-slate-900/40 border-slate-800 rounded-xl h-10 text-xs font-mono text-emerald-400 focus-visible:ring-emerald-500/20"
                    placeholder="Target price..."
                  />
                </div>
              </div>

              {/* R:R Indicator - Compact Version */}
              {riskReward.ratio > 0 ? (
                <div className="bg-sky-500/5 px-4 py-2.5 rounded-xl border border-sky-500/10 flex flex-col justify-center">
                   <div className="flex items-center justify-between">
                     <span className="text-[8px] font-bold text-slate-500 uppercase tracking-tighter">R:R Ratio</span>
                     <span className={cn(
                        "text-xs font-black",
                        riskReward.ratio >= 2 ? "text-emerald-400" : "text-amber-400"
                      )}>
                        1 : {formatPrice(riskReward.ratio)}
                      </span>
                   </div>
                   <div className="flex items-center justify-between mt-1 pt-1 border-t border-white/[0.03]">
                     <span className="text-[8px] font-bold text-slate-500 uppercase tracking-tighter">Risk Amt</span>
                     <span className="text-xs font-black text-rose-400">{formatCurrency(riskReward.risk)}</span>
                   </div>
                </div>
              ) : (
                <div className="h-full flex items-center justify-center border border-dashed border-slate-800/50 rounded-xl px-4 py-2 opacity-50">
                  <p className="text-[9px] font-bold text-slate-600 uppercase tracking-widest text-center leading-tight">Define Targets for Risk Analysis</p>
                </div>
              )}
            </div>

            <div className="flex gap-3 pt-1">
              <Button
                type="button"
                variant="ghost"
                onClick={onClose}
                disabled={isSubmitting}
                className="flex-1 h-10 rounded-xl font-bold text-[10px] text-slate-500 hover:text-white hover:bg-white/5 uppercase tracking-widest"
              >
                Discard
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting}
                className="flex-[2] h-10 rounded-xl font-black text-[10px] bg-amber-500 hover:bg-amber-600 text-white shadow-lg shadow-amber-500/20 transition-all active:scale-95 uppercase tracking-widest"
              >
                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Commit Modification"}
              </Button>
            </div>
          </form>
        </div>
      </DialogContent>
    </Dialog>
  );
}

