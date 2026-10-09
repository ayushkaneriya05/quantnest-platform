import React, { useEffect, useState } from "react";
import { cn } from "@/shared/lib/utils";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Badge } from "@/shared/components/ui/badge";
import { useWebSocket } from "@/shared/hooks/useWebSocket";
import { Activity } from "lucide-react";

import OrderTicket from "@/features/terminal/components/OrderTicket.jsx";

export default function OrderModal({
  isOpen,
  onClose,
  symbol,
  transactionType,
  onOrderPlaced,
}) {
  const [currentPrice, setCurrentPrice] = useState(null);
  const { getTickData, subscribe } = useWebSocket();

  useEffect(() => {
    if (!isOpen || !symbol) {
      setCurrentPrice(null);
      return undefined;
    }

    const cachedTick = getTickData(symbol);
    if (cachedTick?.price != null) {
      setCurrentPrice(Number(cachedTick.price));
    }

    const unsubscribe = subscribe(symbol, (tick) => {
      setCurrentPrice(Number(tick.price));
    });

    return unsubscribe;
  }, [getTickData, isOpen, subscribe, symbol]);

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="left-0 top-[calc(var(--viewport-height)_/_2)] w-full max-w-none translate-x-0 -translate-y-1/2 rounded-b-none rounded-t-2xl sm:left-1/2 sm:top-[calc(var(--viewport-height)_/_2)] sm:bottom-auto sm:w-[calc(100%_-_2rem)] sm:max-w-lg sm:-translate-x-1/2 sm:-translate-y-1/2 bg-card border-border/80 backdrop-blur-3xl text-foreground sm:rounded-2xl shadow-card animate-in zoom-in-95 duration-300 p-0 border overflow-hidden flex flex-col max-h-[95dvh]">
        {/* Header - Fixed at top */}
        <DialogHeader className="px-4 pt-5 pb-3 pr-12 sm:px-6 sm:pr-12 border-b border-border space-y-3 shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={cn(
                "p-2.5 rounded-2xl border transition-colors duration-500 shadow-lg",
                transactionType === "BUY" 
                  ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-700 dark:text-emerald-400" 
                  : "bg-rose-500/10 border-rose-500/20 text-rose-700 dark:text-rose-400"
              )}>
                <Activity className="h-5 w-5" />
              </div>
              <div>
                <DialogTitle className="break-words text-lg font-semibold tracking-tight leading-none mb-1 text-foreground uppercase">
                  {transactionType} {symbol}
                </DialogTitle>
                <p className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest">Terminal order</p>
              </div>
            </div>
            
            <Badge variant="outline" className="border-border bg-card/50 text-[9px] h-5 px-2 text-muted-foreground font-bold tracking-tighter uppercase">
              NSE:EQUITY
            </Badge>
          </div>

          <div className="flex items-center justify-between p-3.5 bg-card/40 rounded-xl border border-border">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                <div className="absolute inset-0 h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping" />
              </div>
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Live Feed</span>
            </div>
            <div className="text-right">
              <div className="font-mono text-lg font-black text-foreground leading-none mb-0.5 tabular-nums">
                {currentPrice != null ? `₹${currentPrice.toFixed(2)}` : "---.--"}
              </div>
            </div>
          </div>
        </DialogHeader>

        {/* Scrollable Content Area */}
        <div className="min-h-0 flex-1 overflow-y-auto scrollbar-custom relative">
          <div className="relative z-10 safe-bottom px-4 pb-6 pt-4 sm:px-6">
            <OrderTicket
              symbol={symbol}
              transactionType={transactionType}
              onOrderPlaced={onOrderPlaced}
              onClose={onClose}
              currentMarketPrice={currentPrice}
            />
          </div>

          {/* Accent glow moved inside scrollable area or kept behind */}
          <div className={cn(
            "absolute -top-24 -left-24 w-48 h-48 opacity-20 blur-[80px] rounded-full pointer-events-none",
            transactionType === "BUY" ? "bg-emerald-500" : "bg-rose-500"
          )} />
        </div>
      </DialogContent>
    </Dialog>
  );
}
