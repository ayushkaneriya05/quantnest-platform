import React, { useEffect, useMemo, useState } from "react";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { Calculator, DollarSign, Loader2, ShieldCheck, Zap } from "lucide-react";

import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Badge } from "@/shared/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useWebSocket } from "@/shared/hooks/useWebSocket";
import { cn } from "@/shared/lib/utils";
import { Separator } from "@/shared/components/ui/separator";

import tradingTerminalApi from "@/features/terminal/services/tradingTerminalApi.js";

const ORDER_TYPES = [
  { value: "MARKET", label: "Market", description: "Best available price" },
  { value: "LIMIT", label: "Limit", description: "Exact price or better" },
  { value: "STOP", label: "Stop", description: "Triggered exit" },
  { value: "STOP_LIMIT", label: "Stop Limit", description: "Triggered boundary" },
];

export default function OrderTicket({
  symbol,
  transactionType,
  onOrderPlaced,
  onClose,
  currentMarketPrice, // Received from parent modal for better sync
}) {
  const { notify } = useNotifications();
  const { getTickData, subscribe } = useWebSocket();

  const [isLoading, setIsLoading] = useState(false);
  const [currentPrice, setCurrentPrice] = useState(currentMarketPrice);
  const [formData, setFormData] = useState({
    transaction_type: transactionType,
    order_type: "MARKET",
    quantity: "",
    price: "",
    trigger_price: "",
  });

  useEffect(() => {
    setFormData((current) => ({ ...current, transaction_type: transactionType }));
  }, [transactionType]);

  useEffect(() => {
    if (currentMarketPrice !== null) {
      setCurrentPrice(currentMarketPrice);
    }
  }, [currentMarketPrice]);

  useEffect(() => {
    if (!symbol || currentMarketPrice !== null) return undefined;

    const cachedTick = getTickData(symbol);
    if (cachedTick?.price != null) {
      setCurrentPrice(Number(cachedTick.price));
    }

    const unsubscribe = subscribe(symbol, (tick) => {
      setCurrentPrice(Number(tick.price));
    });

    return unsubscribe;
  }, [getTickData, subscribe, symbol, currentMarketPrice]);

  const estimatedValue = useMemo(() => {
    const quantity = Number(formData.quantity || 0);
    const effectivePrice =
      formData.order_type === "LIMIT" || formData.order_type === "STOP_LIMIT"
        ? Number(formData.price || 0)
        : Number(currentPrice || 0);

    return quantity * effectivePrice;
  }, [currentPrice, formData.order_type, formData.price, formData.quantity]);

  const requiresPrice =
    formData.order_type === "LIMIT" || formData.order_type === "STOP_LIMIT";
  const requiresTriggerPrice =
    formData.order_type === "STOP" || formData.order_type === "STOP_LIMIT";

  const isFormValid = () => {
    const quantity = Number(formData.quantity);
    if (!quantity || quantity <= 0) return false;
    if (formData.order_type === "MARKET" && Number(currentPrice || 0) <= 0) return false;
    if (requiresPrice && Number(formData.price) <= 0) return false;
    if (requiresTriggerPrice && Number(formData.trigger_price) <= 0) return false;
    return true;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsLoading(true);

    try {
      const payload = {
        instrument_symbol: symbol,
        transaction_type: formData.transaction_type,
        order_type: formData.order_type,
        quantity: Number(formData.quantity),
      };

      if (requiresPrice) payload.price = Number(formData.price);
      if (requiresTriggerPrice) payload.trigger_price = Number(formData.trigger_price);

      await tradingTerminalApi.placeOrder(payload);

      onOrderPlaced();
      onClose();
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Order submission failed."));
    } finally {
      setIsLoading(false);
    }
  };

  const setField = (name, value) => {
    setFormData((current) => ({ ...current, [name]: value }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground ml-1">
            Order Mode
          </Label>
          <Select
            value={formData.order_type}
            onValueChange={(value) => setField("order_type", value)}
          >
            <SelectTrigger className="border-border bg-card/60 rounded-xl h-10 transition-all focus:ring-sky-500/20">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-border bg-background text-foreground rounded-xl">
              {ORDER_TYPES.map((type) => (
                <SelectItem key={type.value} value={type.value} className="focus:bg-muted/50 py-2">
                  <div className="flex flex-col text-left">
                    <span className="font-bold text-sm">{type.label}</span>
                    <span className="text-[10px] text-muted-foreground">{type.description}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground ml-1">
            Market Side
          </Label>
          <Select
            value={formData.transaction_type}
            onValueChange={(value) => setField("transaction_type", value)}
          >
            <SelectTrigger className={cn(
              "border-border bg-card/60 rounded-xl h-10 transition-all focus:ring-opacity-20",
              formData.transaction_type === "BUY" ? "focus:ring-emerald-500" : "focus:ring-rose-500"
            )}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-border bg-background text-foreground rounded-xl">
              <SelectItem value="BUY" className="text-emerald-700 dark:text-emerald-400 focus:text-emerald-800 dark:focus:text-emerald-300 py-2.5 font-bold">
                BUYING
              </SelectItem>
              <SelectItem value="SELL" className="text-rose-700 dark:text-rose-400 focus:text-rose-800 dark:focus:text-rose-300 py-2.5 font-bold">
                SELLING
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground ml-1">
          Quantity Selection
        </Label>
        <div className="relative group">
          <Input
            name="quantity"
            type="number"
            value={formData.quantity}
            onChange={(event) => setField("quantity", event.target.value)}
            className="border-border bg-card/60 rounded-xl h-12 text-lg font-black font-mono text-foreground pl-4 transition-all focus-visible:ring-sky-500/20 focus-visible:border-sky-500/40"
            placeholder="0"
            required
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex gap-1 group-focus-within:opacity-100 transition-opacity">
            {[1, 10, 50].map((qty) => (
              <Button
                key={qty}
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setField("quantity", String(qty))}
                className="h-6 px-2 bg-secondary hover:bg-muted text-[9px] font-black text-foreground rounded-lg border border-border transition-all active:scale-90"
              >
                +{qty}
              </Button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {requiresPrice && (
          <div className="space-y-1.5">
            <Label className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground ml-1">
              Limit Price
            </Label>
            <Input
              type="number"
              step="0.01"
              value={formData.price}
              onChange={(event) => setField("price", event.target.value)}
              className="border-border bg-card/40 rounded-xl h-10 font-black font-mono text-foreground focus-visible:ring-sky-500/20"
              placeholder="Entry value"
              required
            />
          </div>
        )}

        {requiresTriggerPrice && (
          <div className="space-y-1.5">
            <Label className="text-[9px] font-black uppercase tracking-[0.2em] text-muted-foreground ml-1">
              Trigger Price
            </Label>
            <Input
              type="number"
              step="0.01"
              value={formData.trigger_price}
              onChange={(event) => setField("trigger_price", event.target.value)}
              className="border-border bg-card/40 rounded-xl h-10 font-black font-mono text-foreground focus-visible:ring-sky-500/20"
              placeholder="Stop trigger"
              required
            />
          </div>
        )}
      </div>

      <div className="bg-card/60 rounded-2xl border border-border overflow-hidden shadow-xl">
        <div className="px-4 py-2.5 bg-muted/50 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calculator className="h-3 w-3 text-sky-700 dark:text-sky-400" />
            <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground">Summary</span>
          </div>
          <Badge variant="outline" className="text-[8px] h-3.5 leading-none border-border text-muted-foreground font-bold">EST</Badge>
        </div>

        <div className="p-4 space-y-2.5">
          <div className="flex justify-between items-center text-xs">
            <span className="font-bold text-muted-foreground uppercase tracking-tighter">Units</span>
            <span className="font-black text-foreground">{formData.quantity || "--"} units</span>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="font-bold text-muted-foreground uppercase tracking-tighter">Price</span>
            <span className="font-mono font-black text-sky-700 dark:text-sky-400">
              {formData.order_type === "MARKET"
                ? currentPrice != null
                  ? `₹${currentPrice.toFixed(2)}`
                  : "FETCHING..."
                : `₹${parseFloat(formData.price || 0).toFixed(2)}`}
            </span>
          </div>
          
          <Separator className="bg-muted/50" />
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <DollarSign className="h-3.5 w-3.5 text-success" />
              <span className="text-[11px] font-black text-foreground uppercase tracking-tight">Total</span>
            </div>
            <span className="font-mono font-black text-foreground text-lg">
              ₹ {estimatedValue.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>
      </div>

      <div className="p-3 bg-amber-500/5 rounded-xl border border-amber-500/10 border-dashed">
        <div className="flex items-center gap-2.5">
          <ShieldCheck className="h-4 w-4 text-warning shrink-0" />
          <p className="text-[9px] text-warning font-bold uppercase tracking-tighter leading-tight">
            Virtual Execution active. No capital commitment required.
          </p>
        </div>
      </div>

      <div className="flex gap-3 pt-2">
        <Button
          type="button"
          variant="ghost"
          onClick={onClose}
          className="flex-1 h-10 rounded-xl font-bold text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all text-sm"
        >
          Discard
        </Button>
        <Button
          type="submit"
          disabled={isLoading || !isFormValid()}
          className={cn(
            "flex-[1.8] h-11 rounded-xl font-black text-white text-sm shadow-lg transition-all active:scale-95 border-b-[3px]",
            formData.transaction_type === "BUY"
              ? "bg-emerald-700 hover:bg-emerald-800 border-emerald-800 shadow-emerald-900/30"
              : "bg-rose-600 hover:bg-rose-700 border-rose-800 shadow-rose-900/30"
          )}
        >
          {isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin mx-auto text-white" />
          ) : (
            <span className="flex items-center justify-center gap-2 capitalize">
              <Zap className="h-4 w-4 fill-current" />
              {formData.transaction_type.toLowerCase()} {formData.quantity || 0} units
            </span>
          )}
        </Button>
      </div>
    </form>
  );
}
