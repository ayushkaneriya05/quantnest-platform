import React, { useState, useEffect } from "react";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import api from "@/services/api";
import InstrumentSearch from "./InstrumentSearch";

export default function Watchlist() {
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchWatchlist = async () => {
    try {
      const response = await api.get("/trading/watchlist/");
      setWatchlist(response.data.instruments);
    } catch (err) {
      console.error("Failed to fetch watchlist:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const handleAddToWatchlist = async (instrumentId) => {
    try {
      await api.post("/trading/watchlist/", { instrument_id: instrumentId });
      fetchWatchlist(); // Refresh the list
    } catch (err) {
      console.error("Failed to add to watchlist:", err);
    }
  };

  const handleRemoveFromWatchlist = async (instrumentId) => {
    try {
      await api.delete("/trading/watchlist/", {
        data: { instrument_id: instrumentId },
      });
      fetchWatchlist(); // Refresh the list
    } catch (err) {
      console.error("Failed to remove from watchlist:", err);
    }
  };

  if (loading) {
    return <div>Loading Watchlist...</div>;
  }

  return (
    <div className="p-4 bg-gray-900/50 border border-gray-800/50 rounded-lg">
      <h2 className="text-lg font-semibold text-slate-100 mb-4">
        My Watchlist
      </h2>
      <InstrumentSearch onAddToWatchlist={handleAddToWatchlist} />
      <div className="mt-4 space-y-2">
        {watchlist.map((item) => (
          <div
            key={item.id}
            className="flex justify-between items-center p-2 rounded hover:bg-gray-800/50"
          >
            <div>
              <p className="font-medium text-slate-200">{item.symbol}</p>
              <p className="text-xs text-slate-400">{item.company_name}</p>
            </div>
            {/* Price and change will be added here from WebSocket data later */}
            <div className="text-right">
              <p className="font-mono text-slate-200">₹1500.00</p>
              <p className="text-emerald-400 text-xs">+1.25%</p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="text-red-400 hover:bg-red-500/10 hover:text-red-300"
              onClick={() => handleRemoveFromWatchlist(item.id)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
