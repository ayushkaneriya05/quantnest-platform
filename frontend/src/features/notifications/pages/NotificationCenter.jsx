import Pagination from "@/shared/components/Pagination";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { usePagination, useQueryState } from "@/shared/hooks/usePagination";
import RefreshButton from "@/shared/components/RefreshButton";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { formatDateTime } from "@/shared/utils/formatters";
import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock3, ExternalLink, Info, Trash2, XCircle } from "lucide-react";
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
  INFO: { color: "bg-brand/10 text-brand border-brand/20", icon: Info },
  WARNING: { color: "bg-warning/10 text-warning border-warning/20", icon: AlertTriangle },
  CRITICAL: { color: "bg-loss/10 text-loss border-loss/20", icon: XCircle },
};

export default function NotificationCenter() {
  const { notify } = useNotifications();
  const navigate = useNavigate();
  const { syncUnreadCount } = useSystemNotificationsContext();
  const [search, setSearch] = useQueryState("search", "", { namespace: "", replace: true });
  const [activeTab, setActiveTab] = useQueryState("type", "ALL", { namespace: "", replace: false });
  const { page, pageSize, setPage, setPageSize, accept } = usePagination(JSON.stringify([search, activeTab]));
  const [metadata, setMetadata] = useState({ count: 0 });
  const request = useRef(0);
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const loadData = useCallback(async () => {
    const generation = ++request.current;
    setError("");
    try {
      setLoading(true);
      const [itemsResponse, summaryResponse] = await Promise.all([
        notificationApi.getNotifications({ page, page_size: pageSize, search, ...(activeTab !== "ALL" ? { type: activeTab } : {}) }),
        notificationApi.getSummary(),
      ]);
      const nextSummary = summaryResponse.data || {};
      if (generation !== request.current) return;
      setItems(itemsResponse.data.results); setMetadata(itemsResponse.data); accept(itemsResponse.data);
      setSummary(nextSummary);
      syncUnreadCount(nextSummary.unread);
    } catch (error) {
      if (generation === request.current) setError(getApiErrorMessage(error, "Failed to load notifications"));
    } finally {
      if (generation === request.current) setLoading(false);
    }
  }, [syncUnreadCount, page, pageSize, search, activeTab, accept]);

  useEffect(() => {
    const timer = setTimeout(loadData, search ? 250 : 0); const guard = request;
    return () => { clearTimeout(timer); guard.current++; };
  }, [loadData, search]);

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
      <RefreshButton onClick={loadData} label="Refresh notifications" disabled={loading} loading={loading} />
      <Button variant="default"

        onClick={() => runAction("mark-all", notificationApi.markAllRead, (response) => `${response.data?.marked || 0} notifications marked as read`, "Failed to mark notifications as read")}
        disabled={busy === "mark-all" || !summary.unread}
      >
        <CheckCircle2 className="mr-2 h-4 w-4" /> Mark All Read
      </Button>
      <Button
        variant="destructive"

        onClick={() => runAction("delete-read", notificationApi.deleteRead, (response) => `${response.data?.deleted || 0} read notifications deleted`, "Failed to delete read notifications")}
        disabled={busy === "delete-read" || !(summary.total > summary.unread)}
      >
        <Trash2 className="mr-2 h-4 w-4" /> Delete Read
      </Button>
    </>,
  );


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
      live: "/live/portfolio",
      paper: "/paper",
      manual: "/terminal",
      broker: "/brokers",
      marketdata: "/live/strategies",
      backtest: data.backtest_run_id ? `/backtests/results/${data.backtest_run_id}` : "/backtests",
      strategy: data.strategy_id ? `/strategies/${data.strategy_id}/edit` : "/strategies",
      research: data.research_session_id ? `/research?session=${data.research_session_id}` : "/research",
    };
    if (routes[data.module]) navigate(routes[data.module]);
    if (!item.is_read) markRead(item.id);
  };

  const stats = [
    { label: "Unread", value: summary.unread || 0, tone: "text-warning" },
    { label: "Unread critical", value: summary.by_type?.CRITICAL || 0, tone: "text-loss" },
    { label: "Today", value: summary.today || 0, tone: "text-brand" },
    { label: "Total", value: summary.total || 0, tone: "text-foreground" },
  ];

  if (error) return <div className="page-content"><WorkspaceState error={error} onRetry={loadData} /></div>;
  return (
    <div className="page-content">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((item) => (
          <Card key={item.label} className="border-border bg-card/60">
            <CardContent className="p-3">
              <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">{item.label}</p>
              <p className={`mt-2 text-2xl font-semibold ${item.tone}`}>{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-border bg-card/60">
        <CardHeader className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle className="text-foreground">Notification Feed</CardTitle>
            <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search notifications" className="max-w-xs border-border bg-background/70 text-foreground" />
          </div>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList >
              <TabsTrigger value="ALL">All</TabsTrigger>
              <TabsTrigger value="INFO">Info</TabsTrigger>
              <TabsTrigger value="WARNING">Warnings</TabsTrigger>
              <TabsTrigger value="CRITICAL">Critical</TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="py-10 text-center text-muted-foreground"><GlobalLoader inline text="Loading notifications..." /></div>
          ) : items.length === 0 ? (
            <div className="py-10 text-center text-muted-foreground">No notifications found.</div>
          ) : items.map((item) => {
            const typeConfig = TYPE_CONFIG[item.type] || TYPE_CONFIG.INFO;
            const TypeIcon = typeConfig.icon;
            const hasDeepLink = Boolean(item.data?.module);
            return (
              <div key={item.id} className={`rounded-2xl border p-3 transition-colors ${item.is_read ? "border-border bg-muted/40" : "border-brand/50 bg-brand/5"}  ${hasDeepLink ? "cursor-pointer hover:border-brand" : ""}`} onClick={hasDeepLink ? () => handleDeepLink(item) : undefined}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <TypeIcon className={`h-4 w-4 ${item.type === "CRITICAL" ? "text-loss" : item.type === "WARNING" ? "text-warning" : "text-brand"}`} />
                      <p className="font-semibold text-foreground">{item.title}</p>
                      <Badge className={typeConfig.color}>{item.type || "INFO"}</Badge>
                      {!item.is_read && <Badge className="border-brand/20 bg-brand/10 text-brand">NEW</Badge>}
                    </div>
                    <p className="text-sm text-foreground">{item.message}</p>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                      <span>{item.data?.strategy_name || item.data?.broker_name || item.data?.module || "System"}</span>
                      <span className="flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" />{formatDateTime(item.created_at)}</span>
                      {hasDeepLink && <span className="flex items-center gap-1 text-brand"><ExternalLink className="h-3 w-3" />View</span>}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    {!item.is_read && <Button size="sm" variant="outline" className="px-2 text-xs" onClick={(event) => markRead(item.id, event)} disabled={busy === `read-${item.id}`}>Mark Read</Button>}
                    <Button size="sm" variant="ghost" className="w-7 p-0" onClick={(event) => deleteNotification(item.id, event)} disabled={busy === `delete-${item.id}`} aria-label="Delete notification"><Trash2 className="h-3.5 w-3.5" /></Button>
                  </div>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
      <Pagination {...metadata} page={page} pageSize={pageSize} loading={loading} onPageChange={setPage} onPageSizeChange={setPageSize} label="Notification pages" />
    </div>
  );
}
