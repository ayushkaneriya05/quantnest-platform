import { useEffect, useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { SourceTabs, ReviewFilters, MetricCard, TradeTable } from "./components/ReviewWorkspace";
import { useReviewWorkspace, displayNumber, displayMoney, modes } from "./components/useReviewWorkspace";
import TradeReviewDialog from "./components/TradeReviewDialog";

export default function TradeJournal() {
  const { filters, details, trades, loading, error, update, turnPage, reload } = useReviewWorkspace("journal");
  const [selected, setSelected] = useState(null);
  useEffect(() => { setSelected(null); }, [filters.source]);
  const actions = useMemo(() => <>
    <div className="hidden xl:block"><SourceTabs source={filters.source} onChange={(source) => update({ source })} /></div>
    <Button variant="outline" size="sm" onClick={reload} disabled={loading} aria-label="Refresh journal">
      <RefreshCw size={15} /><span className="ml-2 hidden lg:inline">Refresh</span>
    </Button>
  </>, [filters, update, loading, reload]);
  useSetPageActions(actions);

  return <div className="container-padding space-y-4 py-4">
    <div className="xl:hidden"><SourceTabs source={filters.source} onChange={(source) => update({ source })} /></div>
    <ReviewFilters filters={filters} onChange={update} journal />
    <div className="grid grid-cols-2 gap-2 xl:grid-cols-4">
      <MetricCard label="Recorded closes" value={details?.closes ?? "—"} hint="Partial exits count separately" />
      <MetricCard label="Reviewed" value={details?.reviewed ?? "—"} tone="text-emerald-400" hint="Your saved trade reviews" />
      <MetricCard label="To review" value={details?.unreviewed ?? "—"} tone="text-amber-300" />
      <MetricCard label="Execution rating" value={details?.average_rating == null ? "N/A" : displayNumber(details.average_rating) + " / 5"} hint="Self-reported · rated reviews only" />
    </div>
    <p className="text-xs text-slate-400">{modes.find((mode) => mode.value === filters.source).description}</p>
    {error && <div role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">
      {error}<Button variant="ghost" size="sm" onClick={reload}>Retry</Button>
    </div>}
    <TradeTable trades={trades} loading={loading} page={Number(filters.page || 1)} onPage={turnPage} onReview={setSelected} />
    {!!details?.mistake_tags?.length && <section className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
      <h2 className="font-semibold">Patterns in your reviews</h2>
      <p className="mt-1 text-xs text-slate-500">Tags reflect your assessment. A close with several tags appears in each group.</p>
      <div className="mt-3 flex flex-wrap gap-2">{details.mistake_tags.map((item) => <span key={item.tag} className="rounded-full border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300">
        {item.tag}<span className="ml-2 font-semibold text-indigo-300">{item.reviews} · {displayMoney(item.realized_pnl)}</span>
      </span>)}</div>
    </section>}
    {selected && <TradeReviewDialog key={selected.review?.id || selected.id} trade={selected} filters={filters} tags={details?.suggested_tags}
      onClose={() => setSelected(null)} onSaved={reload} />}
  </div>;
}
