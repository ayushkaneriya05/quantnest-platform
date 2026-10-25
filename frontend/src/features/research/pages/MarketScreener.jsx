import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { useEnums } from "@/shared/context/EnumsContext";
import { researchApi } from "@/shared/services/researchApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import RuleConditionEditor from "@/features/strategies/components/RuleConditionEditor.jsx";
import { getDefaultParams } from "@/features/strategies/components/operandUtils.js";
import ResearchUniverse from "@/features/research/components/ResearchUniverse.jsx";
import ResearchEvidence from "@/features/research/components/ResearchEvidence.jsx";
import ResearchDrawer from "@/features/research/components/ResearchDrawer.jsx";
import { useResearchData } from "@/features/research/hooks/useResearchData.js";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { useNotifications } from "@/shared/hooks/useNotifications";

const theme = { accentBar: "bg-emerald-500", badge: "text-emerald-700 dark:text-emerald-400", comparison: "text-emerald-700 dark:text-emerald-400", switch: "data-[state=checked]:bg-emerald-500" };

export default function MarketScreener() {
  const { notify } = useNotifications();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const session = params.get("session");
  const [universe, setUniverse] = useState({ strategy_id: null, instruments: [], watchlist_id: null });
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
      setScreen((previous) => previous || { timeframe: response.data.defaults.timeframe, logical_operator: "AND", conditions: [] });
    }).catch((error) => { if (!disposed) setError(getApiErrorMessage(error, "Could not load screener settings")); });
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
      setUniverse({ strategy_id: context.strategy_id || null, instruments: context.strategy_id || context.watchlist_id ? [] : instruments, watchlist_id: context.watchlist_id || null, watchlist_name: context.watchlist_name });
      setSelection([]);
    }).catch((error) => { if (!disposed) setError(getApiErrorMessage(error, "Could not restore this screen")); });
    return () => { disposed = true; };
  }, [session]);

  const screenConfig = () => ({ timeframe: screen.timeframe, logical_operator: screen.logical_operator, conditions: screen.conditions.filter((item) => item.is_active ?? true) });
  const context = () => ({ strategy_id: universe.strategy_id, instrument_ids: universe.instruments.map((item) => item.id),
    watchlist_id: universe.watchlist_id, backtest_ids: [], timeframe: screen.timeframe, screen: screenConfig() });
  async function save() {
    if (!ready || !name.trim()) return;
    setBusy(true); setError("");
    try {
      const response = session ? await researchApi.updateSession(session, { title: name.trim(), context: context() }) :
        await researchApi.createSession({ title: name.trim(), kind: "SCREEN", context: context() });
      setSavedTitle(response.data.title);
      setParams({ session: String(response.data.id) });
      notify.success("Your screen has been saved.");
    } catch (error) { notify.error(getApiErrorMessage(error, "Could not save screen")); }
    finally { setBusy(false); }
  }
  async function execute() {
    if (!ready) return;
    setBusy(true); setError("");
    try {
      const response = await researchApi.start({ ...context(), request_id: crypto.randomUUID(), mode: "SCREEN", prompt: name,
        ...(session ? { session: Number(session) } : {}) });
      receive([response.data]); setParams({ session: String(response.data.session) }); setSelection([]);
    } catch (error) { notify.error(getApiErrorMessage(error, "Could not screen stocks")); }
    finally { setBusy(false); }
  }
  function updateCondition(index, field, value) {
    setScreen((previous) => ({ ...previous, conditions: previous.conditions.map((item, position) => {
      if (position !== index) return item;
      return { ...item, [field]: value, ...(["operand_a_type", "operand_b_type"].includes(field) ?
        { [field.replace("_type", "_params")]: getDefaultParams(value, enums.OperandParameterConfig) } : {}) };
    }) }));
  }
  function addCondition() {
    setScreen((previous) => ({ ...previous, conditions: [...previous.conditions, {
      operand_a_type: "RSI", operand_a_params: getDefaultParams("RSI", enums.OperandParameterConfig),
      comparison: "GT", operand_b_type: "CONSTANT",
      operand_b_params: getDefaultParams("CONSTANT", enums.OperandParameterConfig), is_active: true,
    }] }));
  }
  function researchSelected() {
    const query = new URLSearchParams({ source: String(run.id), stocks: selection.join(",") });
    navigate(`/research?${query}`);
  }
  const pageActions = useMemo(() => <Select resource="screens" value={session || "new"} disabled={!schema || busy || active}
    onValueChange={(id, option) => {
      setParams(id === "new" ? {} : { session: id });
      if (id === "new") {
        setName("Market screen"); setSelection([]); setSavedTitle("");
        setUniverse({ strategy_id: null, watchlist_id: null, instruments: [] });
        setScreen({ timeframe: schema.defaults.timeframe, logical_operator: "AND", conditions: [] });
      }
      else setSavedTitle(option.title);
    }}>
    <SelectTrigger aria-label="Saved screens" className="h-9 w-48 sm:w-64"><SelectValue placeholder="Saved screens" /></SelectTrigger>
    <SelectContent searchPlaceholder="Search saved screens…">
      <SelectItem persistent value="new">New screen</SelectItem>
      {session && savedTitle && <SelectItem value={session}>{savedTitle}</SelectItem>}
    </SelectContent>
  </Select>, [session, savedTitle, setParams, schema, busy, active]);
  useSetPageActions(pageActions);
  return <div className="container-padding space-y-5 py-6 text-foreground">
    <Card><CardContent className="space-y-5 p-5">
      <div className="flex flex-wrap gap-3"><Input aria-label="Screen name" className="max-w-sm" value={name} maxLength={160} onChange={(event) => setName(event.target.value)} /><Button variant="outline" disabled={!ready || !name.trim() || !screen.conditions.some((item) => item.is_active ?? true)} onClick={save}>Save named screen</Button></div>
      <div className="grid gap-4 lg:grid-cols-2"><ResearchUniverse value={universe} onChange={(value) => setUniverse(value)} disabled={!ready} maxInstruments={schema?.limits.instruments} />{screen && <div className="flex items-start gap-3"><Select value={screen.timeframe} onValueChange={(value) => setScreen({ ...screen, timeframe: value })} disabled={!ready}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{enums?.CandleTimeframe?.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent></Select><Select value={screen.logical_operator} onValueChange={(value) => setScreen({ ...screen, logical_operator: value })} disabled={!ready}><SelectTrigger className="w-44"><SelectValue /></SelectTrigger><SelectContent>{enums?.LogicalOperator?.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent></Select></div>}</div>
      <div className={!ready ? "pointer-events-none opacity-60" : ""}>{screen?.conditions.map((rule, index) => <RuleConditionEditor key={index} rule={rule} ruleType="ENTRY" allowedValues={schema?.screen_operand_types || []} logicalOperator={screen.logical_operator} showOperator={index > 0} theme={theme} deleteTitle="Remove condition" onDelete={() => setScreen({ ...screen, conditions: screen.conditions.filter((_, position) => position !== index) })} onChange={(field, value) => updateCondition(index, field, value)} />)}</div>
      <div className="flex justify-between gap-3"><Button variant="outline" onClick={addCondition} disabled={!ready || !enums?.OperandParameterConfig || screen.conditions.length >= 12}>Add condition</Button><Button onClick={execute} disabled={!ready || !screen.conditions.some((item) => item.is_active ?? true) || (!universe.strategy_id && !universe.watchlist_id && !universe.instruments.length)}>Run screen with new observation</Button></div>
      {error && <p role="alert" className="text-sm text-rose-700 dark:text-rose-300">{error}</p>}
    </CardContent></Card>
    {loading && session && <p className="text-sm text-muted-foreground"><GlobalLoader inline text="Loading saved results…" /></p>}
    {run && <Card><CardContent className="space-y-4 p-5"><div className="flex flex-wrap justify-between items-center gap-3"><p role="status" className="text-sm text-muted-foreground">{run.status} · {run.progress_message}</p><div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" disabled={busy} onClick={() => reload()}>Reload saved result</Button>{["PENDING", "RUNNING"].includes(run.status) && <Button size="sm" variant="outline" onClick={async () => { try { await researchApi.cancel(run.id); notify.success("Screen cancellation requested."); await reload(); } catch (error) { notify.error(getApiErrorMessage(error)); } }}>Cancel</Button>}<Button size="sm" disabled={!selection.length || run.status !== "COMPLETED"} onClick={researchSelected}>Ask AI about selected results</Button></div></div>
      {run.error_message && <p role="alert" className="text-sm text-rose-700 dark:text-rose-300">{run.error_message}</p>}{run.evidence?.map((item) => <ResearchEvidence key={`${run.id}-${item.evidence_id}`} evidence={item} enums={enums} selected={selection} onSelect={(id) => setSelection((previous) => previous.includes(id) ? previous.filter((value) => value !== id) : [...previous, id])} onDetails={setDetails} />)}
    </CardContent></Card>}
    <ResearchDrawer wide open={Boolean(details)} onOpenChange={(open) => { if (!open) setDetails(null); }} title="Screen conditions and evidence">{details && <ResearchEvidence evidence={details} detailed enums={enums} />}</ResearchDrawer>
  </div>;
}
