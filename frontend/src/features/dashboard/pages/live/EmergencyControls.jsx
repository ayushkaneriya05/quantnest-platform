import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Pause, Play, Power, RefreshCw, ShieldX } from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { liveTradingApi } from "@/shared/services/liveTradingApi";

import { statusTone } from "@/shared/constants/statusColors";

export default function EmergencyControls() {
  const { notify } = useNotifications();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState("");

  const loadSessions = async () => {
    try {
      setLoading(true);
      const response = await liveTradingApi.getSessions();
      setSessions(Array.isArray(response.data?.results) ? response.data.results : response.data || []);
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load live emergency controls");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const handleAction = async (key, action, message) => {
    try {
      setBusyAction(key);
      await action();
      notify.success(message);
      await loadSessions();
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Emergency action failed");
    } finally {
      setBusyAction("");
    }
  };

  const pageActions = useMemo(
    () => (
      <>
        <Button variant="outline" onClick={loadSessions} className="border-gray-700 text-gray-100">
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
        <Button
          className="bg-red-600 hover:bg-red-500"
          onClick={() =>
            handleAction(
              "panic-close",
              () => liveTradingApi.stopAllSessions({ close_positions: true }),
              "All sessions stopped and close requests sent",
            )
          }
          disabled={busyAction === "panic-close"}
        >
          <ShieldX className="mr-2 h-4 w-4" />
          Stop All And Close
        </Button>
      </>
    ),
    [busyAction],
  );

  useSetPageActions(pageActions);

  const runningCount = sessions.filter((session) => session.status === "RUNNING").length;

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <Card className="border-red-900/50 bg-red-500/5">
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-red-300" />
            <div>
              <p className="text-sm font-semibold text-red-200">Emergency control surface</p>
              <p className="mt-1 text-sm text-red-100/70">
                Use this page when you need a fast operational response across broker-backed live sessions.
              </p>
            </div>
          </div>
          <Badge className="bg-red-500/10 text-red-300 border-red-500/20">
            {runningCount} running
          </Badge>
        </CardContent>
      </Card>

      {loading ? (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-400">Loading emergency controls...</CardContent>
        </Card>
      ) : sessions.length === 0 ? (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-400">No live sessions are deployed.</CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {sessions.map((session) => (
            <Card key={session.id} className="border-gray-800 bg-gray-900/60">
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle className="text-lg text-white">{session.strategy_name}</CardTitle>
                    <p className="mt-1 text-sm text-gray-400">{session.broker_label || session.broker_name || "Broker not assigned"}</p>
                  </div>
                  <Badge className={statusTone[session.status] || statusTone.STOPPED}>{session.status}</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {session.error_message ? (
                  <div className="rounded-2xl border border-red-900/50 bg-red-500/5 p-4 text-sm text-red-200">
                    {session.error_message}
                  </div>
                ) : null}

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl bg-gray-950/60 p-3 text-sm">
                    <p className="text-gray-500">Open positions</p>
                    <p className="mt-1 text-white">{session.open_positions}</p>
                  </div>
                  <div className="rounded-xl bg-gray-950/60 p-3 text-sm">
                    <p className="text-gray-500">Active orders</p>
                    <p className="mt-1 text-white">{session.active_orders}</p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  {session.status === "RUNNING" ? (
                    <Button
                      className="bg-amber-600 hover:bg-amber-500"
                      onClick={() => handleAction(`pause-${session.id}`, () => liveTradingApi.pauseSession(session.id), "Session paused")}
                      disabled={busyAction === `pause-${session.id}`}
                    >
                      <Pause className="mr-2 h-4 w-4" />
                      Pause
                    </Button>
                  ) : (
                    <Button
                      className="bg-emerald-600 hover:bg-emerald-500"
                      onClick={() => handleAction(`resume-${session.id}`, () => liveTradingApi.resumeSession(session.id), "Session resumed")}
                      disabled={busyAction === `resume-${session.id}`}
                    >
                      <Play className="mr-2 h-4 w-4" />
                      Resume
                    </Button>
                  )}
                  <Button
                    className="bg-red-600 hover:bg-red-500"
                    onClick={() => handleAction(`stop-${session.id}`, () => liveTradingApi.stopSession(session.id, { close_positions: false }), "Session stopped")}
                    disabled={busyAction === `stop-${session.id}`}
                  >
                    <Power className="mr-2 h-4 w-4" />
                    Stop Only
                  </Button>
                  <Button
                    variant="outline"
                    className="border-red-700 text-red-300 hover:text-red-200"
                    onClick={() => handleAction(`close-${session.id}`, () => liveTradingApi.stopSession(session.id, { close_positions: true }), "Session stopped with close requests")}
                    disabled={busyAction === `close-${session.id}`}
                  >
                    Stop And Close
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
