import { useState } from "react";
import PropTypes from "prop-types";
import { Input } from "@/shared/components/ui/input";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { useInstrumentSearch } from "@/shared/hooks/useInstrumentSearch";

export default function ResearchUniverse({ value, onChange, disabled, strategies = [] }) {
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const { results: instruments, loading, error } = useInstrumentSearch(query,
    { exchange: "NSE", type: "STOCK" }, searchOpen && !disabled && !value.strategy_id && !value.use_watchlist);
  const selected = value.instruments || [];
  return <div className="space-y-3">
    <Select resource="strategies" disabled={disabled} value={value.use_watchlist ? "watchlist" : String(value.strategy_id || "selected")} onValueChange={(id, option) => onChange({ ...value, strategy_id: ["selected", "watchlist"].includes(id) ? null : Number(id), use_watchlist: id === "watchlist", instruments: [] }, option.timeframe)}>
      <SelectTrigger><SelectValue placeholder="Choose a watchlist" /></SelectTrigger>
      <SelectContent><SelectItem persistent value="selected">Select instruments manually</SelectItem>
        <SelectItem persistent value="watchlist">Terminal watchlist</SelectItem>
        {strategies.map((strategy) => <SelectItem key={strategy.id} value={String(strategy.id)}>{strategy.name}</SelectItem>)}
      </SelectContent>
    </Select>
    {!value.strategy_id && !value.use_watchlist && <div className="space-y-3" onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setSearchOpen(false); }}>
      <Input aria-label="Search NSE instruments" placeholder="Search NSE stocks…" value={query} disabled={disabled}
        onFocus={() => setSearchOpen(true)} onChange={(event) => { setQuery(event.target.value); setSearchOpen(true); }}
        onKeyDown={(event) => { if (event.key === "Escape") setSearchOpen(false); }} />
      {loading && <p role="status" className="text-xs text-slate-400">Loading instruments…</p>}
      {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}
      {instruments.length > 0 && <div className="scrollbar-thin-theme max-h-52 overflow-y-auto rounded-lg border border-gray-800 divide-y divide-gray-800">
        {instruments.map((item) => <Button key={item.id} variant="ghost" className="w-full justify-start" disabled={disabled || selected.length >= 50 || selected.some((value) => value.id === item.id)} onClick={() => { onChange({ ...value, instruments: [...selected, item] }); setQuery(""); setSearchOpen(false); }}>{item.symbol} · {item.name}</Button>)}
      </div>}
      <div className="flex flex-wrap gap-2">{selected.map((item) => <Badge key={item.id} variant="outline"><button type="button" disabled={disabled} aria-label={`Remove ${item.symbol}`} onClick={() => onChange({ ...value, instruments: selected.filter((value) => value.id !== item.id) })}>{item.symbol} ×</button></Badge>)}</div>
    </div>}
    <p className="text-xs text-slate-500">NSE stocks · up to 50 instruments · calculations use completed candles.</p>
  </div>;
}
ResearchUniverse.propTypes = { value: PropTypes.object.isRequired, onChange: PropTypes.func.isRequired, disabled: PropTypes.bool, strategies: PropTypes.array };
