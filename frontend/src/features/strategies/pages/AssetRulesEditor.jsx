/**
 * Asset Rules Editor - instrument selection for algo trading
 * Features: dropdown search, filter tabs, enriched watchlist, instrument detail dialog
 */
import { useState, useEffect, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Badge } from "@/shared/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/shared/components/ui/dialog";
import {
  Search, Plus, X, Layers, Loader2, Info,
  TrendingUp, BarChart3, Shield, Clock, Eye,
  Package, GitMerge,
} from 'lucide-react';
import StrategyConfigNav from '@/features/strategies/components/StrategyConfigNav.jsx';
import UniversalRoutingModal from '@/features/strategies/components/UniversalRoutingModal.jsx';
import { useInstrumentSearch } from '@/shared/hooks/useInstrumentSearch';
import { instrumentsApi, watchlistApi } from '@/shared/services/instrumentsApi';
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { strategyApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { usePageActions } from '@/shared/context/pageActions';
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { useEnums } from '@/shared/context/EnumsContext';

// ── Constants ──
const TYPE_LABELS = { STOCK: 'Equity', FUTURE: 'Futures', OPTION: 'Options', BOND: 'Bonds' };

const TYPE_COLORS = {
  STOCK: 'bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/20',
  ETF: 'bg-indigo-500/15 text-indigo-700 dark:text-indigo-400 border-indigo-500/20',
  BOND: 'bg-teal-500/15 text-teal-700 dark:text-teal-400 border-teal-500/20',
  MF: 'bg-fuchsia-500/15 text-fuchsia-400 border-fuchsia-500/20',
  INDEX: 'bg-cyan-500/15 text-cyan-700 dark:text-cyan-400 border-cyan-500/20',
  FUTURE: 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/20',
  OPTION: 'bg-violet-500/15 text-violet-700 dark:text-violet-400 border-violet-500/20',
  CURRENCY: 'bg-emerald-500/15 text-emerald-800 dark:text-emerald-400 border-emerald-500/20',
  COMMODITY: 'bg-orange-500/15 text-orange-700 dark:text-orange-400 border-orange-500/20',
};

const TYPE_DOT = {
  STOCK: 'bg-blue-400', ETF: 'bg-indigo-400', BOND: 'bg-teal-400', MF: 'bg-fuchsia-400',
  INDEX: 'bg-cyan-400', FUTURE: 'bg-amber-400',
  OPTION: 'bg-violet-400', CURRENCY: 'bg-emerald-400', COMMODITY: 'bg-orange-400',
};

// ── Helpers ──
const fmt = (p) => p ? `₹${parseFloat(p).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : null;
const fmtExp = (d) => d ? new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' }) : null;
const daysTo = (d) => { if (!d) return null; const diff = Math.ceil((new Date(d) - new Date()) / 864e5); return diff >= 0 ? diff : null; };

// ── Instrument Detail Dialog ──
function DetailDialog({ instrument, open, onClose }) {
  if (!instrument) return null;
  const i = instrument;
  const isDeriv = ['FUTURE', 'OPTION'].includes(i.instrument_type);

  const sections = [
    { title: 'Identity', icon: <Info className="h-3.5 w-3.5" />, rows: [
      ['Symbol', i.sym_ticker], ['Name', i.name], ['ISIN', i.isin || '—'],
      ['Fy Token', i.fy_token], ['Exchange Token', i.exchange_token],
    ]},
    { title: 'Trading Specs', icon: <TrendingUp className="h-3.5 w-3.5" />, rows: [
      ['Lot Size', i.lot_size], ['Tick Size', i.tick_size],
      ['Qty Freeze', i.qty_freeze || '—'], ['Qty Multiplier', i.qty_multiplier],
      ['Face Value', i.face_value || '—'],
    ]},
    { title: 'Circuit Limits', icon: <Shield className="h-3.5 w-3.5" />, rows: [
      ['Upper', fmt(i.circuit_limit_upper) || '—'], ['Lower', fmt(i.circuit_limit_lower) || '—'],
      ['Session', i.trading_session || '—'],
    ]},
    { title: 'Market', icon: <BarChart3 className="h-3.5 w-3.5" />, rows: [
      ['Prev Close', fmt(i.previous_close) || '—'], ['Prev OI', i.previous_oi || '—'],
    ]},
    { title: 'Status', icon: <Eye className="h-3.5 w-3.5" />, rows: [
      ['MTF', i.is_mtf_tradable ? `Yes (${i.mtf_margin || '—'}x)` : 'No'],
      ['ASM/GSM', i.asm_gsm_flag || 'Clean'],
      ['Options Chain', i.has_options ? '✓' : '—'],
      ['Futures', i.has_futures ? '✓' : '—'],
    ]},
  ];
  if (isDeriv) sections.push({ title: 'Derivative', icon: <Clock className="h-3.5 w-3.5" />, rows: [
    ['Underlying', i.underlying_symbol || '—'], ['Expiry', fmtExp(i.expiry_date) || '—'],
    ['Strike', i.strike_price > 0 ? `₹${i.strike_price}` : '—'],
    ['Type', i.option_type !== 'XX' ? i.option_type : '—'],
  ]});

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-background border-border/80 text-foreground max-w-md max-h-[85dvh] overflow-y-auto scrollbar-theme p-0">
        {/* Header */}
        <div className="sticky top-0 bg-background/95 backdrop-blur-sm border-b border-border/60 px-5 pt-5 pb-3 z-10">
          <DialogHeader className="flex flex-row items-start justify-between space-y-0">
            <div>
              <DialogTitle className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${TYPE_DOT[i.instrument_type] || 'bg-muted'}`} />
                <span className="text-base font-semibold">{i.symbol}</span>
                <Badge className={`text-[9px] px-1.5 py-0 border ${TYPE_COLORS[i.instrument_type] || ''}`}>
                  {i.instrument_type}
                </Badge>
                <Badge variant="outline" className="border-border/60 text-muted-foreground text-[9px]">
                  {i.exchange}
                </Badge>
              </DialogTitle>
              <p className="text-[11px] text-muted-foreground mt-0.5">{i.name}</p>
            </div>
            <button
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground bg-card/50 hover:bg-secondary p-1.5 rounded-md transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </DialogHeader>
        </div>

        {/* Body */}
        <div className="px-5 pb-5 space-y-3">
          {sections.map(s => (
            <div key={s.title} className="rounded-lg bg-card/50 border border-border/40 p-3">
              <h4 className="text-[12px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5 mb-2.5">
                {s.icon} {s.title}
              </h4>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                {s.rows.map(([label, value]) => (
                  <div key={label} className="flex justify-between items-center py-0.5">
                    <span className="text-[11px] text-muted-foreground">{label}</span>
                    <span className="text-[11px] text-foreground font-mono">{value ?? '—'}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

const formatOI = (oi) => {
  if (!oi) return '0';
  const num = parseInt(oi, 10);
  if (isNaN(num)) return '0';
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
  return num.toString();
};

// ── Option Chain Viewer Dialog ──
function OptionChainViewer({ underlying, open, onClose, onAdd, watchlistIds }) {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedExpiry, setSelectedExpiry] = useState('');
  const atmRowRef = useRef(null);

  useEffect(() => {
    if (!open || !underlying) return;
    const fetchOptions = async () => {
      setLoading(true);
      try {
        const query = underlying.symbol;
        const res = await instrumentsApi.search({ underlying: query, type: 'OPTION', limit: 500 });
        setOptions(res);
        const exps = [...new Set(res.map(o => o.expiry_date))].sort();
        if (exps.length > 0) setSelectedExpiry(exps[0]);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchOptions();
  }, [open, underlying]);

  const expiries = useMemo(() => [...new Set(options.map(o => o.expiry_date))].sort(), [options]);

  const chainData = useMemo(() => {
    if (!selectedExpiry) return [];
    const activeOptions = options.filter(o => o.expiry_date === selectedExpiry);
    const byStrike = {};
    activeOptions.forEach(o => {
      if (!byStrike[o.strike_price]) byStrike[o.strike_price] = { strike: parseFloat(o.strike_price), CE: null, PE: null };
      if (o.option_type === 'CE') byStrike[o.strike_price].CE = o;
      if (o.option_type === 'PE') byStrike[o.strike_price].PE = o;
    });
    return Object.values(byStrike).sort((a, b) => a.strike - b.strike);
  }, [options, selectedExpiry]);

  const atmStrike = useMemo(() => {
    if (!underlying?.previous_close || chainData.length === 0) return null;
    const spot = parseFloat(underlying.previous_close);
    return chainData.reduce((prev, curr) => 
      Math.abs(curr.strike - spot) < Math.abs(prev.strike - spot) ? curr : prev
    ).strike;
  }, [chainData, underlying?.previous_close]);

  // Auto-scroll to ATM row when chainData loads
  useEffect(() => {
    if (atmRowRef.current) {
      atmRowRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [chainData, atmStrike, selectedExpiry]);

  if (!underlying) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-background border-border/80 text-foreground max-w-4xl max-h-[85dvh] p-0 flex flex-col">
        {/* Header */}
        <div className="bg-background/95 backdrop-blur-sm border-b border-border/60 px-5 py-4 shrink-0">
          <DialogTitle className="flex items-center gap-2">
            <span className="text-lg font-bold">{underlying.symbol} Option Chain</span>
          </DialogTitle>
          <p className="text-xs text-muted-foreground mt-1">LTP: {fmt(underlying.previous_close) || 'N/A'}</p>
        </div>

        {/* Body */}
        {loading ? (
          <div className="flex-1 flex flex-col justify-center items-center py-20">
            <GlobalLoader />
            <p className="text-sm text-muted-foreground">Loading Option Chain...</p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col min-h-[400px]">
            {/* Expiry Tabs */}
            <div className="shrink-0 flex gap-2 p-3 overflow-x-auto scrollbar-thin-theme border-b border-border/60 bg-card/30">
              {expiries.map(exp => (
                <button
                  key={exp}
                  onClick={() => setSelectedExpiry(exp)}
                  className={`px-3 py-1.5 rounded-md text-xs font-semibold whitespace-nowrap transition-colors ${
                    selectedExpiry === exp
                      ? 'bg-indigo-600/20 text-indigo-700 dark:text-indigo-400 border border-indigo-500/30'
                      : 'bg-card text-muted-foreground border border-border hover:border-border'
                  }`}
                >
                  {fmtExp(exp)}
                </button>
              ))}
              {expiries.length === 0 && <span className="text-sm text-muted-foreground py-1">No expiries found.</span>}
            </div>

            {/* Chain Table */}
            <div className="flex-1 overflow-y-auto scrollbar-theme px-3 pb-3">
              <table className="w-full text-xs text-left border-separate border-spacing-0">
                <thead className="sticky top-0 z-10 text-muted-foreground shadow-sm">
                  <tr>
                    <th colSpan={3} className="py-2 px-2 text-center border-b border-border text-success bg-background">CALLS</th>
                    <th className="py-2 px-2 text-center border-b border-l border-r border-border text-foreground bg-background">STRIKE</th>
                    <th colSpan={3} className="py-2 px-2 text-center border-b border-border text-loss bg-background">PUTS</th>
                  </tr>
                  <tr>
                    <th className="py-2 px-2 w-20 border-b border-border bg-background">Action</th>
                    <th className="py-2 px-2 text-right border-b border-border bg-background">OI</th>
                    <th className="py-2 px-2 text-right border-b border-border bg-background">LTP</th>
                    <th className="py-2 px-2 text-center border-b border-l border-r border-border bg-background">₹</th>
                    <th className="py-2 px-2 border-b border-border bg-background">LTP</th>
                    <th className="py-2 px-2 border-b border-border bg-background">OI</th>
                    <th className="py-2 px-2 text-right w-20 border-b border-border bg-background">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {chainData.map((row) => {
                    const isATM = row.strike === atmStrike;
                    const spot = parseFloat(underlying.previous_close || 0);
                    const ceITM = row.strike < spot;
                    const peITM = row.strike > spot;
                    
                    return (
                      <tr 
                        key={row.strike} 
                        ref={isATM ? atmRowRef : null}
                        className={`group transition-colors ${
                          isATM ? 'bg-indigo-50 dark:bg-indigo-900/30 ring-1 ring-indigo-500/50' : 'hover:bg-card/60'
                        }`}
                      >
                        {/* CALLS */}
                        <td className={`py-1 px-2 ${ceITM ? 'bg-amber-50 dark:bg-amber-900/10' : ''}`}>
                        {row.CE && (
                          <Button
                            size="sm"
                            disabled={watchlistIds.has(row.CE.id)}
                            onClick={() => onAdd(row.CE)}
                            className={`h-6 px-3.5 shadow-none text-[10px] ${watchlistIds.has(row.CE.id) ? 'bg-secondary text-muted-foreground' : 'bg-emerald-600/20 hover:bg-emerald-600/20 text-emerald-800 dark:text-emerald-400'}`}
                          >
                            {watchlistIds.has(row.CE.id) ? 'Added' : 'Add'}
                          </Button>
                        )}
                        </td>
                        <td className={`py-1 px-2 text-right font-mono text-muted-foreground ${ceITM ? 'bg-amber-50 dark:bg-amber-900/10' : ''}`}>{formatOI(row.CE?.previous_oi)}</td>
                        <td className={`py-1 px-2 text-right font-mono text-emerald-800 dark:text-emerald-400/90 ${ceITM ? 'bg-amber-50 dark:bg-amber-900/10' : ''}`}>{fmt(row.CE?.previous_close) || '0.00'}</td>
                        
                        {/* STRIKE */}
                        <td className={`py-1.5 px-2 text-center font-bold font-mono border-l border-r border-border/60 ${
                          isATM ? 'text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-900/40' : 'text-foreground bg-card/50'
                        }`}>
                        {row.strike}
                        </td>
                        
                        {/* PUTS */}
                        <td className={`py-1 px-2 font-mono text-rose-800 dark:text-rose-400/90 ${peITM ? 'bg-amber-50 dark:bg-amber-900/10' : ''}`}>{fmt(row.PE?.previous_close) || '0.00'}</td>
                        <td className={`py-1 px-2 font-mono text-muted-foreground ${peITM ? 'bg-amber-50 dark:bg-amber-900/10' : ''}`}>{formatOI(row.PE?.previous_oi)}</td>
                        <td className={`py-1 px-2 text-right ${peITM ? 'bg-amber-50 dark:bg-amber-900/10' : ''}`}>
                          {row.PE && (
                          <Button
                            size="sm"
                            disabled={watchlistIds.has(row.PE.id)}
                            onClick={() => onAdd(row.PE)}
                            className={`h-6 px-3.5 shadow-none text-[10px] ${watchlistIds.has(row.PE.id) ? 'bg-secondary text-muted-foreground' : 'bg-rose-600/20 hover:bg-rose-600/20 text-rose-800 dark:text-rose-400'}`}
                          >
                            {watchlistIds.has(row.PE.id) ? 'Added' : 'Add'}
                          </Button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                  {chainData.length === 0 && !loading && selectedExpiry && (
                    <tr>
                      <td colSpan={7} className="py-10 text-center text-muted-foreground">No options found for this expiry.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ── Dropdown Search Result Item ──
function DropdownItem({ instrument, onAdd, onDetail, isInWatchlist, onOpenOptions }) {
  const isDeriv = ['FUTURE', 'OPTION'].includes(instrument.instrument_type);
  const days = daysTo(instrument.expiry_date);

  return (
    <div className="flex items-center gap-3 px-3 py-2.5 hover:bg-secondary/60 transition-colors cursor-pointer group"
      onClick={() => onDetail(instrument)}>
      {/* Type dot */}
      <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${TYPE_DOT[instrument.instrument_type] || 'bg-muted'}`} />

      {/* Main info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-semibold text-foreground">{instrument.symbol}</span>
          {instrument.option_type && instrument.option_type !== 'XX' && (
            <span className={`text-[10px] font-bold ${instrument.option_type === 'CE' ? 'text-emerald-800 dark:text-emerald-400' : 'text-rose-800 dark:text-rose-400'}`}>
              {instrument.option_type}
            </span>
          )}
          {instrument.strike_price > 0 && (
            <span className="text-[11px] text-muted-foreground">₹{instrument.strike_price}</span>
          )}
        </div>
        <p className="text-xs text-muted-foreground truncate">{instrument.name}</p>
      </div>

      {/* Meta */}
      <div className="flex items-center gap-2 shrink-0">
        {instrument.previous_close && (
          <span className="text-[11px] text-foreground font-mono hidden sm:inline">{fmt(instrument.previous_close)}</span>
        )}
        {instrument.lot_size > 1 && (
          <span className="text-[10px] text-muted-foreground font-mono">Lot:{instrument.lot_size}</span>
        )}
        {isDeriv && days !== null && (
          <span className="text-[10px] text-warning font-mono">{days}d</span>
        )}
        <span className="text-[10px] font-medium text-muted-foreground">{instrument.exchange}</span>
        {instrument.is_mtf_tradable && (
          <span className="text-[9px] text-teal-700 dark:text-teal-400 font-bold tracking-wider">MTF</span>
        )}
      </div>

      <div className="flex items-center gap-1.5 ml-2">
        {/* Option Chain button */}
        {instrument.has_options && (
          <Button
            size="sm"
            variant="outline"
            onClick={(e) => { e.stopPropagation(); onOpenOptions(instrument); }}
            className="h-6 px-2 text-[10px] border-indigo-500/30 text-indigo-700 dark:text-indigo-400 hover:bg-indigo-500/10 hover:text-indigo-800 dark:hover:text-indigo-300"
            title="View Options Chain"
          >
            Options
          </Button>
        )}

        {/* Add button */}
        <Button
          size="sm"
          disabled={isInWatchlist}
          onClick={(e) => { e.stopPropagation(); onAdd(instrument); }}
          className={`h-6 w-6 p-0 shrink-0 transition-all ${
            isInWatchlist
              ? 'bg-muted text-muted-foreground cursor-not-allowed'
              : 'bg-emerald-700 hover:bg-emerald-800 text-white opacity-100'
          }`}
          title={isInWatchlist ? 'Already in watchlist' : 'Add to watchlist'}
        >
          {isInWatchlist ? <span className="text-[9px]">✓</span> : <Plus className="h-3 w-3" />}
        </Button>
      </div>
    </div>
  );
}

// ── Watchlist Card ──
function WatchlistCard({ item, onRemove, onDetail, onOpenOptions, onOpenRouting }) {
  const d = item.instrument_details;
  if (!d) return null;
  const isDeriv = ['FUTURE', 'OPTION'].includes(d.instrument_type);
  const days = daysTo(d.expiry_date);
  const routesCount = item.execution_routes?.length || 0;

  return (
    <div
      className="relative p-3 rounded-xl bg-card/60 border border-border/50 hover:border-border/70 transition-all cursor-pointer group"
      onClick={() => onDetail(d)}
    >
      {/* Type indicator line */}
      <div className={`absolute left-0 top-3 bottom-3 w-0.5 rounded-full ${TYPE_DOT[d.instrument_type] || 'bg-muted'}`} />

      {/* Remove button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={(e) => { e.stopPropagation(); onRemove(item.id); }}
        className="absolute top-1.5 right-1.5 text-foreground hover:text-rose-800 dark:hover:text-rose-400 hover:bg-rose-500/10 h-5 w-5 p-0 opacity-100 transition-opacity"
      >
        <X className="h-2.5 w-2.5" />
      </Button>

      {/* Routing Settings Button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={(e) => { e.stopPropagation(); onOpenRouting(item); }}
        className={`absolute top-1.5 right-8 h-5 px-1.5 text-[10px] rounded transition-all ${
          routesCount > 0 
            ? 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 hover:bg-indigo-500/20 opacity-100 border border-indigo-500/20' 
            : 'text-foreground hover:text-indigo-800 dark:hover:text-indigo-400 hover:bg-indigo-500/10 opacity-100'
        }`}
        title="Execution Routing Settings"
      >
        <GitMerge className="h-3 w-3 mr-1" />
        {routesCount > 0 ? `${routesCount} Route${routesCount > 1 ? 's' : ''}` : 'Routing'}
      </Button>

      <div className="pl-2.5">
        {/* Symbol row */}
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-semibold text-foreground">{d.symbol}</span>
          {d.option_type && d.option_type !== 'XX' && (
            <span className={`text-[10px] font-bold ${d.option_type === 'CE' ? 'text-emerald-800 dark:text-emerald-400' : 'text-rose-800 dark:text-rose-400'}`}>
              {d.option_type}
            </span>
          )}
        </div>

        {/* Tags row */}
        <div className="flex items-center gap-1.5 flex-wrap mb-2">
          <span className="text-[10px] font-medium text-muted-foreground">{d.exchange}</span>
          <span className="text-foreground">·</span>
          <Badge className={`text-[9px] px-1.5 py-0 border ${TYPE_COLORS[d.instrument_type] || ''}`}>
            {d.instrument_type}
          </Badge>
          {d.lot_size > 1 && (
            <>
              <span className="text-foreground">·</span>
              <span className="text-[10px] text-muted-foreground font-mono">Lot:{d.lot_size}</span>
            </>
          )}
          {isDeriv && days !== null && (
            <>
              <span className="text-foreground">·</span>
              <span className={`text-[10px] font-mono ${days <= 7 ? 'text-rose-800 dark:text-rose-400' : 'text-warning'}`}>
                {days}d exp
              </span>
            </>
          )}
        </div>

        {/* Price & Options Button */}
        <div className="flex items-center justify-between mt-1 h-5">
          {d.previous_close && (
            <span className="text-xs text-foreground font-mono">{fmt(d.previous_close)}</span>
          )}
          {d.has_options && (
            <Button
              size="sm"
              variant="outline"
              onClick={(e) => { e.stopPropagation(); onOpenOptions(d); }}
              className="h-5 px-1.5 text-[9px] border-indigo-500/30 text-indigo-700 dark:text-indigo-400 hover:bg-indigo-500/10 opacity-100 transition-opacity"
            >
              Option Chain
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Component ──
export default function AssetRulesEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { setPageHeader } = usePageActions();
  const { enums } = useEnums();
  const typeFilters = [
    { key: '', label: 'All' },
    ...(enums.InstrumentType || []).map((type) => ({
      key: type.value,
      label: TYPE_LABELS[type.value] || type.label,
    })),
  ];
  const exchangeFilters = ['', ...(enums.Exchange || []).map(({ value }) => value)];

  const [strategy, setStrategy] = useState(null);
  const [watchlist, setWatchlist] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [showDropdown, setShowDropdown] = useState(false);
  const [typeFilter, setTypeFilter] = useState('');
  const [exchangeFilter, setExchangeFilter] = useState('');
  const [detailInstrument, setDetailInstrument] = useState(null);
  const [optionChainUnderlying, setOptionChainUnderlying] = useState(null);
  const [routingInstrument, setRoutingInstrument] = useState(null);

  const { results: searchResults, loading: searching, error: searchError } = useInstrumentSearch(
    searchQuery, { type: typeFilter, exchange: exchangeFilter }, showDropdown);
  const dropdownRef = useRef(null);
  const inputRef = useRef(null);

  // Watchlist IDs for quick lookup
  const watchlistIds = useMemo(() =>
    new Set(watchlist.map(w => w.instrument_details?.id || w.instrument)),
    [watchlist]
  );

  // Stats
  const stats = useMemo(() => {
    const c = {};
    watchlist.forEach(w => {
      const t = w.instrument_details?.instrument_type || 'OTHER';
      c[t] = (c[t] || 0) + 1;
    });
    return c;
  }, [watchlist]);

  // Filtered Watchlist
  const filteredWatchlist = useMemo(() => {
    return watchlist.filter(w => {
      const i = w.instrument_details;
      if (!i) return false;
      if (typeFilter && i.instrument_type !== typeFilter) return false;
      if (exchangeFilter && i.exchange !== exchangeFilter) return false;
      return true;
    });
  }, [watchlist, typeFilter, exchangeFilter]);

  useEffect(() => { if (id) fetchData(); }, [id]);

  useEffect(() => {
    setPageHeader(<StrategyConfigNav strategy={strategy} />);
    return () => setPageHeader(null);
  }, [strategy, setPageHeader]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [s, w] = await Promise.all([
        strategyApi.getById(id),
        watchlistApi.getByStrategy(id)
      ]);
      setStrategy(s);
      setWatchlist(w);
    } catch (error) { notify.error(getApiErrorMessage(error, 'Failed to load asset settings')); }
    finally { setLoading(false); }
  };

  const handleQueryChange = (value) => { setSearchQuery(value); setShowDropdown(true); };

  const handleAdd = async (instrument) => {
    try {
      const added = await watchlistApi.add(id, instrument.id);
      setWatchlist(prev => [...prev, added]);
      notify.success(`${instrument.symbol} added`);
    } catch (error) { notify.error(getApiErrorMessage(error, 'Failed to add instrument')); }
  };

  const handleRemove = async (wlId) => {
    try {
      await watchlistApi.remove(wlId);
      setWatchlist(prev => prev.filter(w => w.id !== wlId));
      notify.success('Removed');
    } catch (error) { notify.error(getApiErrorMessage(error, 'Failed to remove instrument')); }
  };

  if (loading) return (
    <div className="flex flex-col justify-center items-center h-96 gap-3">
      <GlobalLoader />
      <p className="text-sm text-muted-foreground">Loading assets...</p>
    </div>
  );

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto scrollbar-theme">
        <div className="container-padding py-3 lg:py-4 space-y-5">

          {/* ━━ Search Section ━━ */}
          <div className="space-y-3">
            {/* Header row with filters */}
            <div className="flex items-center justify-between gap-3 flex-wrap">
              
              {/* Type filter chips */}
              <div className="flex items-center gap-1 flex-wrap">
                {typeFilters.map(f => (
                  <button
                    key={f.key}
                    onClick={() => setTypeFilter(f.key)}
                    className={`px-3 py-1 rounded-full text-[12px] font-medium transition-all border ${
                      typeFilter === f.key
                        ? 'bg-blue-600/20 text-blue-700 dark:text-blue-400 border-blue-500/30'
                        : 'bg-transparent text-muted-foreground border-border/60 hover:border-border hover:text-muted-foreground'
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
              {/* Exchange pills */}
              <div className="flex items-center gap-0.5 bg-secondary/40 rounded-lg p-0.5">
                {exchangeFilters.map(ex => (
                  <button
                    key={ex}
                    onClick={() => setExchangeFilter(ex)}
                    className={`px-2.5 py-1 rounded-md text-[12px] font-semibold transition-all ${
                      exchangeFilter === ex
                        ? 'bg-muted text-foreground shadow-sm'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {ex || 'All'}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-blue-500/10">
                <Search className="h-4 w-4 text-blue-700 dark:text-blue-400" />
              </div>
              <h2 className="text-foreground font-semibold text-sm">Find Instruments</h2>
            </div>

            {/* Search input with dropdown */}
            <div className="relative" ref={dropdownRef}>
              <div className="relative">
                {searching ? (
                  <Loader2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-blue-700 dark:text-blue-400 animate-spin" />
                ) : (
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                )}
                <Input
                  ref={inputRef}
                  value={searchQuery}
                  onChange={(e) => handleQueryChange(e.target.value)}
                  onFocus={() => setShowDropdown(true)}
                  onKeyDown={(e) => e.key === 'Escape' && setShowDropdown(false)}
                  placeholder="Search by symbol or name..."
                  className="bg-card/60 border-border/80 text-foreground pl-10 pr-8 h-10 placeholder:text-muted-foreground focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 rounded-xl"
                />
                {searchQuery && (
                  <button
                    onClick={() => { setSearchQuery(''); setShowDropdown(false); }}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-muted-foreground transition-colors"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>

              {/* ── Floating Dropdown Results ── */}
              {searchError && <p role="alert" className="text-sm text-rose-800 dark:text-rose-300">{searchError}</p>}
              {showDropdown && (
                <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-background border border-border/80 rounded-xl shadow-2xl shadow-black/40 max-h-80 overflow-y-auto scrollbar-theme">
                  {searchResults.length > 0 ? (
                    <>
                      <div className="px-3 py-1.5 border-b border-border/40">
                        <span className="text-[10px] text-muted-foreground">{searchResults.length} results</span>
                      </div>
                      {searchResults.map(inst => (
                        <DropdownItem
                          key={inst.id}
                          instrument={inst}
                          onAdd={handleAdd}
                          onDetail={(i) => { setDetailInstrument(i); setShowDropdown(false); }}
                          onOpenOptions={(i) => { setOptionChainUnderlying(i); setShowDropdown(false); }}
                          isInWatchlist={watchlistIds.has(inst.id)}
                        />
                      ))}
                    </>
                  ) : !searching ? (
                    <div className="px-4 py-6 text-center">
                      <Search className="h-6 w-6 text-foreground mx-auto mb-2" />
                      <p className="text-xs text-muted-foreground">No instruments found</p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">Try different keywords or filters</p>
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          </div>

          {/* ━━ Watchlist Section ━━ */}
          <div className="space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-indigo-500/10">
                  <Layers className="h-4 w-4 text-indigo-700 dark:text-indigo-400" />
                </div>
                <h2 className="text-foreground font-semibold text-sm">Trading Watchlist</h2>
                <Badge variant="outline" className="border-border/60 text-[10px] text-muted-foreground font-mono">
                  {watchlist.length}
                </Badge>
              </div>

              {/* Stats chips */}
              {Object.keys(stats).length > 0 && (
                <div className="flex items-center gap-2 flex-wrap">
                  {Object.entries(stats).map(([type, count]) => {
                    const label = typeFilters.find(f => f.key === type)?.label || type;
                    return (
                      <span key={type} className="flex items-center gap-1.5 bg-card px-2 py-0.5 rounded-md border border-border">
                        <div className={`w-1.5 h-1.5 rounded-full ${TYPE_DOT[type] || 'bg-muted'}`} />
                        <span className="text-[10px] text-muted-foreground font-medium">
                          {count} {label}
                        </span>
                      </span>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Grid */}
            {filteredWatchlist.length === 0 ? (
              <div className="text-center py-14 border border-dashed border-border/60 rounded-2xl bg-card/20">
                <Package className="h-10 w-10 text-foreground mx-auto mb-3" />
                <p className="text-muted-foreground text-sm font-medium">
                  {watchlist.length > 0 ? "No instruments match your filters" : "No instruments yet"}
                </p>
                <p className="text-xs text-muted-foreground mt-1 max-w-xs mx-auto">
                  {watchlist.length > 0 ? "Try adjusting the Exchange or Type filters above." : "Search above to find and add instruments to your trading watchlist."}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
                {filteredWatchlist.map(item => (
                  <WatchlistCard
                    key={item.id}
                    item={item}
                    onRemove={handleRemove}
                    onDetail={setDetailInstrument}
                    onOpenOptions={setOptionChainUnderlying}
                    onOpenRouting={setRoutingInstrument}
                  />
                ))}
              </div>
            )}
          </div>

        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-border/80 bg-background/80 backdrop-blur-sm px-4 lg:px-6 py-3 shrink-0 flex justify-end">
        <Button
          size="sm"
          onClick={() => navigate(`/strategies/${id}/edit`)}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs h-8 px-5"
        >
          Done
        </Button>
      </div>

      <DetailDialog
        instrument={detailInstrument}
        open={!!detailInstrument}
        onClose={() => setDetailInstrument(null)}
      />

      <OptionChainViewer
        underlying={optionChainUnderlying}
        open={!!optionChainUnderlying}
        onClose={() => setOptionChainUnderlying(null)}
        onAdd={handleAdd}
        watchlistIds={watchlistIds}
      />

      <UniversalRoutingModal
        open={!!routingInstrument}
        onClose={() => setRoutingInstrument(null)}
        watchlistInstrument={routingInstrument}
      />
    </div>
  );
}
