// src/components/trading/OrderForm.jsx
import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { useTrading } from "@/contexts/TradingContext";

export default function OrderForm({
  open = false,
  onClose = () => {},
  symbol = "RELIANCE",
}) {
  const trading = useTrading();
  const [side, setSide] = useState("BUY");
  const [qty, setQty] = useState(1);
  const [orderType, setOrderType] = useState("MARKET"); // MARKET / LIMIT / SL / SL-M
  const [price, setPrice] = useState("");
  const [triggerPrice, setTriggerPrice] = useState("");
  const [isBracket, setIsBracket] = useState(false);
  const [tpPrice, setTpPrice] = useState("");
  const [slIsSlm, setSlIsSlm] = useState(true);
  const [shortSell, setShortSell] = useState(false);

  useEffect(() => {
    if (!open) {
      // reset
      setSide("BUY");
      setQty(1);
      setOrderType("MARKET");
      setPrice("");
      setTriggerPrice("");
      setIsBracket(false);
      setTpPrice("");
      setSlIsSlm(true);
      setShortSell(false);
    }
  }, [open]);

  async function place() {
    try {
      const base = {
        symbol,
        side: shortSell ? "SELL" : side,
        qty: Number(qty),
        order_type: orderType,
        price: orderType === "LIMIT" ? Number(price) : null,
        trigger_price:
          orderType === "SL" || orderType === "SL-M"
            ? Number(triggerPrice)
            : null,
        is_slm: orderType === "SL-M",
      };

      if (isBracket) {
        const payload = {
          symbol,
          side,
          qty: Number(qty),
          entry_type: orderType === "LIMIT" ? "LIMIT" : "MARKET",
          entry_price: orderType === "LIMIT" ? Number(price) : undefined,
          tp_price: Number(tpPrice),
          sl_price: Number(triggerPrice),
          sl_is_slm: slIsSlm,
        };
        const res = await trading.placeBracket(payload);
        // optional: toast
      } else {
        const res = await trading.placeOrder(base);
      }
      // refresh local lists
      trading.fetchAll && trading.fetchAll();
      onClose();
    } catch (err) {
      alert("Order error: " + (err?.response?.data?.detail || err.message));
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) onClose();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{symbol} — Place Order</DialogTitle>
        </DialogHeader>

        <div className="p-4 space-y-3">
          <div className="flex gap-2">
            <select
              className="rounded p-2 bg-slate-800"
              value={side}
              onChange={(e) => setSide(e.target.value)}
            >
              <option value="BUY">BUY</option>
              <option value="SELL">SELL</option>
            </select>
            <input
              className="w-full rounded p-2 bg-slate-800"
              type="number"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={shortSell}
                onChange={(e) => setShortSell(e.target.checked)}
              />{" "}
              Allow short
            </label>
          </div>

          <div>
            <select
              className="w-full rounded p-2 bg-slate-800"
              value={orderType}
              onChange={(e) => setOrderType(e.target.value)}
            >
              <option value="MARKET">MARKET</option>
              <option value="LIMIT">LIMIT</option>
              <option value="SL">STOP-LIMIT</option>
              <option value="SL-M">STOP-MARKET</option>
            </select>
          </div>

          {orderType === "LIMIT" && (
            <div>
              <input
                className="w-full rounded p-2 bg-slate-800"
                placeholder="Price"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
              />
            </div>
          )}
          {(orderType === "SL" || orderType === "SL-M") && (
            <div>
              <input
                className="w-full rounded p-2 bg-slate-800"
                placeholder="Trigger price"
                value={triggerPrice}
                onChange={(e) => setTriggerPrice(e.target.value)}
              />
            </div>
          )}

          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={isBracket}
                onChange={(e) => setIsBracket(e.target.checked)}
              />{" "}
              Bracket (TP + SL)
            </label>
          </div>

          {isBracket && (
            <div className="space-y-2">
              <input
                className="w-full rounded p-2 bg-slate-800"
                placeholder="TP price"
                value={tpPrice}
                onChange={(e) => setTpPrice(e.target.value)}
              />
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={slIsSlm}
                  onChange={(e) => setSlIsSlm(e.target.checked)}
                />{" "}
                SL as SL-M (market on trigger)
              </label>
            </div>
          )}
        </div>

        <DialogFooter>
          <div className="flex gap-2">
            <button className="btn" onClick={place}>
              Place
            </button>
            <button className="btn btn-ghost" onClick={onClose}>
              Cancel
            </button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
