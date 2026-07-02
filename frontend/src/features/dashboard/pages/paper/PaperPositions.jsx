import { useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Layers, RefreshCw, TrendingDown, TrendingUp, X } from "lucide-react";
import { paperApi } from "@/shared/services/paperApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";

export default function PaperPositions({ selectedAccountId }) {
  const { notify } = useNotifications();
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchPositions = async () => {
    try {
      const positionsRes = await paperApi.getPositions();
      setPositions(positionsRes.data || []);
    } catch (error) {
      notify.error("Failed to load positions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleClose = async (positionId) => {
    notify.error("Position closing is managed by trading strategies only");
  };

  const filteredPositions = useMemo(
    () =>
      positions.filter(
        (position) => String(position.account) === String(selectedAccountId),
      ),
    [positions, selectedAccountId],
  );

  const formatCurrency = (value) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(value || 0);

  const totalValue = filteredPositions.reduce(
    (sum, position) => sum + parseFloat(position.current_value || 0),
    0,
  );
  const totalUnrealizedPnl = filteredPositions.reduce(
    (sum, position) => sum + parseFloat(position.unrealized_pnl || 0),
    0,
  );

  if (loading) return null;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="grid grid-cols-3 gap-4">
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-white">
              {filteredPositions.length}
            </p>
            <p className="text-xs text-gray-400">Open Positions</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p className="text-2xl font-bold text-white">
              {formatCurrency(totalValue)}
            </p>
            <p className="text-xs text-gray-400">Total Value</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-4 text-center">
            <p
              className={`text-2xl font-bold ${totalUnrealizedPnl >= 0 ? "text-green-400" : "text-red-400"}`}
            >
              {totalUnrealizedPnl >= 0 ? "+" : ""}
              {formatCurrency(totalUnrealizedPnl)}
            </p>
            <p className="text-xs text-gray-400">Unrealized P&L</p>
          </CardContent>
        </Card>
      </div>

      {filteredPositions.length === 0 ? (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardContent className="py-12 text-center">
            <Layers className="h-10 w-10 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-300">
              No open positions
            </h3>
            <p className="text-gray-500 text-sm">
              Place orders in this account to open positions.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredPositions.map((position) => (
            <Card key={position.id} className="bg-gray-900/50 border-gray-800 hover:border-gray-700 transition-colors">
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div
                      className={`p-3 rounded-lg ${position.side === "BUY" ? "bg-emerald-500/10" : "bg-rose-500/10"}`}
                    >
                      {position.side === "BUY" ? (
                        <TrendingUp className="h-6 w-6 text-emerald-400" />
                      ) : (
                        <TrendingDown className="h-6 w-6 text-rose-400" />
                      )}
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-white">
                        {position.instrument_symbol}
                      </h3>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge
                          className={
                            position.side === "BUY"
                              ? "bg-emerald-600"
                              : "bg-rose-600"
                          }
                        >
                          {position.side}
                        </Badge>
                        {position.strategy_name && (
                          <Badge variant="outline" className="border-gray-700 text-gray-400">
                            {position.strategy_name}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-8">
                    <div className="text-right">
                      <p className="text-xs text-gray-500">Quantity</p>
                      <p className="text-white font-medium">
                        {position.quantity}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-500">Avg Price</p>
                      <p className="text-white font-medium text-sm">
                        ₹{parseFloat(position.avg_price).toFixed(2)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-500">Current</p>
                      <p className="text-white font-medium text-sm">
                        ₹{parseFloat(position.current_price).toFixed(2)}
                      </p>
                    </div>
                    <div className="text-right min-w-[100px]">
                      <p className="text-xs text-gray-500">P&L</p>
                      <p
                        className={`font-bold ${parseFloat(position.unrealized_pnl) >= 0 ? "text-emerald-400" : "text-rose-400"}`}
                      >
                        {formatCurrency(position.unrealized_pnl)}
                      </p>
                      <p className="text-[10px] text-gray-500">
                        ({parseFloat(position.unrealized_pnl_pct).toFixed(2)}%)
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleClose(position.id)}
                      className="border-gray-700 text-gray-500 cursor-not-allowed text-xs h-8"
                      disabled
                    >
                      Managed
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
