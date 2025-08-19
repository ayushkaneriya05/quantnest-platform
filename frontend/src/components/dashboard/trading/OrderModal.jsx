import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import OrderTicket from "./OrderTicket";
import React from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function OrderModal({
  isOpen,
  onClose,
  symbol,
  transactionType,
  onOrderPlaced,
}) {
  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-[#0d1117] border border-gray-700 text-white max-w-md p-0 gap-0 rounded-lg overflow-hidden max-h-[90vh] flex flex-col">
        <DialogHeader className="flex-shrink-0 px-6 py-4 border-b border-gray-700 bg-[#161b22]">
          <div className="flex items-center justify-between">
            <DialogTitle className="text-xl font-bold text-white flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${
                transactionType === "BUY" ? "bg-emerald-400" : "bg-red-400"
              }`} />
              {transactionType} {symbol}
            </DialogTitle>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="h-8 w-8 text-gray-400 hover:text-white hover:bg-gray-800"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="text-sm text-gray-400 mt-1">
            Current Price: ₹2,458.50 • Market: NSE
          </div>
        </DialogHeader>
        
        <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-track-gray-800 scrollbar-thumb-gray-600 p-6">
          <OrderTicket
            symbol={symbol}
            transactionType={transactionType}
            onOrderPlaced={onOrderPlaced}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
