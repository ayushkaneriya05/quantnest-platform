import React from "react";
import { Button } from "@/shared/components/ui/button";
import { cn } from "@/shared/lib/utils";

const TIMEFRAMES = ["1m", "5m", "15m", "1h", "1D", "1W"];

export default function TimeframeSelector({ selected, onSelect, disabled }) {
  return (
    <div className="flex items-center gap-1.5 bg-slate-900/40 border border-slate-800/80 backdrop-blur-md rounded-2xl p-1.5 shadow-inner">
      {TIMEFRAMES.map((tf) => (
        <Button
          key={tf}
          variant="ghost"
          size="sm"
          onClick={() => onSelect(tf)}
          disabled={disabled}
          className={cn(
            "px-4 h-8 text-[11px] font-black uppercase tracking-tighter transition-all duration-300 rounded-xl",
            selected === tf
              ? "bg-sky-500 text-white shadow-lg shadow-sky-500/20 active:scale-95"
              : "text-slate-500 hover:bg-white/5 hover:text-slate-200"
          )}
        >
          {tf}
        </Button>
      ))}
    </div>
  );
}
