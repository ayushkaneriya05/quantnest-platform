import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import OrderTicket from "./OrderTicket";
import { useWebSocket } from "@/contexts/websocket-context"; // Import the WebSocket hook

export default function OrderModal({
  isOpen,
  onClose,
  symbol,
  transactionType,
  onOrderPlaced,
}) {
  // State to hold the live market price for the header
  const [currentPrice, setCurrentPrice] = useState(null);
  const { getTickData, subscribe } = useWebSocket(); // Get live data functions

  // Effect to subscribe to live price updates for the selected symbol
  useEffect(() => {
    if (!isOpen || !symbol) {
      // Reset price if modal is closed or there's no symbol
      setCurrentPrice(null);
      return;
    }

    // Get the initial price from the context's cache
    const initialTick = getTickData(symbol);
    if (initialTick) {
      setCurrentPrice(initialTick.price);
    }

    // Subscribe to the symbol for real-time updates
    const unsubscribe = subscribe(symbol, (tick) => {
      setCurrentPrice(tick.price);
    });

    // Cleanup subscription on component unmount or when dependencies change
    return () => unsubscribe();
  }, [isOpen, symbol, getTickData, subscribe]);

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-[#0d1117] border border-gray-700 text-white max-w-md p-0 gap-0 rounded-lg overflow-hidden max-h-[90vh] flex flex-col">
        <DialogHeader className="flex-shrink-0 px-6 py-4 border-b border-gray-700 bg-[#161b22]">
          <DialogTitle className="text-xl font-bold text-white flex items-center gap-3">
            <div
              className={`w-3 h-3 rounded-full ${
                transactionType === "BUY" ? "bg-emerald-400" : "bg-red-400"
              }`}
            />
            {transactionType} {symbol}
          </DialogTitle>
          {/* Display live price in the header */}
          <div className="text-sm text-gray-400 mt-1">
            Current Price:{" "}
            {currentPrice ? `₹${currentPrice.toFixed(2)}` : "Fetching..."} •
            Market: NSE
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto scrollbar-theme p-6">
          <OrderTicket
            symbol={symbol}
            transactionType={transactionType}
            onOrderPlaced={onOrderPlaced}
            onClose={onClose}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
