import { useState } from "react";
import PropTypes from "prop-types";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { formatCurrency, formatDateTime, formatNumber } from "@/shared/utils/formatters";
import ResearchStrategyPreview, { describeRule, ConfigFields } from "./ResearchStrategyPreview";

const number = (value) => value == null ? "N/A" : formatNumber(value);
const pct = (value) => value == null ? "N/A" : `${formatNumber(value)}%`;
function Summary({ items }) {
  return <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">{items.map(([label, value]) => <div key={label} className="rounded-lg bg-slate-900/60 p-3"><dt className="text-xs text-slate-400">{label}</dt><dd className="mt-2 text-lg font-semibold">{value}</dd></div>)}</dl>;
}
Summary.propTypes = { items: PropTypes.array.isRequired };

export default function ResearchEvidence({ evidence, enums = {}, detailed = false, selected = [], onSelect, onResearch, onDetails, onChoose }) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState({ key: "symbol", descending: false });
  const [page, setPage] = useState(1);
  const data = evidence.data;
  function changeSort(key) { setSort({ key, descending: sort.key === key && !sort.descending }); setPage(1); }
  let content;
  if (data.rows) {
    const rows = data.rows.filter((row) => row.symbol.toLowerCase().includes(query.toLowerCase())).sort((a, b) => {
      const comparison = typeof a[sort.key] === "string" ? a[sort.key].localeCompare(b[sort.key]) : (a[sort.key] || 0) - (b[sort.key] || 0);
      return sort.descending ? -comparison : comparison;
    });
    const pages = Math.max(1, Math.ceil(rows.length / 10));
    const current = Math.min(page, pages);
    content = <>
      <Summary items={[["Evaluated", data.evaluated], ["Matched", data.matched], ["Excluded", data.excluded.length], ["Timeframe", data.timeframe]]} />
      <p className="text-xs text-slate-400">Latest completed candles as of {formatDateTime(data.as_of)}. Return: 20 {data.timeframe} bars. Volatility: sample standard deviation of returns over 20 {data.timeframe} bars.</p>
      {(detailed || rows.length > 5) && <Input aria-label="Search result symbols" placeholder="Search symbols" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} />}
      <div className="scrollbar-thin-theme overflow-x-auto rounded-lg border border-slate-800"><table className="w-full text-left text-sm">
        <thead className="bg-slate-900 text-xs text-slate-400"><tr>{onSelect && <th className="p-3">Select</th>}{[["Symbol", "symbol"], ["Close", "close"], ["Return", "return_20_bars_pct"], ["Volatility", "volatility_20_bars_pct"]].map(([label, key]) => <th className="p-3" key={key}><button onClick={() => changeSort(key)} aria-label={`Sort by ${label}`}>{label}{sort.key === key ? sort.descending ? " ↓" : " ↑" : ""}</button></th>)}<th className="p-3">Conditions</th>{detailed && <th className="p-3">Candle closed</th>}</tr></thead>
        <tbody>{rows.slice((current - 1) * 10, current * 10).map((row) => <tr key={row.instrument_id} className="border-t border-slate-800 align-top">
          {onSelect && <td className="p-3"><Checkbox aria-label={`Select ${row.symbol}`} checked={selected.includes(row.instrument_id)} onCheckedChange={() => onSelect(row.instrument_id)} /></td>}
          <td className="p-3 font-medium">{row.symbol}</td><td className="p-3 whitespace-nowrap">{formatCurrency(row.close)}</td><td className="p-3">{pct(row.return_20_bars_pct)}</td><td className="p-3">{pct(row.volatility_20_bars_pct)}</td>
          <td className="p-3"><details><summary className="cursor-pointer whitespace-nowrap text-indigo-300">{row.operand_values.filter((value) => value.passed).length}/{row.operand_values.length} passed</summary><ul className="mt-3 min-w-48 space-y-3">{row.operand_values.map((value, index) => <li key={index} className="text-xs"><p>{describeRule(data.conditions.rules[index], enums)}</p><p className={value.passed ? "mt-1 text-emerald-400" : "mt-1 text-amber-300"}>{number(value.a)} vs {number(value.b)} · {value.passed ? "Passed" : "Not met"}</p></li>)}</ul></details></td>
          {detailed && <td className="p-3 text-xs">{formatDateTime(row.observed_at)}</td>}
        </tr>)}</tbody>
      </table>{!rows.length && <p className="p-6 text-sm text-slate-400">{data.evaluated === 0 ? "No stocks could be evaluated. Check the exclusions below." : "No stocks match this view."}</p>}</div>
      {pages > 1 && <div className="flex justify-end items-center gap-3 text-xs"><Button size="sm" variant="outline" disabled={current === 1} onClick={() => setPage(current - 1)}>Previous</Button>{current} / {pages}<Button size="sm" variant="outline" disabled={current === pages} onClick={() => setPage(current + 1)}>Next</Button></div>}
      {data.excluded.length > 0 && <details className="rounded-lg border border-amber-500/30 p-3 text-sm" open={data.evaluated === 0}><summary className="cursor-pointer text-amber-300">Excluded stocks ({data.excluded.length})</summary><ul className="mt-3 space-y-2 text-slate-400">{data.excluded.map((item) => <li key={item.instrument_id}>{item.symbol || item.instrument_id}: {item.reason}</li>)}</ul></details>}
      {detailed && data.rows.map((row) => <div key={row.instrument_id}>
        {row.chart?.length > 0 && <section><h4 className="mb-2 text-sm font-medium">{row.symbol} · closed-candle prices</h4><div className="h-56 w-full"><ResponsiveContainer><LineChart data={row.chart}><XAxis dataKey="time" hide /><YAxis domain={["auto", "auto"]} width={60} tickFormatter={number} /><Tooltip labelFormatter={formatDateTime} formatter={(value) => [formatCurrency(value), "Close"]} contentStyle={{ background: "#0f172a", borderColor: "#334155" }} /><Line dataKey="close" stroke="#818cf8" dot={false} isAnimationActive={false} /></LineChart></ResponsiveContainer></div></section>}
        {row.quote && <p className="text-xs text-slate-400">Separate quote for {row.symbol}: {formatCurrency(row.quote.ltp)} at {formatDateTime(row.quote.updated_at)}. This quote is separate from the closed-candle analysis.</p>}
      </div>)}
      <div className="flex flex-wrap gap-2">{onDetails && <Button size="sm" variant="outline" onClick={() => onDetails(evidence)}>View conditions and charts</Button>}{onResearch && <Button size="sm" variant="outline" disabled={!selected.length} onClick={() => onResearch(evidence, selected)}>Ask AI about selected stocks</Button>}</div>
    </>;
  } else if (evidence.tool === "get_execution_review") {
    content = <><h4 className="font-medium">{data.source.toLowerCase()} execution review</h4>
      <Summary items={[["Recorded closes", data.summary.closes], ["Realized P&L", formatCurrency(data.summary.realized_pnl)], ["Win rate", pct(data.summary.win_rate)], ["Profit factor", number(data.summary.profit_factor)]]} />
      <p className="text-xs text-slate-400">{data.filters.date_from} – {data.filters.date_to} · {data.pnl_basis}. {data.counting_unit} {data.scope}</p>
      {detailed && <><div className="scrollbar-thin-theme overflow-x-auto rounded-lg border border-slate-800"><table className="w-full text-left text-sm"><thead className="bg-slate-900 text-xs text-slate-400"><tr><th className="p-3">Close</th><th className="p-3">Quantity</th><th className="p-3">Exit time</th><th className="p-3">P&L</th></tr></thead><tbody>{data.closes.map((row) => <tr className="border-t border-slate-800" key={row.id}><td className="p-3">{row.symbol} #{row.id}</td><td className="p-3">{row.quantity}</td><td className="whitespace-nowrap p-3 text-xs">{formatDateTime(row.exit_time)}</td><td className="whitespace-nowrap p-3">{formatCurrency(row.pnl)}</td></tr>)}</tbody></table></div>
        <p className="text-xs text-slate-400">Recorded charges: {data.summary.recorded_charges == null ? "N/A" : formatCurrency(data.summary.recorded_charges)}.</p>
        {data.user_assessments.map((review) => <section key={review.trade_id} className="space-y-2 rounded-lg border border-slate-800 p-3 text-sm"><h5 className="font-medium">Saved user assessment · close #{review.trade_id}</h5><p className="whitespace-pre-wrap text-slate-300">{review.notes}</p><p className="whitespace-pre-wrap text-slate-400">{review.lessons_learned}</p><p className="text-xs text-indigo-300">{review.mistake_tags.join(" · ")}</p></section>)}
        <ul className="list-disc space-y-1 pl-4 text-xs text-slate-400">{data.limitations.map((text) => <li key={text}>{text}</li>)}</ul></>}
      {onDetails && <Button size="sm" variant="outline" onClick={() => onDetails(evidence)}>View closes and evidence</Button>}
    </>;
  } else if (evidence.tool === "get_backtest_report") {
    content = <><h4 className="font-medium">{data.name}</h4><Summary items={[["Trades", data.totals.trades], ["Net P&L", formatCurrency(data.totals.net_pnl)], ["Charges", formatCurrency(data.metrics.total_charges)], ["Max drawdown", pct(data.metrics.max_drawdown_pct)]]} />
      <p className="text-xs text-slate-400">{data.start_date} – {data.end_date} · slippage {pct(data.slippage_pct)} · {data.include_charges ? "Charges included" : "Charges excluded"} · saved strategy snapshot</p>
      {data.data_quality?.complete === false && <p className="rounded-lg bg-amber-500/10 p-3 text-sm text-amber-300">Historical data is incomplete. Interpret this run with its recorded coverage limitations.</p>}
      {detailed && <><Summary items={[["Sharpe", number(data.metrics.sharpe_ratio)], ["Sortino", number(data.metrics.sortino_ratio)], ["Profit factor", number(data.metrics.profit_factor)], ["Return", pct(data.metrics.total_return_pct)]]} />
        <section className="rounded-lg border border-slate-800 p-3"><h4 className="mb-3 text-sm font-medium">Entry diagnostics</h4>{data.diagnostics ? <ConfigFields value={data.diagnostics} /> : <p className="text-sm text-slate-400">The cause of blocked entries was not recorded for this older run. A confirmed rerun can record diagnostics.</p>}</section>
        {[["Monthly realized P&L", data.monthly, "month"], ["Instrument breakdown", data.instruments, "instrument__symbol"], ["Exit reasons", data.exit_reasons, "exit_reason"]].map(([label, values, key]) => <section key={key} className="rounded-lg border border-slate-800 p-3"><h4 className="mb-3 text-sm font-medium">{label}</h4>{values.length ? values.map((row, index) => <div key={index} className="flex justify-between gap-3 py-1 text-sm"><span className="text-slate-400">{key === "month" ? String(row[key]).slice(0, 7) : row[key]}</span><span>{formatCurrency(row.net_pnl)}</span></div>) : <p className="text-xs text-slate-400">No completed trades.</p>}</section>)}
        <ResearchStrategyPreview snapshot={data.snapshot} enums={enums} /></>}
      {onDetails && <Button size="sm" variant="outline" onClick={() => onDetails(evidence)}>View breakdowns and diagnostics</Button>}
    </>;
  } else if (evidence.tool === "compare_backtests") {
    content = <><h4 className="font-medium">Experiment comparison</h4><p className="text-xs text-amber-300">{data.differences.length ? `Configuration differences: ${data.differences.join(", ")}. These runs may not be directly comparable.` : "The recorded dates, rules, instruments and costs match."}</p>{data.reports.map((report) => <ResearchEvidence key={report.backtest_id} evidence={{ ...evidence, tool: "get_backtest_report", data: report }} enums={enums} detailed={detailed} />)}</>;
  } else if (evidence.tool === "validate_strategy_draft" || evidence.tool === "get_strategy_snapshot") {
    content = detailed ? <ResearchStrategyPreview snapshot={data.draft || data} enums={enums} /> : <><h4 className="font-medium">{(data.draft || data).name}</h4><p className="text-sm text-slate-400">{(data.draft || data).rule_groups?.length || 0} rule groups · {(data.draft || data).time_rule?.candle_timeframe} · {evidence.tool === "validate_strategy_draft" ? "Validated draft" : "Saved configuration"}</p>{onDetails && <Button size="sm" variant="outline" onClick={() => onDetails(evidence)}>Review rules and settings</Button>}</>;
  } else if (evidence.tool === "resolve_instruments") {
    content = <><p className="text-sm">{data.ambiguous ? "Choose a stock before continuing." : data.instruments.length ? "Resolved stock" : "No active NSE stock matched."}</p>{data.instruments.map((item) => <div key={item.id} className="flex items-center justify-between gap-3 text-sm text-slate-400"><p>{item.symbol} · {item.name}</p>{onChoose && <Button size="sm" variant="outline" onClick={() => onChoose(item)}>Use {item.symbol}</Button>}</div>)}</>;
  }
  return <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/40 p-4">
    <p className="text-xs text-indigo-300">{evidence.evidence_id} · {evidence.tool.replaceAll("_", " ")} · observed {formatDateTime(evidence.source_as_of || data.as_of)}{evidence.source_run_id ? ` · source turn #${evidence.source_run_id}` : ""}</p>
    {content}
    {detailed && <details className="text-xs text-slate-500"><summary className="cursor-pointer">Technical details</summary><pre className="scrollbar-thin-theme mt-3 max-h-80 overflow-auto whitespace-pre-wrap">{JSON.stringify(data, null, 2)}</pre></details>}
  </div>;
}
ResearchEvidence.propTypes = { evidence: PropTypes.object.isRequired, enums: PropTypes.object, detailed: PropTypes.bool, selected: PropTypes.array, onSelect: PropTypes.func, onResearch: PropTypes.func, onDetails: PropTypes.func, onChoose: PropTypes.func };
