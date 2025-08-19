import React, { useState, useEffect } from "react";
import { Trash2, Star, TrendingUp, TrendingDown, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import api from "@/services/api";
import InstrumentSearch from "./InstrumentSearch";

const WatchlistItem = ({ item, onSymbolSelect, onRemove, isSelected }) => {
  const priceChange = Math.random() > 0.5 ? 1 : -1; // Mock data
  const changePercent = (Math.random() * 5).toFixed(2);
  const currentPrice = (1500 + Math.random() * 1000).toFixed(2);
  
  return (
    <div
      className={`
        group relative p-4 rounded-xl transition-all duration-300 cursor-pointer
        ${isSelected 
          ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 shadow-lg shadow-cyan-500/10' 
          : 'bg-gradient-to-r from-gray-800/50 to-gray-700/30 hover:from-gray-700/60 hover:to-gray-600/40 border border-gray-700/50 hover:border-gray-600/60'
        }
        hover:scale-[1.02] hover:shadow-lg
      `}
      onClick={() => onSymbolSelect(item.symbol)}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-bold text-slate-100 truncate">{item.symbol}</h3>
            {isSelected && (
              <div className="flex-shrink-0 w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
            )}
          </div>
          <p className="text-xs text-slate-400 truncate mb-2">
            {item.company_name || "Company Name Ltd."}
          </p>
          
          <div className="flex items-center justify-between">
            <div className="flex flex-col">
              <span className="font-mono text-lg font-bold text-slate-200">
                ₹{currentPrice}
              </span>
              <div className="flex items-center gap-1">
                {priceChange > 0 ? (
                  <TrendingUp className="h-3 w-3 text-emerald-400" />
                ) : (
                  <TrendingDown className="h-3 w-3 text-red-400" />
                )}
                <span className={`text-xs font-medium ${
                  priceChange > 0 ? 'text-emerald-400' : 'text-red-400'
                }`}>
                  {priceChange > 0 ? '+' : '-'}{changePercent}%
                </span>
              </div>
            </div>
            
            <Button
              variant="ghost"
              size="icon"
              className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 text-red-400 hover:bg-red-500/10 hover:text-red-300 h-8 w-8"
              onClick={(e) => {
                e.stopPropagation();
                onRemove(item.id);
              }}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
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

  if (loading) {
    return (
      <Card className="bg-gradient-to-br from-gray-900/80 to-gray-800/50 border-gray-700/50">
        <CardContent className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-6 bg-gray-700/50 rounded w-3/4"></div>
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="p-4 bg-gray-700/30 rounded-lg">
                  <div className="h-4 bg-gray-600/50 rounded w-1/2 mb-2"></div>
                  <div className="h-3 bg-gray-600/30 rounded w-3/4"></div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-gradient-to-br from-gray-900/80 to-gray-800/50 border-gray-700/50 shadow-xl">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20">
              <Star className="h-5 w-5 text-cyan-400" />
            </div>
            <CardTitle className="text-xl text-slate-100">
              Watchlist
            </CardTitle>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-cyan-400 hover:bg-cyan-500/10 hover:text-cyan-300 transition-all duration-200"
            onClick={() => setSearchExpanded(!searchExpanded)}
          >
            {searchExpanded ? <Search className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          </Button>
        </div>
        
        {searchExpanded && (
          <div className="mt-4 animate-in slide-in-from-top-2 duration-300">
            <InstrumentSearch onAddToWatchlist={handleAddToWatchlist} />
          </div>
        )}
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="space-y-3 max-h-[600px] overflow-y-auto scrollbar-custom">
          {watchlist && watchlist.length > 0 ? (
            watchlist.map((item) => (
              <WatchlistItem
                key={item.id}
                item={item}
                onSymbolSelect={handleSymbolSelect}
                onRemove={handleRemoveFromWatchlist}
                isSelected={selectedSymbol === item.symbol}
              />
            ))
          ) : (
            <div className="text-center py-12">
              <div className="p-4 rounded-full bg-gray-800/50 w-fit mx-auto mb-4">
                <Star className="h-8 w-8 text-gray-600" />
              </div>
              <h3 className="text-lg font-medium text-slate-300 mb-2">
                No instruments in watchlist
              </h3>
              <p className="text-sm text-slate-500 mb-4">
                Add your favorite stocks to track them easily
              </p>
              <Button
                variant="outline"
                className="border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 hover:border-cyan-400/50"
                onClick={() => setSearchExpanded(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Instrument
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
