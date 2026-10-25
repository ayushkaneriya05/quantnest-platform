import { GlobalLoader } from '@/shared/components/ui/global-loader';
import PropTypes from 'prop-types';
import { useEnums } from '@/shared/context/EnumsContext';
import { useState } from 'react';
import { Search, Plus } from 'lucide-react';
import { DatePicker } from '@/shared/components/ui/date-picker';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select';
import { formatDate, formatDateInput, formatNumber } from '@/shared/utils/formatters';
import { Input } from '@/shared/components/ui/input';
import { Button } from '@/shared/components/ui/button';
import { Dialog, DialogContent, DialogTitle } from '@/shared/components/ui/dialog';
import { useInstrumentSearch } from '@/shared/hooks/useInstrumentSearch';
import { searchTerminalInstruments } from '@/shared/services/instrumentsApi';

export default function InstrumentSearch({ onAddToWatchlist, existingWatchlistSymbols = [] }) {
  const { enums } = useEnums();
  const [query, setQuery] = useState(''), [open, setOpen] = useState(false);
  const [exchange, setExchange] = useState('all'), [instrumentType, setInstrumentType] = useState('all'), [expiry, setExpiry] = useState(null);
  const { results, loading, error } = useInstrumentSearch(query,
    { ...(exchange !== 'all' ? { exchange } : {}), ...(instrumentType !== 'all' ? { instrument_type: instrumentType } : {}), ...(expiry ? { expiry_date: formatDateInput(expiry) } : {}) }, open, searchTerminalInstruments);
  return <><Button variant="outline" size="sm" className="w-full justify-start" onClick={() => setOpen(true)}><Search className="mr-2 h-4 w-4" />Add instruments</Button>
    <Dialog open={open} onOpenChange={setOpen}><DialogContent aria-describedby={undefined} className="max-h-[85dvh] overflow-auto sm:max-w-xl">
      <DialogTitle>Find an instrument or contract</DialogTitle>
      <Input autoFocus aria-label="Search instruments" placeholder="Symbol, company, underlying or contract ticker" value={query} onChange={(e) => setQuery(e.target.value)} />
      <div className="grid gap-2 sm:grid-cols-3">
        <Select value={exchange} onValueChange={setExchange}><SelectTrigger aria-label="Exchange"><SelectValue /></SelectTrigger><SelectContent>
          <SelectItem value="all">All exchanges</SelectItem>{enums.Exchange.map((choice) => <SelectItem key={choice.value} value={choice.value}>{choice.label}</SelectItem>)}</SelectContent></Select>
        <Select value={instrumentType} onValueChange={setInstrumentType}><SelectTrigger aria-label="Instrument type"><SelectValue /></SelectTrigger><SelectContent>
          <SelectItem value="all">All instruments</SelectItem>{enums.InstrumentType.map((choice) => <SelectItem key={choice.value} value={choice.value}>{choice.label}</SelectItem>)}</SelectContent></Select>
        <DatePicker date={expiry} setDate={setExpiry} placeholder="Any expiry" className="h-10" />
      </div>
      {(expiry || exchange !== 'all' || instrumentType !== 'all') && <Button size="sm" variant="ghost" onClick={() => { setExpiry(null); setExchange('all'); setInstrumentType('all'); }}>Clear filters</Button>}
      <p className="text-xs text-muted-foreground">First 50 matches. Narrow options by underlying, expiry and strike in the search. Indices are chart-only.</p>
      <div className="max-h-[50dvh] divide-y divide-border overflow-y-auto">{results.map((instrument) => {
        const added = existingWatchlistSymbols.includes(instrument.sym_ticker);
        return <button type="button" key={instrument.sym_ticker} disabled={added} className="flex w-full items-center gap-3 p-3 text-left hover:bg-muted disabled:opacity-50" onClick={() => { onAddToWatchlist(instrument); setOpen(false); }}>
          <div className="min-w-0 flex-1"><strong className="block truncate text-sm">{instrument.name}</strong>
            <span className="text-xs text-muted-foreground">{instrument.exchange} · {enums.InstrumentType.find((choice) => choice.value === instrument.instrument_type)?.label} · {instrument.expiry_date ? formatDate(instrument.expiry_date) : ''} {enums.OptionType.find((choice) => choice.value === instrument.option_type)?.label} · Lot {instrument.lot_size} · Tick {formatNumber(instrument.tick_size, { maximumFractionDigits: 8 })}{!instrument.orderable ? ' · Analysis only' : ''}</span></div>
          {added ? <span className="text-xs">Added</span> : <Plus className="h-4 w-4 shrink-0" />}</button>;
      })}</div>
      {loading && <GlobalLoader inline text="Searching instruments…" />}
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      {!loading && !error && !results.length && <p className="text-sm text-muted-foreground">No matching instruments.</p>}
    </DialogContent></Dialog></>;
}
InstrumentSearch.propTypes = { onAddToWatchlist: PropTypes.func.isRequired, existingWatchlistSymbols: PropTypes.array };
