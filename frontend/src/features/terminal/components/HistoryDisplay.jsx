import { useEffect, useMemo, useState } from 'react';
import { useEnums } from '@/shared/context/EnumsContext';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/components/ui/table';
import { useSelector } from 'react-redux';
import { Button } from '@/shared/components/ui/button';
import { DatePicker } from '@/shared/components/ui/date-picker';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select';
import { formatDateInput, formatDateTime, formatNumber, formatCurrency } from '@/shared/utils/formatters';
import { Input } from '@/shared/components/ui/input';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';
import api from '@/shared/services/api';

const amount = (value) => value == null ? '—' : formatNumber(value, { maximumFractionDigits: 8 });
const instant = (value) => value ? formatDateTime(value) : '—';
const getTables = (enums) => {
  const label = (name, value) => enums[name].find((choice) => choice.value === value)?.label || '—';
  return {
    orders: { label: 'Orders', endpoint: 'orders', columns: [
      ['Order', (r) => <><div>{label('Side', r.transaction_type)} · {label('TerminalOrderType', r.order_type)}</div>
        {r.activated_at && <div className="text-xs text-muted-foreground">Activated</div>}</>],
      ['Quantity', (r) => formatNumber(r.quantity, { maximumFractionDigits: 0 })],
      ['Price', (r) => <><div>{amount(r.avg_fill_price ?? r.price ?? r.trigger_price)}</div>
        {r.price != null && r.trigger_price != null && <div className="text-xs text-muted-foreground">Trigger {amount(r.trigger_price)}</div>}</>],
      ['Status', (r) => <><div>{label('TerminalOrderStatus', r.status)}</div>
        {r.rejection_reason && <div className="max-w-56 whitespace-normal text-xs text-destructive">{r.rejection_reason}</div>}</>],
      ['Placed (IST)', (r) => instant(r.created_at)],
    ] },
    trades: { label: 'Fills', endpoint: 'trades', columns: [
      ['Side', (r) => label('Side', r.transaction_type)],
      ['Quantity', (r) => formatNumber(r.quantity, { maximumFractionDigits: 0 })],
      ['Fill', (r) => amount(r.executed_price)], ['Charges', (r) => formatCurrency(r.charges)],
      ['Time (IST)', (r) => instant(r.timestamp)],
    ] },
    pnl: { label: 'Closed positions', endpoint: 'pnl-report', columns: [
      ['Side', (r) => label('PositionSide', r.side)],
      ['Quantity', (r) => formatNumber(r.quantity, { maximumFractionDigits: 0 })],
      ['Entry / exit', (r) => amount(r.entry_price) + ' / ' + amount(r.exit_price)],
      ['Net P&L', (r) => <><div>{formatCurrency(r.realized_pnl)}</div>
        <div className="text-xs text-muted-foreground">Charges {formatCurrency(r.recorded_charges)}</div></>],
      ['Closed (IST)', (r) => instant(r.exit_time)],
    ] },
  };
};

const numeric = (label) => ['Quantity', 'Price', 'Fill', 'Charges', 'Entry / exit', 'Net P&L'].includes(label);

export default function HistoryDisplay() {
  const { enums } = useEnums();
  const tables = useMemo(() => getTables(enums), [enums]);
  const [tab, setTab] = useState('orders'), [page, setPage] = useState(1), [search, setSearch] = useState('');
  const [status, setStatus] = useState('all'), [start, setStart] = useState(null), [end, setEnd] = useState(null);
  const [data, setData] = useState({ results: [], count: 0 }), [loading, setLoading] = useState(false), [refresh, setRefresh] = useState(0);
  const update = useSelector((state) => state.websocket.manualTradingTerminalUpdate);
  const { notify } = useNotifications();
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const response = await api.get('/trading/' + tables[tab].endpoint + '/', { signal: controller.signal,
          params: { page, symbol: search || undefined, status: tab === 'orders' && status !== 'all' ? status : undefined,
            start_date: start ? formatDateInput(start) : undefined, end_date: end ? formatDateInput(end) : undefined } });
        if (!controller.signal.aborted) setData(response.data);
      } catch (error) { if (!controller.signal.aborted) notify.error(getApiErrorMessage(error, 'Could not load terminal history.')); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }, 300);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [tab, tables, page, search, status, start, end, refresh, update, notify]);
  const changeTab = (value) => { setTab(value); setPage(1); setStatus('all'); setData({ results: [], count: 0 }); };
  return <section className="flex flex-col gap-3 rounded-xl border bg-card p-4">
    <div className="flex flex-wrap gap-2">{Object.entries(tables).map(([key, table]) => <Button key={key} size="sm" variant={tab === key ? 'secondary' : 'ghost'} onClick={() => changeTab(key)}>{table.label}</Button>)}
      <Button className="ml-auto" size="sm" variant="outline" disabled={loading} onClick={() => setRefresh((value) => value + 1)}>Refresh</Button></div>
    <div className="flex flex-wrap items-end gap-2">
      <label className="min-w-36 flex-1 text-xs"><Input value={search} placeholder="Search symbol" onChange={(e) => { setSearch(e.target.value); setPage(1); }} /></label>
      <div className="w-44 space-y-1"><DatePicker date={start} setDate={(value) => { setStart(value); setPage(1); }} placeholder="Start date" className="h-10" /></div>
      <div className="w-44 space-y-1"><DatePicker date={end} setDate={(value) => { setEnd(value); setPage(1); }} placeholder="End date" className="h-10" /></div>
      {tab === 'orders' && <div className="w-40 space-y-1">
        <Select value={status} onValueChange={(value) => { setStatus(value); setPage(1); }}><SelectTrigger aria-label="Order status"><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="all">All statuses</SelectItem>{enums.TerminalOrderStatus.map((choice) => <SelectItem key={choice.value} value={choice.value}>{choice.label}</SelectItem>)}</SelectContent></Select></div>}
      {(start || end || search || status !== 'all') && <Button variant="ghost" size="sm" onClick={() => { setStart(null); setEnd(null); setSearch(''); setStatus('all'); setPage(1); }}>Clear filters</Button>}
    </div>
    <Table containerClassName="max-h-[65vh]" className="whitespace-nowrap">
      <TableHeader className="sticky top-0 z-10 bg-card [&_tr]:bg-secondary/50">
        <TableRow className="border-border hover:bg-transparent"><TableHead className="text-foreground">Instrument</TableHead>
          {tables[tab].columns.map(([label]) => <TableHead key={label} className={numeric(label) ? 'text-right text-foreground' : 'text-foreground'}>{label}</TableHead>)}
        </TableRow>
      </TableHeader>
      <TableBody>{data.results.map((row) => <TableRow className="border-border" key={row.id}>
        <TableCell><div className="max-w-72 whitespace-normal font-medium leading-5">{row.instrument.name}</div><div className="text-xs text-muted-foreground">{row.instrument.exchange}</div></TableCell>
        {tables[tab].columns.map(([label, value]) => <TableCell key={label} className={numeric(label) ? 'text-right tabular-nums' : ''}>{value(row)}</TableCell>)}
      </TableRow>)}
      {!data.results.length && <TableRow><TableCell colSpan={tables[tab].columns.length + 1}
        className="h-24 text-center text-muted-foreground">{loading ? 'Loading…' : 'No records match these filters.'}</TableCell></TableRow>}
      </TableBody>
    </Table>
    <div className="flex items-center justify-between text-sm"><span>{formatNumber(data.count, { maximumFractionDigits: 0 })} records{loading ? ' · Updating…' : ''}</span><div className="flex items-center gap-2">
      <Button size="sm" variant="outline" disabled={loading || page === 1} onClick={() => setPage((value) => value - 1)}>Previous</Button><span>Page {page}</span>
      <Button size="sm" variant="outline" disabled={loading || page * 50 >= data.count} onClick={() => setPage((value) => value + 1)}>Next</Button></div></div>
  </section>;
}
