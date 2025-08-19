import { Button } from "@/components/ui/button";
import React from "react";
const timeframes = ["1m", "5m", "15m", "1h", "1D", "1W"];

export default function TimeframeSelector({ selected, onSelect, disabled }) {
  return (
    <div className="flex items-center space-x-1 bg-gray-900/50 border border-gray-800/50 rounded-md p-1">
      {timeframes.map((tf) => (
        <Button
          key={tf}
          variant={selected === tf ? "secondary" : "ghost"}
          size="sm"
          onClick={() => onSelect(tf)}
          disabled={disabled}
          className={`px-3 py-1 h-auto text-xs transition-colors duration-200 ${
            selected === tf
              ? "bg-indigo-600 text-white hover:bg-indigo-500"
              : "text-slate-400 hover:bg-gray-700/50 hover:text-slate-200"
          }`}
        >
          {tf}
        </Button>
      ))}
    </div>
  );
}
