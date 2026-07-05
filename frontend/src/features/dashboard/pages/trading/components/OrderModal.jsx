import React, { useEffect, useState } from "react";
import { cn } from "@/shared/lib/utils";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Badge } from "@/shared/components/ui/badge";
import { useWebSocket } from "@/shared/hooks/useWebSocket";
import { Activity } from "lucide-react";

import OrderTicket from "./OrderTicket";

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
      <DialogContent className="sm:max-w-lg bg-slate-950/95 border-slate-800/80 backdrop-blur-3xl text-white rounded-[2rem] shadow-[0_25px_70px_rgba(0,0,0,0.6)] animate-in zoom-in-95 duration-300 p-0 border overflow-hidden flex flex-col max-h-[95vh]">
        {/* Header - Fixed at top */}
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-white/[0.03] space-y-3 shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={cn(
                "p-2.5 rounded-2xl border transition-colors duration-500 shadow-lg",
                transactionType === "BUY" 
                  ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" 
                  : "bg-rose-500/10 border-rose-500/20 text-rose-400"
              )}>
                <Activity className="h-5 w-5" />
              </div>
              <div>
                <DialogTitle className="text-xl font-black tracking-tight leading-none mb-1 text-white uppercase">
                  {transactionType} {symbol}
                </DialogTitle>
                <p className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Global Order Gateway</p>
              </div>
            </div>
            
            <Badge variant="outline" className="border-slate-800 bg-slate-900/50 text-[9px] h-5 px-2 text-slate-400 font-bold tracking-tighter uppercase">
              NSE:EQUITY
            </Badge>
          </div>

          <div className="flex items-center justify-between p-3.5 bg-slate-900/40 rounded-xl border border-white/[0.03]">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                <div className="absolute inset-0 h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping" />
              </div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Live Feed</span>
            </div>
            <div className="text-right">
              <div className="font-mono text-lg font-black text-white leading-none mb-0.5 tabular-nums">
                {currentPrice != null ? `₹${currentPrice.toFixed(2)}` : "---.--"}
              </div>
            </div>
          </div>
        </DialogHeader>

        {/* Scrollable Content Area */}
        <div className="flex-1 overflow-y-auto scrollbar-custom relative">
          <div className="relative z-10 px-6 pb-8 pt-4">
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
