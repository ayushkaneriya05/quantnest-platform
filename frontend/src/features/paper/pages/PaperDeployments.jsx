import Pagination from "@/shared/components/Pagination";
import { usePagination, useQueryState } from "@/shared/hooks/usePagination";
import RefreshButton from "@/shared/components/RefreshButton";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, Clock3, FlaskConical, Pause, Play, RotateCcw, Settings, ShieldX, Trash2, Wallet } from "lucide-react";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import AllocationCapitalDialog from "@/features/strategies/components/AllocationCapitalDialog";
import ChangeStrategyVersionDialog from "@/features/strategies/components/ChangeStrategyVersionDialog";
import SessionStatusFilter from "@/features/strategies/components/SessionStatusFilter";
import PaperExecutionCostsDialog from "@/features/paper/components/PaperExecutionCostsDialog";
import { useStableCallback } from "@/shared/hooks/useStableCallback";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { usePageTitle } from "@/shared/hooks/use-page-title";
import { usePaperTradingUpdate, usePaperTradingWebSocket } from "@/shared/hooks/usePaperTradingWebSocket";
import { paperApi } from "@/shared/services/paperApi";
import { formatCurrency, formatDateTime } from "@/shared/utils/formatters";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { statusTone } from "@/shared/constants/statusColors";
import { customConfirm } from "@/shared/components/ui/custom-dialog";
import { useLivePositionSummary } from "@/shared/hooks/useLivePositionsPnL";

export default function PaperDeployments() {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const [sessions, setSessions] = useState([]);
  const [snapshot, setValuation] = useState({ by_account: {} });
  const valuation = useLivePositionSummary(snapshot);
  const [summary, setSummary] = useState({ statuses: {} });
  const [metadata, setMetadata] = useState({ count: 0 });
  const request = useRef(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useQueryState("status", "all", { namespace: "deployments", replace: false });
  const [capitalSession, setCapitalSession] = useState(null);
  const [versionSession, setVersionSession] = useState(null);
  const [costSession, setCostSession] = useState(null);
  usePageTitle({ title: "Paper deployments", subtitle: "Manage strategy sessions, capital and deployed versions" });
  usePaperTradingWebSocket();
  const lastMessage = usePaperTradingUpdate();
  const { page, pageSize, setPage, setPageSize, accept } = usePagination(status, "deployments");

  const loadData = useStableCallback(async () => {
    const generation = ++request.current;
    setRefreshing(true); setError("");
    try {
      const sessionResponse = await paperApi.getSessions({ page, page_size: pageSize, ...(status === 'all' ? {} : { status }) });
      if (generation !== request.current) return;
      const ids = sessionResponse.data.results.map(session => session.account_id || session.account).filter(Boolean);
      const [counts, positions] = await Promise.all([paperApi.getSessionSummary(), ids.length ? paperApi.getPositionsSummary({ account_ids: ids.join(',') }) : Promise.resolve({ data: { by_account: {} } })]);
      if (generation !== request.current) return;
      setSessions(sessionResponse.data.results); setMetadata(sessionResponse.data); accept(sessionResponse.data);
      setSummary(counts.data); setValuation(positions.data);
    } catch (error) {
      if (generation === request.current) setError(getApiErrorMessage(error, "Failed to load Paper deployments"));
    } finally {
      if (generation === request.current) { setLoading(false); setRefreshing(false); }
    }
  });
  useEffect(() => { loadData(); const guard = request; return () => { guard.current++; }; }, [loadData, page, pageSize, status]);
  useEffect(() => {
    if (!lastMessage) return undefined;
    const timer = setTimeout(loadData, 150);
    return () => clearTimeout(timer);
  }, [lastMessage, loadData]);

  const refresh = useStableCallback(async () => {
    await loadData();
  });
  const actions = useMemo(() => <>
    <Button variant="outline" onClick={() => navigate("/paper/capital")}><Wallet className="mr-2 h-4 w-4" />Wallet</Button>
    <Button onClick={() => navigate("/strategies")}><FlaskConical className="mr-2 h-4 w-4" />Deploy strategy</Button>
    <RefreshButton onClick={refresh} label="Refresh paper deployments" disabled={refreshing} loading={refreshing} />
  </>, [navigate, refresh, refreshing]);
  useSetPageActions(actions);

  const unrealizedByAccount = Object.fromEntries(Object.entries(valuation.by_account).map(([id, value]) => [id, Number(value.unrealized_pnl)]));
  async function runAction(action, message) {
    setBusy(true);
    try {
      await action();
      if (message) notify.success(message);
      await loadData();
    } catch (error) { notify.error(getApiErrorMessage(error, "Paper deployment action failed")); }
    finally { setBusy(false); }
  }
  async function stop(session) {
    if (await customConfirm(`Stop new entries and close open positions in ${session.name}?`, "Stop Paper session", "Stop & close")) {
      await runAction(() => paperApi.stopSession(session.id), "Stop requested");
    }
  }
  async function remove(session) {
    if (await customConfirm(
      `Remove ${session.name} and its execution history? Remaining cash returns to your Paper wallet.`,
      "Remove Paper deployment", "Remove deployment",
    )) await runAction(() => paperApi.deleteSession(session.id), "Paper deployment removed");
  }
  async function reset(session) {
    if (await customConfirm(
      "Restore this session's balance to its currently allocated capital using the Paper wallet? Trade history is retained.",
      "Reset session balance", "Reset balance",
    )) await runAction(() => paperApi.resetSession(session.id), "Session balance reset");
  }

  return <div className="page-content">
    <div className="grid gap-3 sm:grid-cols-3">
      {[["Running", "RUNNING"], ["Paused", "PAUSED"], ["Stopped", "STOPPED"]].map(([label, value]) =>
        <Card key={value} className="border-border bg-card/50"><CardContent className="p-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
          <p className="mt-2 text-2xl font-semibold">{summary.statuses[value] || 0}</p>
        </CardContent></Card>)}
    </div>
    <SessionStatusFilter value={status} onValueChange={setStatus} />
    {error ? <WorkspaceState error={error} onRetry={loadData} /> : loading ? <p className="py-12 text-center text-muted-foreground"><GlobalLoader inline text="Loading Paper deployments…" /></p> :
      sessions.length === 0 ? <Card className="border-border bg-card/50"><CardContent className="py-14 text-center">
        <FlaskConical className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
        <p>{summary.total > 0 ? "No sessions match this status" : "No Paper deployments"}</p>
        {!summary.total && <p className="mt-2 text-sm text-muted-foreground">Fund your Paper wallet, then deploy a saved version from My Strategies.</p>}
      </CardContent></Card> :
      <div className="space-y-3">{sessions.map((session) => {
        const pnl = Number(session.realized_pnl) + (unrealizedByAccount[session.account] || 0);
        const canStart = ["PAUSED", "STOPPED", "ERROR"].includes(session.status) && session.strategy_status === "ACTIVE" && session.paper_trading_enabled;
        const stopped = session.status === "STOPPED";
        return <Card key={session.id} className="overflow-hidden border-border bg-card/50">
          <CardHeader className="pb-3"><div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-3">
              <div className="rounded-xl border border-border bg-secondary/60 p-2.5"><FlaskConical className="h-5 w-5 text-brand" /></div>
              <div><div className="flex flex-wrap items-center gap-2">
                <CardTitle className="break-words text-lg">{session.strategy_name}</CardTitle>
                {session.deployed_version && <Badge variant="outline">v{session.deployed_version.version_number}</Badge>}
                {session.deployed_version?.id !== session.applied_version && <Badge variant="outline">Version pending</Badge>}
                <Badge className={statusTone[session.status] || statusTone.STOPPED}>{session.status}</Badge>
              </div><p className="mt-1 text-sm text-muted-foreground">Session S{session.id}</p></div>
            </div>
            <div className="flex flex-wrap gap-2">
              {session.status === "RUNNING" && <Button size="sm" variant="outline" disabled={busy} onClick={() => runAction(() => paperApi.pauseSession(session.id))}><Pause className="mr-2 h-4 w-4" />Pause</Button>}
              {canStart && <Button size="sm" variant="outline" disabled={busy} onClick={() => runAction(() => paperApi.resumeSession(session.id))}><Play className="mr-2 h-4 w-4" />{stopped ? "Start" : "Resume"}</Button>}
              {!stopped && <Button size="sm" variant="outline" disabled={busy} onClick={() => stop(session)}><ShieldX className="mr-2 h-4 w-4" />{session.status === "STOPPING" ? "Retry close" : "Stop & close"}</Button>}
              <Button size="sm" variant="outline" disabled={busy} onClick={() => setCapitalSession(session)}><Wallet className="mr-2 h-4 w-4" />Capital</Button>
              <Button size="sm" variant="outline" disabled={busy} onClick={() => setVersionSession(session)}><RotateCcw className="mr-2 h-4 w-4" />Version</Button>
              {stopped && <Button size="sm" variant="outline" disabled={busy || session.open_positions > 0} onClick={() => setCostSession(session)}><Settings className="mr-2 h-4 w-4" />Costs</Button>}
              {stopped && <Button size="sm" variant="outline" disabled={busy} onClick={() => reset(session)}>Reset balance</Button>}
              {stopped && <Button size="sm" variant="outline" disabled={busy} onClick={() => remove(session)}><Trash2 className="mr-2 h-4 w-4" />Remove</Button>}
              <Button size="sm" variant="outline" onClick={() => navigate(`/paper/portfolio?account_id=${session.account}`)}>Portfolio</Button>
            </div>
          </div></CardHeader>
          <CardContent>
            <div className="grid gap-3 rounded-xl border border-border bg-background/40 p-3 sm:grid-cols-2 xl:grid-cols-5">
              {[["Allocated capital", formatCurrency(session.allocated_capital)], ["Used / reserved", `${formatCurrency(session.used_capital)} / ${formatCurrency(session.reserved_capital)}`],
                ["Available capital", formatCurrency(session.available_capital)], ["Lifetime P&L", formatCurrency(pnl)],
                ["Trades · open positions", `${session.trades_count} · ${session.open_positions}`]].map(([label, value]) =>
                <div key={label}><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 font-medium">{value}</p></div>)}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" />Started {formatDateTime(session.started_at)}</span>
              <span>Slippage: {Number(session.slippage_pct)}% · Charges: {session.include_charges ? session.charge_profile_name || "No profile" : "Off"}</span>
              {session.status === "PAUSED" && <span className="text-warning">Entries paused; exit management remains active.</span>}
              {session.error_message && <span className="inline-flex items-center gap-1 text-loss"><AlertTriangle className="h-3.5 w-3.5" />{session.error_message}</span>}
            </div>
          </CardContent>
        </Card>;
      })}</div>}
    <Pagination {...metadata} page={page} pageSize={pageSize} loading={loading || refreshing} onPageChange={setPage} onPageSizeChange={setPageSize} label="Paper deployment pages" />
    {capitalSession && <AllocationCapitalDialog strategyName={capitalSession.strategy_name} currentAmount={capitalSession.allocated_capital}
      onApply={(amount) => paperApi.updateAllocation(capitalSession.id, { allocation_amount: amount })}
      onClose={() => setCapitalSession(null)} onSuccess={loadData} />}
    {versionSession && <ChangeStrategyVersionDialog strategyId={versionSession.strategy} strategyName={versionSession.strategy_name}
      currentVersionId={versionSession.deployed_version?.id} currentVersionNumber={versionSession.deployed_version?.version_number}
      onApply={(versionId) => paperApi.deployVersion(versionSession.id, { version_id: versionId })}
      onClose={() => setVersionSession(null)} onSuccess={loadData} />}
    {costSession && <PaperExecutionCostsDialog session={costSession} onClose={() => setCostSession(null)} onSuccess={loadData} />}
  </div>;
}
