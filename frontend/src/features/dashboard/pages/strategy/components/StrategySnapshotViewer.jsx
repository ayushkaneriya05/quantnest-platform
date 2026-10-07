import PropTypes from "prop-types";
import { ArrowRight } from "lucide-react";
import { useEnums } from "@/shared/context/EnumsContext";
import StrategyConfiguration from "@/shared/components/StrategyConfiguration";
import { formatStrategyValue } from "@/shared/utils/strategyConfiguration";

export default function StrategySnapshotViewer({ snapshot, changes = [], previousVersionNumber }) {
  const { enums } = useEnums();
  const sections = Object.groupBy ? Object.groupBy(changes, (item) => item.section) :
    changes.reduce((result, item) => ({ ...result, [item.section]: [...(result[item.section] || []), item] }), {});
  return <div className="space-y-6">
    <div>
      <h3 className="font-semibold text-slate-100">{previousVersionNumber ? `${changes.length} change${changes.length === 1 ? "" : "s"} since version ${previousVersionNumber}` : "Initial configuration"}</h3>
      <p className="mt-1 text-sm text-slate-400">{previousVersionNumber ? "Every saved configuration field is compared with the preceding version." : "This is the first saved snapshot of this strategy."}</p>
    </div>
    {previousVersionNumber && !changes.length && <p className="rounded-xl border border-slate-800 p-4 text-sm text-slate-400">The configuration is unchanged.</p>}
    {Object.entries(sections).map(([section, entries]) => <section key={section} className="space-y-3">
      <h4 className="text-sm font-semibold text-slate-200">{section}</h4>
      {entries.map((change, index) => <div key={index} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-medium text-slate-200">{change.label}</p>
          <span className={`rounded-full px-2 py-0.5 text-xs capitalize ${change.kind === "added" ? "bg-emerald-500/10 text-emerald-300" : change.kind === "removed" ? "bg-rose-500/10 text-rose-300" : "bg-amber-500/10 text-amber-300"}`}>{change.kind}</span>
        </div>
        <div className="grid items-start gap-3 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
          <div className="min-w-0"><p className="mb-1 text-xs text-slate-500">Before</p><p className="whitespace-pre-wrap break-words text-sm text-slate-400">{change.kind === "added" ? "Not present" : formatStrategyValue(change.before, enums)}</p></div>
          <ArrowRight className="mt-5 hidden h-4 w-4 text-slate-500 sm:block" aria-hidden="true" />
          <div className="min-w-0"><p className="mb-1 text-xs text-slate-500">After</p><p className="whitespace-pre-wrap break-words text-sm text-slate-100">{change.kind === "removed" ? "Removed" : formatStrategyValue(change.after, enums)}</p></div>
        </div>
      </div>)}
    </section>)}
    <div className="border-t border-slate-800 pt-5"><h3 className="mb-4 font-semibold text-slate-100">Saved configuration</h3><StrategyConfiguration snapshot={snapshot} /></div>
    <details className="rounded-xl border border-slate-800 p-4"><summary className="cursor-pointer text-xs text-slate-400">Technical details</summary><pre className="scrollbar-theme mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words text-xs text-slate-400">{JSON.stringify(snapshot, null, 2)}</pre></details>
  </div>;
}
StrategySnapshotViewer.propTypes = { snapshot: PropTypes.object.isRequired, changes: PropTypes.array, previousVersionNumber: PropTypes.number };
