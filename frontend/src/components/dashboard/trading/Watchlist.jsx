import React, { useState, useEffect, useMemo, useCallback } from "react";
import { Trash2, Loader2, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import api from "@/services/api";
import InstrumentSearch from "./InstrumentSearch";
import { cn } from "@/lib/utils";
import { useWebSocket } from "@/contexts/websocket-context";

// Helper function to safely parse numbers
const safeNumber = (value, defaultValue = 0) => {
  const num = parseFloat(value);
  return isNaN(num) ? defaultValue : num;
};

export default function Watchlist({ onSymbolSelect, activeSymbol }) {
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const { subscribe, tickData, isConnected } = useWebSocket();

  const fetchWatchlist = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get("/trading/watchlist/");
      setWatchlist(response.data.instruments || []);
    } catch (err) {
      console.error("Failed to fetch watchlist:", err);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Could not fetch watchlist.",
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchWatchlist();
  }, [fetchWatchlist]);

  // Effect to manage WebSocket subscriptions for watchlist items
  useEffect(() => {
    if (!isConnected || watchlist.length === 0) return;

    const unsubscribers = watchlist.map((item) => {
      return subscribe(item.symbol, () => {});
    });

    return () => {
      unsubscribers.forEach((unsub) => unsub());
    };
  }, [watchlist, isConnected, subscribe]);

  const handleAddToWatchlist = async (instrument) => {
    try {
      await api.post("/trading/watchlist/", {
        instrument_id: instrument.id,
      });
      toast({
        title: "Success",
        description: `${instrument.symbol} added to watchlist.`,
      });
      fetchWatchlist();
    } catch (err) {
      console.error("Failed to add to watchlist:", err);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Could not add to watchlist.",
      });
    }
  };

  const handleRemoveFromWatchlist = async (instrumentId) => {
    try {
      await api.delete("/trading/watchlist/", {
        data: { instrument_id: instrumentId },
      });
      toast({ title: "Success", description: "Removed from watchlist." });
      setWatchlist((prev) => prev.filter((item) => item.id !== instrumentId));
    } catch (err) {
      console.error("Failed to remove from watchlist:", err);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Could not remove from watchlist.",
      });
      fetchWatchlist();
    }
  };

  const existingWatchlistSymbols = useMemo(
    () => watchlist.map((item) => item.symbol),
    [watchlist]
  );

  return (
    <div className="p-4 bg-gray-950/70 border border-gray-800/50 rounded-lg h-full flex flex-col">
      <h2 className="text-lg font-semibold text-white flex items-center gap-2 p-3">
        <Star className="h-5 w-5 text-yellow-400" />
        Watchlist
      </h2>
      <InstrumentSearch
        onAddToWatchlist={handleAddToWatchlist}
        existingWatchlistSymbols={existingWatchlistSymbols}
      />
      <div className="mt-4 space-y-1 flex-grow overflow-y-auto">
        {loading ? (
          <div className="flex justify-center items-center h-full">
            <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
          </div>
        ) : watchlist.length > 0 ? (
          watchlist.map((item) => {
            const liveTick = tickData.get(item.symbol);

            // FIX: Safely handle price and change data, using live ticks when available
            let price, change, changePercent;

            if (liveTick) {
              price = liveTick.price;
              change = liveTick.change;
              changePercent = liveTick.change_percent;
            } else {
              // Fallback to data from initial API load if available
              price = item.last_price;
              const prevClose = item.prev_close;
              if (price != null && prevClose != null) {
                change = price - prevClose;
                changePercent = prevClose > 0 ? (change / prevClose) * 100 : 0;
              }
            }

            return (
              <div
                key={item.id}
                className={cn(
                  "flex justify-between items-center p-2 rounded hover:bg-gray-800/50 cursor-pointer transition-colors duration-150",
                  activeSymbol === item.symbol &&
                    "bg-indigo-600/20 border-l-2 border-indigo-400"
                )}
                onClick={() => onSymbolSelect(item.symbol)}
              >
                <div className="flex-1 overflow-hidden">
                  <p className="font-medium text-slate-200">{item.symbol}</p>
                  <p className="text-xs text-slate-400 truncate">
                    {item.company_name}
                  </p>
                </div>
                <div className="text-right mx-2">
                  <p className="font-mono text-slate-200">
                    {price != null ? `₹${safeNumber(price).toFixed(2)}` : "---"}
                  </p>
                  {/* FIX: Only render change/percent if the data is available */}
                  {change != null && changePercent != null ? (
                    <p
                      className={cn(
                        "text-xs",
                        change >= 0 ? "text-emerald-400" : "text-red-400"
                      )}
                    >
                      {change >= 0 ? "+" : ""}
                      {change.toFixed(2)} ({changePercent.toFixed(2)}%)
                    </p>
                  ) : (
                    <p className="text-xs text-slate-500">---</p>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-slate-500 hover:bg-red-900/50 hover:text-red-400"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveFromWatchlist(item.id);
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            );
          })
        ) : (
          <div className="text-center text-slate-500 pt-10">
            <p>Your watchlist is empty.</p>
            <p className="text-xs mt-1">
              Use the search bar above to add stocks.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
