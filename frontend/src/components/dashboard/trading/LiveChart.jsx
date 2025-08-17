import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  createChart,
  CrosshairMode,
  CandlestickSeries,
} from "lightweight-charts";
import api from "@/services/api";
import { sma, ema, rsi as rsiCalc } from "technicalindicators";

export default function LiveChart({ symbol, ws }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const indicatorSeriesRef = useRef([]);
  const [tf, setTf] = useState("1m");
  const [candles, setCandles] = useState([]);
  const [indicators, setIndicators] = useState([
    { id: "sma20", type: "SMA", period: 20 },
  ]);
  const tfOptions = useMemo(() => ["1m", "5m", "15m", "1h"], []);

  // Initialize Chart once
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const chart = createChart(el, {
      layout: { backgroundColor: "#071423", textColor: "#cbd5e1" },
      width: el.clientWidth,
      height: 480,
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderVisible: false },
      timeScale: {
        borderVisible: false,
        timeVisible: true,
        secondsVisible: true,
      },
      grid: {
        vertLines: { color: "rgba(197,203,206,0.08)" },
        horzLines: { color: "rgba(197,203,206,0.08)" },
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#16a34a",
      downColor: "#ef4444",
      wickUpColor: "#16a34a",
      wickDownColor: "#ef4444",
      borderVisible: false,
    });

    chart.timeScale().fitContent();

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;

    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: el.clientWidth, height: 480 });
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      indicatorSeriesRef.current.forEach(({ series }) => series.remove());
      indicatorSeriesRef.current = [];
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
    };
  }, []);

  // Load Historical Candles
  useEffect(() => {
    let abort = new AbortController();

    const load = async () => {
      if (!candleSeriesRef.current) return;
      try {
        const res = await api.get(
          `/market/ohlc/?symbol=${symbol}&tf=${tf}&limit=500`,
          { signal: abort.signal }
        );
        const arr = (Array.isArray(res?.data) ? res.data : [])
          .map((c) => ({
            time: Math.floor(new Date(c.ts).getTime() / 1000),
            open: Number(c.o),
            high: Number(c.h),
            low: Number(c.l),
            close: Number(c.c),
          }))
          .filter((d) => !isNaN(d.open));

        setCandles(arr);
        candleSeriesRef.current.setData(arr);
        chartRef.current?.timeScale().fitContent();
      } catch (e) {
        if (e.name !== "CanceledError") console.error(e);
      }
    };

    load();
    return () => abort.abort();
  }, [symbol, tf]);

  // Indicators
  useEffect(() => {
    if (!candles.length || !chartRef.current) return;

    indicatorSeriesRef.current.forEach(({ series }) => series.remove());
    indicatorSeriesRef.current = [];

    const closes = candles.map((c) => c.close);
    const addLine = (width = 2) =>
      chartRef.current.addLineSeries({
        lineWidth: width,
        priceScaleId: "right",
      });

    indicators.forEach((ind) => {
      let out = null;
      if (ind.type === "SMA") out = sma({ period: ind.period, values: closes });
      else if (ind.type === "EMA")
        out = ema({ period: ind.period, values: closes });
      else if (ind.type === "RSI")
        out = rsiCalc({ period: ind.period, values: closes });

      if (!out?.length) return;

      const line = addLine(ind.type === "RSI" ? 1 : 2);
      const aligned = out.map((v, i) => ({
        time: candles[i + (closes.length - out.length)].time,
        value: v,
      }));
      line.setData(aligned);
      indicatorSeriesRef.current.push({ ...ind, series: line });
    });
  }, [candles, indicators]);

  // Live Updates
  useEffect(() => {
    if (!candleSeriesRef.current) return;

    let rafId = null;

    const applyTick = (tick) => {
      if (!tick?.symbol || tick.symbol !== symbol || !tick.ts) return;
      const sec = Math.floor(new Date(tick.ts).getTime() / 1000);

      setCandles((prev) => {
        const last = prev[prev.length - 1];
        const close = Number(tick.c ?? tick.last ?? last?.close ?? 0);
        const high =
          last && last.time === sec ? Math.max(last.high, close) : close;
        const low =
          last && last.time === sec ? Math.min(last.low, close) : close;
        const open = last && last.time === sec ? last.open : close;

        const next =
          last && last.time === sec
            ? [...prev.slice(0, -1), { time: sec, open, high, low, close }]
            : [
                ...prev,
                { time: sec, open: close, high: close, low: close, close },
              ];

        if (!rafId) {
          rafId = requestAnimationFrame(() => {
            candleSeriesRef.current.update(next[next.length - 1]);
            rafId = null;
          });
        }
        return next;
      });
    };

    let wsListener = null;
    if (ws?.addEventListener) {
      wsListener = (e) => {
        try {
          const data = typeof e.data === "string" ? JSON.parse(e.data) : e.data;
          applyTick(data.tick || data);
        } catch {}
      };
      ws.addEventListener("message", wsListener);
    }

    const onTick = (e) => applyTick(e.detail);
    window.addEventListener("quantnest:tick", onTick);

    return () => {
      window.removeEventListener("quantnest:tick", onTick);
      if (ws?.removeEventListener)
        ws.removeEventListener("message", wsListener);
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, [symbol, ws]);

  return (
    <div className="bg-slate-900 p-3 rounded-md">
      <div className="flex justify-between mb-2">
        <select value={tf} onChange={(e) => setTf(e.target.value)}>
          {tfOptions.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
        <div className="flex gap-2">
          {["SMA", "EMA", "RSI"].map((t) => (
            <button
              key={t}
              onClick={() =>
                setIndicators((prev) => [
                  ...prev,
                  {
                    id: `${t}-${Date.now()}`,
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
      <div ref={containerRef} style={{ width: "100%", height: 480 }} />
    </div>
  );
}
