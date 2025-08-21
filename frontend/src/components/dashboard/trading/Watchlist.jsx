import React, { useState, useEffect } from "react";
import { Trash2, Search, Star, TrendingUp, TrendingDown, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useWebSocketContext } from "@/contexts/websocket-context";
import api from "@/services/api";
import toast from "react-hot-toast";

const WatchlistItem = ({ item, onSymbolSelect, onRemove, isSelected }) => {
  const { getLatestPrice } = useWebSocketContext();
  
  // Get live price or use mock data
  const currentPrice = getLatestPrice(item.symbol) || (2000 + Math.random() * 1000);
  const priceChange = Math.random() > 0.5 ? 1 : -1;
  const changePercent = (Math.random() * 5).toFixed(2);
  const isPositive = priceChange > 0;

  return (
    <div
      className={`
        group relative px-4 py-3 cursor-pointer transition-all duration-200 border-l-2
        ${
          isSelected
            ? "bg-gray-600/20 border-l-gray-500 text-white"
            : "hover:bg-[#21262d] border-l-transparent text-gray-300 hover:text-white"
        }
      `}
      onClick={() => onSymbolSelect(item.symbol)}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-sm truncate">
              {item.symbol}
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="opacity-0 group-hover:opacity-100 transition-opacity h-6 w-6 text-red-400 hover:bg-red-500/10 hover:text-red-300"
              onClick={(e) => {
                e.stopPropagation();
                onRemove(item.id);
              }}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>

          <div className="flex items-center justify-between">
            <span className="font-mono text-sm font-medium">
              ₹{currentPrice.toFixed(2)}
            </span>
            <div
              className={`flex items-center text-xs ${
                isPositive ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {isPositive ? (
                <TrendingUp className="h-3 w-3 mr-1" />
              ) : (
                <TrendingDown className="h-3 w-3 mr-1" />
              )}
              {isPositive ? "+" : ""}
              {changePercent}%
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default function Watchlist({ onSymbolSelect }) {
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSymbol, setSelectedSymbol] = useState("RELIANCE");
  const [searchQuery, setSearchQuery] = useState("");

  const { isConnected } = useWebSocketContext();

  const fetchWatchlist = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await api.get("/api/v1/trading/watchlist/");

      if (response.data) {
        const instruments = response.data.instruments || response.data || [];
        
        if (Array.isArray(instruments)) {
          setWatchlist(instruments);
        } else {
          console.warn("Invalid watchlist response format:", response.data);
          setWatchlist([]);
        }
      } else {
        setWatchlist([]);
      }
    } catch (err) {
      console.error("Failed to fetch watchlist:", err);
      setError("Failed to load watchlist");
      setWatchlist([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const handleRemoveFromWatchlist = async (instrumentId) => {
    try {
      await api.delete("/api/v1/trading/watchlist/", {
        data: { instrument_id: instrumentId },
      });
      
      toast.success("Removed from watchlist");
      fetchWatchlist();
    } catch (err) {
      console.error("Failed to remove from watchlist:", err);
      toast.error("Failed to remove from watchlist");
    }
  };

  const handleSymbolSelect = (symbol) => {
    setSelectedSymbol(symbol);
    if (onSymbolSelect) {
      onSymbolSelect(symbol);
    }
  };

  const filteredWatchlist = watchlist.filter(
    (item) =>
      item.symbol?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.company_name &&
        item.company_name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  if (loading) {
    return (
      <div className="h-full bg-[#0d1117] p-4">
        <div className="animate-pulse space-y-3">
          <div className="h-6 bg-gray-800 rounded w-3/4"></div>
          <div className="space-y-2">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-800/50 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-[#0d1117] flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 p-4 border-b border-gray-800/50">
        <div className="flex items-center mb-3">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Star className="h-5 w-5 text-yellow-400" />
            Watchlist
          </h2>
          {!isConnected && (
            <Badge variant="outline" className="ml-2 text-xs border-yellow-600 text-yellow-400">
              Demo
            </Badge>
          )}
        </div>

        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-500" />
          <Input
            placeholder="Search symbols..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-[#21262d] border-gray-700 text-white placeholder-gray-500 focus:border-gray-500 focus:ring-1 focus:ring-gray-500"
          />
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-900/20 border border-red-700/50 rounded-lg">
          <div className="flex items-center gap-2 text-red-300 text-sm">
            <AlertCircle className="h-4 w-4" />
            {error}
            <Button
              onClick={fetchWatchlist}
              size="sm"
              variant="outline"
              className="ml-auto h-6 px-2 text-xs border-red-700 text-red-300 hover:bg-red-800"
            >
              Retry
            </Button>
          </div>
        </div>
      )}

      {/* Watchlist Items */}
      <div className="flex-1 overflow-y-auto scrollbar-theme">
        {filteredWatchlist && filteredWatchlist.length > 0 ? (
          <div className="divide-y divide-gray-800/50">
            {filteredWatchlist.map((item) => (
              <WatchlistItem
                key={item.id || item.symbol}
                item={item}
                onSymbolSelect={handleSymbolSelect}
                onRemove={handleRemoveFromWatchlist}
                isSelected={selectedSymbol === item.symbol}
              />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-6">
            <div className="p-4 rounded-full bg-gray-800/50 mb-4">
              <Star className="h-8 w-8 text-gray-600" />
            </div>
            <h3 className="text-lg font-medium text-gray-300 mb-2">
              {searchQuery ? "No results found" : "No instruments in watchlist"}
            </h3>
            <p className="text-sm text-gray-500">
              {searchQuery
                ? `No symbols match "${searchQuery}"`
                : "Use the search above to add instruments to your watchlist"}
            </p>
            {!searchQuery && (
              <Button
                onClick={fetchWatchlist}
                variant="outline"
                size="sm"
                className="mt-4 border-gray-700 text-gray-300 hover:bg-gray-800"
              >
                Refresh Watchlist
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
