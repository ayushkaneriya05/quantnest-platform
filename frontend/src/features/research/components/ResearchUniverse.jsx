import { useState } from "react";
import PropTypes from "prop-types";
import { Input } from "@/shared/components/ui/input";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { useInstrumentSearch } from "@/shared/hooks/useInstrumentSearch";

export default function ResearchUniverse({ value, onChange, disabled, maxInstruments }) {
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const source = value.watchlist_id ? "watchlist" : value.strategy_id ? "strategy" : value.source || "manual";
  const { results: instruments, loading, error } = useInstrumentSearch(query,
    { exchange: "NSE", type: "STOCK" }, searchOpen && !disabled && source === "manual");
  const selected = value.instruments || [];
  return <div className="space-y-3">
    <Select disabled={disabled} value={source} onValueChange={(source) => onChange({ source, strategy_id: null, watchlist_id: null, instruments: [] })}>
      <SelectTrigger aria-label="Research instrument source"><SelectValue /></SelectTrigger>
      <SelectContent><SelectItem value="manual">Select instruments manually</SelectItem>
        <SelectItem value="watchlist">Terminal watchlist</SelectItem>
        <SelectItem value="strategy">Saved strategy</SelectItem>
      </SelectContent>
    </Select>
    {source === "watchlist" && <Select resource="terminal-watchlists" disabled={disabled} value={String(value.watchlist_id || "")}
      onValueChange={(id, option) => onChange({ ...value, watchlist_id: Number(id), watchlist_name: option.name, instruments: [] })}>
      <SelectTrigger aria-label="Terminal watchlist"><SelectValue placeholder="Choose a terminal watchlist" /></SelectTrigger>
      <SelectContent searchPlaceholder="Search terminal watchlists" />
    </Select>}
    {source === "strategy" && <Select resource="strategies" disabled={disabled} value={String(value.strategy_id || "")}
      onValueChange={(id, option) => onChange({ ...value, strategy_id: Number(id), instruments: [] }, option.timeframe)}>
      <SelectTrigger aria-label="Strategy"><SelectValue placeholder="Choose a strategy" /></SelectTrigger>
      <SelectContent searchPlaceholder="Search strategies" />
    </Select>}
    {source === "manual" && <div className="space-y-3" onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setSearchOpen(false); }}>
      <Input aria-label="Search NSE instruments" placeholder="Search NSE stocks…" value={query} disabled={disabled}
        onFocus={() => setSearchOpen(true)} onChange={(event) => { setQuery(event.target.value); setSearchOpen(true); }}
        onKeyDown={(event) => { if (event.key === "Escape") setSearchOpen(false); }} />
      {loading && <p role="status" className="text-xs text-muted-foreground">Loading instruments…</p>}
      {error && <p role="alert" className="text-sm text-rose-700 dark:text-rose-300">{error}</p>}
      {instruments.length > 0 && <div className="scrollbar-thin-theme max-h-52 overflow-y-auto rounded-lg border border-border divide-y divide-border">
        {instruments.map((item) => <Button key={item.id} variant="ghost" className="w-full justify-start" disabled={disabled || (maxInstruments != null && selected.length >= maxInstruments) || selected.some((value) => value.id === item.id)} onClick={() => { onChange({ ...value, instruments: [...selected, item] }); setQuery(""); setSearchOpen(false); }}>{item.symbol} · {item.name}</Button>)}
      </div>}
      <div className="flex flex-wrap gap-2">{selected.map((item) => <Badge key={item.id} variant="outline"><button type="button" disabled={disabled} aria-label={`Remove ${item.symbol}`} onClick={() => onChange({ ...value, instruments: selected.filter((value) => value.id !== item.id) })}>{item.symbol} ×</button></Badge>)}</div>
    </div>}
    <p className="text-xs text-muted-foreground">NSE stocks{maxInstruments != null ? ` · up to ${maxInstruments} per request` : ''} · calculations use completed candles.</p>
  </div>;
}
ResearchUniverse.propTypes = { value: PropTypes.object.isRequired, onChange: PropTypes.func.isRequired, disabled: PropTypes.bool, maxInstruments: PropTypes.number };
