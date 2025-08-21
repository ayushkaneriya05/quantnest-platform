import React, { useState, useEffect, useRef } from "react";
import { Search, PlusCircle, TrendingUp, TrendingDown, AlertCircle, CheckCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useWebSocketContext } from "@/contexts/websocket-context";
import api from "@/services/api";
import toast from "react-hot-toast";

const SearchResultItem = ({ instrument, onSelect, isAdding }) => {
  const { getLatestPrice } = useWebSocketContext();
  const price = getLatestPrice(instrument.symbol);
  const priceChange = Math.random() > 0.5 ? 1 : -1;
  const changePercent = (Math.random() * 5).toFixed(2);
  const isPositive = priceChange > 0;

  return (
    <div className="px-4 py-3 hover:bg-gray-800/50 cursor-pointer border-b border-gray-700/30 last:border-b-0">
      <div className="flex justify-between items-center">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <div className="font-medium text-slate-200 text-sm">
                {instrument.symbol}
              </div>
              <div className="text-xs text-slate-400 truncate max-w-48">
                {instrument.company_name}
              </div>
            </div>
            
            {price && (
              <div className="text-right">
                <div className="font-mono text-sm text-slate-200">
                  ₹{price.toFixed(2)}
                </div>
                <div className={`flex items-center text-xs ${
                  isPositive ? "text-emerald-400" : "text-red-400"
                }`}>
                  {isPositive ? (
                    <TrendingUp className="h-3 w-3 mr-1" />
                  ) : (
                    <TrendingDown className="h-3 w-3 mr-1" />
                  )}
                  {isPositive ? "+" : ""}{changePercent}%
                </div>
              </div>
            )}
          </div>
        </div>
        
        <Button 
          variant="ghost" 
          size="sm" 
          className="ml-3 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-400/10"
          onClick={(e) => {
            e.stopPropagation();
            onSelect(instrument);
          }}
          disabled={isAdding}
        >
          {isAdding ? (
            <div className="animate-spin h-4 w-4 border-2 border-emerald-400 border-t-transparent rounded-full" />
          ) : (
            <PlusCircle className="h-4 w-4 mr-1" />
          )}
          {isAdding ? 'Adding...' : 'Add'}
        </Button>
      </div>
    </div>
  );
};

export default function InstrumentSearch({ onAddToWatchlist }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [addingInstruments, setAddingInstruments] = useState(new Set());
  
  const searchTimeoutRef = useRef(null);
  const inputRef = useRef(null);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Search functionality with debouncing
  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      setIsOpen(false);
      setError(null);
      return;
    }

    // Clear previous timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    setIsLoading(true);
    setError(null);

    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const response = await api.get(`/api/v1/trading/instruments/search/`, {
          params: { query: encodeURIComponent(query) }
        });
        setResults(response.data || []);
        setIsOpen(true);
        setError(null);
      } catch (err) {
        console.error("Search failed:", err);
        setError("Search failed. Please try again.");
        setResults([]);
        setIsOpen(false);
      } finally {
        setIsLoading(false);
      }
    }, 300);

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [query]);

  const handleSelect = async (instrument) => {
    if (addingInstruments.has(instrument.id)) return;

    setAddingInstruments(prev => new Set([...prev, instrument.id]));

    try {
      await api.post("/api/v1/trading/watchlist/", {
        instrument_id: instrument.id
      });
      
      toast.success(`${instrument.symbol} added to watchlist`, {
        icon: <CheckCircle className="h-4 w-4 text-emerald-400" />,
        duration: 2000,
      });
      
      if (onAddToWatchlist) {
        onAddToWatchlist(instrument);
      }
      
      // Clear search after successful addition
      setQuery("");
      setResults([]);
      setIsOpen(false);
      inputRef.current?.blur();
      
    } catch (err) {
      console.error("Failed to add to watchlist:", err);
      
      if (err.response?.status === 409) {
        toast.error(`${instrument.symbol} is already in your watchlist`);
      } else {
        toast.error("Failed to add to watchlist. Please try again.");
      }
    } finally {
      setAddingInstruments(prev => {
        const newSet = new Set(prev);
        newSet.delete(instrument.id);
        return newSet;
      });
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
      inputRef.current?.blur();
    }
  };

  const handleInputChange = (e) => {
    setQuery(e.target.value);
    if (e.target.value.length < 2) {
      setIsOpen(false);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <Input
          ref={inputRef}
          type="text"
          placeholder="Search stocks... (e.g., RELIANCE, TCS)"
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          className="pl-10 bg-gray-800/50 border-gray-700/50 focus:border-gray-600 focus:ring-1 focus:ring-gray-600 text-slate-200 placeholder-slate-400"
        />
        {isLoading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="animate-spin h-4 w-4 border-2 border-slate-400 border-t-transparent rounded-full" />
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="absolute z-10 w-full mt-1 p-3 bg-red-900/50 border border-red-700/50 rounded-md text-red-200 text-sm flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {/* Search Results Dropdown */}
      {isOpen && !error && (
        <div className="absolute z-10 w-full mt-1 bg-gray-900/95 backdrop-blur-sm border border-gray-700/50 rounded-md shadow-xl max-h-80 overflow-y-auto">
          {results.length > 0 ? (
            <div className="py-1">
              {results.map((instrument) => (
                <SearchResultItem
                  key={instrument.id}
                  instrument={instrument}
                  onSelect={handleSelect}
                  isAdding={addingInstruments.has(instrument.id)}
                />
              ))}
            </div>
          ) : (
            !isLoading && (
              <div className="px-4 py-6 text-center text-slate-400">
                <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No instruments found for "{query}"</p>
                <p className="text-xs mt-1">Try searching with symbol or company name</p>
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}
