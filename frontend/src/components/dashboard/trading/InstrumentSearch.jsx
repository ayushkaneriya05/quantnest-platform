import React, { useState, useEffect } from "react";
import { Search, PlusCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import api from "@/services/api";

export default function InstrumentSearch({ onAddToWatchlist }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    const delayDebounce = setTimeout(() => {
      api
        .get(`/trading/instruments/search/?query=${query}`)
        .then((res) => {
          setResults(res.data);
          setIsOpen(true);
        })
        .catch((err) => console.error("Search failed:", err));
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [query]);

  const handleSelect = (instrument) => {
    onAddToWatchlist(instrument.id);
    setQuery("");
    setResults([]);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <Input
          type="text"
          placeholder="Search for stocks (e.g., RELIANCE)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-10 bg-gray-800/50 border-gray-700/50"
        />
      </div>
      {isOpen && results.length > 0 && (
        <div className="absolute z-10 w-full mt-1 bg-gray-900 border border-gray-700 rounded-md shadow-lg">
          <ul className="py-1">
            {results.map((instrument) => (
              <li
                key={instrument.id}
                className="px-3 py-2 hover:bg-gray-800 cursor-pointer flex justify-between items-center"
                onClick={() => handleSelect(instrument)}
              >
                <div>
                  <div className="font-medium text-slate-200">
                    {instrument.symbol}
                  </div>
                  <div className="text-xs text-slate-400">
                    {instrument.company_name}
                  </div>
                </div>
                <Button variant="ghost" size="sm">
                  <PlusCircle className="h-4 w-4 mr-2" /> Add
                </Button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
