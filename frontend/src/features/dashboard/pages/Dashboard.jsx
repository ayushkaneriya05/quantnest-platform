import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Brain, Layers, FlaskConical, Radio } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { executionReportsApi } from "@/shared/services/executionReportsApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { displayMoney, displayNumber, modes, pnlTone } from "./journal/components/useReviewWorkspace";

export default function Dashboard() {
  const [reports, setReports] = useState({});
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    Promise.allSettled(modes.map((mode) => executionReportsApi.report({ source: mode.value }, controller.signal))).then((responses) => {
      if (controller.signal.aborted) return;
      setReports(Object.fromEntries(responses.map((response, index) => [modes[index].value,
        response.status === "fulfilled" ? { data: response.value.data } : { error: getApiErrorMessage(response.reason, "Could not load results") }])));
      setLoading(false);
    });
    return () => controller.abort();
  }, []);
  return <div className="container-padding space-y-6 py-6">
    <section className="rounded-2xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/10 via-slate-950 to-slate-950 p-6 sm:p-8">
      <p className="text-xs font-medium uppercase tracking-widest text-indigo-300">Your trading workspace</p><h2 className="mt-3 text-2xl font-semibold sm:text-3xl">Research, test, execute, and review.</h2>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">Keep your manual terminal, strategy simulations, and live broker execution clearly separated as you develop your ideas.</p>
      <div className="mt-5 flex flex-wrap gap-3"><Link to="/dashboard/analysis/ai-research-assistant"><Button><Brain size={16} className="mr-2" />Start research</Button></Link><Link to="/dashboard/strategy/list"><Button variant="outline"><Layers size={16} className="mr-2" />My strategies</Button></Link><Link to="/dashboard/backtest"><Button variant="outline">Backtesting lab</Button></Link></div>
    </section>
    <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-lg font-semibold">Execution review</h2><p className="text-xs text-slate-500">Recorded closes · last 30 calendar days</p></div>
    <div className="grid gap-4 lg:grid-cols-3">{modes.map(({ value, label, icon: Icon, description }) => {
      const result = reports[value];
      const summary = result?.data?.summary;
      return <section key={value} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-5">
        <div className="flex items-center gap-3"><div className="rounded-xl bg-indigo-500/10 p-3 text-indigo-300"><Icon size={20} /></div><h3 className="font-semibold">{label}</h3></div><p className="mt-3 text-xs text-slate-500">{description}</p>
        {result?.error ? <p role="alert" className="mt-4 text-sm text-rose-300">{result.error}</p> : <><p className={`mt-5 text-2xl font-semibold tabular-nums ${pnlTone(summary?.realized_pnl)}`}>{loading ? "—" : displayMoney(summary?.realized_pnl)}</p><p className="mt-2 text-xs text-slate-400">{summary?.closes ?? "—"} closes · {summary?.win_rate == null ? "N/A" : displayNumber(summary.win_rate) + "%"} win rate</p></>}
        <div className="mt-5 flex gap-3"><Link to={`/dashboard/journal/reports?source=${value}`} className="inline-flex items-center gap-1 text-sm text-indigo-300 hover:text-indigo-200">Report<ArrowUpRight size={15} /></Link><Link to={`/dashboard/journal?source=${value}`} className="text-sm text-slate-400 hover:text-slate-100">Journal</Link></div>
      </section>;
    })}</div>
    <div className="grid gap-4 sm:grid-cols-2"><Link to="/dashboard/paper" className="flex items-center justify-between rounded-2xl border border-slate-800 p-5 hover:bg-slate-900/50"><span className="flex items-center gap-3"><FlaskConical size={20} className="text-emerald-400" />Paper execution</span><ArrowUpRight size={18} className="text-slate-500" /></Link><Link to="/dashboard/live/strategies" className="flex items-center justify-between rounded-2xl border border-slate-800 p-5 hover:bg-slate-900/50"><span className="flex items-center gap-3"><Radio size={20} className="text-amber-300" />Live execution</span><ArrowUpRight size={18} className="text-slate-500" /></Link></div>
  </div>;
}
