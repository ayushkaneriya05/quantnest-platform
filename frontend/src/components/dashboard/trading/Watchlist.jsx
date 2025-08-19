import React, { useState, useEffect } from "react";
import { Trash2, Plus, Search, Star, TrendingUp, TrendingDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import api from "@/services/api";
import InstrumentSearch from "./InstrumentSearch";

const WatchlistItem = ({ item, onSymbolSelect, onRemove, isSelected }) => {
  const priceChange = Math.random() > 0.5 ? 1 : -1; // Mock data
  const changePercent = (Math.random() * 5).toFixed(2);
  const currentPrice = (1500 + Math.random() * 1000).toFixed(2);
  const isPositive = priceChange > 0;
  
  return (
    <div
      className={`
        group relative px-4 py-3 cursor-pointer transition-all duration-200 border-l-2
        ${isSelected 
          ? 'bg-[#0969da]/10 border-l-[#0969da] text-white' 
          : 'hover:bg-[#21262d] border-l-transparent text-gray-300 hover:text-white'
        }
      `}
      onClick={() => onSymbolSelect(item.symbol)}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-sm truncate">{item.symbol}</span>
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
              ₹{currentPrice}
            </span>
            <div className={`flex items-center text-xs ${
              isPositive ? 'text-emerald-400' : 'text-red-400'
            }`}>
              {isPositive ? (
                <TrendingUp className="h-3 w-3 mr-1" />
              ) : (
                <TrendingDown className="h-3 w-3 mr-1" />
              )}
              {isPositive ? '+' : ''}{changePercent}%
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
  const [selectedSymbol, setSelectedSymbol] = useState("RELIANCE");
  const [searchExpanded, setSearchExpanded] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchWatchlist = async () => {
    try {
      const response = await api.get("/trading/watchlist/");
      
      if (response.data && response.data.instruments && Array.isArray(response.data.instruments)) {
        setWatchlist(response.data.instruments);
      } else {
        console.error("Invalid watchlist response:", response.data);
        setWatchlist([]); // Set empty array as fallback
      }
    } catch (err) {
      console.error("Failed to fetch watchlist:", err);
      setWatchlist([]); // Set empty array on error
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
      setSearchExpanded(false);
      setSearchQuery("");
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

  const handleSymbolSelect = (symbol) => {
    setSelectedSymbol(symbol);
    onSymbolSelect(symbol);
  };

  const filteredWatchlist = watchlist.filter(item =>
    item.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (item.company_name && item.company_name.toLowerCase().includes(searchQuery.toLowerCase()))
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
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Star className="h-5 w-5 text-yellow-400" />
            Watchlist
          </h2>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-gray-400 hover:text-white hover:bg-gray-800"
            onClick={() => setSearchExpanded(!searchExpanded)}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-500" />
          <Input
            placeholder="Search symbols..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-[#21262d] border-gray-700 text-white placeholder-gray-500 focus:border-[#0969da] focus:ring-1 focus:ring-[#0969da]"
          />
        </div>

        {searchExpanded && (
          <div className="mt-3 animate-in slide-in-from-top-2 duration-200">
            <InstrumentSearch onAddToWatchlist={handleAddToWatchlist} />
          </div>
        )}
      </div>
      
      {/* Watchlist Items */}
      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-track-gray-800 scrollbar-thumb-gray-600">
        {filteredWatchlist && filteredWatchlist.length > 0 ? (
          <div className="divide-y divide-gray-800/50">
            {filteredWatchlist.map((item) => (
              <WatchlistItem
                key={item.id}
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
              {searchQuery ? 'No results found' : 'No instruments in watchlist'}
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              {searchQuery 
                ? `No symbols match "${searchQuery}"`
                : 'Add your favorite stocks to track them'
              }
            </p>
            {!searchQuery && (
              <Button
                variant="outline"
                size="sm"
                className="border-gray-700 text-gray-400 hover:bg-gray-800 hover:text-white"
                onClick={() => setSearchExpanded(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Symbol
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
