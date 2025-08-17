// src/components/trading/OrderModal.jsx
// This component appears to be legacy and is not used in PaperTradingTerminal.jsx.
// It is recommended to remove this file and use OrderForm.jsx instead.
import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import api from "@/services/api";

export default function OrderModal({
  open = false,
  onClose = () => {},
  side = "BUY",
  preset = {},
  onPlaced = () => {},
}) {
  const [qty, setQty] = useState(preset.qty || 1);
  const [orderType, setOrderType] = useState(preset.order_type || "MARKET");
  const [price, setPrice] = useState(preset.price || "");
  const [trigger, setTrigger] = useState(preset.trigger_price || "");
  const [isBracket, setIsBracket] = useState(false);
  const [tpPrice, setTpPrice] = useState("");
  const [slIsSlm, setSlIsSlm] = useState(true);

  useEffect(() => {
    setQty(preset.qty || 1);
    setPrice(preset.price || "");
    setTrigger(preset.trigger_price || "");
  }, [preset]);

  async function handlePlace() {
    try {
      if (isBracket) {
        const payload = {
          symbol: preset.symbol,
          side,
          qty: Number(qty),
          entry_type: orderType === "LIMIT" ? "LIMIT" : "MARKET",
          entry_price: orderType === "LIMIT" ? Number(price) : undefined,
          tp_price: Number(tpPrice),
          sl_price: Number(trigger),
          sl_is_slm: slIsSlm,
        };
        const res = await api.post("/paper/bracket/", payload);
        onPlaced(res.data || res);
      } else {
        const payload = {
          symbol: preset.symbol,
          side,
          qty: Number(qty),
          order_type: orderType,
          price: orderType === "LIMIT" ? Number(price) : null,
          trigger_price:
            orderType === "SL" || orderType === "SL-M" ? Number(trigger) : null,
          is_slm: orderType === "SL-M",
        };
        const res = await api.post("/paper/orders/", payload);
        onPlaced(res.data || res);
      }
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
          <DialogTitle>
            {side} {preset.symbol}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-2">
          <div>
            <label className="text-sm text-muted-foreground">Qty</label>
            <Input
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              type="number"
            />
          </div>

          <div>
            <label className="text-sm text-muted-foreground">Order Type</label>
            <select
              className="w-full rounded-md bg-muted p-2"
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
              <label>Price</label>
              <Input value={price} onChange={(e) => setPrice(e.target.value)} />
            </div>
          )}
          {(orderType === "SL" || orderType === "SL-M") && (
            <div>
              <label>Trigger</label>
              <Input
                value={trigger}
                onChange={(e) => setTrigger(e.target.value)}
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
              Place bracket (TP+SL)
            </label>
          </div>

          {isBracket && (
            <>
              <div>
                <label>TP price</label>
                <Input
                  value={tpPrice}
                  onChange={(e) => setTpPrice(e.target.value)}
                />
              </div>
              <div>
                <label>SL as SL-M?</label>
                <input
                  type="checkbox"
                  checked={slIsSlm}
                  onChange={(e) => setSlIsSlm(e.target.checked)}
                />
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <div className="flex gap-2">
            <button className="btn" onClick={handlePlace}>
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
