import PropTypes from 'prop-types';
import { useEnums } from '@/shared/context/EnumsContext';
import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { Label } from '@/shared/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select';
import { useWebSocket } from '@/shared/hooks/useWebSocket';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { formatCurrency, formatNumber } from '@/shared/utils/formatters';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';
import { isObservedQuote } from '@/shared/utils/marketData';
import terminalApi from '../services/tradingTerminalApi';

export default function OrderTicket({ instrument, account, side, onSideChange, onOrderPlaced, session, draft }) {
  const { enums, values } = useEnums();
  const orderTypes = enums.TerminalOrderType.filter((choice) => choice.user_selectable);
  const { subscribe, getTickData } = useWebSocket();
  const { notify } = useNotifications();
  const [tick, setTick] = useState(null), [now, setNow] = useState(Date.now());
  const [busy, setBusy] = useState(false), [type, setType] = useState(values.TerminalOrderType.MARKET), [size, setSize] = useState('1');
  const [price, setPrice] = useState(''), [trigger, setTrigger] = useState('');
  const [stop, setStop] = useState(''), [target, setTarget] = useState(''), [preview, setPreview] = useState(null);
  const symbol = instrument?.sym_ticker;
  const derivative = instrument && [values.InstrumentType.FUTURE, values.InstrumentType.OPTION].includes(instrument.instrument_type);
  const unitStep = Number(instrument?.lot_size || 1);
  const quantity = Number(size) * (derivative ? unitStep : 1);
  const orderConfig = orderTypes.find((choice) => choice.value === type);
  const needsPrice = orderConfig.requires_price, needsTrigger = orderConfig.requires_trigger;
  const time = Math.max(now, Date.now());
  const hasPrice = isObservedQuote(tick);
  const open = session?.is_open && time / 1000 >= session.open && time / 1000 < session.close;

  useEffect(() => {
    setTick(symbol ? getTickData(symbol) : null);
    setPrice(''); setTrigger(''); setStop(''); setTarget(''); setPreview(null); setSize('1');
    if (!symbol) return undefined;
    return subscribe(symbol, setTick);
  }, [symbol, getTickData, subscribe]);
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  useEffect(() => { if (draft) { setType(values.TerminalOrderType.LIMIT); setPrice(String(draft.price)); } }, [draft, values.TerminalOrderType.LIMIT]);
  const payload = useMemo(() => ({ sym_ticker: symbol, transaction_type: side, order_type: type, quantity,
    ...(needsPrice ? { price } : {}), ...(needsTrigger ? { trigger_price: trigger } : {}),
    ...(stop ? { stop_loss: stop } : {}), ...(target ? { take_profit: target } : {}) }),
  [symbol, side, type, quantity, needsPrice, needsTrigger, price, trigger, stop, target]);
  const valid = Number.isInteger(quantity) && quantity > 0 && quantity % unitStep === 0
    && (!needsPrice || Number(price) > 0) && (!needsTrigger || Number(trigger) > 0);
  const previewCycle = type === values.TerminalOrderType.MARKET && hasPrice && open ? Math.floor(now / 5000) : 0;
  useEffect(() => {
    if (!instrument?.orderable || !valid) { setPreview(null); return undefined; }
    const controller = new AbortController();
    const timer = setTimeout(() => terminalApi.previewOrder(payload, controller.signal)
      .then((response) => { if (!controller.signal.aborted) setPreview(response.data); })
      .catch(() => { if (!controller.signal.aborted) setPreview(null); }), 300);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [instrument?.orderable, valid, payload, previewCycle, account?.futures_margin_pct, account?.short_option_margin_pct, account?.balance]);
  const submit = async (event) => {
    event.preventDefault();
    if (busy || !valid) return;
    setBusy(true);
    try {
      const response = await terminalApi.placeOrder(payload);
      if (response.data.status === values.TerminalOrderStatus.REJECTED) notify.error(response.data.rejection_reason);
      else notify.success(response.data.status === values.TerminalOrderStatus.COMPLETE ? 'Simulated order filled' : 'Simulated order submitted');
      onOrderPlaced?.();
    } catch (failure) { notify.error(getApiErrorMessage(failure, 'Could not submit order.')); }
    finally { setBusy(false); }
  };
  if (!instrument) return <p className="p-4 text-sm text-muted-foreground">Select an instrument to place an order.</p>;
  return <form onSubmit={submit} className="flex min-h-full flex-col gap-4 p-4 [&>*]:shrink-0">
    <div><h2 className="text-sm font-semibold">Order ticket</h2><p className="mt-1 break-words text-xs text-muted-foreground">{instrument.name} · {instrument.exchange}</p></div>
    <div className="grid grid-cols-2 gap-2">{enums.Side.map(({ value, label }) => <Button key={value} type="button" variant={side === value ? 'default' : 'outline'}
      onClick={() => onSideChange(value)} className={side === value ? value === values.Side.BUY ? 'bg-emerald-700 text-white hover:bg-emerald-800' : 'bg-rose-600 text-white hover:bg-rose-700' : ''}>{label}</Button>)}</div>
    <div className="space-y-1.5"><Label htmlFor="terminal-type">Order type</Label>
      <Select value={type} onValueChange={setType}><SelectTrigger id="terminal-type"><SelectValue /></SelectTrigger>
        <SelectContent>{orderTypes.map(({ value, label }) => <SelectItem key={value} value={value}>{label}</SelectItem>)}</SelectContent></Select></div>
    <div className="space-y-1.5"><div className="flex justify-between gap-2"><Label htmlFor="terminal-size">{derivative ? 'Lots' : 'Units'}</Label>
      {derivative && <span className="text-xs text-muted-foreground">{formatNumber(quantity, { maximumFractionDigits: 0 })} order units</span>}</div>
      <Input id="terminal-size" type="number" min={derivative ? 1 : unitStep} step={derivative ? 1 : unitStep} value={size} onChange={(event) => setSize(event.target.value)} required /></div>
    {needsPrice && <div className="space-y-1.5"><Label htmlFor="terminal-price">Limit price</Label><Input id="terminal-price" type="number" min={instrument.tick_size} step={instrument.tick_size} value={price} onChange={(event) => setPrice(event.target.value)} required /></div>}
    {needsTrigger && <div className="space-y-1.5"><Label htmlFor="terminal-trigger">Trigger price</Label><Input id="terminal-trigger" type="number" min={instrument.tick_size} step={instrument.tick_size} value={trigger} onChange={(event) => setTrigger(event.target.value)} required /></div>}
    <details className="rounded-lg border bg-muted/20 p-3 text-sm"><summary className="cursor-pointer font-medium">Stop loss & take profit</summary>
      <div className="mt-3 space-y-3"><div className="space-y-1.5"><Label htmlFor="terminal-stop">Stop loss</Label><Input id="terminal-stop" type="number" min={instrument.tick_size} step={instrument.tick_size} value={stop} onChange={(event) => setStop(event.target.value)} /></div>
        <div className="space-y-1.5"><Label htmlFor="terminal-target">Take profit</Label><Input id="terminal-target" type="number" min={instrument.tick_size} step={instrument.tick_size} value={target} onChange={(event) => setTarget(event.target.value)} /></div></div></details>
    <dl className="mt-auto space-y-2 border-t pt-4 text-xs">
      <div className="flex justify-between gap-2"><dt className="text-muted-foreground">Available capital</dt><dd className="tabular-nums">{formatCurrency(account?.available_balance)}</dd></div>
      <div className="flex justify-between gap-2"><dt className="text-muted-foreground">Estimated funds</dt><dd className="tabular-nums">{preview?.available ? formatCurrency(preview.estimated_funds) : '—'}</dd></div>
    </dl>
    {!instrument.orderable ? <p className="text-xs text-muted-foreground">This instrument is available for charts only.</p>
      : !open ? <p className="text-xs text-muted-foreground">Orders are available during this segment’s trading session.</p>
      : !hasPrice && type === values.TerminalOrderType.MARKET && <p className="text-xs text-muted-foreground">Waiting for a market price.</p>}
    <Button type="submit" disabled={busy || !instrument.orderable || !open || !valid || type === values.TerminalOrderType.MARKET && !hasPrice}
      className={side === values.Side.BUY ? 'w-full bg-emerald-700 text-white hover:bg-emerald-800' : 'w-full bg-rose-600 text-white hover:bg-rose-700'}>
      {busy ? 'Submitting…' : (side === values.Side.BUY ? 'Buy' : 'Sell') + ' ' + formatNumber(size, { maximumFractionDigits: 0 }) + (derivative ? Number(size) === 1 ? ' lot' : ' lots' : Number(size) === 1 ? ' unit' : ' units')}</Button>
  </form>;
}
OrderTicket.propTypes = { instrument: PropTypes.object, account: PropTypes.object, side: PropTypes.string,
  onSideChange: PropTypes.func.isRequired, onOrderPlaced: PropTypes.func, session: PropTypes.object, draft: PropTypes.object };
