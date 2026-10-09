import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Brain, Plus, Send, Paperclip, PanelLeft, X, Loader2 } from "lucide-react";
import PropTypes from "prop-types";
import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";
import { TooltipHint } from "@/shared/components/ui/tooltip";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/shared/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import Markdown from "@/shared/components/ui/markdown";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { researchApi } from "@/shared/services/researchApi";
import { backtestApi } from "@/shared/services/backtestApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { formatDateTime } from "@/shared/utils/formatters";
import { useResearchData, isResearchActive } from "@/features/research/hooks/useResearchData.js";
import ResearchUniverse from "@/features/research/components/ResearchUniverse.jsx";
import ResearchEvidence from "@/features/research/components/ResearchEvidence.jsx";
import ResearchDrawer from "@/features/research/components/ResearchDrawer.jsx";
import ResearchConversations from "@/features/research/components/ResearchConversations.jsx";
import ResearchActionPreview, { actionLabel, ResearchActionLinks } from "@/features/research/components/ResearchActionPreview.jsx";

const starters = [
  { title: "Explore the market", prompts: [
    ["Analyze a stock", "Explain RELIANCE’s daily trend and momentum using EMA 50 and RSI 14."],
    ["Compare my watchlist", "Compare the attached stocks using momentum and volatility."],
    ["Find technical setups", "Find stocks above EMA 50 with RSI above 50 in my selected watchlist."]]},
  { title: "Develop a strategy", prompts: [
    ["Turn an idea into rules", "Help me turn an intraday EMA crossover idea into clear entry, stop-loss and target rules. Ask me about missing settings first."],
    ["Review a backtest", "Review the attached backtest using its actual trades, costs, drawdown and entry diagnostics."],
    ["Compare experiments", "Compare the attached backtests, their configurations and results. Explain comparability limitations."]]}
];

function CitedText({ text, evidence, onEvidence }) {
  const linked = text.replace(/\[(E\d+)\](?!\()/g, (match, id) => evidence.some((item) => item.evidence_id === id) ? `[${id}](#evidence-${id})` : match);
  const renderLink = ({ href, children }) => {
    const item = evidence.find((value) => href === `#evidence-${value.evidence_id}`);
    return item ? <button className="inline rounded bg-indigo-500/10 px-1 text-xs font-medium text-indigo-700 dark:text-indigo-300" onClick={() => onEvidence(item)} aria-label={`Open ${item.evidence_id} evidence`}>{children}</button> : <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
  };
  return <Markdown renderLink={renderLink}>{linked}</Markdown>;
}
CitedText.propTypes = { text: PropTypes.string.isRequired, evidence: PropTypes.array.isRequired, onEvidence: PropTypes.func.isRequired };

export default function AIResearchAssistant() {
  const [params, setParams] = useSearchParams();
  const session = params.get("session");
  const [schema, setSchema] = useState(null);
  const [backtests, setBacktests] = useState([]);
  const [backtestPage, setBacktestPage] = useState(1);
  const [moreBacktests, setMoreBacktests] = useState(false);
  const [universe, setUniverse] = useState({ strategy_id: null, instruments: [], use_watchlist: false });
  const [attached, setAttached] = useState(params.get("backtest") ? [Number(params.get("backtest"))] : []);
  const [source, setSource] = useState(params.get("source") ? Number(params.get("source")) : null);
  const [timeframe, setTimeframe] = useState("");
  const [executionReview, setExecutionReview] = useState(null);
  const [prompt, setPrompt] = useState(params.get("review") ? "Review the attached execution results. Explain the recorded P&L, costs, strongest and weakest closes, and useful next steps. Distinguish observations from hypotheses." : params.get("backtest") ? "Review this backtest using actual trades, costs, drawdown and diagnostics." : params.get("source") ? "Analyze these screening results and suggest useful next investigations." : "");
  const [sidebar, setSidebar] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [attachmentsOpen, setAttachmentsOpen] = useState(false);
  const [details, setDetails] = useState(null);
  const [target, setTarget] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState({});
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const restored = useRef(null);
  const submitting = useRef(false);
  const { runs, receive, loading, activeRun, active, connected, reload, hasMore, loadMore } = useResearchData(session);
  const turns = session ? runs : [];
  const latest = turns.at(-1);
  const contextReady = !session || restored.current === session;

  useEffect(() => {
    let disposed = false;
    Promise.all([researchApi.schema(), backtestApi.getRuns({ status: "COMPLETED" })]).then(async ([contract, reports]) => {
      if (disposed) return;
      setSchema(contract.data); setTimeframe((previous) => previous || contract.data.defaults.timeframe);
      const items = reports.data.results || reports.data;
      setMoreBacktests(Boolean(reports.data.next));
      const id = params.get("backtest");
      if (id && !items.some((item) => item.id === Number(id))) {
        const report = (await backtestApi.getRun(id)).data;
        if (report.status === "COMPLETED") items.unshift(report);
      }
      if (!disposed) setBacktests(items);
      if (params.get("source")) {
        const response = await researchApi.run(params.get("source"));
        const ids = (params.get("stocks") || "").split(",").map(Number).filter(Boolean);
        if (!disposed) setUniverse({ strategy_id: null, instruments: response.data.request.instruments.filter((item) => !ids.length || ids.includes(item.id)), use_watchlist: false });
      }
    }).catch((error) => { if (!disposed) setError(getApiErrorMessage(error, "Could not load research context")); });
    return () => { disposed = true; };
    // Query attachments are initial context; conversation navigation restores each saved turn instead.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (!session && activeRun && !params.get("backtest") && !params.get("source")) setParams({ session: String(activeRun.session) }, { replace: true });
  }, [activeRun, session, params, setParams]);
  useEffect(() => {
    const context = latest?.request;
    // Progress events omit the frozen request; restore attachments after REST loads it.
    if (!context || !session || loading || String(latest.session) !== session || restored.current === session) return;
    setUniverse({ strategy_id: context.strategy_id || null, instruments: context.strategy_id || context.use_watchlist ? [] : context.instruments, use_watchlist: Boolean(context.use_watchlist) });
    setAttached(context.backtest_ids); setTimeframe(context.timeframe); setSource(context.source_run_id || null);
    setExecutionReview(context.execution_review || null);
    restored.current = session;
  }, [session, loading, latest]);
  useEffect(() => {
    if (!session || loading || latest || restored.current === session) return;
    const controller = new AbortController();
    researchApi.session(session, { signal: controller.signal }).then(({ data }) => {
      if (controller.signal.aborted) return;
      const context = data.context;
      setExecutionReview(context.execution_review || null);
      setUniverse({ strategy_id: context.strategy_id || null, instruments: context.instruments || [], use_watchlist: Boolean(context.use_watchlist) });
      setAttached(context.backtest_ids || []); setTimeframe(context.timeframe || "1D"); setSource(context.source_run_id || null);
      restored.current = session;
    }).catch((error) => { if (!controller.signal.aborted) setError(getApiErrorMessage(error, "Could not load the conversation context")); });
    return () => controller.abort();
  }, [session, loading, latest]);
  useEffect(() => {
    const node = scrollRef.current;
    if (node && node.scrollHeight - node.scrollTop - node.clientHeight < 400) node.scrollTop = node.scrollHeight;
  }, [latest?.id, latest?.status, latest?.revision]);
  useEffect(() => {
    const input = inputRef.current;
    if (input) {
      input.style.height = "auto";
      input.style.height = `${Math.min(input.scrollHeight, 128)}px`;
    }
  }, [prompt]);

  function newChat() {
    setParams({}); restored.current = null; setPrompt(""); setError(""); setSource(null); setAttached([]); setExecutionReview(null);
    setUniverse({ strategy_id: null, instruments: [], use_watchlist: false });
    setTimeframe(schema?.defaults.timeframe || ""); setSidebar(false); inputRef.current?.focus();
  }
  const headerActions = useMemo(() => <>
    <Button variant="ghost" size="icon" aria-label="Open conversations" className="h-9 w-9 lg:hidden" onClick={() => setSidebar(true)}><PanelLeft size={17} /></Button>
    <Button variant="ghost" size="icon" aria-label="Toggle conversation sidebar" aria-expanded={!sidebarCollapsed} className="hidden h-9 w-9 lg:flex" onClick={() => setSidebarCollapsed((previous) => !previous)}><PanelLeft size={17} /></Button>
    <Button variant="outline" size="sm" onClick={newChat}><Plus className="h-4 w-4" /><span className="hidden sm:inline">New chat</span><span className="sr-only sm:hidden">New chat</span></Button>
  </>, [schema, sidebarCollapsed]); // eslint-disable-line react-hooks/exhaustive-deps
  useSetPageActions(headerActions);

  async function send(previous) {
    if (submitting.current || active || loading || !contextReady || !schema || (!previous && !prompt.trim())) return;
    submitting.current = true; setBusy(true); setError("");
    const context = previous ? previous.request : { strategy_id: universe.strategy_id, instrument_ids: universe.instruments.map((item) => item.id),
      backtest_ids: attached, timeframe, use_watchlist: universe.use_watchlist, source_run_id: source, execution_review: executionReview };
    const payload = { prompt: previous ? previous.prompt : prompt.trim(), request_id: crypto.randomUUID(), mode: "RESEARCH",
      ...(session ? { session: Number(session) } : {}), refresh: previous?.status === "COMPLETED",
      ...Object.fromEntries(Object.entries(context).filter(([key]) =>
        ["strategy_id", "instrument_ids", "backtest_ids", "timeframe", "use_watchlist", "source_run_id", "execution_review"].includes(key))) };
    try {
      const response = await researchApi.start(payload); receive([response.data]);
      setParams({ session: String(response.data.session) }); setPrompt("");
      requestAnimationFrame(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; });
    } catch (error) { setError(getApiErrorMessage(error, "Could not start research")); }
    finally { submitting.current = false; setBusy(false); }
  }
  async function cancel(run) {
    try { setBusy(true); const response = await researchApi.cancel(run.id); receive([response.data]); await reload(true); }
    catch (error) { setError(getApiErrorMessage(error, "Could not cancel research")); }
    finally { setBusy(false); }
  }
  async function loadBacktests() {
    setBusy(true);
    try {
      const response = await backtestApi.getRuns({ status: "COMPLETED", page: backtestPage + 1 });
      setBacktests((previous) => [...new Map([...previous, ...response.data.results].map((item) => [item.id, item])).values()]);
      setBacktestPage((previous) => previous + 1); setMoreBacktests(Boolean(response.data.next));
    } catch (error) { setError(getApiErrorMessage(error, "Could not load more backtests")); }
    finally { setBusy(false); }
  }
  function followUp(text) { setPrompt(text); inputRef.current?.focus(); }
  function chooseInstrument(item) {
    setUniverse({ strategy_id: null, instruments: [item], use_watchlist: false });
    setDetails(null); followUp(`Use ${item.symbol} (${item.sym_ticker}) for this investigation.`);
  }
  function toggleSelected(runId, id) { setSelected((previous) => ({ ...previous, [runId]: (previous[runId] || []).includes(id) ? previous[runId].filter((item) => item !== id) : [...previous[runId] || [], id] })); }
  const conversations = <ResearchConversations session={session} refreshKey={`${latest?.id || ""}-${latest?.status || ""}`} onSelect={(id) => { setParams({ session: String(id) }); setPrompt(""); setSidebar(false); setError(""); }} onDelete={(id) => { if (String(id) === session) newChat(); }} />;

  return <div className="flex min-h-0 flex-1 overflow-hidden bg-background/40 text-foreground" data-testid="research-workspace">
    <aside className={`hidden w-60 shrink-0 border-r border-border p-3 ${sidebarCollapsed ? "" : "lg:block"}`}>{conversations}</aside>
    <section className="flex min-w-0 flex-1 flex-col overflow-hidden">
      <div ref={scrollRef} className="scrollbar-theme min-h-0 flex-1 overflow-y-auto overscroll-contain" data-testid="research-messages">
        <div className={`mx-auto w-full max-w-[1040px] space-y-6 px-4 py-5 sm:px-6 ${!session ? "flex min-h-full flex-col justify-center" : ""}`}>
          {loading && session && <p className="text-sm text-muted-foreground">Loading conversation…</p>}
          {!session && <div className="space-y-5 py-3"><div className="flex items-start gap-3"><Brain className="mt-1 h-7 w-7 shrink-0 text-indigo-700 dark:text-indigo-400" /><div><h2 className="text-xl font-semibold sm:text-2xl">What would you like to investigate?</h2><p className="mt-2 text-sm text-muted-foreground">Explore stocks, develop rules, and learn from real backtests. Attach context when it helps.</p></div></div><div className="grid gap-4 sm:grid-cols-2">{starters.map((group) => <section key={group.title} className="rounded-xl border border-border p-4"><h3 className="mb-3 text-sm font-semibold text-indigo-700 dark:text-indigo-300">{group.title}</h3><div className="space-y-2">{group.prompts.map(([label, text]) => <button key={label} onClick={() => followUp(text)} className="block w-full rounded-lg bg-card/60 p-3 text-left text-sm hover:bg-secondary">{label}</button>)}</div></section>)}</div></div>}
          {hasMore && session && <Button className="w-full" variant="outline" disabled={loading} onClick={loadMore}>Load earlier turns</Button>}
          {turns.map((run) => <article key={run.id} className="space-y-4" data-run-id={run.id}>
            <div className="ml-auto max-w-[85%] rounded-xl bg-secondary/70 px-4 py-3"><p className="mb-2 text-[10px] uppercase tracking-wider text-muted-foreground">You</p><p className="whitespace-pre-wrap text-sm">{run.prompt || "Run the saved market screen."}</p></div>
            <div className="space-y-4"><div className="flex items-center gap-2 text-xs text-indigo-700 dark:text-indigo-300"><Brain size={16} />QuantNest Research<span className="ml-auto text-muted-foreground">{formatDateTime(run.as_of)}</span></div>
              {run.request && <p className="text-xs text-muted-foreground">{run.request.execution_review ? `${run.request.execution_review.filters.source.toLowerCase()} execution · ${run.request.execution_review.filters.date_from} – ${run.request.execution_review.filters.date_to}` : `${run.request.instruments.map((item) => item.symbol).join(", ") || "General research"} · ${run.request.timeframe} · closed candles`}</p>}
              {isResearchActive(run) || !run.request || run.status === "COMPLETED" && run.loadedRevision < run.revision ? <div role="status" className="flex items-center gap-3 rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4"><Loader2 className="h-4 w-4 animate-spin text-indigo-700 dark:text-indigo-400" /><p className="flex-1 text-sm text-foreground">{run.progress_message}</p>{isResearchActive(run) && <Button size="sm" variant="outline" disabled={busy} onClick={() => cancel(run)}>Cancel</Button>}</div> : run.status === "COMPLETED" ? <>
                <CitedText text={run.result.answer} evidence={run.evidence} onEvidence={setDetails} />
                {run.evidence.filter((item) => (run.result.artifact_refs?.length ? run.result.artifact_refs : run.result.evidence_ids || []).includes(item.evidence_id)).map((item) => <ResearchEvidence key={item.evidence_id} evidence={item} enums={schema?.enums} onDetails={setDetails} onChoose={active ? undefined : chooseInstrument} selected={selected[run.id] || []} onSelect={item.data.rows ? (id) => toggleSelected(run.id, id) : undefined} />)}
                {run.result.clarification_questions?.length > 0 && <div className="rounded-xl border border-indigo-500/20 p-4"><h4 className="mb-3 text-sm font-medium">To continue</h4>{run.result.clarification_questions.map((text, index) => <CitedText key={index} text={text} evidence={run.evidence} onEvidence={setDetails} />)}</div>}
                {run.result.limitations?.length > 0 && <details className="text-sm text-muted-foreground"><summary className="cursor-pointer">Limitations and assumptions</summary><div className="mt-3 space-y-2">{run.result.limitations.map((text, index) => <CitedText key={index} text={text} evidence={run.evidence} onEvidence={setDetails} />)}</div></details>}
                <div className="flex flex-wrap gap-2">{run.result.next_steps?.map((text, index) => <Button key={index} variant="outline" size="sm" className="h-auto whitespace-normal text-left" onClick={() => followUp(text)}>{text.replace(/\[E\d+\]/g, "")}</Button>)}</div>
                <div className="flex flex-wrap gap-2">{run.evidence.map((item) => <Button key={item.evidence_id} size="sm" variant="ghost" onClick={() => setDetails(item)}>Source {item.evidence_id}</Button>)}<Button variant="ghost" size="sm" disabled={active || busy} onClick={() => send(run)}>Refresh analysis</Button>{run.result.draft && !run.created_strategy && <Button size="sm" variant="outline" onClick={() => setTarget({ run, type: "CREATE_DRAFT" })}>Preview strategy draft</Button>}{selected[run.id]?.length > 0 && <Button size="sm" variant="outline" onClick={() => setTarget({ run, type: "ADD_TO_WATCHLIST", payload: { instrument_ids: selected[run.id] } })}>Preview watchlist additions</Button>}{Boolean(run.created_strategy || run.request.strategy_id || run.request.backtest_ids.length) && <Button size="sm" variant="outline" onClick={() => setTarget({ run, type: "START_BACKTEST" })}>Configure one backtest</Button>}</div>
                {run.actions?.map((action) => <div key={action.id} className="space-y-2 rounded-lg border border-border p-3 text-sm"><p>{actionLabel[action.action_type]} · {action.status === "PROPOSED" ? "Awaiting confirmation" : action.status.toLowerCase()}</p>{action.status === "PROPOSED" && <Button size="sm" variant="outline" onClick={() => setTarget({ run, type: action.action_type, action })}>Review proposed action</Button>}{action.error_message && <p className="text-rose-700 dark:text-rose-300">{action.error_message}</p>}<ResearchActionLinks action={action} /></div>)}
              </> : <div role="alert" className="space-y-3 rounded-xl border border-rose-500/20 p-4"><p className="text-sm text-rose-700 dark:text-rose-300">{run.status === "CANCELLED" ? "Research was cancelled. Earlier messages and evidence are retained." : run.error_message}</p><Button variant="outline" size="sm" disabled={busy || active} onClick={() => send(run)}>Retry this question</Button></div>}
            </div>
          </article>)}
        </div>
      </div>
      <div className="safe-bottom shrink-0 border-t border-border bg-background px-3 py-2 sm:px-6 sm:py-3" data-testid="research-composer"><div className="mx-auto w-full max-w-[1040px] space-y-2">
        <div className="scrollbar-thin-theme flex max-h-20 flex-wrap items-center gap-2 overflow-y-auto text-xs">
          {universe.instruments.map((item) => <button key={item.id} className="flex items-center gap-2 rounded-full border border-border px-3 py-1.5" aria-label={`Remove ${item.symbol}`} disabled={active} onClick={() => setUniverse({ ...universe, instruments: universe.instruments.filter((value) => value.id !== item.id) })}>{item.symbol}<X size={12} /></button>)}
          {(universe.strategy_id || universe.use_watchlist) && <button className="flex items-center gap-2 rounded-full border border-border px-3 py-1.5" disabled={active} onClick={() => setUniverse({ strategy_id: null, instruments: [], use_watchlist: false })} aria-label="Remove watchlist context">{universe.use_watchlist ? "Terminal watchlist" : "Strategy"}<X size={12} /></button>}
          {attached.map((id) => <button key={id} className="flex max-w-52 items-center gap-2 rounded-full border border-border px-3 py-1.5" disabled={active} aria-label={`Remove backtest ${id}`} onClick={() => setAttached(attached.filter((value) => value !== id))}><span className="truncate">{backtests.find((item) => item.id === id)?.name || `Backtest #${id}`}</span><X size={12} /></button>)}
          {source && <button className="flex items-center gap-2 rounded-full border border-border px-3 py-1.5" disabled={active} onClick={() => setSource(null)} aria-label="Remove screening evidence">Screen evidence #{source}<X size={12} /></button>}
          {executionReview && <button className="flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1.5 text-indigo-700 dark:text-indigo-200" disabled={active} onClick={() => setExecutionReview(null)} aria-label="Remove execution review context">{executionReview.filters.source.toLowerCase()} execution {executionReview.trade_id ? `#${executionReview.trade_id}` : `· ${executionReview.filters.date_from} – ${executionReview.filters.date_to}`}<X size={12} /></button>}
          <Select value={timeframe} onValueChange={setTimeframe} disabled={active || !schema}><SelectTrigger aria-label="Research timeframe" className="h-8 w-36 text-xs"><SelectValue placeholder="Timeframe" /></SelectTrigger><SelectContent>{schema?.enums.CandleTimeframe.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent></Select>
          <Button variant="ghost" size="sm" disabled={active || !schema} onClick={() => setAttachmentsOpen(true)}><Paperclip size={14} className="mr-1" />Attach context</Button>
          <TooltipHint content={connected ? "Live research updates connected" : "Reconnecting; saved research is retained"}><span tabIndex={0} role="status" aria-label={connected ? "Research updates connected" : "Research updates reconnecting"} className={`ml-auto mr-1 h-2 w-2 shrink-0 rounded-full ${connected ? "bg-emerald-400" : "bg-amber-400"}`} /></TooltipHint>
        </div>
        <form className="flex items-end gap-2 rounded-xl border border-border bg-card/40 p-1.5 focus-within:border-indigo-500/60" onSubmit={(event) => { event.preventDefault(); send(); }}><Textarea ref={inputRef} rows={1} aria-label="Research question" title="Enter to send; Shift+Enter for a new line" placeholder="Ask a question or describe your trading idea…" className="max-h-32 min-h-[40px] resize-none rounded-lg border-0 bg-transparent py-2.5 focus-visible:ring-0 focus-visible:ring-offset-0" value={prompt} maxLength={6000} onChange={(event) => setPrompt(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); send(); } }} /><Button type="submit" size="icon" className="h-10 w-10 shrink-0 bg-indigo-600 text-white hover:bg-indigo-700" aria-label="Send research question" disabled={busy || active || loading || !contextReady || !prompt.trim() || !schema?.service_configured}><Send size={17} /></Button></form>
        {(error || !schema?.service_configured && schema) && <p role="alert" className="text-xs text-rose-700 dark:text-rose-300">{error || "The research service needs configuration before you can send a question."}</p>}
        {activeRun && String(activeRun.session) !== session && <p className="text-xs text-amber-700 dark:text-amber-300">Another conversation has active research. <button className="underline" onClick={() => setParams({ session: String(activeRun.session) })}>Open it to follow progress or cancel.</button></p>}
      </div></div>
    </section>
    <ResearchDrawer open={sidebar} onOpenChange={setSidebar} title="Conversations">{sidebar && conversations}</ResearchDrawer>
    <ResearchDrawer open={Boolean(details)} onOpenChange={(open) => { if (!open) setDetails(null); }} title="Evidence and calculations">{details && <ResearchEvidence evidence={details} enums={schema?.enums} onChoose={active ? undefined : chooseInstrument} detailed />}</ResearchDrawer>
    <Dialog open={attachmentsOpen} onOpenChange={setAttachmentsOpen}>
      <DialogContent style={{ "--tw-enter-scale": 1, "--tw-exit-scale": 1 }} className="flex max-h-[85dvh] w-[calc(100%_-_2rem)] max-w-xl flex-col border-border bg-background p-5 text-foreground">
        <div className="space-y-2 pr-7">
        <DialogTitle>Attach research context</DialogTitle>
        <DialogDescription>Optional stocks, a watchlist, a strategy, or up to three completed backtests.</DialogDescription>
        </div>
        <div className="scrollbar-theme min-h-0 space-y-5 overflow-y-auto pr-1">
        <ResearchUniverse value={universe} onChange={(value, preferredTimeframe) => { setUniverse(value); if (preferredTimeframe) setTimeframe(preferredTimeframe); }} disabled={active} strategies={schema?.strategies} />
        <section>
          <h3 className="mb-3 text-sm">Completed backtests ({attached.length}/3)</h3>
          <div className="scrollbar-thin-theme max-h-52 space-y-1 overflow-y-auto pr-1">
            {backtests.map((item) => <label key={item.id} htmlFor={`research-backtest-${item.id}`} className="flex cursor-pointer items-start gap-3 rounded-lg p-2.5 text-sm text-foreground hover:bg-card has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-50">
              <Checkbox id={`research-backtest-${item.id}`} className="mt-0.5" checked={attached.includes(item.id)} disabled={active || attached.length >= 3 && !attached.includes(item.id)}
                onCheckedChange={(checked) => setAttached((previous) => checked === true ? [...previous, item.id] : previous.filter((id) => id !== item.id))} /><span className="min-w-0 break-words">{item.name}</span>
            </label>)}
            {!backtests.length && <p className="text-xs text-muted-foreground">Completed backtests will appear here.</p>}
          </div>
          {moreBacktests && <Button size="sm" variant="ghost" disabled={busy} onClick={loadBacktests}>Load more backtests</Button>}
        </section>
        <Link to="/screener" className="text-xs text-indigo-700 dark:text-indigo-300">Open the market screener</Link>
        </div>
        <div className="safe-bottom shrink-0 border-t border-border pt-3"><Button className="w-full bg-indigo-600 text-white hover:bg-indigo-700" onClick={() => setAttachmentsOpen(false)}>Done</Button></div>
      </DialogContent>
    </Dialog>
    {target && schema && <ResearchActionPreview key={`${target.run.id}-${target.type}-${target.action?.id || "new"}`} target={target} schema={schema} onClose={() => setTarget(null)} onComplete={() => reload(true)} />}
  </div>;
}
