import { useEffect, useId, useState } from "react";
import PropTypes from "prop-types";
import { ChevronsLeft, ChevronLeft, ChevronRight, ChevronsRight } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { useEnums } from "@/shared/context/EnumsContext";
import { formatNumber } from "@/shared/utils/formatters";

const integer = value => formatNumber(value, { maximumFractionDigits: 0 });

export default function Pagination({ page = 1, pageSize, count = 0, onPageChange, onPageSizeChange, loading = false, compact = false, label = "Record pages" }) {
  const { enums } = useEnums();
  const size = pageSize || enums.PaginationDefaults?.page_size;
  const pages = size ? Math.max(1, Math.ceil(count / size)) : 1;
  const [input, setInput] = useState(String(page));
  const [error, setError] = useState("");
  const id = useId();
  useEffect(() => { setInput(String(page)); setError(""); }, [page, size]);
  const jump = event => {
    event.preventDefault();
    if (loading) return;
    const value = Number(input);
    if (!/^\d+$/.test(input) || !Number.isSafeInteger(value) || value < 1 || value > pages) {
      setError(`Enter a page from 1 to ${integer(pages)}.`);
      return;
    }
    setError("");
    if (value !== page) onPageChange(value);
  };
  return <nav aria-label={label} aria-busy={loading} className="flex min-w-0 flex-wrap items-center justify-between gap-2 border-t border-border px-3 py-2 text-xs">
    <span role="status" aria-live="polite" className="text-muted-foreground tabular-nums">
      {loading ? "Updating…" : count ? `${integer((page - 1) * size + 1)}–${integer(Math.min(page * size, count))} of ${integer(count)}${compact ? "" : " records"}` : "0 records"}
    </span>
    <div className="flex flex-wrap items-center gap-2">
      {onPageSizeChange && size && <label className="flex items-center gap-2"><span className={compact ? "sr-only" : ""}>Rows</span><Select value={String(size)} onValueChange={value => onPageSizeChange(Number(value))} disabled={loading}><SelectTrigger className="w-20" aria-label="Rows per page"><SelectValue /></SelectTrigger><SelectContent>{enums.PaginationDefaults.page_sizes.map(value => <SelectItem key={value} value={String(value)}>{integer(value)}</SelectItem>)}</SelectContent></Select></label>}
      <div className="flex items-center gap-1">
        {!compact && <Button size="icon" variant="ghost" title="First page" disabled={loading || page <= 1} onClick={() => onPageChange(1)}><ChevronsLeft size={16} /></Button>}
        <Button size="icon" variant="ghost" title="Previous page" disabled={loading || page <= 1} onClick={() => onPageChange(page - 1)}><ChevronLeft size={16} /></Button>
        <form onSubmit={jump} className="flex items-center gap-1.5"><label htmlFor={id}>Page</label><Input id={id} inputMode="numeric" autoComplete="off" className="w-14 px-1 text-center tabular-nums" value={input} disabled={!count} readOnly={loading} aria-disabled={loading || !count} aria-invalid={!!error} aria-describedby={error ? `${id}-error` : undefined} onChange={event => { setInput(event.target.value); setError(""); }} onKeyDown={event => { if (event.key === "Escape") { setInput(String(page)); setError(""); } }} /><span className="whitespace-nowrap text-muted-foreground">of {integer(pages)}</span></form>
        <Button size="icon" variant="ghost" title="Next page" disabled={loading || page >= pages} onClick={() => onPageChange(page + 1)}><ChevronRight size={16} /></Button>
        {!compact && <Button size="icon" variant="ghost" title="Last page" disabled={loading || page >= pages} onClick={() => onPageChange(pages)}><ChevronsRight size={16} /></Button>}
      </div>
    </div>
    {error && <span id={`${id}-error`} role="alert" className="w-full text-destructive">{error}</span>}
  </nav>;
}

Pagination.propTypes = { page: PropTypes.number, pageSize: PropTypes.number, count: PropTypes.number, onPageChange: PropTypes.func.isRequired, onPageSizeChange: PropTypes.func, loading: PropTypes.bool, compact: PropTypes.bool, label: PropTypes.string };
