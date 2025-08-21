import React, { useState, useEffect } from "react";
import { Search, PlusCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import api from "@/services/api";

// Mock data for testing when API is not available
const mockInstruments = [
  { id: 1, symbol: "RELIANCE", company_name: "Reliance Industries Ltd." },
  { id: 2, symbol: "TCS", company_name: "Tata Consultancy Services Ltd." },
  { id: 3, symbol: "INFY", company_name: "Infosys Ltd." },
  { id: 4, symbol: "HDFCBANK", company_name: "HDFC Bank Ltd." },
  { id: 5, symbol: "ICICIBANK", company_name: "ICICI Bank Ltd." },
  { id: 6, symbol: "HINDUNILVR", company_name: "Hindustan Unilever Ltd." },
  { id: 7, symbol: "ITC", company_name: "ITC Ltd." },
  { id: 8, symbol: "SBIN", company_name: "State Bank of India" },
  { id: 9, symbol: "BHARTIARTL", company_name: "Bharti Airtel Ltd." },
  { id: 10, symbol: "MARUTI", company_name: "Maruti Suzuki India Ltd." },
];

export default function InstrumentSearch({ onAddToWatchlist }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      setIsOpen(false);
      setLoading(false);
      return;
    }

    setLoading(true);
    const delayDebounce = setTimeout(() => {
      api
        .get(`/trading/instruments/search/?query=${query}`)
        .then((res) => {
          setResults(res.data);
          setIsOpen(true);
          setLoading(false);
        })
        .catch((err) => {
          console.warn("API search failed, using mock data:", err);
          // Fallback to mock data if API fails
          const filteredMockData = mockInstruments.filter(
            (instrument) =>
              instrument.symbol.toLowerCase().includes(query.toLowerCase()) ||
              instrument.company_name
                .toLowerCase()
                .includes(query.toLowerCase())
          );
          setResults(filteredMockData);
          setIsOpen(true);
          setLoading(false);
        });
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [query]);

  const handleSelect = (instrument) => {
    onAddToWatchlist(instrument.id);
    setQuery("");
    setResults([]);
    setIsOpen(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Escape") {
      setIsOpen(false);
      setQuery("");
      setResults([]);
    }
  };

  const handleInputFocus = () => {
    if (results.length > 0) {
      setIsOpen(true);
    }
  };

  const handleInputBlur = () => {
    // Delay closing to allow click events on results
    setTimeout(() => setIsOpen(false), 200);
  };

  return (
    <div className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Search for stocks (e.g., RELIANCE)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={handleInputFocus}
          onBlur={handleInputBlur}
          onKeyDown={handleKeyDown}
          className="pl-10 bg-[#21262d] border-gray-700 text-white placeholder-gray-500 focus:border-gray-500 focus:ring-1 focus:ring-gray-500"
        />
        {loading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="animate-spin h-4 w-4 border-2 border-gray-400 border-t-transparent rounded-full"></div>
          </div>
        )}
      </div>
      {isOpen && (
        <div className="absolute z-10 w-full mt-1 bg-[#21262d] border border-gray-700 rounded-md shadow-lg max-h-60 overflow-y-auto">
          {loading ? (
            <div className="px-3 py-4 text-center text-gray-400">
              <div className="animate-spin h-4 w-4 border-2 border-gray-400 border-t-transparent rounded-full mx-auto mb-2"></div>
              Searching...
            </div>
          ) : results.length > 0 ? (
            <ul className="py-1">
              {results.map((instrument) => (
                <li
                  key={instrument.id}
                  className="px-3 py-2 hover:bg-gray-700/50 cursor-pointer flex justify-between items-center transition-colors"
                  onClick={() => handleSelect(instrument)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-white truncate">
                      {instrument.symbol}
                    </div>
                    <div className="text-xs text-gray-400 truncate">
                      {instrument.company_name}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="ml-2 text-gray-400 hover:text-white"
                  >
                    <PlusCircle className="h-4 w-4" />
                  </Button>
                </li>
              ))}
            </ul>
          ) : query.length >= 2 ? (
            <div className="px-3 py-4 text-center text-gray-400">
              No instruments found for "{query}"
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
