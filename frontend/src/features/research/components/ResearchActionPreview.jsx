import { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import { format, parseISO } from "date-fns";
import { useEnums } from "@/shared/context/EnumsContext";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { DatePicker } from "@/shared/components/ui/date-picker";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import StrategyConfiguration from "@/shared/components/StrategyConfiguration";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { researchApi } from "@/shared/services/researchApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { formatCurrency, formatNumber } from "@/shared/utils/formatters";
import { actionLabel } from "@/features/research/researchActions";

export function ResearchActionLinks({ action }) {
  return <div className="flex flex-wrap gap-3 text-sm text-brand">
    {action.resource_ids?.strategy_id && <Link to={`/strategies/${action.resource_ids.strategy_id}/studio`} className="underline">Open strategy builder{action.resource_ids.version_number ? ` · version ${action.resource_ids.version_number}` : ""}</Link>}
    {action.resource_ids?.backtest_id && <Link to={`/backtests/results/${action.resource_ids.backtest_id}`} className="underline">Open backtest progress and results</Link>}
  </div>;
}
ResearchActionLinks.propTypes = { action: PropTypes.object.isRequired };

export default function ResearchActionPreview({ target, schema, onClose, onComplete }) {
  const { notify } = useNotifications();
  const { enums } = useEnums();
  const run = target.run;
  const [preview, setPreview] = useState(target.action || null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [source, setSource] = useState(target.payload?.source_backtest_id ? 'backtest' : 'strategy');
  const [settings, setSettings] = useState(() => ({ ...schema.backtest_defaults,
    strategy_id: run.created_strategy || run.request.strategy_id || '',
    source_backtest_id: '', charge_profile: schema.default_charge_profile || '', ...target.payload }));
  const submitted = useRef(target.payload || {});
  async function propose(payload, automatic = false) {
    submitted.current = payload; setBusy(true); setError("");
    try { const { data } = await researchApi.proposeAction(run.id, target.type, payload); setPreview(data); await onComplete(); }
    catch (failure) { const message = getApiErrorMessage(failure, "Could not validate this action"); if (automatic) setError(message); else notify.error(message); }
    finally { setBusy(false); }
  }
  useEffect(() => {
    if (!target.action && target.type === "CREATE_DRAFT") propose(target.payload || {}, true);
    // A new target mounts its own preview; form edits never change an approved payload.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  async function confirm() {
    if (busy || preview?.status !== "PROPOSED") return;
    setBusy(true);
    try {
      const { data } = await researchApi.confirmAction(preview.id); setPreview(data); await onComplete();
      if (data.status === "FAILED") notify.error(data.error_message);
      else notify.success("Your action has completed.");
    } catch (failure) { notify.error(getApiErrorMessage(failure)); }
    finally { setBusy(false); }
  }
  const payload = preview?.payload;
  const editable = !preview && target.type !== 'CREATE_DRAFT';
  function submit(event) {
    event.preventDefault();
    if (target.type === 'SAVE_STRATEGY_VERSION') {
      propose({ strategy_id: Number(settings.strategy_id), evidence_id: target.payload?.evidence_id || run.result.draft_evidence_id });
    } else {
      const { strategy_id, source_backtest_id, ...values } = settings;
      propose({ ...values, ...(source === 'strategy' ? { strategy_id: Number(strategy_id) } : { source_backtest_id: Number(source_backtest_id) }), charge_profile: settings.charge_profile || null });
    }
  }
  return <Dialog open onOpenChange={open => { if (!open && !busy) onClose(); }}><DialogContent className="flex max-h-[90dvh] max-w-3xl flex-col border-border bg-background text-foreground">
    <DialogTitle>{actionLabel[target.type]}</DialogTitle>
    <DialogDescription>Review the exact settings. Changes execute only after confirmation.</DialogDescription>
    <div className="scrollbar-theme min-h-0 space-y-3 overflow-y-auto pr-1">
      {editable && <form id="research-action-settings" className="space-y-3" onSubmit={submit}>
        {target.type === 'START_BACKTEST' && <Select value={source} onValueChange={setSource}><SelectTrigger aria-label="Backtest configuration source"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="strategy">Saved strategy</SelectItem><SelectItem value="backtest">Previous backtest snapshot</SelectItem></SelectContent></Select>}
        {source === 'strategy' || target.type === 'SAVE_STRATEGY_VERSION' ? <label className="block text-sm">Strategy
          <Select resource="strategies" required value={String(settings.strategy_id)} onValueChange={value => setSettings({ ...settings, strategy_id: Number(value) })}><SelectTrigger aria-label="Action strategy"><SelectValue placeholder="Search your strategies" /></SelectTrigger><SelectContent searchPlaceholder="Search strategies" /></Select>
        </label> : <label className="block text-sm">Source backtest
          <Select resource="backtests" filters={{ status: 'COMPLETED' }} required value={String(settings.source_backtest_id)} onValueChange={value => setSettings({ ...settings, source_backtest_id: Number(value) })}><SelectTrigger aria-label="Source backtest"><SelectValue placeholder="Search completed backtests" /></SelectTrigger><SelectContent searchPlaceholder="Search backtests" /></Select>
        </label>}
        {target.type === 'START_BACKTEST' && <>
          <div className="grid gap-3 sm:grid-cols-2">{[['Name', 'name', 'text'], ['From', 'start_date', 'date'], ['Through', 'end_date', 'date'], ['Initial capital (₹)', 'initial_capital', 'number'], ['Slippage (%)', 'slippage_pct', 'number']].map(([label, key, type]) => <label key={key} className="text-sm text-muted-foreground">{label}{type === 'date' ? <DatePicker date={settings[key] ? parseISO(settings[key]) : undefined} setDate={date => setSettings({ ...settings, [key]: date ? format(date, 'yyyy-MM-dd') : '' })} /> : <Input aria-label={label} required type={type} min={type === 'number' ? 0 : undefined} step={type === 'number' ? '0.0001' : undefined} value={settings[key] ?? ''} onChange={event => setSettings({ ...settings, [key]: event.target.value })} />}</label>)}</div>
          <label className="flex items-center gap-2 text-sm"><Checkbox checked={settings.include_charges} onCheckedChange={value => setSettings({ ...settings, include_charges: value === true })} />Include charges</label>
          {settings.include_charges && <Select resource="charge-profiles" value={String(settings.charge_profile)} onValueChange={value => setSettings({ ...settings, charge_profile: Number(value) })}><SelectTrigger aria-label="Charge profile"><SelectValue placeholder="Charge profile" /></SelectTrigger><SelectContent /></Select>}
        </>}
      </form>}
      {payload?.snapshot && <div className="space-y-1 text-sm"><p>{payload.start_date} – {payload.end_date}</p><p>Capital {formatCurrency(payload.initial_capital)} · slippage {formatNumber(payload.slippage_pct)}%</p><p>{payload.include_charges ? `Charges: ${payload.charge_profile_name}` : 'Charges excluded'}</p><p>Estimated credits: {formatNumber(payload.workload_estimate?.credits)}</p></div>}
      {payload?.changes && <section className="space-y-2 text-sm"><p className="text-muted-foreground">{payload.strategy_name} · existing deployments keep their saved versions.</p>{payload.changes.length ? payload.changes.map((change, index) => <div key={index} className="border-b border-border py-2"><p className="font-medium">{change.label}</p><p className="break-words text-muted-foreground">{JSON.stringify(change.before)} → {JSON.stringify(change.after)}</p></div>) : <p>No configuration changes.</p>}</section>}
      {(payload?.draft || payload?.snapshot) && <StrategyConfiguration snapshot={payload.draft || payload.snapshot} enums={enums} />}
      {error && <WorkspaceState error={error} onRetry={() => propose(submitted.current, true)} />}
      {preview && preview.status !== 'PROPOSED' && <><p className="text-sm">{preview.status === 'COMPLETED' ? 'Action completed.' : preview.error_message}</p><ResearchActionLinks action={preview} /></>}
    </div>
    <div className="flex shrink-0 justify-end gap-2"><Button variant="outline" disabled={busy} onClick={onClose}>Close</Button>{editable ? <Button type="submit" form="research-action-settings" disabled={busy}>{busy ? 'Validating…' : 'Preview exact configuration'}</Button> : preview?.status === 'PROPOSED' && <Button disabled={busy} onClick={confirm}>{busy ? 'Executing…' : 'Confirm action'}</Button>}</div>
  </DialogContent></Dialog>;
}
ResearchActionPreview.propTypes = { target: PropTypes.object.isRequired, schema: PropTypes.object.isRequired, onClose: PropTypes.func.isRequired, onComplete: PropTypes.func.isRequired };
