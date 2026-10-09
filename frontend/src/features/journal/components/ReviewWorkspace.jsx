import PropTypes from "prop-types";
import { format } from "date-fns";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { TooltipHint } from "@/shared/components/ui/tooltip";
import { DatePicker } from "@/shared/components/ui/date-picker";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/shared/components/ui/table";
import { formatDateTime } from "@/shared/utils/formatters";
import { modes, displayMoney, pnlTone } from "@/features/journal/hooks/useReviewWorkspace.js";

export function SourceTabs({ source, onChange }) {
  return <div className="inline-flex shrink-0 rounded-lg border border-border bg-background p-1" role="group" aria-label="Execution source">
      {modes.map(({ value, label, icon: Icon, description }) => <TooltipHint key={value} content={description}><button type="button" aria-pressed={source === value} onClick={() => onChange(value)}
        className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset ${source === value ? "bg-indigo-500/20 text-indigo-700 dark:text-indigo-200" : "text-muted-foreground hover:bg-card hover:text-foreground"}`}>
        <Icon size={14} />{label}
      </button></TooltipHint>)}
  </div>;
}
SourceTabs.propTypes = { source: PropTypes.string.isRequired, onChange: PropTypes.func.isRequired };

export function ReviewFilters({ filters, onChange, journal = false }) {
  const columns = filters.source === "TERMINAL" ? (journal ? "xl:grid-cols-4" : "xl:grid-cols-3") : (journal ? "xl:grid-cols-6" : "xl:grid-cols-5");
  return <section aria-label="Execution filters" className={`grid gap-2 rounded-xl border border-border bg-background/70 p-3 sm:grid-cols-2 [&_input]:h-9 [&_input]:text-xs [&_button[role=combobox]]:h-9 [&_button[role=combobox]]:text-xs ${columns}`}>
    <div className="relative"><Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" /><Input aria-label="Search instruments" placeholder="Search instrument…" value={filters.search || ""} onChange={(event) => onChange({ search: event.target.value })} className="pl-9" /></div>
    {filters.source !== "TERMINAL" && <Select resource={filters.source === "PAPER" ? "paper-accounts" : "broker-accounts"} value={filters.account_id || "all"} onValueChange={(value) => onChange({ account_id: value === "all" ? "" : value })}>
      <SelectTrigger aria-label="Account"><SelectValue placeholder="All accounts" /></SelectTrigger><SelectContent><SelectItem persistent value="all">All accounts</SelectItem></SelectContent>
    </Select>}
    {filters.source !== "TERMINAL" && <Select resource="strategies" value={filters.strategy_id || "all"} onValueChange={(value) => onChange({ strategy_id: value === "all" ? "" : value })}>
      <SelectTrigger aria-label="Strategy"><SelectValue placeholder="All strategies" /></SelectTrigger><SelectContent><SelectItem persistent value="all">All strategies</SelectItem></SelectContent>
    </Select>}
    <DatePicker className="h-9 px-3 text-xs" date={new Date(filters.date_from + "T00:00:00")} setDate={(date) => { if (date) onChange({ date_from: format(date, "yyyy-MM-dd") }); }} placeholder="From date" />
    <DatePicker className="h-9 px-3 text-xs" date={new Date(filters.date_to + "T00:00:00")} setDate={(date) => { if (date) onChange({ date_to: format(date, "yyyy-MM-dd") }); }} placeholder="To date" />
    {journal && <Select value={filters.reviewed || "all"} onValueChange={(reviewed) => onChange({ reviewed })}>
      <SelectTrigger aria-label="Review status"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All closes</SelectItem><SelectItem value="reviewed">Reviewed</SelectItem><SelectItem value="unreviewed">Unreviewed</SelectItem></SelectContent>
    </Select>}
  </section>;
}
ReviewFilters.propTypes = { filters: PropTypes.object.isRequired, onChange: PropTypes.func.isRequired, journal: PropTypes.bool };

export function MetricCard({ label, value, hint, tone = "text-foreground" }) {
  return <div className="min-w-0 rounded-xl border border-border bg-gradient-to-br from-background/70 to-background p-3 sm:p-4">
    <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
    <p className={`mt-1 text-xl font-semibold tabular-nums ${tone}`}>{value}</p>
    {hint && <p className="mt-1 text-[11px] leading-4 text-muted-foreground">{hint}</p>}
  </div>;
}
MetricCard.propTypes = { label: PropTypes.string.isRequired, value: PropTypes.node, hint: PropTypes.string, tone: PropTypes.string };

export function TradeTable({ trades, page, onPage, onReview, loading }) {
  return <section className="overflow-hidden rounded-2xl border border-border bg-background/60">
    <div className="flex items-center justify-between border-b border-border px-5 py-4"><h2 className="font-semibold">Recorded closes</h2><span className="text-xs text-muted-foreground">{trades?.count || 0} records</span></div>
    <Table><TableHeader><TableRow><TableHead>Instrument / account</TableHead><TableHead>Entry → exit</TableHead><TableHead>Qty / side</TableHead><TableHead>Prices</TableHead><TableHead>Realized P&L</TableHead><TableHead>Charges</TableHead><TableHead>Review</TableHead></TableRow></TableHeader>
      <TableBody>{loading ? <TableRow><TableCell colSpan={7} className="py-12 text-center text-muted-foreground">Loading execution records…</TableCell></TableRow> : !trades?.results?.length ? <TableRow><TableCell colSpan={7} className="py-12 text-center text-muted-foreground">No closes match these filters.</TableCell></TableRow> : trades.results.map((trade) => <TableRow key={trade.id}>
        <TableCell><p className="font-semibold text-foreground">{trade.symbol}</p><p className="mt-1 text-xs text-muted-foreground">{trade.strategy_name || "Strategy unavailable"}</p><p className="mt-1 text-xs text-muted-foreground">{trade.account_name || "Account unavailable"}</p></TableCell>
        <TableCell className="whitespace-nowrap text-xs"><p>{formatDateTime(trade.entry_time)}</p><p className="mt-1 text-muted-foreground">{formatDateTime(trade.exit_time)}</p></TableCell>
        <TableCell><p>{trade.quantity}</p><span className="text-xs text-muted-foreground">{trade.side}</span></TableCell>
        <TableCell className="whitespace-nowrap text-xs"><p>{displayMoney(trade.entry_price)}</p><p className="mt-1 text-muted-foreground">{displayMoney(trade.exit_price)}</p></TableCell>
        <TableCell className={`whitespace-nowrap font-semibold tabular-nums ${pnlTone(trade.pnl)}`}>{displayMoney(trade.pnl)}</TableCell>
        <TableCell className="text-muted-foreground">{displayMoney(trade.charges)}</TableCell>
        <TableCell><Button size="sm" variant={trade.review ? "outline" : "secondary"} onClick={() => onReview(trade)}>{trade.review ? "View review" : "Review"}</Button></TableCell>
      </TableRow>)}</TableBody>
    </Table>
    <div className="flex items-center justify-between border-t border-border px-4 py-3 text-xs text-muted-foreground"><span>Partial exits are separate closes.</span><div className="flex items-center gap-2">
      <Button size="icon" variant="ghost" disabled={loading || page <= 1} onClick={() => onPage(page - 1)} aria-label="Previous page"><ChevronLeft size={16} /></Button><span>Page {page}</span>
      <Button size="icon" variant="ghost" disabled={loading || !trades?.next} onClick={() => onPage(page + 1)} aria-label="Next page"><ChevronRight size={16} /></Button>
    </div></div>
  </section>;
}
TradeTable.propTypes = { trades: PropTypes.object, page: PropTypes.number.isRequired, onPage: PropTypes.func.isRequired, onReview: PropTypes.func.isRequired, loading: PropTypes.bool };
