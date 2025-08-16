// src/components/trading/PaperTradingTerminal.jsx
import React, { useEffect, useMemo, useState, useRef } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import Watchlist from "./Watchlist";
import LiveChart from "./LiveChart";
import OrdersTable from "./OrdersTable";
import PositionsPanel from "./PositionsPanel";
import Orderbook from "./Orderbook";
import OrderModal from "./OrderModal";
import api from "@/services/api";
import { useSelector } from "react-redux";
import { useToast } from "@/components/ui/notification";

const DEFAULT_SYMBOL = "RELIANCE";

export default function PaperTradingTerminal() {
  const [symbol, setSymbol] = useState(DEFAULT_SYMBOL);
  const [watchlist, setWatchlist] = useState([
    DEFAULT_SYMBOL,
    "TCS",
    "INFY",
    "HDFCBANK",
  ]);
  const [orderModal, setOrderModal] = useState({
    open: false,
    side: "BUY",
    preset: {},
  });
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef(null);
  const toast = useToast();
  const auth = useSelector((s) => s.auth); // reuse your store auth if present

  // Manage websocket to backend Channels consumer (marketdata)
  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${protocol}://${window.location.host}/ws/marketdata/`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
      // auto-subscribe to active WATCHLIST symbols so server knows which symbols are active
      for (const s of watchlist) {
        ws.send(JSON.stringify({ action: "subscribe", symbol: s }));
      }
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        // handle user messages (order_update/position_update) which backend will send to user group
        if (
          msg.type &&
          (msg.type === "order_update" ||
            msg.type === "position_update" ||
            msg.type === "account_update")
        ) {
          // broadcast local update requests via custom event so child components can react
          window.dispatchEvent(
            new CustomEvent("quantnest:user_message", { detail: msg })
          );
        }
        // delayed tick messages will be published to channel groups; they come as {type:'tick', data: {...}}
        if (msg.type === "tick" && msg.data) {
          window.dispatchEvent(
            new CustomEvent("quantnest:tick", { detail: msg.data })
          );
        }
      } catch (e) {
        /* ignore */
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
      // attempt reconnect (exponential backoff would be better in prod)
      setTimeout(() => {
        window.location.reload();
      }, 1200);
    };

    return () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        // unsubscribe all to be polite
        for (const s of watchlist)
          ws.send(JSON.stringify({ action: "unsubscribe", symbol: s }));
        ws.close();
      }
    };
  }, [watchlist]);

  // helper: open order modal
  function openOrder(side, preset = {}) {
    setOrderModal({ open: true, side, preset });
  }

  // simple toast to inform
  function notify(title, message) {
    toast({ title, description: message });
  }

  return (
    <div className="grid grid-cols-12 gap-4 p-4">
      <div className="col-span-3 space-y-4">
        <Watchlist
          symbols={watchlist}
          onAdd={(s) => setWatchlist((w) => (w.includes(s) ? w : [s, ...w]))}
          onRemove={(s) => setWatchlist((w) => w.filter((x) => x !== s))}
          onSelect={(s) => setSymbol(s)}
          onQuickBuy={(s) => openOrder("BUY", { symbol: s })}
          onQuickSell={(s) => openOrder("SELL", { symbol: s })}
        />
        <Orderbook symbol={symbol} ws={wsRef.current} />
      </div>

      <div className="col-span-6">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-lg font-semibold">
            {symbol}{" "}
            <span className="text-xs text-muted-foreground ml-2">
              15m delayed
            </span>
          </div>
          <div className="flex gap-2">
            <button
              className="btn"
              onClick={() => openOrder("BUY", { symbol })}
            >
              Buy
            </button>
            <button
              className="btn btn-outline"
              onClick={() => openOrder("SELL", { symbol })}
            >
              Sell
            </button>
          </div>
        </div>

        <LiveChart symbol={symbol} ws={wsRef.current} />
      </div>

      <div className="col-span-3 space-y-4">
        <div className="space-y-4">
          <OrdersTable />
          <PositionsPanel />
        </div>
      </div>

      <OrderModal
        open={orderModal.open}
        side={orderModal.side}
        preset={orderModal.preset}
        onClose={() => setOrderModal({ open: false, side: "BUY", preset: {} })}
        onPlaced={(order) => {
          notify("Order placed", `Order ${order.id} created`);
          // fire a refresh event for tables
          window.dispatchEvent(new CustomEvent("quantnest:refresh_orders"));
        }}
      />
    </div>
  );
}
