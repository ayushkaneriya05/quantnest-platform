import { GlobalLoader, LoaderMark } from '@/shared/components/ui/global-loader';
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, Clock3, FlaskConical, Pause, Play, RefreshCw, RotateCcw, Settings, ShieldX, Trash2, Wallet } from "lucide-react";
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
import { usePaperPositionsPnL } from "@/shared/hooks/useLivePositionsPnL";
import { usePaperTradingUpdate, usePaperTradingWebSocket } from "@/shared/hooks/usePaperTradingWebSocket";
import { paperApi } from "@/shared/services/paperApi";
import { formatCurrency, formatDateTime } from "@/shared/utils/formatters";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { statusTone } from "@/shared/constants/statusColors";
import { customConfirm } from "@/shared/components/ui/custom-dialog";

export default function PaperDeployments() {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const [sessions, setSessions] = useState([]);
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("all");
  const [capitalSession, setCapitalSession] = useState(null);
  const [versionSession, setVersionSession] = useState(null);
  const [costSession, setCostSession] = useState(null);
  usePageTitle({ title: "Paper deployments", subtitle: "Manage strategy sessions, capital and deployed versions" });
  usePaperTradingWebSocket();
  const lastMessage = usePaperTradingUpdate();
  const { livePnLByPositionId } = usePaperPositionsPnL(positions);

  const loadData = useStableCallback(async () => {
    try {
      const [sessionResponse, positionResponse] = await Promise.all([paperApi.getSessions(), paperApi.getPositions()]);
      setSessions(sessionResponse.data);
      setPositions(positionResponse.data);
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to load Paper deployments"));
    } finally { setLoading(false); }
  });
  useEffect(() => { loadData(); }, [loadData]);
  useEffect(() => {
    if (!lastMessage) return undefined;
    const timer = setTimeout(loadData, 150);
    return () => clearTimeout(timer);
  }, [lastMessage, loadData]);

  const refresh = useStableCallback(async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  });
  const actions = useMemo(() => <>
    <Button variant="outline" onClick={() => navigate("/paper/capital")}><Wallet className="mr-2 h-4 w-4" />Wallet</Button>
    <Button onClick={() => navigate("/strategies")}><FlaskConical className="mr-2 h-4 w-4" />Deploy strategy</Button>
    <Button variant="outline" onClick={refresh} disabled={refreshing}>{refreshing ? <LoaderMark className="mr-2 h-4 w-4" /> : <RefreshCw className="mr-2 h-4 w-4" />}Refresh</Button>
  </>, [navigate, refresh, refreshing]);
  useSetPageActions(actions);

  const unrealizedByAccount = useMemo(() => positions.reduce((totals, position) => {
    totals[position.account] = (totals[position.account] || 0) + (livePnLByPositionId[position.id]?.pnl ?? Number(position.unrealized_pnl));
    return totals;
  }, {}), [positions, livePnLByPositionId]);
  const visible = status === "all" ? sessions : sessions.filter((session) => session.status === status);
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

  return <div className="container-padding space-y-6 py-6 lg:py-8">
    <div className="grid gap-4 sm:grid-cols-3">
      {[["Running", "RUNNING"], ["Paused", "PAUSED"], ["Stopped", "STOPPED"]].map(([label, value]) =>
        <Card key={value} className="border-border bg-card/50"><CardContent className="p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
          <p className="mt-2 text-2xl font-semibold">{sessions.filter((session) => session.status === value).length}</p>
        </CardContent></Card>)}
    </div>
    <SessionStatusFilter value={status} onValueChange={setStatus} />
    {loading ? <p className="py-12 text-center text-muted-foreground"><GlobalLoader inline text="Loading Paper deployments…" /></p> :
      visible.length === 0 ? <Card className="border-border bg-card/50"><CardContent className="py-14 text-center">
        <FlaskConical className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
        <p>{sessions.length ? "No sessions match this status" : "No Paper deployments"}</p>
        {!sessions.length && <p className="mt-2 text-sm text-muted-foreground">Fund your Paper wallet, then deploy a saved version from My Strategies.</p>}
      </CardContent></Card> :
      <div className="space-y-3">{visible.map((session) => {
        const pnl = Number(session.realized_pnl) + (unrealizedByAccount[session.account] || 0);
        const canStart = ["PAUSED", "STOPPED", "ERROR"].includes(session.status) && session.strategy_status === "ACTIVE" && session.paper_trading_enabled;
        const stopped = session.status === "STOPPED";
        return <Card key={session.id} className="overflow-hidden border-border bg-card/50">
          <CardHeader className="pb-3"><div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex min-w-0 items-start gap-3">
              <div className="rounded-xl border border-border bg-secondary/60 p-2.5"><FlaskConical className="h-5 w-5 text-cyan-700 dark:text-cyan-300" /></div>
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
            <div className="grid gap-4 rounded-xl border border-border bg-background/40 p-4 sm:grid-cols-2 xl:grid-cols-5">
              {[["Allocated capital", formatCurrency(session.allocated_capital)], ["Margin used", formatCurrency(session.used_capital)],
                ["Available capital", formatCurrency(session.available_capital)], ["Lifetime P&L", formatCurrency(pnl)],
                ["Trades · open positions", `${session.trades_count} · ${session.open_positions}`]].map(([label, value]) =>
                <div key={label}><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 font-medium">{value}</p></div>)}
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" />Started {formatDateTime(session.started_at)}</span>
              <span>Slippage: {Number(session.slippage_pct)}% · Charges: {session.include_charges ? session.charge_profile_name || "No profile" : "Off"}</span>
              {session.status === "PAUSED" && <span className="text-amber-700 dark:text-amber-300">Entries paused; exit management remains active.</span>}
              {session.error_message && <span className="inline-flex items-center gap-1 text-rose-700 dark:text-rose-300"><AlertTriangle className="h-3.5 w-3.5" />{session.error_message}</span>}
            </div>
          </CardContent>
        </Card>;
      })}</div>}
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
