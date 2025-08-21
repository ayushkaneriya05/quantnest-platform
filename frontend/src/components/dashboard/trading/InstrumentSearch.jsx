import { useState, useEffect, useCallback, useRef } from "react";
import { Search, PlusCircle, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import api from "@/services/api";

export default function InstrumentSearch({
  onAddToWatchlist,
  existingWatchlistSymbols,
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  const searchRef = useRef(null); // Ref to detect outside clicks

  // ** THE FIX: Detect clicks outside the component to close suggestions **
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleSearch = useCallback(
    async (searchQuery) => {
      if (searchQuery.length < 2) {
        setResults([]);
        setIsOpen(false);
        return;
      }
      setIsLoading(true);
      try {
        const response = await api.get(
          `/trading/instruments/search/?query=${searchQuery}`
        );
        setResults(response.data);
        setIsOpen(true);
      } catch (err) {
        console.error("Search failed:", err);
        toast({
          variant: "destructive",
          title: "Search Failed",
          description: "Could not fetch instruments.",
        });
      } finally {
        setIsLoading(false);
      }
    },
    [toast]
  );

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      handleSearch(query);
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [query, handleSearch]);

  const handleSelect = (instrument) => {
    onAddToWatchlist(instrument.id);
    setQuery("");
    setResults([]);
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={searchRef}>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <Input
          type="text"
          placeholder="Search to add stocks..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => query.length > 1 && setIsOpen(true)}
          className="pl-10 bg-gray-900/50 border-gray-800/50 text-white"
        />
        {isLoading && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-slate-400" />
        )}
      </div>
      {isOpen && results.length > 0 && (
        <div className="absolute z-20 w-full mt-1 bg-gray-950 border border-gray-800 rounded-md shadow-lg max-h-60 overflow-y-auto">
          <ul className="py-1">
            {results.map((instrument) => {
              const isInWatchlist = existingWatchlistSymbols.includes(
                instrument.symbol
              );
              return (
                <li
                  key={instrument.id}
                  className="px-3 py-2 hover:bg-gray-800/50 cursor-pointer flex justify-between items-center"
                  // Now that we handle outside clicks, a simple onClick is reliable
                  onClick={() => !isInWatchlist && handleSelect(instrument)}
                >
                  <div>
                    <div className="font-medium text-slate-200">
                      {instrument.symbol}
                    </div>
                    <div className="text-xs text-slate-400">
                      {instrument.company_name}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={isInWatchlist}
                    className={
                      isInWatchlist
                        ? "text-slate-500 cursor-not-allowed"
                        : "text-slate-300 hover:text-white"
                    }
                  >
                    <PlusCircle className="h-4 w-4 mr-2" />{" "}
                    {isInWatchlist ? "Added" : "Add"}
                  </Button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
