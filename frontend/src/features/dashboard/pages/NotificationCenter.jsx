import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock3, ExternalLink, Info, RefreshCw, Trash2, XCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/shared/components/ui/tabs";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { useSystemNotificationsContext } from "@/shared/context/SystemNotificationsContext";
import { notificationApi } from "@/shared/services/notificationApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";

const TYPE_CONFIG = {
  INFO: { color: "bg-cyan-500/10 text-cyan-300 border-cyan-500/20", icon: Info },
  WARNING: { color: "bg-amber-500/10 text-amber-300 border-amber-500/20", icon: AlertTriangle },
  CRITICAL: { color: "bg-red-500/10 text-red-300 border-red-500/20", icon: XCircle },
};

function formatDateTime(value) {
  if (!value) return "-";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "medium" });
}

function responseList(data) {
  if (Array.isArray(data?.results)) return data.results;
  return Array.isArray(data) ? data : [];
}

export default function NotificationCenter() {
  const { notify } = useNotifications();
  const navigate = useNavigate();
  const { syncUnreadCount } = useSystemNotificationsContext();
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState("ALL");
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [itemsResponse, summaryResponse] = await Promise.all([
        notificationApi.getNotifications(),
        notificationApi.getSummary(),
      ]);
      const nextSummary = summaryResponse.data || {};
      setItems(responseList(itemsResponse.data));
      setSummary(nextSummary);
      syncUnreadCount(nextSummary.unread);
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to load notifications"));
    } finally {
      setLoading(false);
    }
  }, [notify, syncUnreadCount]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const runAction = useCallback(async (key, action, successMessage, failureMessage) => {
    try {
      setBusy(key);
      const response = await action();
      if (successMessage) notify.success(successMessage(response));
      await loadData();
    } catch (error) {
      notify.error(getApiErrorMessage(error, failureMessage));
    } finally {
      setBusy("");
    }
  }, [loadData, notify]);

  useSetPageActions(
    <>
      <Button variant="outline" onClick={loadData} disabled={loading} className="border-gray-700 text-gray-100">
        <RefreshCw className="mr-2 h-4 w-4" /> Refresh
      </Button>
      <Button
        className="bg-cyan-600 hover:bg-cyan-500"
        onClick={() => runAction("mark-all", notificationApi.markAllRead, (response) => `${response.data?.marked || 0} notifications marked as read`, "Failed to mark notifications as read")}
        disabled={busy === "mark-all" || !summary.unread}
      >
        <CheckCircle2 className="mr-2 h-4 w-4" /> Mark All Read
      </Button>
      <Button
        variant="destructive"
        className="bg-red-600/80 hover:bg-red-500/90"
        onClick={() => runAction("delete-read", notificationApi.deleteRead, (response) => `${response.data?.deleted || 0} read notifications deleted`, "Failed to delete read notifications")}
        disabled={busy === "delete-read" || !items.some((item) => item.is_read)}
      >
        <Trash2 className="mr-2 h-4 w-4" /> Delete Read
      </Button>
    </>,
  );

  const filteredItems = useMemo(() => {
    const query = search.trim().toLowerCase();
    return items.filter((item) => {
      if (activeTab !== "ALL" && item.type !== activeTab) return false;
      return !query || [item.title, item.message, item.data?.strategy_name]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query));
    });
  }, [items, search, activeTab]);

  const markRead = (id, event) => {
    event?.stopPropagation();
    runAction(`read-${id}`, () => notificationApi.markRead(id), null, "Failed to mark notification as read");
  };

  const deleteNotification = (id, event) => {
    event?.stopPropagation();
    runAction(`delete-${id}`, () => notificationApi.deleteNotification(id), null, "Failed to delete notification");
  };

  const handleDeepLink = (item) => {
    const data = item.data || {};
    const routes = {
      live: "/dashboard/live/portfolio",
      paper: "/dashboard/paper",
      manual: "/dashboard/trading/paper-trading",
      broker: "/dashboard/brokers",
      marketdata: "/dashboard/live/strategies",
      backtest: data.backtest_run_id ? `/dashboard/backtest/results/${data.backtest_run_id}` : "/dashboard/backtest",
      strategy: data.strategy_id ? `/dashboard/strategy/${data.strategy_id}/edit` : "/dashboard/strategy/list",
      research: data.research_session_id ? `/dashboard/analysis/ai-research-assistant?session=${data.research_session_id}` : "/dashboard/analysis/ai-research-assistant",
    };
    if (routes[data.module]) navigate(routes[data.module]);
    if (!item.is_read) markRead(item.id);
  };

  const stats = [
    { label: "Unread", value: summary.unread || 0, tone: "text-amber-300" },
    { label: "Unread critical", value: summary.by_type?.CRITICAL || 0, tone: "text-red-300" },
    { label: "Today", value: summary.today || 0, tone: "text-cyan-300" },
    { label: "Total", value: summary.total || 0, tone: "text-white" },
  ];

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((item) => (
          <Card key={item.label} className="border-gray-800 bg-gray-900/60">
            <CardContent className="p-5">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">{item.label}</p>
              <p className={`mt-2 text-2xl font-semibold ${item.tone}`}>{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-gray-800 bg-gray-900/60">
        <CardHeader className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle className="text-white">Notification Feed</CardTitle>
            <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search notifications" className="max-w-xs border-gray-700 bg-gray-950/70 text-white" />
          </div>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="bg-gray-800/50">
              <TabsTrigger value="ALL">All</TabsTrigger>
              <TabsTrigger value="INFO">Info</TabsTrigger>
              <TabsTrigger value="WARNING">Warnings</TabsTrigger>
              <TabsTrigger value="CRITICAL">Critical</TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="py-10 text-center text-gray-400">Loading notifications...</div>
          ) : filteredItems.length === 0 ? (
            <div className="py-10 text-center text-gray-400">No notifications found.</div>
          ) : filteredItems.map((item) => {
            const typeConfig = TYPE_CONFIG[item.type] || TYPE_CONFIG.INFO;
            const TypeIcon = typeConfig.icon;
            const hasDeepLink = Boolean(item.data?.module);
            return (
              <div key={item.id} className={`rounded-2xl border p-4 transition-colors ${item.is_read ? "border-gray-800 bg-black/20" : "border-cyan-900/50 bg-cyan-500/5"} ${hasDeepLink ? "cursor-pointer hover:border-cyan-700" : ""}`} onClick={hasDeepLink ? () => handleDeepLink(item) : undefined}>
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <TypeIcon className={`h-4 w-4 ${item.type === "CRITICAL" ? "text-red-400" : item.type === "WARNING" ? "text-amber-400" : "text-cyan-400"}`} />
                      <p className="font-semibold text-white">{item.title}</p>
                      <Badge className={typeConfig.color}>{item.type || "INFO"}</Badge>
                      {!item.is_read && <Badge className="border-indigo-500/20 bg-indigo-500/10 text-indigo-300">NEW</Badge>}
                    </div>
                    <p className="text-sm text-gray-300">{item.message}</p>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
                      <span>{item.data?.strategy_name || item.data?.broker_name || item.data?.module || "System"}</span>
                      <span className="flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" />{formatDateTime(item.created_at)}</span>
                      {hasDeepLink && <span className="flex items-center gap-1 text-cyan-400"><ExternalLink className="h-3 w-3" />View</span>}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    {!item.is_read && <Button size="sm" variant="outline" className="h-7 border-gray-700 px-2 text-xs text-gray-100" onClick={(event) => markRead(item.id, event)} disabled={busy === `read-${item.id}`}>Mark Read</Button>}
                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-400 hover:bg-red-400/10 hover:text-red-300" onClick={(event) => deleteNotification(item.id, event)} disabled={busy === `delete-${item.id}`} aria-label="Delete notification"><Trash2 className="h-3.5 w-3.5" /></Button>
                  </div>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}
