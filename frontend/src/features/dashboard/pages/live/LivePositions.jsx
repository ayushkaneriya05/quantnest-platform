import { useEffect, useState, useCallback } from "react";
import { Layers3, RefreshCw, TrendingDown, TrendingUp } from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { useLiveTradingWebSocket } from "@/shared/hooks/useLiveTradingWebSocket";
import { liveTradingApi } from "@/shared/services/liveTradingApi";

import { formatNumber } from "@/shared/utils/formatters";

export default function LivePositions() {
  const { notify } = useNotifications();
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadPositions = async () => {
    try {
      setLoading(true);
      const response = await liveTradingApi.getPositions();
      setPositions(
        Array.isArray(response.data?.results)
          ? response.data.results
          : response.data || [],
      );
    } catch (error) {
      notify.error(
        error?.response?.data?.detail || "Failed to load live positions",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleLiveUpdate = useCallback((payload) => {
    if (
      payload?.event_type === "POSITION_UPDATE" &&
      payload?.data?.position_id
    ) {
      if (payload.data.quantity === 0) {
        setPositions((prev) =>
          prev.filter((p) => p.id !== payload.data.position_id),
        );
      } else {
        // Simple update approach, could also trigger a full refresh depending on needed fields
        liveTradingApi
          .getPositions()
          .then((res) => setPositions(res.data?.results || res.data || []))
          .catch(console.error);
      }
    } else if (payload?.event_type === "ORDER_UPDATE") {
      liveTradingApi
        .getPositions()
        .then((res) => setPositions(res.data?.results || res.data || []))
        .catch(console.error);
    }
  }, []);

  useLiveTradingWebSocket(handleLiveUpdate);

  useEffect(() => {
    loadPositions();
  }, []);

  useSetPageActions(
    <Button
      variant="outline"
      onClick={loadPositions}
      className="border-gray-700 text-gray-100"
    >
      <RefreshCw className="mr-2 h-4 w-4" />
      Refresh
    </Button>,
  );

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      {loading ? (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-400">
            Loading live positions...
          </CardContent>
        </Card>
      ) : positions.length === 0 ? (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-400">
            No open live positions right now.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {positions.map((row) => {
            const pnlUp = Number(row.unrealized_pnl || 0) >= 0;
            return (
              <Card key={row.id} className="border-gray-800 bg-gray-900/60">
                <CardHeader className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <CardTitle className="text-lg text-white">
                        {row.instrument_symbol}
                      </CardTitle>
                      <p className="mt-1 text-sm text-gray-400">
                        {row.strategy_name || "Manual"}
                      </p>
                    </div>
                    <Badge
                      className={
                        row.side === "BUY"
                          ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                          : "bg-red-500/10 text-red-300 border-red-500/20"
                      }
                    >
                      {row.side}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <Layers3 className="h-4 w-4 text-cyan-300" />
                        Size
                      </div>
                      <p className="mt-2 text-white">{row.quantity}</p>
                    </div>
                    <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        {pnlUp ? (
                          <TrendingUp className="h-4 w-4 text-emerald-300" />
                        ) : (
                          <TrendingDown className="h-4 w-4 text-red-300" />
                        )}
                        Mark-to-market
                      </div>
                      <p
                        className={`mt-2 ${pnlUp ? "text-emerald-300" : "text-red-300"}`}
                      >
                        Rs {formatNumber(row.unrealized_pnl)}
                      </p>
                    </div>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-xl bg-gray-950/60 p-3 text-sm">
                      <p className="text-gray-500">Avg Price</p>
                      <p className="mt-1 text-white">
                        {formatNumber(row.avg_price)}
                      </p>
                    </div>
                    <div className="rounded-xl bg-gray-950/60 p-3 text-sm">
                      <p className="text-gray-500">LTP</p>
                      <p className="mt-1 text-white">
                        {formatNumber(row.current_price)}
                      </p>
                    </div>
                    <div className="rounded-xl bg-gray-950/60 p-3 text-sm">
                      <p className="text-gray-500">Day P&L</p>
                      <p
                        className={`mt-1 ${Number(row.day_pnl || 0) >= 0 ? "text-emerald-300" : "text-red-300"}`}
                      >
                        Rs {formatNumber(row.day_pnl)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
