// src/components/trading/Watchlist.jsx
import React, { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import api from "@/services/api";

export default function Watchlist({
  symbols = [],
  onAdd,
  onRemove,
  onSelect,
  onQuickBuy,
  onQuickSell,
}) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    if (!query) {
      setSuggestions([]);
      return;
    }
    // try backend symbol search endpoint if exists
    let cancelled = false;
    (async () => {
      try {
        const resp = await api.get(
          `/symbols/search/?q=${encodeURIComponent(query)}`
        );
        if (!cancelled)
          setSuggestions(
            (resp?.data || []).slice(0, 12).map((s) => s.symbol || s)
          );
      } catch (e) {
        // fallback to nothing (project includes a small symbols.json in repo; you can expand)
        setSuggestions([]);
      }
    })();
    return () => (cancelled = true);
  }, [query]);

  return (
    <Card className="sticky top-4 max-h-[70vh] overflow-auto">
      <CardHeader>
        <CardTitle>Watchlist</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mb-2">
          <Input
            placeholder="Search symbol"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {suggestions.length > 0 && (
            <div className="mt-2 bg-muted rounded-md p-2 space-y-1">
              {suggestions.map((s) => (
                <div className="flex items-center justify-between" key={s}>
                  <button
                    className="text-sm font-medium"
                    onClick={() => {
                      onAdd(s);
                      setQuery("");
                    }}
                  >
                    {s}
                  </button>
                  <div className="flex gap-2">
                    <button
                      className="text-xs"
                      onClick={() => onQuickBuy && onQuickBuy(s)}
                    >
                      B
                    </button>
                    <button
                      className="text-xs"
                      onClick={() => onQuickSell && onQuickSell(s)}
                    >
                      S
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <ul className="space-y-2">
          {symbols.map((s) => (
            <li key={s} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  className="font-medium text-sm"
                  onClick={() => onSelect && onSelect(s)}
                >
                  {s}
                </button>
              </div>
              <div className="flex gap-2">
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => onQuickBuy && onQuickBuy(s)}
                >
                  Buy
                </button>
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => onQuickSell && onQuickSell(s)}
                >
                  Sell
                </button>
                <button
                  className="text-sm text-muted-foreground"
                  onClick={() => onRemove && onRemove(s)}
                >
                  ✕
                </button>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
