import PropTypes from 'prop-types';
import { useEnums } from '@/shared/context/EnumsContext';
import { useEffect } from 'react';
import { Trash2 } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { formatNumber } from '@/shared/utils/formatters';
import { useWebSocket } from '@/shared/hooks/useWebSocket';
import InstrumentSearch from './InstrumentSearch';

export default function Watchlist({ items = [], loading, activeSymbol, onSymbolSelect, onAddToWatchlist, onRemoveFromWatchlist }) {
  const { enums } = useEnums();
  const { subscribe, getTickData } = useWebSocket();
  const symbols = items.map((item) => item.sym_ticker).sort().join('\u001f');
  useEffect(() => {
    const cleanups = (symbols ? symbols.split('\u001f') : []).map((symbol) => subscribe(symbol));
    return () => cleanups.forEach((cleanup) => cleanup());
  }, [symbols, subscribe]);
  return <section className="flex h-full min-h-0 flex-col rounded-xl border border-border bg-card">
    <div className="shrink-0 border-b border-border p-2"><InstrumentSearch onAddToWatchlist={onAddToWatchlist} existingWatchlistSymbols={items.map((row) => row.sym_ticker)} /></div>
    <div className="min-h-0 flex-1 overflow-y-auto">{loading ? <p className="p-3 text-sm text-muted-foreground">Loading…</p> : !items.length ? <p className="p-3 text-sm text-muted-foreground">Add an instrument to this watchlist.</p> : items.map((item) => {
      const quote = getTickData(item.sym_ticker);
      return <div key={item.sym_ticker} className={'flex items-center gap-1 border-b border-border p-2 ' + (activeSymbol === item.sym_ticker ? 'bg-primary/10' : 'hover:bg-muted/40')}>
        <button type="button" className="min-w-0 flex-1 text-left" onClick={() => onSymbolSelect(item.sym_ticker)}>
          <span className="flex justify-between gap-2 text-sm"><strong className="min-w-0 break-words leading-5" title={item.name}>{item.name}</strong><span className="shrink-0 tabular-nums">{quote?.price != null ? formatNumber(quote.price, { maximumFractionDigits: 8 }) : '—'}</span></span>
          <span className="mt-1 flex justify-between gap-1 text-[11px] text-muted-foreground"><span>{item.exchange} · {enums.InstrumentType.find((choice) => choice.value === item.instrument_type)?.label}</span>
            <span className={Number(quote?.change_percent) >= 0 ? 'text-emerald-500' : 'text-rose-500'}>{quote?.change_percent != null ? formatNumber(quote.change_percent) + '%' : ''}</span></span>
        </button><Button type="button" size="icon" variant="ghost" className="h-7 w-7 shrink-0" aria-label={'Remove ' + item.name + ' from watchlist'} onClick={() => onRemoveFromWatchlist(item.sym_ticker)}><Trash2 className="h-3 w-3" /></Button>
      </div>;
    })}</div>
  </section>;
}
Watchlist.propTypes = { items: PropTypes.array, loading: PropTypes.bool, activeSymbol: PropTypes.string, onSymbolSelect: PropTypes.func.isRequired,
  onAddToWatchlist: PropTypes.func.isRequired, onRemoveFromWatchlist: PropTypes.func.isRequired };
