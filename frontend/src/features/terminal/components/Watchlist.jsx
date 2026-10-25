import PropTypes from 'prop-types';
import { useEnums } from '@/shared/context/EnumsContext';
import { useEffect, useRef } from 'react';
import { Trash2 } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { TooltipHint } from '@/shared/components/ui/tooltip';
import { formatNumber } from '@/shared/utils/formatters';
import { useWebSocket } from '@/shared/hooks/useWebSocket';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';
import InstrumentSearch from './InstrumentSearch';

export default function Watchlist({ items = [], loading, activeSymbol, onSymbolSelect, onAddToWatchlist, onRemoveFromWatchlist }) {
  const { enums } = useEnums();
  const { subscribe, tickData, isConnected, getLatestPrices } = useWebSocket();
  const { notify } = useNotifications();
  const loadedSymbols = useRef(''), connectedOnce = useRef(false);
  const symbols = items.map((item) => item.sym_ticker).sort().join('\u001f');
  useEffect(() => {
    const cleanups = (symbols ? symbols.split('\u001f') : []).map((symbol) => subscribe(symbol));
    return () => cleanups.forEach((cleanup) => cleanup());
  }, [symbols, subscribe]);
  useEffect(() => {
    // Initial prices do not wait for the socket; reconnects refresh them once.
    const refresh = symbols !== loadedSymbols.current || isConnected && connectedOnce.current;
    if (isConnected) connectedOnce.current = true;
    if (!symbols || !refresh) return undefined;
    loadedSymbols.current = symbols;
    let mounted = true;
    getLatestPrices(symbols.split('\u001f')).catch((error) => {
      if (mounted) notify.warning(getApiErrorMessage(error, 'Could not refresh watchlist prices.'));
    });
    return () => { mounted = false; };
  }, [symbols, isConnected, getLatestPrices, notify]);
  return <section className="flex h-full min-h-0 flex-col rounded-xl border border-border bg-card">
    <div className="shrink-0 border-b border-border p-2"><InstrumentSearch onAddToWatchlist={onAddToWatchlist} existingWatchlistSymbols={items.map((row) => row.sym_ticker)} /></div>
    <div className="scrollbar-thin-theme min-h-0 flex-1 overflow-y-auto">{loading ? <p className="p-3 text-sm text-muted-foreground">Loading…</p> : !items.length ? <p className="p-3 text-sm text-muted-foreground">Add an instrument to this watchlist.</p> : items.map((item) => {
      const quote = tickData[item.sym_ticker];
      return <div key={item.sym_ticker} className={'group flex items-center gap-0.5 border-b border-l-2 border-b-border py-2 pl-2 pr-1 transition-colors last:border-b-0 ' + (activeSymbol === item.sym_ticker ? 'border-l-primary bg-primary/10' : 'border-l-transparent hover:bg-muted/40')}>
        <TooltipHint content={item.name}><button type="button" aria-pressed={activeSymbol === item.sym_ticker} className="min-w-0 flex-1 rounded-sm text-left outline-none focus-visible:ring-2 focus-visible:ring-ring" onClick={() => onSymbolSelect(item.sym_ticker)}>
          <span className="flex justify-between gap-2 text-xs"><strong className="line-clamp-2 min-w-0 break-words font-semibold leading-4">{item.name}</strong><span className="shrink-0 font-medium tabular-nums">{quote?.price != null ? formatNumber(quote.price, { maximumFractionDigits: 8 }) : '—'}</span></span>
          <span className="mt-1 flex justify-between gap-1 text-[11px] text-muted-foreground"><span className="truncate">{item.exchange} · {enums.InstrumentType.find((choice) => choice.value === item.instrument_type)?.label}</span>
            <span className={Number(quote?.change_percent) >= 0 ? 'text-emerald-500' : 'text-rose-500'}>{quote?.change_percent != null ? formatNumber(quote.change_percent) + '%' : ''}</span></span>
        </button></TooltipHint><Button type="button" size="icon" variant="ghost" className="h-7 w-7 shrink-0" aria-label={'Remove ' + item.name + ' from watchlist'} onClick={() => onRemoveFromWatchlist(item.sym_ticker)}><Trash2 className="h-3 w-3" /></Button>
      </div>;
    })}</div>
  </section>;
}
Watchlist.propTypes = { items: PropTypes.array, loading: PropTypes.bool, activeSymbol: PropTypes.string, onSymbolSelect: PropTypes.func.isRequired,
  onAddToWatchlist: PropTypes.func.isRequired, onRemoveFromWatchlist: PropTypes.func.isRequired };
