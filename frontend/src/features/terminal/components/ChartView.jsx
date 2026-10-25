import { GlobalLoader } from '@/shared/components/ui/global-loader';
import PropTypes from 'prop-types';
import { useEnums } from '@/shared/context/EnumsContext';
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { CandlestickSeries, LineSeries, ColorType, TickMarkType, createChart } from 'lightweight-charts';
import { RotateCw } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select';
import { useTheme } from '@/shared/context/theme';
import { getChartPalette } from '@/shared/lib/chartTheme';
import { formatDate, formatDateKey, formatDateTime, formatNumber, formatTime } from '@/shared/utils/formatters';
import useRealtimeCandles from '../hooks/useRealtimeCandles';

const intraday = (interval) => interval.endsWith('m') || interval.endsWith('H');
const chartTime = (stamp, interval) => intraday(interval) ? stamp : formatDateKey(new Date(stamp * 1000));

// Lightweight Charts supplies an epoch, date string, or BusinessDay object.
function chartDate(value) {
  if (typeof value === 'number') return new Date(value * 1000);
  if (typeof value === 'string') return new Date(value + 'T00:00:00Z');
  return new Date(Date.UTC(value.year, value.month - 1, value.day));
}
function axisLabel(value, type) {
  const date = chartDate(value);
  if (type === TickMarkType.Year) return formatDate(date, { year: 'numeric' });
  if (type === TickMarkType.Month) return formatDate(date, { month: 'short', year: '2-digit' });
  if (type === TickMarkType.DayOfMonth) return formatDate(date, { day: 'numeric', month: 'short' });
  return formatTime(date, type === TickMarkType.TimeWithSeconds ? { second: '2-digit' } : {});
}

export default function ChartView({ symbol, instrument, onBuyClick, onSellClick, onSessionChange, onPriceSelect, className = '' }) {
  const { enums, values } = useEnums();
  const [interval, setInterval] = useState(() => localStorage.getItem('terminal.interval') || values.ChartTimeframe.M1);
  const [kind, setKind] = useState(() => localStorage.getItem('terminal.chartType') || 'candles');
  const [hover, setHover] = useState(null);
  const container = useRef(null), chart = useRef(null), series = useRef({}), rows = useRef([]);
  const settings = useRef({ interval }); settings.current = { interval };
  const priceNode = useRef(null), older = useRef(null), navigating = useRef(false), fit = useRef(true);
  const { resolvedTheme } = useTheme();
  const onTick = useCallback((tick) => {
    if (priceNode.current && tick.price) priceNode.current.textContent = formatNumber(tick.price, { maximumFractionDigits: 8 });
  }, []);
  const onCandle = useCallback((candle) => {
    if (!chart.current) return;
    const last = rows.current.at(-1);
    if (last && (candle.time < last.time || candle.time === last.time && candle.revision < last.revision)) return;
    if (last?.time === candle.time) rows.current[rows.current.length - 1] = candle; else rows.current.push(candle);
    const time = chartTime(candle.time, settings.current.interval);
    series.current.candles.update({ ...candle, time });
    series.current.line.update({ time, value: candle.close });
  }, []);
  const data = useRealtimeCandles(symbol, interval, onCandle, onTick);
  older.current = data.hasMoreHistory && !data.isLoadingOlder ? data.loadOlder : null;
  useEffect(() => { onSessionChange?.(data.session); }, [onSessionChange, data.session]);

  useLayoutEffect(() => {
    const palette = getChartPalette();
    const instance = createChart(container.current, {
      width: container.current.clientWidth, height: container.current.clientHeight,
      layout: { background: { type: ColorType.Solid, color: palette.background }, textColor: palette.text, fontSize: 11 },
      grid: { vertLines: { color: palette.grid }, horzLines: { color: palette.grid } },
      timeScale: { timeVisible: true, secondsVisible: false, rightOffset: 4, tickMarkFormatter: axisLabel },
      localization: { locale: 'en-IN', timeFormatter: (value) => formatDateTime(chartDate(value)) },
      rightPriceScale: { borderColor: palette.border, scaleMargins: { top: 0.08, bottom: 0.08 } },
    });
    chart.current = instance;
    series.current.candles = instance.addSeries(CandlestickSeries, {
      upColor: palette.up, downColor: palette.down, wickUpColor: palette.up, wickDownColor: palette.down, borderVisible: false,
    });
    series.current.line = instance.addSeries(LineSeries, { color: palette.line, visible: false, lineWidth: 2 });
    instance.subscribeCrosshairMove((event) => {
      const point = event.seriesData.get(series.current.candles);
      setHover(point || null);
    });
    instance.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (range && range.from < 20 && navigating.current) older.current?.();
    });
    const node = container.current;
    const navigate = () => { navigating.current = true; };
    node.addEventListener('wheel', navigate, { passive: true });
    node.addEventListener('pointerdown', navigate);
    const observer = new ResizeObserver(([entry]) => {
      // Expanding the bottom panel hides this chart. Keep its visible range intact.
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) instance.resize(width, height);
    });
    observer.observe(node);
    return () => {
      observer.disconnect(); node.removeEventListener('wheel', navigate); node.removeEventListener('pointerdown', navigate);
      instance.remove(); chart.current = null;
    };
  }, []);

  useLayoutEffect(() => {
    rows.current = []; fit.current = true; navigating.current = false; setHover(null);
    Object.values(series.current).forEach((item) => item.setData([]));
    if (priceNode.current) priceNode.current.textContent = '—';
    chart.current?.applyOptions({ timeScale: { timeVisible: intraday(interval) } });
    localStorage.setItem('terminal.interval', interval);
  }, [interval, symbol]);

  useEffect(() => {
    if (!chart.current || !data.historicalData.length) return;
    const merged = new Map(rows.current.map((row) => [row.time, row]));
    data.historicalData.forEach((row) => {
      if (!merged.has(row.time) || row.revision >= merged.get(row.time).revision) merged.set(row.time, row);
    });
    const range = chart.current.timeScale().getVisibleLogicalRange(), previousFirst = rows.current[0]?.time;
    const previousCount = rows.current.length;
    rows.current = [...merged.values()].sort((a, b) => a.time - b.time);
    const candles = rows.current.map((row) => ({ ...row, time: chartTime(row.time, interval) }));
    series.current.candles.setData(candles);
    series.current.line.setData(candles.map((row) => ({ time: row.time, value: row.close })));
    if (fit.current) { chart.current.timeScale().fitContent(); fit.current = false; }
    else if (range && previousFirst && rows.current[0]?.time < previousFirst) {
      const added = rows.current.length - previousCount;
      chart.current.timeScale().setVisibleLogicalRange({ from: range.from + added, to: range.to + added });
    }
    if (priceNode.current && priceNode.current.textContent === '—') priceNode.current.textContent = formatNumber(rows.current.at(-1).close, { maximumFractionDigits: 8 });
  }, [data.historicalData, interval]);

  useEffect(() => {
    series.current.candles.applyOptions({ visible: kind === 'candles' });
    series.current.line.applyOptions({ visible: kind === 'line' });
    localStorage.setItem('terminal.chartType', kind);
  }, [kind]);
  useEffect(() => {
    const palette = getChartPalette();
    chart.current?.applyOptions({
      layout: { background: { type: ColorType.Solid, color: palette.background }, textColor: palette.text },
      grid: { vertLines: { color: palette.grid }, horzLines: { color: palette.grid } },
    });
  }, [resolvedTheme]);
  useEffect(() => {
    if (!instrument) return undefined;
    const precision = String(instrument.tick_size).replace(/0+$/, '').split('.')[1]?.length || 0;
    Object.values(series.current).forEach((item) => item.applyOptions({ priceFormat: { type: 'price', precision, minMove: Number(instrument.tick_size) } }));
    const select = (event) => {
      if (!event.point || !event.sourceEvent?.ctrlKey || !instrument.orderable) return;
      const value = series.current.candles.coordinateToPrice(event.point.y), step = Number(instrument.tick_size);
      if (value > 0) onPriceSelect?.({ price: Number((Math.round(value / step) * step).toFixed(8)) });
    };
    chart.current.subscribeClick(select);
    return () => chart.current?.unsubscribeClick(select);
  }, [instrument, onPriceSelect]);

  return <section className={'flex min-h-0 flex-col overflow-hidden rounded-xl border bg-card ' + className}>
    <header className="shrink-0 border-b px-3 py-2">
      <div className="flex items-center gap-3">
        <div className="min-w-0 flex-1"><h2 className="line-clamp-2 break-words text-sm font-semibold leading-5" title={instrument?.name}>{instrument?.name || 'Select an instrument'}</h2>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">{instrument ? instrument.exchange + ' · ' + enums.InstrumentType.find((choice) => choice.value === instrument.instrument_type)?.label : 'Add an instrument to your watchlist'}</p></div>
        <div className="shrink-0 text-right"><strong ref={priceNode} className="text-lg leading-6 tabular-nums">—</strong>
          <p className="text-[11px] text-muted-foreground">{data.session?.is_open ? 'Session open' : 'Session closed'}</p></div>
        <div className="flex shrink-0 flex-col gap-1 sm:flex-row xl:hidden"><Button className="h-7 bg-emerald-700 px-2 text-xs text-white hover:bg-emerald-800" size="sm" onClick={onBuyClick}>Buy</Button><Button className="h-7 px-2 text-xs" size="sm" variant="outline" onClick={onSellClick}>Sell</Button></div>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <Select value={interval} onValueChange={setInterval}><SelectTrigger aria-label="Chart timeframe" className="h-8 w-24"><SelectValue /></SelectTrigger>
          <SelectContent>{enums.ChartTimeframe.map(({ value, label }) => <SelectItem key={value} value={value} title={label}>{value}</SelectItem>)}</SelectContent></Select>
        <Select value={kind} onValueChange={setKind}><SelectTrigger aria-label="Chart type" className="h-8 w-36"><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="candles">Candlesticks</SelectItem><SelectItem value="line">Line</SelectItem></SelectContent></Select>
        <div className="ml-auto hidden flex-wrap items-center gap-x-2 gap-y-1 text-[11px] tabular-nums text-muted-foreground sm:flex">
          {hover && ['open','high','low','close'].map((key) => <span key={key} className="inline-flex items-center gap-1 whitespace-nowrap">
            <strong className="font-bold text-primary">{key[0].toUpperCase()}</strong>
            <span>{formatNumber(hover[key], { maximumFractionDigits: 8 })}</span>
          </span>)}
        </div>
      </div>
    </header>
    <div className="relative flex min-h-[96px] flex-1 flex-col">
      <div ref={container} className="absolute inset-0" />
      {data.status === 'loading' && !data.historicalData.length && <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center bg-card/80"><GlobalLoader text="Loading chart…" fullHeight={false} /></div>}
      {data.status === 'empty' && <div className="pointer-events-none absolute inset-0 z-10 grid place-items-center text-sm text-muted-foreground">No candles returned for this range.</div>}
    </div>
    <footer className="flex min-h-7 shrink-0 flex-wrap items-center gap-x-2 gap-y-1 border-t px-3 py-1 text-[11px] text-muted-foreground">
      {data.fetchingHistory || data.isLoadingOlder ? <GlobalLoader inline text="Fetching provider history…" className="text-[11px]" /> : <><span className="hidden sm:inline">Scroll left for older history · IST</span><span className="sm:hidden">History · IST</span></>}
      {symbol && <Button variant="ghost" size="sm" className="h-6 px-2" disabled={data.status === 'loading' || data.fetchingHistory || data.isLoadingOlder} onClick={data.loadOlder}>Older history</Button>}
      {data.error && <span role="alert" className="min-w-0 flex-1 text-destructive">{data.error}</span>}
      <Button variant="ghost" size="sm" className="ml-auto h-6 px-2" onClick={data.reload} aria-label="Reload chart"><RotateCw className="h-3 w-3" /></Button>
    </footer>
  </section>;
}
ChartView.propTypes = { symbol: PropTypes.string, instrument: PropTypes.object, onBuyClick: PropTypes.func,
  onSellClick: PropTypes.func, onSessionChange: PropTypes.func, onPriceSelect: PropTypes.func, className: PropTypes.string };
