import React, { useEffect, useMemo } from "react";
import { ArrowUpRight, ArrowDownRight, Trash2, Search, X, Loader2, RefreshCw, Star } from "lucide-react";
import { GlobalLoader } from "@/shared/components/ui/global-loader";
import { useNotifications } from "@/shared/hooks/useNotifications";

import { Button } from "@/shared/components/ui/button";
import { useWebSocket } from "@/shared/hooks/useWebSocket";
import { cn } from "@/shared/lib/utils";

import InstrumentSearch from "./InstrumentSearch";

const formatPrice = (value) =>
  value == null
    ? "--"
    : new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(Number(value));

function Watchlist({
  items = [],
  loading = false,
  activeSymbol,
  onSymbolSelect,
  onAddToWatchlist,
  onRemoveFromWatchlist,
  onRefresh,
  className,
}) {
  const { subscribe, tickData, isConnected, getLatestPrice, getTickData } =
    useWebSocket();
  const { notify } = useNotifications();

  useEffect(() => {
    if (!isConnected || !items.length) return undefined;
    const unsubscribers = items.map((item) =>
      subscribe(item.sym_ticker || item.symbol, () => {}),
    );
    return () => unsubscribers.forEach((unsubscribe) => unsubscribe());
  }, [isConnected, items, subscribe]);

  useEffect(() => {
    items.forEach((item) => {
      const key = item.sym_ticker || item.symbol;
      getLatestPrice(key);
    });
  }, [getLatestPrice, items]);

  const existingWatchlistSymbols = useMemo(
    () =>
      items.flatMap((item) => [item.symbol, item.sym_ticker].filter(Boolean)),
    [items],
  );

  return (
    <section
      className={cn(
        "flex h-full min-h-0 flex-col overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/80 backdrop-blur",
        className,
      )}
    >
      <div className="shrink-0 flex items-center justify-between border-b border-slate-800 px-4 py-4">
        <div className="flex items-center gap-2">
          <Star className="h-5 w-5 text-amber-400" />
          <div>
            <h2 className="text-sm font-semibold text-white">Watchlist</h2>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => {
            if (onRefresh) onRefresh();
            items.forEach((item) => {
              getLatestPrice(item.sym_ticker || item.symbol, { force: true });
            });
            notify.success("Watchlist refreshed");
          }}
          className="text-slate-400 hover:bg-slate-800 hover:text-white"
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      <div className="shrink-0 border-b border-slate-800 px-4 py-4">
        <InstrumentSearch
          onAddToWatchlist={onAddToWatchlist}
          existingWatchlistSymbols={existingWatchlistSymbols}
        />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-2 py-3 custom-scrollbar">
        {loading ? (
          <GlobalLoader fullHeight={false} />
        ) : items.length ? (
          items.map((item) => {
            const effectiveTick = getTickData(item.sym_ticker || item.symbol);
            const price = effectiveTick?.price ?? null;
            const change = effectiveTick?.change ?? 0;
            const changePercent = effectiveTick?.change_percent ?? 0;

            return (
              <div
                key={item.id}
                onClick={() => onSymbolSelect(item.sym_ticker || item.symbol)}
                className={cn(
                  "mb-2 flex cursor-pointer items-center justify-between rounded-2xl border px-3 py-3 text-left transition",
                  activeSymbol === item.symbol ||
                    activeSymbol === item.sym_ticker
                    ? "border-sky-500/60 bg-sky-500/10"
                    : "border-transparent bg-slate-900/80 hover:border-slate-700 hover:bg-slate-900",
                )}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="truncate text-sm font-semibold text-white">
                      {item.symbol}
                    </p>
                  </div>
                  <p className="truncate text-[11px] text-slate-500 mt-0.5">
                    {item.company_name}
                  </p>
                </div>

                <div className="ml-3 text-right">
                  <p className="text-sm font-bold text-slate-100 tabular-nums">
                    {formatPrice(price)}
                  </p>
                  <p
                    className={cn(
                      "text-[10px] font-medium mt-0.5 tabular-nums",
                      price == null
                        ? "text-slate-500"
                        : Number(change) >= 0
                          ? "text-emerald-400"
                          : "text-rose-400",
                    )}
                  >
                    {price == null
                      ? "---"
                      : `${Number(change) >= 0 ? "+" : ""}${Number(change).toFixed(2)} (${Number(
                          changePercent,
                        ).toFixed(2)}%)`}
                  </p>
                </div>

                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={(event) => {
                    event.stopPropagation();
                    onRemoveFromWatchlist(item.id);
                  }}
                  className="ml-2 text-slate-500 hover:bg-rose-500/10 hover:text-rose-300"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            );
          })
        ) : (
          <div className="flex h-full flex-col items-center justify-center px-6 text-center">
            <Star className="mb-3 h-10 w-10 text-slate-700" />
            <p className="text-sm font-medium text-slate-300">No symbols yet</p>
            <p className="mt-1 text-xs text-slate-500">
              Add instruments to start streaming quotes into the terminal.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

export default React.memo(Watchlist);
