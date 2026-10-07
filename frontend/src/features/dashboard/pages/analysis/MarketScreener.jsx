import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { useEnums } from "@/shared/context/EnumsContext";
import { researchApi } from "@/shared/services/researchApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import RuleConditionEditor from "../strategy/components/RuleConditionEditor";
import { getDefaultParams } from "../strategy/components/operandUtils";
import ResearchUniverse from "./components/ResearchUniverse";
import ResearchEvidence from "./components/ResearchEvidence";
import ResearchDrawer from "./components/ResearchDrawer";
import { useResearchData } from "./hooks/useResearchData";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";

const theme = { accentBar: "bg-emerald-500", badge: "text-emerald-400", comparison: "text-emerald-400", switch: "data-[state=checked]:bg-emerald-500" };

export default function MarketScreener() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const session = params.get("session");
  const [universe, setUniverse] = useState({ strategy_id: null, instruments: [], use_watchlist: false });
  const [screen, setScreen] = useState(null);
  const [schema, setSchema] = useState(null);
  const [name, setName] = useState("Market screen");
  const [savedTitle, setSavedTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [selection, setSelection] = useState([]);
  const [details, setDetails] = useState(null);
  const { enums } = useEnums();
  const { runs, receive, reload, active, loading } = useResearchData(session);
  const run = session ? runs.filter((value) => value.mode === "SCREEN" && String(value.session) === session).at(-1) : null;
  const ready = !busy && !active && Boolean(screen);
  useEffect(() => {
    let disposed = false;
    researchApi.schema().then((response) => {
      if (disposed) return;
      setSchema(response.data);
      setScreen((previous) => previous || { ...response.data.presets[0] });
    }).catch((error) => { if (!disposed) setError(getApiErrorMessage(error, "Could not load screen presets")); });
    return () => { disposed = true; };
  }, []);
  useEffect(() => {
    if (!session) return;
    let disposed = false;
    researchApi.session(session).then((response) => {
      if (disposed) return;
      const context = response.data.context;
      const instruments = context.instruments;
      setName(response.data.title); setScreen(context.screen);
      setSavedTitle(response.data.title);
      setUniverse({ strategy_id: context.strategy_id || null, instruments: context.strategy_id || context.use_watchlist ? [] : instruments, use_watchlist: Boolean(context.use_watchlist) });
      setSelection([]);
    }).catch((error) => { if (!disposed) setError(getApiErrorMessage(error, "Could not restore this screen")); });
    return () => { disposed = true; };
  }, [session]);

  const screenConfig = () => ({ timeframe: screen.timeframe, logical_operator: screen.logical_operator, conditions: screen.conditions.filter((item) => item.is_active ?? true) });
  const context = () => ({ strategy_id: universe.strategy_id, instrument_ids: universe.instruments.map((item) => item.id),
    use_watchlist: universe.use_watchlist, backtest_ids: [], timeframe: screen.timeframe, screen: screenConfig() });
  async function save() {
    if (!ready || !name.trim()) return;
    setBusy(true); setError("");
    try {
      const response = session ? await researchApi.updateSession(session, { title: name.trim(), context: context() }) :
        await researchApi.createSession({ title: name.trim(), kind: "SCREEN", context: context() });
      setSavedTitle(response.data.title);
      setParams({ session: String(response.data.id) });
    } catch (error) { setError(getApiErrorMessage(error, "Could not save screen")); }
    finally { setBusy(false); }
  }
  async function execute() {
    if (!ready) return;
    setBusy(true); setError("");
    try {
      const response = await researchApi.start({ ...context(), request_id: crypto.randomUUID(), mode: "SCREEN", prompt: name,
        ...(session ? { session: Number(session) } : {}) });
      receive([response.data]); setParams({ session: String(response.data.session) }); setSelection([]);
    } catch (error) { setError(getApiErrorMessage(error, "Could not screen stocks")); }
    finally { setBusy(false); }
  }
  function updateCondition(index, field, value) {
    setScreen((previous) => ({ ...previous, conditions: previous.conditions.map((item, position) => {
      if (position !== index) return item;
      return { ...item, [field]: value, ...(["operand_a_type", "operand_b_type"].includes(field) ?
        { [field.replace("_type", "_params")]: getDefaultParams(value, enums.OperandParameterConfig) } : {}) };
    }) }));
  }
  function researchSelected() {
    const query = new URLSearchParams({ source: String(run.id), stocks: selection.join(",") });
    navigate(`/dashboard/analysis/ai-research-assistant?${query}`);
  }
  const pageActions = useMemo(() => <Select resource="screens" value={session || "new"}
    onValueChange={(id, option) => {
      setParams(id === "new" ? {} : { session: id });
      if (id === "new") { setName("Market screen"); setSelection([]); setSavedTitle(""); }
      else setSavedTitle(option.title);
    }}>
    <SelectTrigger aria-label="Saved screens" className="h-9 w-48 sm:w-64"><SelectValue placeholder="Saved screens" /></SelectTrigger>
    <SelectContent searchPlaceholder="Search saved screens…">
      <SelectItem persistent value="new">New screen</SelectItem>
      {session && savedTitle && <SelectItem value={session}>{savedTitle}</SelectItem>}
    </SelectContent>
  </Select>, [session, savedTitle, setParams]);
  useSetPageActions(pageActions);
  return <div className="container-padding space-y-5 py-6 text-slate-100">
    <Card><CardContent className="space-y-5 p-5">
      <div className="flex flex-wrap gap-3"><Input aria-label="Screen name" className="max-w-sm" value={name} maxLength={160} onChange={(event) => setName(event.target.value)} /><Button variant="outline" disabled={!ready || !name.trim()} onClick={save}>Save named screen</Button></div>
      <div className="grid gap-3 sm:grid-cols-2">{schema?.presets.map((preset) => <button key={preset.id} disabled={!ready} className="rounded-lg border border-slate-800 p-3 text-left hover:border-indigo-500/40" onClick={() => setScreen({ timeframe: preset.timeframe, logical_operator: preset.logical_operator, conditions: preset.conditions })}><h3 className="text-sm font-medium">{preset.name}</h3><p className="mt-1 text-xs text-slate-400">{preset.description}</p></button>)}</div>
      <div className="grid gap-4 lg:grid-cols-2"><ResearchUniverse value={universe} onChange={(value) => setUniverse(value)} disabled={!ready} strategies={schema?.strategies} />{screen && <div className="flex items-start gap-3"><Select value={screen.timeframe} onValueChange={(value) => setScreen({ ...screen, timeframe: value })} disabled={!ready}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{schema?.enums.CandleTimeframe.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent></Select><Select value={screen.logical_operator} onValueChange={(value) => setScreen({ ...screen, logical_operator: value })} disabled={!ready}><SelectTrigger className="w-44"><SelectValue /></SelectTrigger><SelectContent>{schema?.enums.LogicalOperator.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent></Select></div>}</div>
      <div className={!ready ? "pointer-events-none opacity-60" : ""}>{screen?.conditions.map((rule, index) => <RuleConditionEditor key={index} rule={rule} ruleType="ENTRY" logicalOperator={screen.logical_operator} showOperator={index > 0} theme={theme} deleteTitle="Remove condition" onDelete={() => setScreen({ ...screen, conditions: screen.conditions.filter((_, position) => position !== index) })} onChange={(field, value) => updateCondition(index, field, value)} />)}</div>
      <div className="flex justify-between gap-3"><Button variant="outline" onClick={() => setScreen({ ...screen, conditions: [...screen.conditions, schema.presets[0].conditions[0]] })} disabled={!ready || screen.conditions.length >= 12}>Add condition</Button><Button onClick={execute} disabled={!ready || !screen.conditions.some((item) => item.is_active ?? true) || (!universe.strategy_id && !universe.use_watchlist && !universe.instruments.length)}>Run screen with new observation</Button></div>
      <p className="text-xs text-slate-500">Shared strategy evaluator · configured warmup · broker backfill · closed-candle conditions. Saved results retain their original observation time.</p>
      {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}
    </CardContent></Card>
    {loading && session && <p className="text-sm text-slate-400">Loading saved results…</p>}
    {run && <Card><CardContent className="space-y-4 p-5"><div className="flex flex-wrap justify-between items-center gap-3"><p role="status" className="text-sm text-slate-400">{run.status} · {run.progress_message}</p><div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" disabled={busy} onClick={() => reload()}>Reload saved result</Button>{["PENDING", "RUNNING"].includes(run.status) && <Button size="sm" variant="outline" onClick={async () => { try { await researchApi.cancel(run.id); await reload(); } catch (error) { setError(getApiErrorMessage(error)); } }}>Cancel</Button>}<Button size="sm" disabled={!selection.length || run.status !== "COMPLETED"} onClick={researchSelected}>Ask AI about selected results</Button></div></div>
      {run.error_message && <p role="alert" className="text-sm text-rose-300">{run.error_message}</p>}{run.evidence?.map((item) => <ResearchEvidence key={`${run.id}-${item.evidence_id}`} evidence={item} enums={schema?.enums} selected={selection} onSelect={(id) => setSelection((previous) => previous.includes(id) ? previous.filter((value) => value !== id) : [...previous, id])} onDetails={setDetails} />)}
    </CardContent></Card>}
    <ResearchDrawer open={Boolean(details)} onOpenChange={(open) => { if (!open) setDetails(null); }} title="Screen conditions and evidence">{details && <ResearchEvidence evidence={details} detailed enums={schema?.enums} />}</ResearchDrawer>
  </div>;
}
