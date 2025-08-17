// src/pages/dashboard/trading/PaperTrading.jsx
import React, { useState } from "react";
import { TradingProvider, useTrading } from "@/contexts/TradingContext";
import OrdersList from "@/components/dashboard/trading/OrdersList";
import PositionsList from "@/components/dashboard/trading/PositionsList";
import OrderForm from "@/components/dashboard/trading/OrderForm";
import AuditLogs from "@/components/dashboard/trading/AuditLogs";
import LiveChart from "@/components/dashboard/trading/LiveChart"; // keep your existing LiveChart (or the one added earlier)
import { Card, CardHeader, CardContent } from "@/components/ui/card";

function TerminalInner() {
  const [activeSymbol, setActiveSymbol] = useState("RELIANCE");
  const [showOrderModal, setShowOrderModal] = useState(false);
  const trading = useTrading();

  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-3 space-y-4">
        <Card>
          <CardHeader>
            <div className="font-semibold">Watch</div>
          </CardHeader>
          <CardContent>
            {/* simple quick-select list (replace with your Watchlist component if present) */}
            {["RELIANCE", "TCS", "INFY", "HDFCBANK", "TECHM"].map((s) => (
              <div key={s} className="flex items-center justify-between py-1">
                <button
                  className="font-medium"
                  onClick={() => setActiveSymbol(s)}
                >
                  {s}
                </button>
                <div className="flex gap-2">
                  <button
                    className="btn btn-xs"
                    onClick={() => {
                      setShowOrderModal(true);
                    }}
                  >
                    Buy
                  </button>
                  <button
                    className="btn btn-xs"
                    onClick={() => {
                      setShowOrderModal(true);
                    }}
                  >
                    Sell
                  </button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="font-semibold">Positions</div>
          </CardHeader>
          <CardContent>
            <PositionsList />
          </CardContent>
        </Card>
      </div>

      <div className="col-span-6 space-y-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="font-semibold">
                {activeSymbol}{" "}
                <span className="text-xs text-muted-foreground ml-2">
                  15m delayed
                </span>
              </div>
              <div>
                <button className="btn" onClick={() => setShowOrderModal(true)}>
                  Place Order
                </button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <LiveChart symbol={activeSymbol} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="font-semibold">Audit Logs</div>
          </CardHeader>
          <CardContent>
            <AuditLogs />
          </CardContent>
        </Card>
      </div>

      <div className="col-span-3 space-y-4">
        <Card>
          <CardHeader>
            <div className="font-semibold">Orders</div>
          </CardHeader>
          <CardContent>
            <OrdersList />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="font-semibold">Orderbook</div>
          </CardHeader>
          <CardContent>
            {/* lightweight orderbook snapshot */}
            <button
              className="btn btn-ghost"
              onClick={() => trading.fetchOrderbook(activeSymbol)}
            >
              Refresh
            </button>
            <pre className="text-xs mt-2">
              {JSON.stringify(trading.orderbook, null, 2)}
            </pre>
          </CardContent>
        </Card>
      </div>

      <OrderForm
        open={showOrderModal}
        symbol={activeSymbol}
        onClose={() => setShowOrderModal(false)}
      />
    </div>
  );
}

export default function PaperTradingPage() {
  return (
    <TradingProvider>
      <TerminalInner />
    </TradingProvider>
  );
}
