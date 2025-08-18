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

    let cancelled = false;
    (async () => {
      try {
        const resp = await api.get(
          `/api/v1/market/symbols/search/?q=${encodeURIComponent(query)}`
        );
        if (!cancelled) {
          setSuggestions(resp.data || []);
        }
      } catch (e) {
        console.error("Failed to fetch symbol suggestions:", e);
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
            placeholder="Search to add (e.g., RELIANCE)"
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
                      setSuggestions([]);
                    }}
                  >
                    {s}
                  </button>
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
