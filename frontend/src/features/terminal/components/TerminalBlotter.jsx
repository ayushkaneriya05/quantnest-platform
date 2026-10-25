import PropTypes from 'prop-types';
import { useState } from 'react';
import { Maximize2, Minimize2, ChevronDown } from 'lucide-react';
import { useEnums } from '@/shared/context/EnumsContext';
import { Badge } from '@/shared/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/components/ui/table';
import { Button } from '@/shared/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/shared/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select';
import { Checkbox } from '@/shared/components/ui/checkbox';
import { formatNumber, formatCurrency } from '@/shared/utils/formatters';
import { Input } from '@/shared/components/ui/input';
import { Dialog, DialogContent, DialogTitle } from '@/shared/components/ui/dialog';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useTerminalPositionsPnL } from '@/shared/hooks/useLivePositionsPnL';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';
import api from '@/shared/services/api';
import terminalApi from '../services/tradingTerminalApi';

const price = (value) => value == null ? '—' : formatNumber(value, { maximumFractionDigits: 8 });

export default function TerminalBlotter({ positions, orders, onSelect, expanded, onToggleExpand, onCollapse }) {
  const { enums, values } = useEnums();
  const orderTypes = enums.TerminalOrderType.filter((choice) => choice.user_selectable);
  const [tab, setTab] = useState('positions');
  const [selected, setSelected] = useState([]);
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [fields, setFields] = useState({});
  const { livePnLByPositionId } = useTerminalPositionsPnL(positions);
  const { notify } = useNotifications();
  const orderConfig = orderTypes.find((choice) => choice.value === fields.order_type);
  const actionConfig = enums.TerminalPositionAction.find((choice) => choice.value === fields.action);
  const open = (kind, row, action = values.TerminalPositionAction.REDUCE) => {
    setEditing({ kind, row });
    setFields({ action, lots: kind === 'order' ? String(row.quantity / row.instrument.lot_size) : '1', order_type: row.order_type,
      price: row.price || '', trigger_price: row.trigger_price || '',
      stop_loss: row.stop_loss || '', take_profit: row.take_profit || '', settlement_price: '' });
  };
  const act = async (operation) => {
    if (busy) return;
    setBusy(true);
    try {
      const response = await operation();
      if (response.data.status === values.TerminalOrderStatus.REJECTED) notify.error(response.data.rejection_reason);
      else notify.success('Terminal updated');
      setEditing(null); setSelected([]);
    } catch (error) { notify.error(getApiErrorMessage(error, 'Could not update the terminal.')); }
    finally { setBusy(false); }
  };
  const save = (event) => {
    event.preventDefault();
    const { kind, row } = editing;
    if (kind === 'protection') return act(() => api.patch('/trading/positions/' + row.id + '/', {
      stop_loss: fields.stop_loss || null, take_profit: fields.take_profit || null }));
    if (kind === 'order') {
      const data = {};
      for (const key of ['price', 'trigger_price']) if (String(fields[key] || '') !== String(row[key] || '')) data[key] = fields[key] || null;
      if (fields.order_type !== row.order_type) data.order_type = fields.order_type;
      const quantity = Number(fields.lots) * row.instrument.lot_size;
      if (quantity !== row.quantity) data.quantity = quantity;
      return act(() => api.patch('/trading/orders/' + row.id + '/', data));
    }
    return act(() => terminalApi.positionAction(row.id, { action: fields.action,
      quantity: Number(fields.lots) * row.instrument.lot_size,
      ...(fields.action === values.TerminalPositionAction.SETTLE ? { settlement_price: fields.settlement_price } : {}) }));
  };
  const field = (key, label) => <label className="block space-y-1 text-sm">{label}<Input type="number" min="0" step={editing.row.instrument.tick_size}
    value={fields[key]} onChange={(e) => setFields((current) => ({ ...current, [key]: e.target.value }))} /></label>;
  return <Tabs value={tab} onValueChange={setTab} asChild><section aria-label="Positions and orders" className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-xl border bg-card">
    <div className="flex shrink-0 flex-wrap items-center gap-1 border-b border-border px-2 py-1.5">
      <TabsList aria-label="Trading activity" className="h-8 gap-1 bg-transparent p-0">{['positions', 'orders'].map((value) => <TabsTrigger key={value} value={value}
        className="h-8 gap-2 px-2.5 text-xs data-[state=active]:bg-secondary data-[state=active]:shadow-none">
        {value === 'positions' ? 'Positions' : 'Orders'}<span className="rounded bg-background/80 px-1.5 py-0.5 text-[11px] tabular-nums text-muted-foreground">{value === 'positions' ? positions.length : orders.length}</span></TabsTrigger>)}</TabsList>
      <div className="ml-auto flex items-center gap-1">
        {tab === 'orders' && selected.length > 0 && <Button className="h-8 px-2 text-xs" size="sm" variant="outline" disabled={busy}
          onClick={() => act(() => terminalApi.cancelOrders(selected))}>Cancel ({selected.length})</Button>}
        <Button size="icon" variant="ghost" className="h-7 w-7" aria-label={expanded ? 'Restore trading panel' : 'Expand trading panel'} title={expanded ? 'Restore panel' : 'Expand panel'} onClick={onToggleExpand}>
          {expanded ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}</Button>
        <Button size="icon" variant="ghost" className="h-7 w-7" aria-label="Collapse trading panel" title="Collapse panel" onClick={onCollapse}><ChevronDown className="h-4 w-4" /></Button>
      </div>
    </div>
    <TabsContent value={tab} className="m-0 flex min-h-0 flex-1 flex-col">
    <Table containerClassName="min-h-0 flex-1" className="min-w-[720px] whitespace-nowrap text-xs [&_th]:h-9 [&_th]:px-3 [&_th]:text-xs [&_td]:px-3 [&_td]:py-2 [&_td_button]:text-xs">
      <TableHeader className="sticky top-0 z-10 bg-card [&_tr]:bg-secondary/50">
        <TableRow className="border-border hover:bg-transparent">
          {tab === 'orders' && <TableHead><Checkbox aria-label="Select all working orders" checked={!!orders.length && selected.length === orders.length}
            onCheckedChange={(checked) => setSelected(checked ? orders.map((order) => order.id) : [])} /></TableHead>}
          {(tab === 'positions' ? ['Instrument', 'Quantity', 'Average', 'LTP', 'P&L', 'Actions'] : ['Instrument', 'Order', 'Quantity', 'Price', 'Actions'])
            .map((label) => <TableHead key={label} className={label === 'Instrument' ? 'min-w-48 text-foreground' : ['Quantity', 'Average', 'LTP', 'P&L', 'Price'].includes(label) ? 'text-right text-foreground' : 'text-foreground'}>{label}</TableHead>)}
        </TableRow>
      </TableHeader>
      <TableBody>
        {tab === 'positions' ? positions.map((row) => {
          const live = livePnLByPositionId[row.id];
          return <TableRow key={row.id} className="border-border">
            <TableCell><button className="max-w-72 whitespace-normal text-left font-medium leading-5 hover:underline" onClick={() => onSelect(row.instrument.sym_ticker)}>
              {row.instrument.name}</button><div className="text-xs text-muted-foreground">{row.instrument.exchange}</div></TableCell>
            <TableCell className="text-right tabular-nums">{formatNumber(row.quantity, { maximumFractionDigits: 0 })}
              {[values.InstrumentType.FUTURE, values.InstrumentType.OPTION].includes(row.instrument.instrument_type) && <div className="text-xs text-muted-foreground">{formatNumber(Math.abs(row.quantity) / row.instrument.lot_size, { maximumFractionDigits: 0 })} lots</div>}</TableCell>
            <TableCell className="text-right tabular-nums">{price(row.average_price)}</TableCell>
            <TableCell className="text-right tabular-nums" title={live?.isLive ? 'Latest observed price' : 'Stored valuation'}>{price(live?.livePrice)}{!live?.isLive ? '*' : ''}</TableCell>
            <TableCell className={'text-right tabular-nums ' + (live?.pnl >= 0 ? 'text-emerald-500' : 'text-rose-500')}>{formatCurrency(live?.pnl)}</TableCell>
            <TableCell><div className="flex gap-1"><Button size="sm" variant="ghost" className="h-7 px-2" onClick={() => open('action', row)}>Manage</Button>
              <Button size="sm" variant="ghost" className="h-7 px-2" onClick={() => open('protection', row)}>Protect</Button>
              <Button size="sm" variant="outline" className="h-7 px-2" disabled={busy} onClick={() => open('action', row, values.TerminalPositionAction.CLOSE)}>Close</Button></div></TableCell>
          </TableRow>;
        }) : orders.map((row) => <TableRow key={row.id} className="border-border">
          <TableCell><Checkbox aria-label={'Select order ' + row.id} checked={selected.includes(row.id)}
            onCheckedChange={(checked) => setSelected((current) => checked ? [...current, row.id] : current.filter((id) => id !== row.id))} /></TableCell>
          <TableCell><button className="max-w-72 whitespace-normal text-left font-medium leading-5 hover:underline" onClick={() => onSelect(row.instrument.sym_ticker)}>
            {row.instrument.name}</button><div className="text-xs text-muted-foreground">{row.instrument.exchange}</div></TableCell>
          <TableCell><div className="flex items-center gap-2">
            <Badge variant="outline" className={row.transaction_type === values.Side.BUY ? 'border-emerald-500/30 text-emerald-700 dark:text-emerald-300' : 'border-rose-500/30 text-rose-700 dark:text-rose-300'}>{enums.Side.find((choice) => choice.value === row.transaction_type)?.label}</Badge>
            {enums.TerminalOrderType.find((choice) => choice.value === row.order_type)?.label}</div>
            <div className="mt-1 text-xs text-muted-foreground">{row.activated_at ? 'Activated' : orderTypes.find((choice) => choice.value === row.order_type)?.requires_trigger ? 'Waiting for trigger' : 'Working'}</div></TableCell>
          <TableCell className="text-right tabular-nums">{formatNumber(row.quantity, { maximumFractionDigits: 0 })}</TableCell>
          <TableCell className="text-right tabular-nums">{price(row.price ?? row.trigger_price)}
            {row.price != null && row.trigger_price != null && <div className="text-xs text-muted-foreground">Trigger {price(row.trigger_price)}</div>}</TableCell>
          <TableCell><Button variant="ghost" size="sm" onClick={() => open('order', row)}>Modify</Button>
            <Button variant="ghost" size="sm" disabled={busy} onClick={() => act(() => terminalApi.cancelOrders([row.id]))}>Cancel</Button></TableCell>
        </TableRow>)}
        {!(tab === 'positions' ? positions : orders).length && <TableRow><TableCell colSpan={6}
          className="h-24 text-center text-muted-foreground">No {tab === 'positions' ? 'open positions' : 'working orders'}.</TableCell></TableRow>}
      </TableBody>
    </Table>
    </TabsContent>
    <Dialog open={!!editing} onOpenChange={(value) => { if (!value) setEditing(null); }}><DialogContent aria-describedby={undefined} className="max-w-md">
      <DialogTitle>{editing?.row.instrument.name} · {editing?.kind === 'protection' ? 'Protection' : editing?.kind === 'order' ? 'Modify order' : 'Position action'}</DialogTitle>
      {editing && <form onSubmit={save} className="space-y-4">
        {editing.kind === 'protection' ? <>{field('stop_loss', 'Stop loss')}{field('take_profit', 'Take profit')}<p className="text-xs text-muted-foreground">Leave a field empty to remove that protection. Existing profitable stops can move beyond entry.</p></> : editing.kind === 'order' ? <>
          <label className="block text-sm">Type<Select value={fields.order_type} onValueChange={(value) => setFields((current) => ({ ...current, order_type: value }))}><SelectTrigger aria-label="Order type" className="mt-1"><SelectValue /></SelectTrigger>
            <SelectContent>{orderTypes.map((choice) => <SelectItem key={choice.value} value={choice.value}>{choice.label}</SelectItem>)}</SelectContent></Select></label>
            <label className="block text-sm">{![values.InstrumentType.FUTURE, values.InstrumentType.OPTION].includes(editing.row.instrument.instrument_type) ? 'Units' : 'Lots'}<Input required type="number" min="1" step="1" value={fields.lots} onChange={(e) => setFields((current) => ({ ...current, lots: e.target.value }))} /></label>
          {orderConfig?.requires_price && field('price', 'Limit price')}{orderConfig?.requires_trigger && field('trigger_price', 'Trigger price')}
          {editing.row.activated_at && <p className="text-xs text-muted-foreground">Changing the trigger rearms this stop-limit order.</p>}</> : <>
          <label className="block text-sm">Action<Select value={fields.action} onValueChange={(value) => setFields((current) => ({ ...current, action: value }))}><SelectTrigger aria-label="Position action" className="mt-1"><SelectValue /></SelectTrigger><SelectContent>
            {enums.TerminalPositionAction.filter((choice) => !choice.requires_expiry || editing.row.instrument.expiry_date)
              .map((choice) => <SelectItem key={choice.value} value={choice.value}>{choice.label}</SelectItem>)}</SelectContent></Select></label>
          {actionConfig?.requires_quantity && <label className="block text-sm">{![values.InstrumentType.FUTURE, values.InstrumentType.OPTION].includes(editing.row.instrument.instrument_type) ? 'Units' : 'Lots'}{fields.action === values.TerminalPositionAction.REVERSE ? ' in the new direction' : ''}<Input type="number" step="1" min="1" value={fields.lots} onChange={(e) => setFields((current) => ({ ...current, lots: e.target.value }))} required /></label>}
          {fields.action === values.TerminalPositionAction.SETTLE && <label className="block text-sm">Official settlement price<Input required type="number" min="0" step="any" value={fields.settlement_price} onChange={(e) => setFields((current) => ({ ...current, settlement_price: e.target.value }))} /></label>}
          <p className="text-sm text-muted-foreground">{fields.action === values.TerminalPositionAction.SETTLE ? 'After expiry only: enter the official settlement price yourself (0 for a worthless option). This records a manual simulation settlement, not a broker fill or physical delivery.' : fields.action === values.TerminalPositionAction.REVERSE ? 'This closes the existing exposure and opens the specified amount in the opposite direction.' : 'A simulated market order will use the next eligible observed price.'}</p></>}
        <Button type="submit" disabled={busy} className="w-full">{busy ? 'Applying…' : 'Confirm'}</Button>
      </form>}
    </DialogContent></Dialog>
  </section></Tabs>;
}
TerminalBlotter.propTypes = { positions: PropTypes.array.isRequired, orders: PropTypes.array.isRequired, onSelect: PropTypes.func.isRequired,
  expanded: PropTypes.bool.isRequired, onToggleExpand: PropTypes.func.isRequired, onCollapse: PropTypes.func.isRequired };
