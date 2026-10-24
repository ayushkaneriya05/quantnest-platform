import { useCallback, useEffect, useRef, useState } from 'react';
import { CandlestickChart, History, Wallet, List, RefreshCw, PanelBottomClose, PanelBottomOpen, GripHorizontal, GripVertical } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/shared/components/ui/tabs';
import { Dialog, DialogContent, DialogTitle } from '@/shared/components/ui/dialog';
import RouteLoading from '@/shared/components/RouteLoading';
import { usePageActions } from '@/shared/context/pageActions';
import { useEnums } from '@/shared/context/EnumsContext';
import { useWebSocket } from '@/shared/hooks/useWebSocket';
import ChartView from '../components/ChartView';
import Watchlist from '../components/Watchlist';
import OrderTicket from '../components/OrderTicket';
import TerminalBlotter from '../components/TerminalBlotter';
import HistoryDisplay from '../components/HistoryDisplay';
import AccountSummary from '../components/AccountSummary';
import WatchlistPicker from '../components/WatchlistPicker';
import useTradingTerminal from '../hooks/useTradingTerminal';

const VIEWS = [
  { value: 'workspace', label: 'Trade', icon: CandlestickChart },
  { value: 'history', label: 'History', icon: History },
  { value: 'account', label: 'Account', icon: Wallet },
];

export default function TradingTerminal() {
  const terminal = useTradingTerminal();
  const { account, positions, openOrders, selectedInstrument, selectedSymbol, refreshSnapshot } = terminal;
  const { values, loading: loadingEnums, error: enumError, refreshEnums } = useEnums();
  const [view, setView] = useState('workspace'), [side, setSide] = useState('');
  const [watchlistOpen, setWatchlistOpen] = useState(false), [ticketOpen, setTicketOpen] = useState(false);
  const [bottomOpen, setBottomOpen] = useState(true);
  const [bottomHeight, setBottomHeight] = useState(() => Number(localStorage.getItem('terminal.panelHeight')) || 240);
  const [watchlistWidth, setWatchlistWidth] = useState(() => Number(localStorage.getItem('terminal.watchlistWidth')) || 240);
  const [session, setSession] = useState(null), [draft, setDraft] = useState(null);
  const workspace = useRef(null), row = useRef(null), drag = useRef(null);
  const { isConnected } = useWebSocket();
  const { setPageHeader, clearPageHeader } = usePageActions();
  const buy = values.Side?.BUY, sell = values.Side?.SELL;
  const trade = useCallback((value) => {
    if (!value) return;
    setSide(value); setView('workspace');
    if (window.innerWidth < 1280) setTicketOpen(true);
  }, []);
  useEffect(() => {
    setPageHeader(<div className="flex min-w-0 flex-wrap items-center gap-2">
      <span className="sr-only">Trading Terminal</span>
      <Tabs value={view} onValueChange={setView}>
        <TabsList className="h-10" aria-label="Trading terminal">
          {VIEWS.map(({ value, label, icon: Icon }) => <TabsTrigger key={value} value={value}
            id={'terminal-tab-' + value} aria-controls={'terminal-panel-' + value} className="gap-2 px-2 sm:px-3">
            <Icon className="hidden h-4 w-4 sm:block" />{label}</TabsTrigger>)}
        </TabsList>
      </Tabs>
      <div className="ml-auto flex items-center gap-1">
        <span className="mr-2 hidden items-center gap-1.5 text-xs text-muted-foreground md:flex">
          <span className={'h-1.5 w-1.5 rounded-full ' + (isConnected ? 'bg-emerald-500' : 'bg-amber-500')} />
          {isConnected ? 'Connected' : 'Reconnecting'}
        </span>
        {view === 'workspace' && <>
          <Button size="icon" variant="ghost" className="h-8 w-8 lg:hidden" aria-label="Open watchlist" onClick={() => setWatchlistOpen(true)}><List className="h-4 w-4" /></Button>
          <Button size="icon" variant="ghost" className="h-8 w-8" aria-label="Toggle order panel" onClick={() => setBottomOpen((value) => !value)}>
            {bottomOpen ? <PanelBottomClose className="h-4 w-4" /> : <PanelBottomOpen className="h-4 w-4" />}
          </Button>
        </>}
        <Button size="icon" variant="ghost" className="h-8 w-8" aria-label="Refresh terminal" onClick={refreshSnapshot}><RefreshCw className="h-4 w-4" /></Button>
      </div>
    </div>);
  }, [setPageHeader, view, isConnected, bottomOpen, refreshSnapshot]);
  useEffect(() => clearPageHeader, [clearPageHeader]);
  useEffect(() => {
    const handle = (event) => {
      if (['INPUT','TEXTAREA','SELECT'].includes(event.target.tagName) || event.target.closest('[role="dialog"],[role="combobox"],[role="listbox"]') || event.target.isContentEditable || event.ctrlKey || event.metaKey || event.altKey) return;
      if (event.key.toLowerCase() === 'b') trade(buy);
      if (event.key.toLowerCase() === 's') trade(sell);
    };
    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [trade, buy, sell]);

  // Both handles use pointer capture, keyboard arrows and persisted dimensions.
  const resizeHandle = (panel) => {
    const vertical = panel === 'bottom';
    const size = vertical ? bottomHeight : watchlistWidth;
    const axis = vertical ? 'clientY' : 'clientX';
    const update = (next) => {
      const maximum = vertical ? (workspace.current?.clientHeight || 600) - 270
        : Math.min(420, (row.current?.clientWidth || 1000) * 0.35,
          (row.current?.clientWidth || 1000) - (window.innerWidth >= 1280 ? 650 : 360));
      const value = Math.round(Math.max(vertical ? 130 : 200, Math.min(next, maximum)));
      (vertical ? setBottomHeight : setWatchlistWidth)(value);
      return value;
    };
    return {
      role: 'separator', tabIndex: 0, 'aria-orientation': vertical ? 'horizontal' : 'vertical',
      'aria-label': vertical ? 'Resize positions and orders panel' : 'Resize watchlist',
      'aria-valuenow': size, 'aria-valuemin': vertical ? 130 : 200,
      onPointerDown: (event) => {
        if (event.button !== 0) return;
        event.preventDefault(); drag.current = { panel, origin: event[axis], size };
        event.currentTarget.setPointerCapture(event.pointerId);
      },
      onPointerMove: (event) => {
        if (drag.current?.panel === panel) update(drag.current.size + (event[axis] - drag.current.origin) * (vertical ? -1 : 1));
      },
      onPointerUp: (event) => {
        drag.current = null;
        if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
        localStorage.setItem(vertical ? 'terminal.panelHeight' : 'terminal.watchlistWidth', String(size));
      },
      onPointerCancel: () => { drag.current = null; },
      onKeyDown: (event) => {
        const keys = vertical ? ['ArrowDown', 'ArrowUp'] : ['ArrowLeft', 'ArrowRight'];
        if (keys.includes(event.key)) {
          event.preventDefault();
          const value = update(size + (event.key === keys[0] ? -24 : 24));
          localStorage.setItem(vertical ? 'terminal.panelHeight' : 'terminal.watchlistWidth', String(value));
        }
      },
    };
  };
  const select = (symbol) => { terminal.setSelectedSymbol(symbol); setWatchlistOpen(false); setSession(null); setDraft(null); };
  const selectPrice = useCallback((value) => { setDraft(value); if (window.innerWidth < 1280) setTicketOpen(true); }, []);
  if (loadingEnums) return <RouteLoading />;
  if (enumError) return <div className="space-y-3 p-6"><p className="text-sm text-muted-foreground">Could not load trading choices.</p><Button variant="outline" onClick={refreshEnums}>Retry</Button></div>;

  const ticket = <OrderTicket instrument={selectedInstrument} account={account} side={side || buy} onSideChange={setSide}
    session={session} draft={draft} onOrderPlaced={() => setTicketOpen(false)} />;
  const watchlist = <div className="flex h-full min-h-0 flex-col gap-2">
    <WatchlistPicker lists={terminal.watchlists} activeId={terminal.watchlistId} onChange={terminal.setWatchlistId} onRefresh={refreshSnapshot} />
    <div className="min-h-0 flex-1"><Watchlist items={terminal.watchlist} loading={terminal.loading} activeSymbol={selectedSymbol}
      onSymbolSelect={select} onAddToWatchlist={terminal.addToWatchlist} onRemoveFromWatchlist={terminal.removeFromWatchlist} /></div>
  </div>;
  return <div role="tabpanel" id={'terminal-panel-' + view} aria-labelledby={'terminal-tab-' + view}
    className="flex min-h-0 min-w-0 flex-1 flex-col p-3 outline-none sm:p-4" tabIndex={0}>
    {view === 'workspace' && <div ref={workspace} className="flex min-h-0 flex-1 flex-col">
      <div ref={row} className="flex min-h-[270px] flex-1 gap-3">
        <aside className="hidden min-w-0 shrink-0 lg:block" style={{ width: watchlistWidth, maxWidth: '35%' }}>{watchlist}</aside>
        <div {...resizeHandle('watchlist')} className="group -mx-2 hidden w-2 shrink-0 touch-none cursor-col-resize items-center justify-center rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring lg:flex">
          <GripVertical className="h-6 w-2 rounded-full text-muted-foreground group-hover:bg-primary/20 group-hover:text-primary" />
        </div>
        <div className="min-w-0 flex-1"><ChartView symbol={selectedSymbol} instrument={selectedInstrument}
          onBuyClick={() => trade(buy)} onSellClick={() => trade(sell)} onSessionChange={setSession} onPriceSelect={selectPrice} className="h-full" /></div>
        <aside className="scrollbar-thin-theme hidden w-[290px] shrink-0 overflow-y-auto rounded-xl border bg-card xl:block">{ticket}</aside>
      </div>
      {bottomOpen && <>
        <div {...resizeHandle('bottom')} className="group flex h-4 shrink-0 touch-none cursor-row-resize items-center justify-center rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <span className="flex h-2 items-center rounded-full bg-muted px-3 transition-colors group-hover:bg-primary/20"><GripHorizontal className="h-3 w-4 text-muted-foreground group-hover:text-primary" /></span>
        </div>
        <div className="flex min-h-[130px] min-w-0 shrink-0" style={{ height: bottomHeight, maxHeight: '55%' }}>
          <TerminalBlotter positions={positions} orders={openOrders} onSelect={select} />
        </div>
      </>}
    </div>}
    {view === 'history' && <div className="scrollbar-theme min-h-0 flex-1 overflow-auto"><HistoryDisplay /></div>}
    {view === 'account' && <div className="scrollbar-theme min-h-0 flex-1 overflow-auto">
      {account && <AccountSummary account={account} positions={positions} onSaved={refreshSnapshot} />}
    </div>}
    <Dialog open={watchlistOpen} onOpenChange={setWatchlistOpen}><DialogContent aria-describedby={undefined} className="flex h-[80dvh] flex-col">
      <DialogTitle>Watchlist</DialogTitle><div className="min-h-0 flex-1">{watchlist}</div></DialogContent></Dialog>
    <Dialog open={ticketOpen} onOpenChange={setTicketOpen}><DialogContent aria-describedby={undefined} className="max-h-[90dvh] overflow-auto p-0 sm:max-w-sm">
      <DialogTitle className="sr-only">Simulated order</DialogTitle>{ticket}</DialogContent></Dialog>
  </div>;
}
