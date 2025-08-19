import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import OrderTicket from "./OrderTicket";
import React from "react";
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
      <DialogContent className="bg-gray-950 border-gray-800 text-white">
        <DialogHeader>
          <DialogTitle
            className={`text-2xl font-bold ${
              transactionType === "BUY" ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {transactionType} {symbol}
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            Place your {transactionType.toLowerCase()} order for {symbol}. All
            orders are simulated.
          </DialogDescription>
        </DialogHeader>
        <OrderTicket
          symbol={symbol}
          transactionType={transactionType}
          onOrderPlaced={onOrderPlaced}
        />
      </DialogContent>
    </Dialog>
  );
}
