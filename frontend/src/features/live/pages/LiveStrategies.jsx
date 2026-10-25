import { GlobalLoader, LoaderMark } from '@/shared/components/ui/global-loader';
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, Clock3, Pause, Play, RefreshCw, RotateCw, Settings, Zap, ShieldX } from "lucide-react";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { useLiveTradingData } from "@/features/live/hooks/useLiveTradingData.js";
import { liveTradingApi } from "@/shared/services/liveTradingApi";
import AllocationCapitalDialog from "@/features/strategies/components/AllocationCapitalDialog.jsx";
import SessionStatusFilter from "@/features/strategies/components/SessionStatusFilter.jsx";
import ChangeStrategyVersionDialog from "@/features/strategies/components/ChangeStrategyVersionDialog.jsx";
import LiveSyncStatus from "@/features/live/components/LiveSyncStatus.jsx";
import { formatBrokerAccount, formatDateTime, formatCurrency } from "@/shared/utils/formatters";
import { statusTone } from "@/shared/constants/statusColors";
import { customConfirm } from "@/shared/components/ui/custom-dialog";

export default function LiveStrategies() {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const data = useLiveTradingData({ notify });
  const [status, setStatus] = useState("all");
  const visibleSessions = status === "all" ? data.sessions : data.sessions.filter((session) => session.status === status);
  const [busy, setBusy] = useState(false);
  const [allocationSession, setAllocationSession] = useState(null);
  const [versionSession, setVersionSession] = useState(null);
  const runAction = async (action, success) => {
    try {
      setBusy(true);
      const response = await action();
      if (success) notify.success(success(response));
      await data.loadData(false);
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Live strategy action failed"));
    } finally {
      setBusy(false);
    }
  };

  const stopAndClose = async (session, alreadyStopped = false) => {
    const title = alreadyStopped ? "Close remaining positions?" : "Stop strategy and close positions?";
    const message = alreadyStopped
      ? `This submits market exit orders for open positions in ${session.strategy_name || "this deployment"}. Broker confirmation can arrive asynchronously; reconcile before assuming exposure is flat.`
      : `This stops new entries for ${session.strategy_name || "this deployment"} and submits market exit orders for its open positions. Broker confirmation can arrive asynchronously; reconcile before assuming exposure is flat.`;
    const action = alreadyStopped ? "Close positions" : "Stop & close";
    if (!(await customConfirm(message, title, action))) return;
    await runAction(() => liveTradingApi.stopSession(session.id, { close_positions: true }));
  };

  const pageActions = useMemo(() => (
    <>
      <div className="hidden lg:block"><LiveSyncStatus isConnected={data.isConnected} /></div>
      <Button onClick={() => navigate("/strategies")} className="bg-indigo-600 text-white hover:bg-indigo-700"><Zap className="mr-2 h-4 w-4" />Deploy strategy</Button>
      <Button variant="outline" onClick={data.refresh} disabled={data.refreshing} className="border-border text-foreground">{data.refreshing ? <LoaderMark className="mr-2 h-4 w-4" /> : <RefreshCw className="mr-2 h-4 w-4" />}Refresh</Button>
    </>
  ), [data.isConnected, data.refresh, data.refreshing, navigate]);
  useSetPageActions(pageActions);

  const activeCount = data.sessions.filter((session) => session.status === "RUNNING").length;
  const pausedCount = data.sessions.filter((session) => session.status === "PAUSED").length;
  const attentionCount = data.sessions.filter((session) => !session.broker_session_valid && session.status !== "STOPPED").length;

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="border-border bg-card/50"><CardContent className="p-5"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Running</p><p className="mt-2 text-2xl font-semibold text-emerald-700 dark:text-emerald-400">{activeCount}</p></CardContent></Card>
        <Card className="border-border bg-card/50"><CardContent className="p-5"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Paused</p><p className="mt-2 text-2xl font-semibold text-amber-700 dark:text-amber-300">{pausedCount}</p></CardContent></Card>
        <Card className="border-border bg-card/50"><CardContent className="p-5"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Authentication attention</p><p className="mt-2 text-2xl font-semibold text-rose-700 dark:text-rose-300">{attentionCount}</p><p className="mt-1 text-xs text-muted-foreground">Expired or unavailable broker session</p></CardContent></Card>
      </div>

      <SessionStatusFilter value={status} onValueChange={setStatus} />
      {data.loading ? (
        <Card className="border-border bg-card/60"><CardContent className="py-12 text-center text-muted-foreground"><GlobalLoader inline text="Loading live deployments…" /></CardContent></Card>
      ) : visibleSessions.length === 0 ? (
        <Card className="border-border bg-card/60"><CardContent className="py-14 text-center"><Zap className="mx-auto mb-3 h-8 w-8 text-muted-foreground" /><p className="text-foreground">{data.sessions.length ? "No sessions match this status" : "No live deployments"}</p><p className="mt-1 text-sm text-muted-foreground">Deploy a strategy to a connected broker account to see it here.</p></CardContent></Card>
      ) : (
        <div className="space-y-3">
          {visibleSessions.map((session) => {
            const canClose = ["RUNNING", "PAUSED", "ERROR", "STOPPING"].includes(session.status);
            const allocation = session.allocation;
            const brokerHealth = data.summary?.broker_accounts?.find((account) => String(account.credential_id) === String(session.broker_credential));
            return <Card key={session.id} className="overflow-hidden border-border bg-card/50">
              <CardHeader className="pb-3">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="flex min-w-[220px] items-start gap-3">
                    <div className="rounded-xl border border-border bg-secondary/60 p-2.5"><Zap className="h-5 w-5 text-indigo-700 dark:text-indigo-300" /></div>
                    <div>
                      <div className="flex flex-wrap items-center gap-2"><CardTitle className="text-lg text-foreground">{session.strategy_name || `Strategy #${session.strategy}`}</CardTitle>{allocation?.version_number && <Badge className="border-indigo-500/30 bg-indigo-500/10 text-indigo-700 dark:text-indigo-300">v{allocation.version_number}</Badge>}<Badge className={statusTone[session.status] || statusTone.STOPPED}>{session.status}</Badge>{allocation?.version_id !== session.applied_version && <Badge variant="outline">Version pending</Badge>}</div>
                      <p className="mt-1 text-sm text-muted-foreground">{formatBrokerAccount(session.broker_name, session.broker_label)}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {session.status === "RUNNING" && <Button size="sm" variant="outline" onClick={() => runAction(() => liveTradingApi.pauseSession(session.id))} disabled={busy}><Pause className="mr-2 h-4 w-4" />Pause</Button>}
                    {["PAUSED", "ERROR"].includes(session.status) && session.strategy_status === "ACTIVE" && session.live_trading_enabled && <Button size="sm" variant="outline" onClick={() => runAction(() => liveTradingApi.resumeSession(session.id))} disabled={busy}><Play className="mr-2 h-4 w-4" />Resume</Button>}
                    {session.status === "STOPPED" && session.strategy_status === "ACTIVE" && session.live_trading_enabled && <Button size="sm" variant="outline" onClick={() => runAction(() => liveTradingApi.resumeSession(session.id))} disabled={busy}><Play className="mr-2 h-4 w-4" />Start</Button>}
                    {!["RUNNING", "STOPPING"].includes(session.status) && (session.strategy_status !== "ACTIVE" || !session.live_trading_enabled) && <span className="px-2 py-2 text-xs text-amber-700 dark:text-amber-300">Activate the strategy and enable live trading to resume.</span>}
                    {canClose && <Button size="sm" className="bg-rose-700 text-white hover:bg-rose-600" onClick={() => stopAndClose(session)} disabled={busy}><ShieldX className="mr-2 h-4 w-4" />{session.status === "STOPPING" ? "Retry close" : "Stop & close"}</Button>}
                    {session.status === "STOPPED" && Number(session.open_positions || 0) > 0 && <Button size="sm" className="bg-rose-700 text-white hover:bg-rose-600" onClick={() => stopAndClose(session, true)} disabled={busy}><ShieldX className="mr-2 h-4 w-4" />Close remaining</Button>}
                    {allocation && <Button size="sm" variant="outline" disabled={busy} onClick={() => setAllocationSession(session)}><Settings className="mr-2 h-4 w-4" />Capital</Button>}
                    {allocation && <Button size="sm" variant="outline" disabled={busy} onClick={() => setVersionSession(session)}><RotateCw className="mr-2 h-4 w-4" />Version</Button>}
                    <Button size="sm" variant="outline" onClick={() => runAction(() => liveTradingApi.syncSession(session.id), (response) => `Reconciled ${response.data.synced_orders} orders`)} disabled={busy}><RefreshCw className="mr-2 h-4 w-4" />Reconcile orders</Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 rounded-xl border border-border bg-background/40 p-4 sm:grid-cols-2 xl:grid-cols-5">
                  <div><p className="text-xs text-muted-foreground">Allocation</p><p className="mt-1 font-medium text-foreground">{formatCurrency(Number(allocation?.allocated_capital || 0))}</p></div>
                  <div><p className="text-xs text-muted-foreground">Used / reserved</p><p className="mt-1 font-medium text-foreground">{formatCurrency(Number(allocation?.used_capital || 0))} / {formatCurrency(Number(allocation?.reserved_capital || 0))}</p></div>
                  <div><p className="text-xs text-muted-foreground">Available</p><p className="mt-1 font-medium text-foreground">{formatCurrency(Number(allocation?.available_capital || 0))}</p></div>
                  <div><p className="text-xs text-muted-foreground">Lifetime P&amp;L before charges</p><p className={`mt-1 font-medium ${Number(session.pnl || 0) >= 0 ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"}`}>{formatCurrency(Number(session.pnl || 0))}</p></div>
                  <div><p className="text-xs text-muted-foreground">Trades · open positions · active orders</p><p className="mt-1 font-medium text-foreground">{session.trades_count || 0} · {session.open_positions || 0} · {session.active_orders || 0}</p></div>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted-foreground">
                  {session.status === "PAUSED" && <span className="text-amber-700 dark:text-amber-300">Entries paused; exit management remains active.</span>}
                  {session.status === "STOPPED" && Number(session.open_positions || 0) > 0 && <span className="text-rose-700 dark:text-rose-300">Strategy stopped with open positions remaining. Review broker positions before treating exposure as closed.</span>}
                  <span className="inline-flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${session.broker_session_valid ? "bg-emerald-500" : "bg-rose-500"}`} />Broker authentication: {session.broker_session_valid ? "Valid" : "Reconnect required"}</span>
                  <span>Broker order updates: <span className={brokerHealth?.order_websocket_status === "connected" ? "text-emerald-700 dark:text-emerald-300" : brokerHealth?.order_websocket_status === "reconciliation" ? "text-amber-700 dark:text-amber-300" : "text-rose-700 dark:text-rose-300"}>{brokerHealth?.order_websocket_status || "unknown"}</span></span>
                      <span className="inline-flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" />Started {formatDateTime(session.started_at)}</span>
                  {session.error_message && <span className="inline-flex items-center gap-1 text-rose-700 dark:text-rose-300"><AlertTriangle className="h-3.5 w-3.5" />{session.error_message}</span>}
                  {allocation?.is_over_allocated && <span className="text-rose-700 dark:text-rose-300">{allocation.breach_reason || "Allocation exceeds broker equity"}</span>}
                </div>
              </CardContent>
            </Card>;
          })}
        </div>
      )}

      {allocationSession && <AllocationCapitalDialog strategyName={allocationSession.strategy_name}
        currentAmount={allocationSession.allocation.allocated_capital}
        onApply={(amount) => liveTradingApi.updateAllocation(allocationSession.allocation.id, { allocation_amount: amount })}
        onClose={() => setAllocationSession(null)} onSuccess={() => data.loadData(false)} />}
      {versionSession && <ChangeStrategyVersionDialog
        strategyId={versionSession.strategy}
        strategyName={versionSession.strategy_name}
        currentVersionId={versionSession.allocation.version_id}
        currentVersionNumber={versionSession.allocation.version_number}
        onApply={(versionId) => liveTradingApi.deployVersion(versionSession.allocation.id, { version_id: versionId })}
        onClose={() => setVersionSession(null)}
        onSuccess={() => data.loadData(false)}
      />}
    </div>
  );
}
