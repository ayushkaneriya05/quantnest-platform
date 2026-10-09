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
      <h3 className="font-semibold text-foreground">{previousVersionNumber ? `${changes.length} change${changes.length === 1 ? "" : "s"} since version ${previousVersionNumber}` : "Initial configuration"}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{previousVersionNumber ? "Every saved configuration field is compared with the preceding version." : "This is the first saved snapshot of this strategy."}</p>
    </div>
    {previousVersionNumber && !changes.length && <p className="rounded-xl border border-border p-4 text-sm text-muted-foreground">The configuration is unchanged.</p>}
    {Object.entries(sections).map(([section, entries]) => <section key={section} className="space-y-3">
      <h4 className="text-sm font-semibold text-foreground">{section}</h4>
      {entries.map((change, index) => <div key={index} className="rounded-xl border border-border bg-card/40 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-medium text-foreground">{change.label}</p>
          <span className={`rounded-full px-2 py-0.5 text-xs capitalize ${change.kind === "added" ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300" : change.kind === "removed" ? "bg-rose-500/10 text-rose-700 dark:text-rose-300" : "bg-amber-500/10 text-amber-700 dark:text-amber-300"}`}>{change.kind}</span>
        </div>
        <div className="grid items-start gap-3 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
          <div className="min-w-0"><p className="mb-1 text-xs text-muted-foreground">Before</p><p className="whitespace-pre-wrap break-words text-sm text-muted-foreground">{change.kind === "added" ? "Not present" : formatStrategyValue(change.before, enums)}</p></div>
          <ArrowRight className="mt-5 hidden h-4 w-4 text-muted-foreground sm:block" aria-hidden="true" />
          <div className="min-w-0"><p className="mb-1 text-xs text-muted-foreground">After</p><p className="whitespace-pre-wrap break-words text-sm text-foreground">{change.kind === "removed" ? "Removed" : formatStrategyValue(change.after, enums)}</p></div>
        </div>
      </div>)}
    </section>)}
    <div className="border-t border-border pt-5"><h3 className="mb-4 font-semibold text-foreground">Saved configuration</h3><StrategyConfiguration snapshot={snapshot} /></div>
    <details className="rounded-xl border border-border p-4"><summary className="cursor-pointer text-xs text-muted-foreground">Technical details</summary><pre className="scrollbar-theme mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words text-xs text-muted-foreground">{JSON.stringify(snapshot, null, 2)}</pre></details>
  </div>;
}
StrategySnapshotViewer.propTypes = { snapshot: PropTypes.object.isRequired, changes: PropTypes.array, previousVersionNumber: PropTypes.number };
