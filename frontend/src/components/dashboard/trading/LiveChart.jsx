// src/components/trading/LiveChart.jsx
import React, { useEffect, useRef, useState } from "react";
import { createChart, CrosshairMode } from "lightweight-charts";
import api from "@/services/api";
import { sma, ema, rsi as rsiCalc } from "technicalindicators";

export default function LiveChart({ symbol, ws }) {
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const [tf, setTf] = useState("1m");
  const indicatorsRef = useRef([]);
  const mounted = useRef(true);

  useEffect(() => {
    const el = chartRef.current;
    if (!el) return;
    const chart = createChart(el, {
      layout: { backgroundColor: "#071423", textColor: "#cbd5e1" },
      width: el.clientWidth,
      height: 480,
      crosshair: { mode: CrosshairMode.Normal },
    });
    chart.timeScale().fitContent();
    const candle = chart.addCandlestickSeries();
    seriesRef.current = candle;

    // bootstrap candles from backend OHLC endpoint (matches backend get_bootstrap_ohlc)
    (async () => {
      try {
        const res = await api.get(
          `/market/ohlc/?symbol=${encodeURIComponent(
            symbol
          )}&tf=${tf}&limit=500`
        );
        const arr = (res?.data || res || []).map((c) => ({
          time: Math.floor(new Date(c.ts).getTime() / 1000),
          open: c.o,
          high: c.h,
          low: c.l,
          close: c.c,
        }));
        candle.setData(arr);
      } catch (e) {
        // Older project might use different endpoint: try fallback /api/v1/ohlc
        try {
          const res2 = await api.get(
            `/api/v1/ohlc?symbol=${encodeURIComponent(
              symbol
            )}&tf=${tf}&limit=500`
          );
          const arr2 = (res2?.data || res2 || []).map((c) => ({
            time: Math.floor(new Date(c.ts).getTime() / 1000),
            open: c.o,
            high: c.h,
            low: c.l,
            close: c.c,
          }));
          candle.setData(arr2);
        } catch (err) {
          // ignore
        }
      }
    })();

    // resize handler
    const onResize = () => chart.applyOptions({ width: el.clientWidth });
    window.addEventListener("resize", onResize);
    return () => {
      mounted.current = false;
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, [symbol, tf]);

  // handle incoming tick events from window-level dispatcher (PaperTradingTerminal emits them)
  useEffect(() => {
    function onTick(e) {
      const tick = e.detail;
      if (!tick || tick.symbol !== symbol) return;
      // merge tick into last candle (simple approach)
      const sec = Math.floor(new Date(tick.ts).getTime() / 1000);
      const last = {
        time: sec,
        open: tick.last,
        high: tick.last,
        low: tick.last,
        close: tick.last,
      };
      try {
        seriesRef.current.update(last);
      } catch (err) {}
    }
    window.addEventListener("quantnest:tick", onTick);
    return () => window.removeEventListener("quantnest:tick", onTick);
  }, [symbol]);

  // indicator toggles (SMA, EMA, RSI)
  const [indicators, setIndicators] = useState([
    { id: "sma20", type: "SMA", period: 20 },
  ]);

  // Recompute simple indicators when candles change — naive implementation
  useEffect(() => {
    async function compute() {
      if (!seriesRef.current) return;
      try {
        const res = await api.get(
          `/api/v1/ohlc?symbol=${encodeURIComponent(symbol)}&tf=${tf}&limit=500`
        );
        const candles = (res?.data || []).map((c) => ({
          t: Math.floor(new Date(c.ts).getTime() / 1000),
          c: c.c,
        }));
        const closes = candles.map((c) => c.c);
        // remove old indicator series
        indicatorsRef.current.forEach((s) => s.remove());
        indicatorsRef.current = [];
        for (const ind of indicators) {
          if (ind.type === "SMA") {
            const out = sma({ period: ind.period, values: closes });
            const line = seriesRef.current
              .chart()
              .addLineSeries({ lineWidth: 2 });
            const aligned = out.map((v, i) => ({
              time: candles[i + (closes.length - out.length)].t,
              value: v,
            }));
            line.setData(aligned);
            indicatorsRef.current.push(line);
          } else if (ind.type === "EMA") {
            const out = ema({ period: ind.period, values: closes });
            const line = seriesRef.current
              .chart()
              .addLineSeries({ lineWidth: 2 });
            const aligned = out.map((v, i) => ({
              time: candles[i + (closes.length - out.length)].t,
              value: v,
            }));
            line.setData(aligned);
            indicatorsRef.current.push(line);
          } else if (ind.type === "RSI") {
            const out = rsiCalc({ period: ind.period, values: closes });
            const line = seriesRef.current
              .chart()
              .addLineSeries({ lineWidth: 1 });
            const aligned = out.map((v, i) => ({
              time: candles[i + (closes.length - out.length)].t,
              value: v,
            }));
            line.setData(aligned);
            indicatorsRef.current.push(line);
          }
        }
      } catch (e) {
        // ignore
      }
    }
    compute();
  }, [symbol, tf, indicators]);

  return (
    <div className="bg-slate-900 p-3 rounded-md">
      <div className="flex gap-3 items-center mb-2">
        <div>
          <label className="text-sm text-muted-foreground">Timeframe</label>
          <select
            value={tf}
            onChange={(e) => setTf(e.target.value)}
            className="ml-2 rounded-md bg-muted px-2 py-1"
          >
            <option value="1m">1m</option>
            <option value="5m">5m</option>
            <option value="15m">15m</option>
            <option value="1h">1h</option>
          </select>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {["SMA", "EMA", "RSI"].map((t) => (
            <button
              key={t}
              className="btn btn-sm"
              onClick={() =>
                setIndicators((arr) => [
                  ...arr,
                  {
                    id: `${t}${Math.random()}`,
                    type: t,
                    period: t === "RSI" ? 14 : 20,
                  },
                ])
              }
            >
              + {t}
            </button>
          ))}
        </div>
      </div>

      <div ref={chartRef} style={{ width: "100%", height: 480 }} />
    </div>
  );
}
