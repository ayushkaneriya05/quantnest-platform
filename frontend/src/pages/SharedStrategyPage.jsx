import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Lock, Share2, RefreshCw } from "lucide-react";
import { strategyApi } from "@/shared/services/strategyApi";
import StrategyConfiguration from "@/shared/components/StrategyConfiguration";
import { GlobalLoader } from "@/shared/components/ui/global-loader";
import { Button } from "@/shared/components/ui/button";

export default function SharedStrategyPage() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setData(null);
    strategyApi.getShared(id, controller.signal).then(setData).catch((failure) => {
      if (!controller.signal.aborted) setError(failure.response?.status === 404 ? "This strategy is private or the link is no longer available." : "Could not load this strategy. Please try again.");
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [id, revision]);
  return <div className="scrollbar-theme min-h-dvh bg-background text-foreground">
    <header className="border-b border-border bg-card"><div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-5 py-4">
      <Link to="/" className="text-xl font-semibold">QuantNest</Link>
      <span className="flex items-center gap-2 text-sm text-muted-foreground"><Lock className="h-4 w-4" />Read-only strategy</span>
    </div></header>
    <main className="mx-auto max-w-5xl space-y-6 px-5 py-8">
      {loading ? <div className="flex justify-center py-20"><GlobalLoader /></div> : error ? <section className="rounded-xl border border-border bg-card p-6">
        <h1 className="mb-3 text-xl font-semibold">Strategy unavailable</h1><p role="alert" className="text-muted-foreground">{error}</p>
        <div className="mt-5 flex gap-3"><Button onClick={() => setRevision((value) => value + 1)}>Retry</Button><Button variant="outline" asChild><Link to="/">Home</Link></Button></div>
      </section> : data && <>
        <section className="flex flex-wrap items-start justify-between gap-4">
          <div><p className="mb-2 flex items-center gap-2 text-xs text-muted-foreground"><Share2 className="h-4 w-4" />Shared strategy configuration</p>
            <h1 className="text-2xl font-semibold">{data.configuration.name}</h1>
            <p className="mt-2 text-sm text-muted-foreground">Current saved configuration</p></div>
          <Button variant="outline" onClick={() => setRevision((value) => value + 1)}><RefreshCw />Refresh</Button>
        </section>
        <StrategyConfiguration snapshot={data.configuration} />
      </>}
    </main>
  </div>;
}
