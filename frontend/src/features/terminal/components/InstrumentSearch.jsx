import { GlobalLoader } from "@/shared/components/ui/global-loader";
import PropTypes from "prop-types";
import { useEnums } from "@/shared/context/EnumsContext";
import { useState } from "react";
import { Search, Plus } from "lucide-react";
import { DatePicker } from "@/shared/components/ui/date-picker";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import {
  formatDate,
  formatDateInput,
  formatNumber,
} from "@/shared/utils/formatters";
import { Input } from "@/shared/components/ui/input";
import { Button } from "@/shared/components/ui/button";
import { Switch } from "@/shared/components/ui/switch";
import { Radio } from "@/shared/components/ui/radio";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { useInstrumentSearch } from "@/shared/hooks/useInstrumentSearch";
import { searchTerminalInstruments } from "@/shared/services/instrumentsApi";

export default function InstrumentSearch({
  onAddToWatchlist,
  existingWatchlistSymbols = [],
  allowHistorical = false,
  label = "Add instruments",
  triggerClassName = "w-full justify-start",
  modes = [],
  getDisabledReason,
}) {
  const { enums } = useEnums();
  const [query, setQuery] = useState(""),
    [open, setOpen] = useState(false);
  const [mode, setMode] = useState(modes[0]?.value || "");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [exchange, setExchange] = useState("all"),
    [instrumentType, setInstrumentType] = useState("all"),
    [expiry, setExpiry] = useState(null);
  const { results, loading, error } = useInstrumentSearch(
    query,
    {
      ...(allowHistorical && includeArchived ? { include_archived: true } : {}),
      ...(exchange !== "all" ? { exchange } : {}),
      ...(instrumentType !== "all" ? { instrument_type: instrumentType } : {}),
      ...(expiry ? { expiry_date: formatDateInput(expiry) } : {}),
    },
    open,
    searchTerminalInstruments,
  );
  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className={triggerClassName}
        onClick={() => setOpen(true)}
      >
        <Search className="mr-2 h-4 w-4" />
        {label}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          aria-describedby={undefined}
          className="instrument-search-dialog flex max-h-[85dvh] flex-col gap-3 overflow-hidden sm:max-w-xl"
        >
          <DialogTitle>Find an instrument or contract</DialogTitle>
          {modes.length > 0 && (
            <fieldset className="flex flex-wrap gap-3 text-sm">
              <legend className="sr-only">Selection method</legend>
              {modes.map((item) => (
                <label
                  key={item.value}
                  className="flex min-h-9 items-center gap-2"
                >
                  <Radio
                    name="instrument-selection-mode"
                    value={item.value}
                    checked={mode === item.value}
                    onChange={() => setMode(item.value)}
                  />
                  {item.label}
                </label>
              ))}
            </fieldset>
          )}
          <Input
            autoFocus
            aria-label="Search instruments"
            placeholder="Symbol, company, underlying or contract ticker"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="grid grid-cols-3 gap-2">
            <Select value={exchange} onValueChange={setExchange}>
              <SelectTrigger aria-label="Exchange">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All exchanges</SelectItem>
                {enums.Exchange.map((choice) => (
                  <SelectItem key={choice.value} value={choice.value}>
                    {choice.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={instrumentType} onValueChange={setInstrumentType}>
              <SelectTrigger aria-label="Instrument type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All instruments</SelectItem>
                {enums.InstrumentType.map((choice) => (
                  <SelectItem key={choice.value} value={choice.value}>
                    {choice.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <DatePicker
              date={expiry}
              setDate={setExpiry}
              placeholder="Any expiry"
            />
          </div>
          {(expiry || exchange !== "all" || instrumentType !== "all") && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setExpiry(null);
                setExchange("all");
                setInstrumentType("all");
              }}
            >
              Clear filters
            </Button>
          )}
          <p className="text-xs text-muted-foreground">
            First 50 matches. Narrow options by underlying, expiry and strike in
            the search. Indices are available for analysis, not orders.
          </p>
          {allowHistorical && (
            <label className="flex items-center gap-2 text-sm">
              <Switch
                checked={includeArchived}
                onCheckedChange={setIncludeArchived}
              />
              Include expired and archived instruments for backtesting
            </label>
          )}
          {allowHistorical && includeArchived && (
            <p className="text-xs text-muted-foreground">
              Historical derivatives need sourced contract terms and confirmed
              candles for the requested dates. Archived contracts cannot be
              deployed to Paper or Live.
            </p>
          )}
          <div className="instrument-search-results scrollbar-theme min-h-0 flex-1 divide-y divide-border overflow-y-auto overscroll-contain">
            {results.map((instrument) => {
              const added = existingWatchlistSymbols.includes(
                instrument.sym_ticker,
              );
              const disabledReason = added
                ? "Added"
                : getDisabledReason?.(instrument, mode);
              return (
                <Button variant="ghost"
                  type="button"
                  key={instrument.sym_ticker}
                  disabled={Boolean(disabledReason)}
                  className="block h-auto justify-start whitespace-normal p-0 flex w-full items-center gap-3 p-3 text-left disabled:opacity-60"
                  onClick={() => {
                    onAddToWatchlist(instrument, mode);
                    setOpen(false);
                  }}
                >
                  <div className="min-w-0 flex-1">
                    <strong className="block truncate text-sm">
                      {instrument.name}
                    </strong>
                    <span className="text-xs text-muted-foreground">
                      {instrument.exchange} ·{" "}
                      {
                        enums.InstrumentType.find(
                          (choice) =>
                            choice.value === instrument.instrument_type,
                        )?.label
                      }{" "}
                      ·{" "}
                      {instrument.expiry_date
                        ? formatDate(instrument.expiry_date)
                        : ""}{" "}
                      {
                        enums.OptionType.find(
                          (choice) => choice.value === instrument.option_type,
                        )?.label
                      }{" "}
                      · Lot {instrument.lot_size} · Tick{" "}
                      {formatNumber(instrument.tick_size, {
                        maximumFractionDigits: 8,
                      })}
                      {instrument.analysis_only
                        ? " · Analysis only"
                        : !instrument.orderable
                          ? " · Not currently tradable"
                          : ""}
                    </span>
                  </div>
                  {disabledReason ? (
                    <span className="max-w-32 text-xs">{disabledReason}</span>
                  ) : (
                    <Plus className="h-4 w-4 shrink-0" />
                  )}
                </Button>
              );
            })}
          </div>
          {loading && <GlobalLoader inline text="Searching instruments…" />}
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          {!loading && !error && !results.length && (
            <p className="text-sm text-muted-foreground">
              No matching instruments.
            </p>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
InstrumentSearch.propTypes = {
  onAddToWatchlist: PropTypes.func.isRequired,
  existingWatchlistSymbols: PropTypes.array,
  allowHistorical: PropTypes.bool,
  label: PropTypes.string,
  triggerClassName: PropTypes.string,
  modes: PropTypes.array,
  getDisabledReason: PropTypes.func,
};
