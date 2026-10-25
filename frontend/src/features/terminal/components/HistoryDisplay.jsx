import { useEffect, useMemo, useState } from 'react';
import { useEnums } from '@/shared/context/EnumsContext';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/components/ui/table';
import { useSelector } from 'react-redux';
import { Button } from '@/shared/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/shared/components/ui/tabs';
import { RefreshCw, Search } from 'lucide-react';
import { DatePicker } from '@/shared/components/ui/date-picker';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select';
import { formatDateInput, formatDateTime, formatNumber, formatCurrency } from '@/shared/utils/formatters';
import { Input } from '@/shared/components/ui/input';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';
import api from '@/shared/services/api';

const amount = (value) => value == null ? '—' : formatNumber(value, { maximumFractionDigits: 8 });
const instant = (value) => value ? formatDateTime(value) : '—';
const pnl = (value) => <span className={Number(value) >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}>{formatCurrency(value)}</span>;
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
      ['Gross P&L', (r) => pnl(r.gross_pnl)],
      ['Charges', (r) => formatCurrency(r.recorded_charges)],
      ['Net P&L', (r) => pnl(r.realized_pnl)],
      ['Closed (IST)', (r) => instant(r.exit_time)],
    ] },
  };
};

const numeric = (label) => ['Quantity', 'Price', 'Fill', 'Charges', 'Entry / exit', 'Gross P&L', 'Net P&L'].includes(label);

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
  return <Tabs value={tab} onValueChange={changeTab} asChild><section aria-label="Trading history" className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-xl border bg-card">
    <div className="flex shrink-0 flex-wrap items-center gap-2 border-b px-3 py-2">
      <TabsList aria-label="History type" className="h-9 bg-transparent p-0">{Object.entries(tables).map(([key, table]) => <TabsTrigger key={key} value={key}
        className="px-2.5 text-xs data-[state=active]:bg-secondary data-[state=active]:shadow-none">{table.label}</TabsTrigger>)}</TabsList>
      <Button className="ml-auto h-8 w-8" size="icon" variant="ghost" aria-label="Refresh history" disabled={loading} onClick={() => setRefresh((value) => value + 1)}><RefreshCw className={'h-4 w-4 ' + (loading ? 'animate-spin' : '')} /></Button></div>
    <div className="flex shrink-0 flex-wrap items-center gap-2 border-b bg-muted/10 p-3">
      <div className="relative min-w-36 flex-1"><Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" /><Input className="h-9 pl-8 text-sm" aria-label="Search history instruments" value={search} placeholder="Search instruments" onChange={(e) => { setSearch(e.target.value); setPage(1); }} /></div>
      <div className="w-36"><DatePicker date={start} setDate={(value) => { setStart(value); setPage(1); }} placeholder="Start date" className="h-9 text-xs" /></div>
      <div className="w-36"><DatePicker date={end} setDate={(value) => { setEnd(value); setPage(1); }} placeholder="End date" className="h-9 text-xs" /></div>
      {tab === 'orders' && <div className="w-36">
        <Select value={status} onValueChange={(value) => { setStatus(value); setPage(1); }}><SelectTrigger className="h-9 text-xs" aria-label="Order status"><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="all">All statuses</SelectItem>{enums.TerminalOrderStatus.map((choice) => <SelectItem key={choice.value} value={choice.value}>{choice.label}</SelectItem>)}</SelectContent></Select></div>}
      {(start || end || search || status !== 'all') && <Button variant="ghost" size="sm" onClick={() => { setStart(null); setEnd(null); setSearch(''); setStatus('all'); setPage(1); }}>Clear filters</Button>}
    </div>
    <TabsContent value={tab} className="m-0 flex min-h-0 flex-1 flex-col">
    <Table containerClassName="min-h-0 flex-1" className="whitespace-nowrap text-xs [&_th]:h-9 [&_th]:px-3 [&_th]:text-xs [&_td]:px-3 [&_td]:py-2.5">
      <TableHeader className="sticky top-0 z-10 bg-card [&_tr]:bg-secondary/50">
        <TableRow className="border-border hover:bg-transparent"><TableHead className="min-w-48 text-foreground">Instrument</TableHead>
          {tables[tab].columns.map(([label]) => <TableHead key={label} className={numeric(label) ? 'text-right text-foreground' : 'text-foreground'}>{label}</TableHead>)}
        </TableRow>
      </TableHeader>
      <TableBody>{data.results.map((row) => <TableRow className="border-border" key={row.id}>
        <TableCell><div className="line-clamp-2 max-w-64 whitespace-normal font-medium leading-4" title={row.instrument.name}>{row.instrument.name}</div><div className="mt-0.5 text-[11px] text-muted-foreground">{row.instrument.exchange}</div></TableCell>
        {tables[tab].columns.map(([label, value]) => <TableCell key={label} className={numeric(label) ? 'text-right tabular-nums' : ''}>{value(row)}</TableCell>)}
      </TableRow>)}
      {!data.results.length && <TableRow><TableCell colSpan={tables[tab].columns.length + 1}
        className="h-24 text-center text-muted-foreground">{loading ? 'Loading…' : 'No records match these filters.'}</TableCell></TableRow>}
      </TableBody>
    </Table>
    </TabsContent>
    <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t px-3 py-2 text-xs"><span className="text-muted-foreground" aria-live="polite">{formatNumber(data.count, { maximumFractionDigits: 0 })} records{loading ? ' · Updating…' : ''}</span><div className="flex items-center gap-2">
      <Button size="sm" className="h-8 px-2 text-xs" variant="outline" disabled={loading || page === 1} onClick={() => setPage((value) => value - 1)}>Previous</Button><span className="tabular-nums">Page {page}</span>
      <Button size="sm" className="h-8 px-2 text-xs" variant="outline" disabled={loading || page * 50 >= data.count} onClick={() => setPage((value) => value + 1)}>Next</Button></div></div>
  </section></Tabs>;
}
