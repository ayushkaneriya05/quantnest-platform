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
  side = "BUY",
}) {
  const trading = useTrading();
  const [qty, setQty] = useState(1);
  const [orderType, setOrderType] = useState("MARKET"); // MARKET / LIMIT / SL / SL-M
  const [productType, setProductType] = useState("NRML"); // NRML / MIS / CNC
  const [price, setPrice] = useState("");
  const [triggerPrice, setTriggerPrice] = useState("");
  const [orderTag, setOrderTag] = useState("ENTRY"); // ENTRY / BRACKET / COVER

  // Bracket Order State
  const [tpPrice, setTpPrice] = useState("");
  const [slPrice, setSlPrice] = useState("");
  const [slIsSlm, setSlIsSlm] = useState(true);

  useEffect(() => {
    if (!open) {
      // reset form on close
      setQty(1);
      setOrderType("MARKET");
      setProductType("NRML");
      setPrice("");
      setTriggerPrice("");
      setOrderTag("ENTRY");
      setTpPrice("");
      setSlPrice("");
      setSlIsSlm(true);
    }
  }, [open]);

  async function place() {
    try {
      let res;
      if (orderTag === "BRACKET") {
        const payload = {
          symbol,
          side,
          qty: Number(qty),
          entry_type: orderType,
          entry_price: orderType === "LIMIT" ? Number(price) : undefined,
          tp_price: Number(tpPrice),
          sl_price: Number(slPrice),
          sl_is_slm: slIsSlm,
        };
        res = await trading.placeBracket(payload);
      } else if (orderTag === "COVER") {
        const payload = {
          symbol,
          side,
          qty: Number(qty),
          entry_type: orderType,
          entry_price: orderType === "LIMIT" ? Number(price) : undefined,
          sl_price: Number(slPrice),
          sl_is_slm: true,
        };
        res = await trading.placeCover(payload);
      } else {
        const payload = {
          symbol,
          side,
          qty: Number(qty),
          order_type: orderType,
          product_type: productType,
          price: orderType === "LIMIT" ? Number(price) : null,
          trigger_price:
            orderType === "SL" || orderType === "SL-M"
              ? Number(triggerPrice)
              : null,
          is_slm: orderType === "SL-M",
        };
        res = await trading.placeOrder(payload);
      }

      trading.fetchAll();
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
            {side} {symbol} — Place Order
          </DialogTitle>
        </DialogHeader>

        <div className="p-4 space-y-3">
          {/* Order Type Tabs */}
          <div className="flex gap-2">
            {["ENTRY", "BRACKET", "COVER"].map((tag) => (
              <button
                key={tag}
                onClick={() => setOrderTag(tag)}
                className={`btn ${
                  orderTag === tag ? "btn-primary" : "btn-ghost"
                }`}
              >
                {tag}
              </button>
            ))}
          </div>

          <div className="flex gap-2">
            <input
              className="w-full rounded p-2 bg-slate-800"
              type="number"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              placeholder="Quantity"
            />
            <select
              className="rounded p-2 bg-slate-800"
              value={productType}
              onChange={(e) => setProductType(e.target.value)}
            >
              <option value="NRML">NRML</option>
              <option value="MIS">MIS</option>
              <option value="CNC">CNC</option>
            </select>
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

          {/* Bracket and Cover Order Fields */}
          {(orderTag === "BRACKET" || orderTag === "COVER") && (
            <div className="space-y-2 border-t pt-3 mt-3">
              <h4 className="font-semibold">{orderTag} Order Details</h4>
              {orderTag === "BRACKET" && (
                <input
                  className="w-full rounded p-2 bg-slate-800"
                  placeholder="Take Profit price"
                  value={tpPrice}
                  onChange={(e) => setTpPrice(e.target.value)}
                />
              )}
              <input
                className="w-full rounded p-2 bg-slate-800"
                placeholder="Stop Loss price"
                value={slPrice}
                onChange={(e) => setSlPrice(e.target.value)}
              />
              {orderTag === "BRACKET" && (
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={slIsSlm}
                    onChange={(e) => setSlIsSlm(e.target.checked)}
                  />
                  SL as SL-M (market on trigger)
                </label>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <div className="flex gap-2">
            <button className="btn btn-primary" onClick={place}>
              Place {side} Order
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
