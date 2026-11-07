import RefreshButton from "@/shared/components/RefreshButton";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/shared/components/ui/button";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { SourceTabs, ReviewFilters, MetricCard, TradeTable } from "@/features/journal/components/ReviewWorkspace.jsx";
import { useReviewWorkspace, displayNumber, displayMoney, modes } from "@/features/journal/hooks/useReviewWorkspace.js";
import TradeReviewDialog from "@/features/journal/components/TradeReviewDialog.jsx";

export default function TradeJournal() {
  const { filters, details, trades, loading, error, update, turnPage, setPageSize, reload } = useReviewWorkspace("journal");
  const [selected, setSelected] = useState(null);
  useEffect(() => { setSelected(null); }, [filters.source]);
  const actions = useMemo(() => <>
    <div className="hidden xl:block"><SourceTabs appearance="plain" source={filters.source} onChange={(source) => update({ source })} /></div>
    <RefreshButton onClick={reload} label="Refresh journal" disabled={loading} loading={loading} />
  </>, [filters, update, loading, reload]);
  useSetPageActions(actions);

  return <div className="page-content">
    <div className="xl:hidden"><SourceTabs source={filters.source} onChange={(source) => update({ source })} /></div>
    <ReviewFilters filters={filters} onChange={update} journal />
    <div className="grid grid-cols-2 gap-2 xl:grid-cols-4">
      <MetricCard label="Recorded closes" value={details?.closes ?? "—"} hint="Broker partial fills and manual reductions count separately" />
      <MetricCard label="Reviewed" value={details?.reviewed ?? "—"} tone="text-success" hint="Your saved trade reviews" />
      <MetricCard label="To review" value={details?.unreviewed ?? "—"} tone="text-warning" />
      <MetricCard label="Execution rating" value={details?.average_rating == null ? "N/A" : displayNumber(details.average_rating) + " / 5"} hint="Self-reported · rated reviews only" />
    </div>
    <p className="text-xs text-muted-foreground">{modes.find((mode) => mode.value === filters.source).description}</p>
    {error && <div role="alert" className="rounded-xl border border-loss/30 bg-loss/10 p-3 text-sm text-loss">
      {error}<Button variant="ghost" size="sm" onClick={reload}>Retry</Button>
    </div>}
    <TradeTable trades={trades} loading={loading} page={Number(filters.page || 1)} onPage={turnPage} onPageSize={setPageSize} onReview={setSelected} />
    {!!details?.mistake_tags?.length && <section className="rounded-xl border border-border bg-background/60 p-3">
      <h2 className="font-semibold">Patterns in your reviews</h2>
      <p className="mt-1 text-xs text-muted-foreground">Tags reflect your assessment. A close with several tags appears in each group.</p>
      <div className="mt-3 flex flex-wrap gap-2">{details.mistake_tags.map((item) => <span key={item.tag} className="rounded-full border border-border bg-card px-3 py-2 text-xs text-foreground">
        {item.tag}<span className="ml-2 font-semibold text-brand">{item.reviews} · {displayMoney(item.realized_pnl)}</span>
      </span>)}</div>
    </section>}
    {selected && <TradeReviewDialog key={selected.review?.id || selected.id} trade={selected} filters={filters} tags={details?.suggested_tags}
      onClose={() => setSelected(null)} onSaved={reload} />}
  </div>;
}
