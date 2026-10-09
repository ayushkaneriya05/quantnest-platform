import { useState, useEffect, useRef } from "react";
import { cn } from "@/shared/lib/utils";
import { Search, PlusCircle, Loader2 } from "lucide-react";
import { Input } from "@/shared/components/ui/input";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { useInstrumentSearch } from "@/shared/hooks/useInstrumentSearch";
import { searchTerminalInstruments } from "@/shared/services/instrumentsApi";

export default function InstrumentSearch({
  onAddToWatchlist,
  existingWatchlistSymbols = [],
}) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const { results, loading: isLoading, error } = useInstrumentSearch(query, {}, isOpen, searchTerminalInstruments);
  const searchRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (instrument) => {
    onAddToWatchlist(instrument);
    setQuery("");
    setIsOpen(false);
  };

  return (
    <div className="relative group" ref={searchRef}>
      <div className="relative">
        <Search className={cn(
          "absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 transition-colors duration-300",
          isOpen ? "text-sky-700 dark:text-sky-400" : "text-muted-foreground"
        )} />
        <Input
          type="text"
          placeholder="Search for stocks (e.g. RELIANCE)..."
          value={query}
          onChange={(e) => { setQuery(e.target.value); setIsOpen(true); }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={(event) => { if (event.key === "Escape") setIsOpen(false); }}
          className="pl-11 h-12 bg-card/60 border-border/80 text-foreground rounded-2xl focus-visible:ring-sky-500/20 focus-visible:border-sky-500/40 transition-all duration-300 placeholder:text-muted-foreground"
        />
        {isLoading && (
          <div className="absolute right-4 top-1/2 -translate-y-1/2">
            <Loader2 className="h-4 w-4 animate-spin text-sky-700 dark:text-sky-400" />
          </div>
        )}
      </div>

      {isOpen && (
        <div className="absolute z-50 w-full mt-2 bg-background/95 border border-border/80 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] backdrop-blur-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
          <div className="px-4 py-2 bg-card/40 border-b border-border/50">
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">{query ? "Matching instruments" : "Latest 20 instruments"}</span>
          </div>
          <ul className="py-1 max-h-[300px] overflow-y-auto scrollbar-thin-theme">
            {results.map((instrument) => {
              const isInWatchlist = existingWatchlistSymbols.includes(instrument.sym_ticker);
              return (
                <li
                  key={instrument.id}
                  className="px-4 py-3 hover:bg-muted/50 cursor-pointer flex justify-between items-center transition-colors border-b border-border/30 last:border-0"
                  onClick={() => !isInWatchlist && handleSelect(instrument)}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-black text-foreground">{instrument.symbol}</span>
                      <Badge variant="outline" className="text-[8px] h-3.5 px-1 py-0 border-border bg-card text-muted-foreground">
                        {instrument.exchange}
                      </Badge>
                    </div>
                    <div className="text-[10px] text-muted-foreground font-medium truncate mt-0.5">
                      {instrument.company_name}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={isInWatchlist}
                    className={cn(
                      "h-8 rounded-xl font-bold text-xs transition-all",
                      isInWatchlist
                        ? "text-muted-foreground cursor-not-allowed bg-transparent"
                        : "text-sky-700 dark:text-sky-400 hover:bg-sky-500/10 hover:text-sky-800 dark:hover:text-sky-300"
                    )}
                  >
                    {isInWatchlist ? (
                      <span className="flex items-center gap-1">Added</span>
                    ) : (
                      <span className="flex items-center gap-1">
                        <PlusCircle className="h-3 w-3" /> Add
                      </span>
                    )}
                  </Button>
                </li>
              );
            })}
          </ul>
          {isLoading && <p role="status" className="px-4 py-3 text-sm text-muted-foreground">Loading instruments…</p>}
          {error && <p role="alert" className="px-4 py-3 text-sm text-rose-700 dark:text-rose-300">{error}</p>}
          {!isLoading && !error && !results.length && <p className="px-4 py-3 text-sm text-muted-foreground">No instruments found.</p>}
        </div>
      )}
    </div>
  );
}

