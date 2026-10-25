import { DatePicker } from "@/shared/components/ui/date-picker";
import { useEnums } from "@/shared/context/EnumsContext";
import { format, parseISO } from "date-fns";
import { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { researchApi } from "@/shared/services/researchApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useNotifications } from "@/shared/hooks/useNotifications";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { formatCurrency, formatNumber } from "@/shared/utils/formatters";
import ResearchStrategyPreview from "@/features/research/components/ResearchStrategyPreview.jsx";

import { actionLabel } from "@/features/research/researchActions";

export function ResearchActionLinks({ action }) {
  return <div className="flex flex-wrap gap-3 text-sm text-indigo-700 dark:text-indigo-300">
    {action.resource_ids?.strategy_id && <Link to={`/strategies/${action.resource_ids.strategy_id}/edit`} className="underline">Open strategy builder</Link>}
    {action.resource_ids?.backtest_id && <Link to={`/backtests/results/${action.resource_ids.backtest_id}`} className="underline">Open backtest progress and results</Link>}
    {action.resource_ids?.watchlist_id && <Link to={`/terminal?watchlist=${action.resource_ids.watchlist_id}`} className="underline">Open terminal watchlist</Link>}
  </div>;
}
ResearchActionLinks.propTypes = { action: PropTypes.object.isRequired };

export default function ResearchActionPreview({ target, schema, onClose, onComplete }) {
  const { notify } = useNotifications();
  const { enums } = useEnums();
  const [preview, setPreview] = useState(target.action || null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [watchlistId, setWatchlistId] = useState(String(target.action?.payload.watchlist_id || target.payload?.watchlist_id || target.run.request.watchlist_id || ""));
  const chooseWatchlist = target.type === "ADD_TO_WATCHLIST" && (!preview || (preview.status === "PROPOSED" && !preview.payload.watchlist_id));
  const [settings, setSettings] = useState(() => ({ ...schema.backtest_defaults,
    charge_profile: schema.default_charge_profile || "",
    ...(!target.run.created_strategy && !target.run.request.strategy_id && target.run.request.backtest_ids?.length ? { source_backtest_id: target.run.request.backtest_ids[0] } : {}), ...target.payload }));
  const submittedPayload = useRef(target.payload || {});
  const run = target.run;
  const propose = async (payload, automatic = false) => {
    submittedPayload.current = payload;
    setBusy(true); setError("");
    try { const response = await researchApi.proposeAction(run.id, target.type, payload); setPreview(response.data); await onComplete(); }
    catch (error) {
      const message = getApiErrorMessage(error, "Could not validate this action");
      if (automatic) setError(message);
      else notify.error(message);
    }
    finally { setBusy(false); }
  };
  useEffect(() => {
    if (!target.action && target.type === "CREATE_DRAFT") propose(target.payload || {}, true);
    // The parent mounts a fresh preview for each target; edits never change a validated preview.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  async function confirm() {
    if (busy || !preview || preview.status !== "PROPOSED") return;
    setBusy(true); setError("");
    try {
      const response = await researchApi.confirmAction(preview.id);
      setPreview(response.data);
      await onComplete();
      if (response.data.status === "FAILED") notify.error(response.data.error_message || "The action could not complete.");
      else if (response.data.status === "COMPLETED") notify.success("Your action has completed.");
    } catch (error) { notify.error(getApiErrorMessage(error, "Could not confirm this action")); }
    finally { setBusy(false); }
  }
  const payload = preview?.payload;
  return <Dialog open onOpenChange={(open) => { if (!open && !busy) onClose(); }}><DialogContent className="flex max-h-[90dvh] max-w-2xl flex-col border-border bg-background text-foreground">
    <DialogTitle>{actionLabel[target.type]}</DialogTitle><DialogDescription>Review the exact settings. This action executes only after your confirmation.</DialogDescription>
    <div className="scrollbar-theme min-h-0 overflow-y-auto space-y-4 pr-1">
      {chooseWatchlist && <form id="research-watchlist-settings" onSubmit={(event) => {
        event.preventDefault();
        propose({ instrument_ids: preview?.payload.instrument_ids || target.payload?.instrument_ids, watchlist_id: Number(watchlistId) });
      }}>
        <label className="block text-sm">Destination watchlist
          <Select resource="terminal-watchlists" value={watchlistId} onValueChange={setWatchlistId} disabled={busy} required name="watchlist_id">
            <SelectTrigger className="mt-2" aria-label="Destination terminal watchlist"><SelectValue placeholder="Choose a terminal watchlist" /></SelectTrigger>
            <SelectContent searchPlaceholder="Search terminal watchlists" />
          </Select>
        </label>
      </form>}
      {payload?.watchlist_name && <p className="text-sm">Destination: <strong>{payload.watchlist_name}</strong></p>}
      {!preview && target.type === "START_BACKTEST" && <form id="research-backtest-settings" className="space-y-4" onSubmit={(event) => { event.preventDefault(); propose({ ...settings, charge_profile: settings.charge_profile || null }); }}>
        {run.request.backtest_ids?.length > 0 && <label className="block text-sm">Strategy configuration<Select value={String(settings.source_backtest_id || "strategy")} onValueChange={(value) => setSettings({ ...settings, source_backtest_id: value === "strategy" ? undefined : Number(value) })}><SelectTrigger className="mt-2" aria-label="Strategy configuration"><SelectValue /></SelectTrigger><SelectContent>{Boolean(run.created_strategy || run.request.strategy_id) && <SelectItem value="strategy">{run.created_strategy ? "Created strategy draft" : "Attached strategy"}</SelectItem>}{run.request.backtests.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.name}</SelectItem>)}</SelectContent></Select></label>}
        <div className="grid gap-3 sm:grid-cols-2">{[["Name", "name", "text"], ["From", "start_date", "date"], ["Through", "end_date", "date"], ["Initial capital (₹)", "initial_capital", "number"], ["Slippage (%)", "slippage_pct", "number"]].map(([label, key, type]) => <label key={key} className="text-sm text-muted-foreground">{label}{type === "date" ? <DatePicker date={settings[key] ? parseISO(settings[key]) : undefined} setDate={(date) => setSettings({ ...settings, [key]: date ? format(date, "yyyy-MM-dd") : "" })} /> : <Input aria-label={label} className="mt-2" required type={type} step={type === "number" ? "0.0001" : undefined} min={type === "number" ? "0" : undefined} value={settings[key] || ""} onChange={(event) => setSettings({ ...settings, [key]: event.target.value })} />}</label>)}</div>
        <label htmlFor="research-include-charges" className="flex cursor-pointer items-center gap-2 text-sm"><Checkbox id="research-include-charges" checked={settings.include_charges} onCheckedChange={(checked) => setSettings({ ...settings, include_charges: checked === true })} />Include charges</label>
        {settings.include_charges && <label className="block text-sm">Charge profile<Select resource="charge-profiles" required name="charge_profile" value={String(settings.charge_profile)} onValueChange={(value) => setSettings({ ...settings, charge_profile: Number(value) })}><SelectTrigger className="mt-2" aria-label="Charge profile"><SelectValue placeholder="Select charge profile" /></SelectTrigger><SelectContent /></Select></label>}
      </form>}
      {payload?.instruments && <ul className="space-y-2 text-sm">{payload.instruments.map((item) => <li key={item.id}>{item.symbol} · {item.name}</li>)}</ul>}
      {payload?.snapshot && <div className="space-y-2 rounded-lg bg-card p-4 text-sm"><p>{payload.start_date} – {payload.end_date}</p><p>Capital {formatCurrency(payload.initial_capital)} · slippage {formatNumber(payload.slippage_pct)}%</p><p>{payload.include_charges ? `Charges: ${payload.charge_profile_name}` : "Charges excluded"}</p><p className="text-xs text-muted-foreground">Simulated fills follow the saved execution configuration. Exit rules close the full position.</p></div>}
      {(payload?.draft || payload?.snapshot) && <ResearchStrategyPreview snapshot={payload.draft || payload.snapshot} enums={enums} />}
      {error && <WorkspaceState error={error} onRetry={() => propose(submittedPayload.current, true)} />}
      {preview && preview.status !== "PROPOSED" && <><p className="text-sm">{preview.status === "COMPLETED" ? "Action completed." : "Action failed. Any created resource is linked below."}</p><ResearchActionLinks action={preview} /></>}
    </div>
    <div className="flex shrink-0 justify-end gap-3"><Button variant="outline" disabled={busy} onClick={onClose}>{preview?.status === "COMPLETED" ? "Close" : "Cancel"}</Button>{chooseWatchlist ? <Button type="submit" form="research-watchlist-settings" disabled={busy || !watchlistId}>{busy ? "Validating…" : "Preview additions"}</Button> : !preview && target.type === "START_BACKTEST" ? <Button type="submit" form="research-backtest-settings" disabled={busy}>{busy ? "Validating…" : "Preview exact configuration"}</Button> : preview?.status === "PROPOSED" && <Button disabled={busy} onClick={confirm}>{busy ? "Executing…" : "Confirm action"}</Button>}</div>
  </DialogContent></Dialog>;
}
ResearchActionPreview.propTypes = { target: PropTypes.object.isRequired, schema: PropTypes.object.isRequired, onClose: PropTypes.func.isRequired, onComplete: PropTypes.func.isRequired };
