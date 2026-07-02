import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Bell, CheckCircle2, Clock3, RefreshCw, Settings2, Info, XCircle, Trash2, ExternalLink } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { Switch } from "@/shared/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/components/ui/tabs";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { analyticsSuiteApi } from "@/shared/services/analyticsSuiteApi";
import { useSystemNotificationsContext } from "@/shared/context/SystemNotificationsContext";

const severityConfig = {
  INFO: { color: "bg-cyan-500/10 text-cyan-300 border-cyan-500/20", icon: Info },
  WARNING: { color: "bg-amber-500/10 text-amber-300 border-amber-500/20", icon: AlertTriangle },
  CRITICAL: { color: "bg-red-500/10 text-red-300 border-red-500/20", icon: XCircle },
};

function formatDateTime(value) {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export default function NotificationCenter() {
  const { notify } = useNotifications();
  const navigate = useNavigate();
  const { clearUnreadCount } = useSystemNotificationsContext();
  
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState("all");
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState({});
  const [preferences, setPreferences] = useState([]);
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [itemsRes, summaryRes, prefsRes, scheduleRes] = await Promise.all([
        analyticsSuiteApi.getNotifications(),
        analyticsSuiteApi.getNotificationSummary(),
        analyticsSuiteApi.getNotificationPrefs(),
        analyticsSuiteApi.getSummarySchedule(),
      ]);
      setItems(Array.isArray(itemsRes.data?.results) ? itemsRes.data.results : itemsRes.data || []);
      setSummary(summaryRes.data || {});
      setPreferences(Array.isArray(prefsRes.data?.results) ? prefsRes.data.results : prefsRes.data || []);
      setSchedule(Array.isArray(scheduleRes.data?.results) ? scheduleRes.data.results[0] : scheduleRes.data || null);
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load notifications");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // When the user opens the Notification Center, clear the global unread count
    clearUnreadCount();
  }, [clearUnreadCount]);

  useSetPageActions(
    <>
      <Button variant="outline" onClick={loadData} className="border-gray-700 text-gray-100">
        <RefreshCw className="mr-2 h-4 w-4" />
        Refresh
      </Button>
      <Button
        className="bg-cyan-600 hover:bg-cyan-500"
        onClick={async () => {
          try {
            await analyticsSuiteApi.markAllNotificationsRead();
            notify.success("All notifications marked as read");
            await loadData();
          } catch (error) {
            notify.error(error?.response?.data?.detail || "Failed to mark notifications as read");
          }
        }}
      >
        <CheckCircle2 className="mr-2 h-4 w-4" />
        Mark All Read
      </Button>
      <Button
        variant="destructive"
        className="bg-red-600/80 hover:bg-red-500/90"
        onClick={async () => {
          try {
            await analyticsSuiteApi.deleteReadNotifications();
            notify.success("Deleted all read notifications");
            await loadData();
          } catch (error) {
            notify.error(error?.response?.data?.detail || "Failed to delete read notifications");
          }
        }}
      >
        <Trash2 className="mr-2 h-4 w-4" />
        Delete Read
      </Button>
    </>,
  );

  const filteredItems = useMemo(() => {
    const query = search.trim().toLowerCase();
    return items.filter((item) => {
      // Tab Filtering
      const isTrading = ["TRADE_EXECUTED", "SL_HIT", "TARGET_HIT"].includes(item.notification_type);
      const isSystem = ["STRATEGY_PAUSED", "STRATEGY_ERROR", "RISK_ALERT", "DAILY_SUMMARY", "MODERATION_ALERT"].includes(item.notification_type);
      const isCommunity = ["COMMUNITY_REPLY", "COMMUNITY_MENTION", "COMMUNITY_FOLLOW", "BADGE_UNLOCKED", "STREAK_WARNING", "CHALLENGE_PROGRESS", "CERTIFICATE_ISSUED", "PROOF_VERIFIED"].includes(item.notification_type);
      
      if (activeTab === "trading" && !isTrading) return false;
      if (activeTab === "system" && !isSystem) return false;
      if (activeTab === "community" && !isCommunity) return false;

      // Text Filtering
      if (!query) return true;
      return [item.title, item.message, item.strategy_name]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(query));
    });
  }, [items, search, activeTab]);

  const markRead = async (id, e) => {
    if (e) e.stopPropagation();
    try {
      setBusy(`read-${id}`);
      await analyticsSuiteApi.markNotificationRead(id);
      await loadData();
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to mark notification as read");
    } finally {
      setBusy("");
    }
  };

  const deleteNotification = async (id, e) => {
    if (e) e.stopPropagation();
    try {
      setBusy(`delete-${id}`);
      await analyticsSuiteApi.deleteNotification(id);
      await loadData();
      notify.success("Notification deleted");
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to delete notification");
    } finally {
      setBusy("");
    }
  };

  const updatePreference = async (id, field, value) => {
    try {
      setBusy(`pref-${id}`);
      await analyticsSuiteApi.updateNotificationPref(id, { [field]: value });
      await loadData();
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to update notification preference");
    } finally {
      setBusy("");
    }
  };

  const toggleSchedule = async (value) => {
    try {
      setBusy("schedule");
      await analyticsSuiteApi.updateSummarySchedule({ is_enabled: value }, schedule?.id || 1);
      await loadData();
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to update daily summary schedule");
    } finally {
      setBusy("");
    }
  };

  const handleDeepLink = (item) => {
    if (item.data && item.data.module) {
      if (item.data.module === "live") navigate("/dashboard/trading/live");
      else if (item.data.module === "paper") navigate("/dashboard/trading/paper-trading");
    }
    if (!item.is_read) {
      markRead(item.id);
    }
  };

  const stats = [
    { label: "Unread", value: summary.unread || 0, tone: "text-amber-300" },
    { label: "Critical", value: summary.critical || 0, tone: "text-red-300" },
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

      <div className="grid gap-4 xl:grid-cols-[1.3fr_0.7fr]">
        <Card className="border-gray-800 bg-gray-900/60">
          <CardHeader className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <CardTitle className="text-white">Notification Feed</CardTitle>
              <div className="relative w-full max-w-xs">
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search notifications"
                  className="border-gray-700 bg-gray-950/70 text-white"
                />
              </div>
            </div>
            
            <Tabs defaultValue="all" onValueChange={setActiveTab} className="w-full">
              <TabsList className="bg-gray-800/50">
                <TabsTrigger value="all">All</TabsTrigger>
                <TabsTrigger value="trading">Trading</TabsTrigger>
                <TabsTrigger value="system">System</TabsTrigger>
                <TabsTrigger value="community">Community</TabsTrigger>
              </TabsList>
            </Tabs>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <div className="py-10 text-center text-gray-400">Loading notifications...</div>
            ) : filteredItems.length === 0 ? (
              <div className="py-10 text-center text-gray-400">No notifications found.</div>
            ) : (
              filteredItems.map((item) => {
                const SeverityIcon = severityConfig[item.severity]?.icon || Info;
                const severityClass = severityConfig[item.severity]?.color || severityConfig.INFO.color;
                const hasDeepLink = !!item.data?.module;

                return (
                  <div 
                    key={item.id} 
                    className={`rounded-2xl border p-4 transition-all duration-200 ${item.is_read ? "border-gray-800 bg-black/20" : "border-cyan-900/50 bg-cyan-500/5"} ${hasDeepLink ? "cursor-pointer hover:border-cyan-700" : ""}`}
                    onClick={() => hasDeepLink ? handleDeepLink(item) : null}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-2 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <SeverityIcon className={`h-4 w-4 ${item.severity === "CRITICAL" ? "text-red-400" : item.severity === "WARNING" ? "text-amber-400" : "text-cyan-400"}`} />
                          <p className="font-semibold text-white">{item.title}</p>
                          <Badge className={severityClass}>{item.severity}</Badge>
                          {!item.is_read ? <Badge className="bg-indigo-500/10 text-indigo-300 border-indigo-500/20">NEW</Badge> : null}
                        </div>
                        <p className="text-sm text-gray-300">{item.message}</p>
                        <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
                          <span>{item.strategy_name || "System"}</span>
                          <span className="flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" /> {formatDateTime(item.created_at)}</span>
                          {hasDeepLink && <span className="flex items-center gap-1 text-cyan-400"><ExternalLink className="h-3 w-3"/> View</span>}
                        </div>
                      </div>
                      <div className="flex flex-col gap-2 items-end">
                        {!item.is_read && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-gray-700 text-gray-100 h-7 text-xs px-2"
                            onClick={(e) => markRead(item.id, e)}
                            disabled={busy === `read-${item.id}`}
                          >
                            Mark Read
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-red-400 hover:text-red-300 hover:bg-red-400/10 h-7 w-7 p-0"
                          onClick={(e) => deleteNotification(item.id, e)}
                          disabled={busy === `delete-${item.id}`}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader><CardTitle className="flex items-center gap-2 text-white"><Settings2 className="h-4 w-4 text-cyan-300" /> Daily Summary</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between rounded-2xl border border-gray-800 bg-black/20 p-4">
                <div>
                  <p className="text-sm font-medium text-white">Daily report notification</p>
                  <p className="text-xs text-gray-500">{schedule?.send_time || "18:00"} local time</p>
                </div>
                <Switch checked={Boolean(schedule?.is_enabled)} onCheckedChange={toggleSchedule} disabled={busy === "schedule"} />
              </div>
            </CardContent>
          </Card>

          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader><CardTitle className="flex items-center gap-2 text-white"><Bell className="h-4 w-4 text-cyan-300" /> Preferences</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {preferences.map((pref) => (
                <div key={pref.id} className="flex items-center justify-between rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <div>
                    <p className="text-sm font-medium text-white">{pref.notification_type.replaceAll("_", " ")}</p>
                    <p className="text-xs text-gray-500">In-app delivery</p>
                  </div>
                  <Switch
                    checked={Boolean(pref.in_app_enabled)}
                    onCheckedChange={(value) => updatePreference(pref.id, "in_app_enabled", value)}
                    disabled={busy === `pref-${pref.id}`}
                  />
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader><CardTitle className="text-white">Operational note</CardTitle></CardHeader>
            <CardContent className="text-sm text-gray-400">
              Risk notifications, analytics refresh updates, and daily summaries are now routed through the same in-app notification system.
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
