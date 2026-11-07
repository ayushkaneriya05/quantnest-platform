import Pagination from "@/shared/components/Pagination";
import { usePagination, useQueryState } from "@/shared/hooks/usePagination";
import api from "@/shared/services/api";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { GlobalLoader } from "@/shared/components/ui/global-loader";
import { describeRule } from "@/features/research/researchDescriptions";
import { chartTooltipProps } from "@/shared/lib/chartTheme";
import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { formatCurrency, formatDate, formatDateTime, formatNumber } from "@/shared/utils/formatters";
import StrategyConfiguration, { ConfigurationFields as ConfigFields } from "@/shared/components/StrategyConfiguration";

const number = (value) => value == null ? "N/A" : formatNumber(value);
const pct = (value) => value == null ? "N/A" : `${formatNumber(value)}%`;
const marketColumns = [["Symbol", "symbol"], ["Close", "close"], ["Return", "return_20_bars_pct"], ["Volatility", "volatility_20_bars_pct"]];
function Summary({ items }) {
  return <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">{items.map(([label, value]) => <div key={label} className="min-w-0 rounded-lg bg-card/60 p-3"><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-2 break-words text-base font-semibold tabular-nums sm:text-lg">{value}</dd></div>)}</dl>;
}
Summary.propTypes = { items: PropTypes.array.isRequired };

const evidenceProps = { evidence: PropTypes.object.isRequired, enums: PropTypes.object, detailed: PropTypes.bool, selected: PropTypes.array, onSelect: PropTypes.func, onResearch: PropTypes.func, onDetails: PropTypes.func, onChoose: PropTypes.func };

function StockConditions({ row, rules, enums }) {
  return <details className="text-sm"><summary className="cursor-pointer text-brand">Conditions: {row.operand_values.filter((value) => value.passed).length}/{row.operand_values.length} passed</summary>
    <ul className="mt-3 space-y-3">{row.operand_values.map((value, index) => <li key={index} className="break-words text-xs leading-relaxed"><p>{describeRule(rules[index], enums)}</p><p className={value.passed ? "mt-1 font-medium text-success" : "mt-1 font-medium text-warning"}>{number(value.a)} vs {number(value.b)} · {value.passed ? "Passed" : "Not met"}</p></li>)}</ul>
  </details>;
}
StockConditions.propTypes = { row: PropTypes.object.isRequired, rules: PropTypes.array.isRequired, enums: PropTypes.object };

function StockDetail({ row, rules, enums }) {
  return <section className="min-w-0 space-y-3 rounded-xl border border-border bg-card/40 p-3">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><h4 className="font-semibold text-foreground">{row.symbol}</h4><p className="mt-1 text-xs text-muted-foreground">Candle closed {formatDateTime(row.observed_at)}</p></div><p className="text-lg font-semibold tabular-nums">{formatCurrency(row.close)}</p></div>
    <dl className="grid grid-cols-2 gap-3 rounded-lg bg-background/70 p-3 text-sm"><div><dt className="text-xs text-muted-foreground">20-bar return</dt><dd className="mt-1 font-medium tabular-nums">{pct(row.return_20_bars_pct)}</dd></div><div><dt className="text-xs text-muted-foreground">20-bar volatility</dt><dd className="mt-1 font-medium tabular-nums">{pct(row.volatility_20_bars_pct)}</dd></div></dl>
    <StockConditions row={row} rules={rules} enums={enums} />
    {row.chart?.length > 0 && <div className="min-w-0 border-t border-border pt-4"><p className="mb-3 text-xs font-medium text-muted-foreground">{row.symbol} · closed-candle prices</p><div className="h-56 min-w-0 w-full sm:h-64"><ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <LineChart data={row.chart} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
        <XAxis dataKey="time" tickFormatter={(value) => formatDate(value, { day: "numeric", month: "short" })} minTickGap={32} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
        <YAxis domain={["auto", "auto"]} width={64} tickFormatter={(value) => formatNumber(value)} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
        <Tooltip labelFormatter={formatDateTime} formatter={(value) => [formatCurrency(value), "Close"]} {...chartTooltipProps} wrapperStyle={{ maxWidth: "100%", whiteSpace: "normal", zIndex: 1 }} />
        <Line dataKey="close" stroke="hsl(var(--chart-line))" strokeWidth={1.5} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer></div></div>}
    {row.quote && <p className="border-t border-border pt-3 text-xs leading-relaxed text-muted-foreground">{Number(row.quote.ltp) > 0 ? `Separate quote: ${formatCurrency(row.quote.ltp)} at ${formatDateTime(row.quote.updated_at)}. This is separate from the closed-candle analysis.` : "A separate quote is unavailable."}</p>}
  </section>;
}
StockDetail.propTypes = StockConditions.propTypes;

function MarketEvidence({ evidence, enums, detailed, selected, onSelect, onResearch, onDetails }) {
  const data = evidence.data;
  const identity = `${evidence.storage_run_id}/${evidence.evidence_id}`;
  const namespace = `evidence_${identity.replace('/', '_')}`;
  const [query, setQuery] = useQueryState('search', '', { namespace, replace: true });
  const [ordering, setOrdering] = useQueryState('ordering', 'symbol', { namespace });
  const [result, setResult] = useState({ results: [], count: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [detail, setDetail] = useState(null);
  const [detailRevision, setDetailRevision] = useState(0);
  const [detailLoading, setDetailLoading] = useState(false);
  const { page, pageSize, setPage, setPageSize, accept } = usePagination(JSON.stringify([identity, query, ordering]), namespace);
  const endpoint = `/research/runs/${identity.split('/')[0]}/evidence/${evidence.evidence_id}/rows/`;
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    const timer = setTimeout(async () => {
      try {
        const response = await api.get(endpoint, { signal: controller.signal, params: { page, page_size: pageSize, search: query, ordering } });
        if (!controller.signal.aborted) { setResult(response.data); accept(response.data); }
      } catch (failure) { if (!controller.signal.aborted) setError(getApiErrorMessage(failure)); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }, query ? 250 : 0);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [endpoint, page, pageSize, query, ordering, revision, accept]);
  useEffect(() => { setResult({ results: [], count: 0 }); setDetail(null); }, [identity, query, ordering]);
  const detailOrdinal = detail?.ordinal;
  useEffect(() => {
    if (detailOrdinal == null) return undefined;
    const controller = new AbortController(); setDetailLoading(true);
    api.get(`${endpoint}${detailOrdinal}/`, { signal: controller.signal })
      .then(response => { if (!controller.signal.aborted) setDetail(current => ({ ...current, row: response.data })); })
      .catch(failure => { if (!controller.signal.aborted) setError(getApiErrorMessage(failure)); })
      .finally(() => { if (!controller.signal.aborted) setDetailLoading(false); });
    return () => controller.abort();
  }, [endpoint, detailOrdinal, detailRevision]);
  const sort = key => setOrdering(ordering === key ? `-${key}` : key);
  return <>
    <Summary items={[["Evaluated", data.evaluated], ["Matched", data.matched], ["Excluded", data.excluded.length], ["Timeframe", data.timeframe]]} />
    <p className="text-xs text-muted-foreground">Latest completed candles as of {formatDateTime(data.as_of)}. Return and volatility use 20 {data.timeframe} bars.</p>
    <Input aria-label="Search evidence symbols" placeholder="Search symbols" value={query} onChange={event => setQuery(event.target.value)} />
    {error && <div role="alert" className="text-sm text-destructive">{error}<Button variant="ghost" onClick={() => { setRevision(value => value + 1); setDetailRevision(value => value + 1); }}>Retry</Button></div>}
    <div className="scrollbar-thin-theme overflow-x-auto rounded-lg border border-border"><table className="w-full text-left text-sm">
      <thead className="bg-card text-xs text-muted-foreground"><tr>{onSelect && <th className="p-2">Select</th>}{marketColumns.map(([label, key]) => <th className="p-2" key={key}><Button variant="ghost" onClick={() => sort(key)} aria-label={`Sort by ${label}`}>{label}{ordering.replace('-', '') === key ? ordering.startsWith('-') ? " ↓" : " ↑" : ""}</Button></th>)}<th className="p-2">Conditions</th>{detailed && <th className="p-2">Chart</th>}</tr></thead>
      <tbody>{result.results.map(row => <tr key={row.instrument_id} className="border-t border-border align-top">
        {onSelect && <td className="p-2"><Checkbox aria-label={`Select ${row.symbol}`} checked={selected.includes(row.instrument_id)} onCheckedChange={() => onSelect(row.instrument_id)} /></td>}
        <td className="p-2 font-medium">{row.symbol}</td><td className="p-2 whitespace-nowrap">{formatCurrency(row.close)}</td><td className="p-2">{pct(row.return_20_bars_pct)}</td><td className="p-2">{pct(row.volatility_20_bars_pct)}</td>
        <td className="min-w-44 p-2"><StockConditions row={row} rules={data.conditions.rules} enums={enums} /></td>
        {detailed && <td className="p-2"><Button variant="outline" size="sm" onClick={() => { setDetail({ ordinal: row.ordinal }); setDetailRevision(value => value + 1); }}>View chart</Button></td>}
      </tr>)}</tbody>
    </table>{!result.results.length && <p className="p-3 text-sm text-muted-foreground">{loading ? <GlobalLoader inline text="Loading evidence…" /> : "No stocks match this view."}</p>}</div>
    <Pagination {...result} page={page} pageSize={pageSize} loading={loading} onPageChange={setPage} onPageSizeChange={setPageSize} label={`${evidence.evidence_id} stock pages`} />
    {detail && (detailLoading ? <GlobalLoader inline text="Loading chart…" /> : detail.row && <StockDetail row={detail.row} rules={data.conditions.rules} enums={enums} />)}
    {data.excluded.length > 0 && <details className="rounded-lg border border-warning/30 p-3 text-sm"><summary className="cursor-pointer text-warning">Excluded stocks ({data.excluded.length})</summary><ul className="mt-3 space-y-2 text-muted-foreground">{data.excluded.map(item => <li key={item.instrument_id}>{item.symbol || item.instrument_id}: {item.reason}</li>)}</ul></details>}
    <div className="flex flex-wrap gap-2">{onDetails && <Button size="sm" variant="outline" onClick={() => onDetails(evidence)}>View conditions and charts</Button>}{onResearch && <Button size="sm" variant="outline" disabled={!selected.length} onClick={() => onResearch(evidence, selected)}>Ask AI about selected stocks</Button>}</div>
  </>;
}
MarketEvidence.propTypes = evidenceProps;

function ExecutionEvidence({ evidence, detailed, onDetails }) {
  const data = evidence.data;
    return <><h4 className="font-medium">{data.source.toLowerCase()} execution review</h4>
      <Summary items={[["Recorded closes", data.summary.closes], ["Realized P&L", formatCurrency(data.summary.realized_pnl)], ["Win rate", pct(data.summary.win_rate)], ["Profit factor", number(data.summary.profit_factor)]]} />
      <p className="text-xs text-muted-foreground">{data.filters.date_from} – {data.filters.date_to} · {data.pnl_basis}. {data.counting_unit} {data.scope}</p>
      {detailed && <><div className="scrollbar-thin-theme overflow-x-auto rounded-lg border border-border"><table className="w-full text-left text-sm"><thead className="bg-card text-xs text-muted-foreground"><tr><th className="p-3">Close</th><th className="p-3">Quantity</th><th className="p-3">Exit time</th><th className="p-3">P&L</th></tr></thead><tbody>{data.closes.map((row) => <tr className="border-t border-border" key={row.id}><td className="p-3">{row.symbol} #{row.id}</td><td className="p-3">{formatNumber(row.quantity, { maximumFractionDigits: 0 })}</td><td className="whitespace-nowrap p-3 text-xs">{formatDateTime(row.exit_time)}</td><td className="whitespace-nowrap p-3">{formatCurrency(row.pnl)}</td></tr>)}</tbody></table></div>
        <p className="text-xs text-muted-foreground">Recorded charges: {data.summary.recorded_charges == null ? "N/A" : formatCurrency(data.summary.recorded_charges)}.</p>
        {data.user_assessments.map((review) => <section key={review.trade_id} className="space-y-2 rounded-lg border border-border p-3 text-sm"><h5 className="font-medium">Saved user assessment · close #{review.trade_id}</h5><p className="whitespace-pre-wrap text-foreground">{review.notes}</p><p className="whitespace-pre-wrap text-muted-foreground">{review.lessons_learned}</p><p className="text-xs text-brand">{review.mistake_tags.join(" · ")}</p></section>)}
        <ul className="list-disc space-y-1 pl-4 text-xs text-muted-foreground">{data.limitations.map((text) => <li key={text}>{text}</li>)}</ul></>}
      {onDetails && <Button size="sm" variant="outline" onClick={() => onDetails(evidence)}>View closes and evidence</Button>}
    </>;
}
ExecutionEvidence.propTypes = evidenceProps;

function BacktestEvidence({ evidence, enums, detailed, onDetails }) {
  const data = evidence.data;
    return <><h4 className="font-medium">{data.name}</h4><Summary items={[["Trades", data.totals.trades], ["Net P&L", formatCurrency(data.totals.net_pnl)], ["Charges", formatCurrency(data.metrics.total_charges)], ["Max drawdown", pct(data.metrics.max_drawdown_pct)]]} />
      <p className="text-xs text-muted-foreground">{data.start_date} – {data.end_date} · slippage {pct(data.slippage_pct)} · {data.include_charges ? "Charges included" : "Charges excluded"} · saved strategy snapshot</p>
      {data.data_quality?.complete === false && <p className="rounded-lg bg-warning/10 p-3 text-sm text-warning">Historical data is incomplete. Interpret this run with its recorded coverage limitations.</p>}
      {detailed && <><Summary items={[["Sharpe", number(data.metrics.sharpe_ratio)], ["Sortino", number(data.metrics.sortino_ratio)], ["Profit factor", number(data.metrics.profit_factor)], ["Return", pct(data.metrics.total_return_pct)]]} />
        <section className="rounded-lg border border-border p-3"><h4 className="mb-3 text-sm font-medium">Entry diagnostics</h4>{data.diagnostics ? <ConfigFields value={data.diagnostics} /> : <p className="text-sm text-muted-foreground">The cause of blocked entries was not recorded for this older run. A confirmed rerun can record diagnostics.</p>}</section>
        {[["Monthly realized P&L", data.monthly, "month"], ["Instrument breakdown", data.instruments, "instrument__symbol"], ["Exit reasons", data.exit_reasons, "exit_reason"]].map(([label, values, key]) => <section key={key} className="rounded-lg border border-border p-3"><h4 className="mb-3 text-sm font-medium">{label}</h4>{values.length ? values.map((row, index) => <div key={index} className="flex justify-between gap-3 py-1 text-sm"><span className="text-muted-foreground">{key === "month" ? String(row[key]).slice(0, 7) : row[key]}</span><span>{formatCurrency(row.net_pnl)}</span></div>) : <p className="text-xs text-muted-foreground">No completed trades.</p>}</section>)}
        <StrategyConfiguration snapshot={data.snapshot} enums={enums} /></>}
      {onDetails && <Button size="sm" variant="outline" onClick={() => onDetails(evidence)}>View breakdowns and diagnostics</Button>}
    </>;
}
BacktestEvidence.propTypes = evidenceProps;

function ComparisonEvidence({ evidence, enums, detailed }) {
  const data = evidence.data;
    return <><h4 className="font-medium">Experiment comparison</h4><p className="text-xs text-warning">{data.differences.length ? `Configuration differences: ${data.differences.join(", ")}. These runs may not be directly comparable.` : "The recorded dates, rules, instruments and costs match."}</p>{data.reports.map((report) => <ResearchEvidence key={report.backtest_id} evidence={{ ...evidence, tool: "get_backtest_report", data: report }} enums={enums} detailed={detailed} />)}</>;
}
ComparisonEvidence.propTypes = evidenceProps;

function StrategyEvidence({ evidence, enums, detailed, onDetails }) {
  const data = evidence.data;
    return detailed ? <StrategyConfiguration snapshot={data.draft || data} enums={enums} /> : <><h4 className="font-medium">{(data.draft || data).name}</h4><p className="text-sm text-muted-foreground">{(data.draft || data).rule_groups?.length || 0} rule groups · {(data.draft || data).time_rule?.candle_timeframe} · {evidence.tool === "validate_strategy_draft" ? "Validated draft" : "Saved configuration"}</p>{onDetails && <Button size="sm" variant="outline" onClick={() => onDetails(evidence)}>Review rules and settings</Button>}</>;
}
StrategyEvidence.propTypes = evidenceProps;

function InstrumentEvidence({ evidence, onChoose }) {
  const data = evidence.data;
    return <><p className="text-sm">{data.selection_required ? "Select a stock for your next research request." : data.ambiguous ? "Choose a stock before continuing." : data.instruments.length ? "Resolved stock" : "No active NSE stock matched."}</p>{data.instruments.map((item) => <div key={item.id} className="flex items-center justify-between gap-3 text-sm text-muted-foreground"><p>{item.symbol} · {item.name}</p>{onChoose && <Button size="sm" variant="outline" onClick={() => onChoose(item)}>Use {item.symbol}</Button>}</div>)}</>;
}
InstrumentEvidence.propTypes = evidenceProps;
const renderers = {
  screen_instruments: MarketEvidence, compare_instruments: MarketEvidence, analyze_stock: MarketEvidence,
  get_execution_review: ExecutionEvidence, get_backtest_report: BacktestEvidence,
  compare_backtests: ComparisonEvidence, validate_strategy_draft: StrategyEvidence,
  get_strategy_snapshot: StrategyEvidence, resolve_instruments: InstrumentEvidence,
};

export default function ResearchEvidence({ evidence, enums = {}, detailed = false, selected = [], onSelect, onResearch, onDetails, onChoose }) {
  const data = evidence.data;
  const Renderer = renderers[evidence.tool];
  return <div className={`min-w-0 max-w-full space-y-3 break-words ${detailed ? "" : "rounded-xl border border-border bg-background/40 p-3"}`}>
    <p className="text-xs text-brand">{evidence.evidence_id} · {evidence.tool.replaceAll("_", " ")} · observed {formatDateTime(evidence.source_as_of || data.as_of)}{evidence.source_run_id ? ` · source turn #${evidence.source_run_id}` : ""}</p>
    {Renderer ? <Renderer {...{ evidence, enums, detailed, selected, onSelect, onResearch, onDetails, onChoose }} /> : <p className="text-sm text-muted-foreground">Builder metadata retrieved for this research.</p>}
    {detailed && <details className="rounded-lg border border-border p-3 text-xs text-muted-foreground"><summary className="cursor-pointer">Technical details</summary><pre className="mt-3 whitespace-pre-wrap break-all">{JSON.stringify(data, null, 2)}</pre></details>}
  </div>;
}
ResearchEvidence.propTypes = evidenceProps;
