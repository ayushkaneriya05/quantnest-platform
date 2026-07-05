import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Calendar,
  ChevronDown,
  ChevronRight,
  Clock,
  Download,
  Filter,
  Globe,
  RefreshCw,
  Search,
  Shield,
  User,
} from "lucide-react";
import { format } from "date-fns";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { DatePicker } from "@/shared/components/ui/date-picker";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { auditApi } from "@/shared/services/auditApi";
import { GlobalLoader } from '@/shared/components/ui/global-loader';

/* ── constants ── */
const ACTION_COLORS = {
  CREATE: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
  UPDATE: "bg-cyan-500/10 text-cyan-300 border-cyan-500/20",
  DELETE: "bg-red-500/10 text-red-300 border-red-500/20",
  LOGIN: "bg-blue-500/10 text-blue-300 border-blue-500/20",
  LOGOUT: "bg-gray-500/10 text-gray-300 border-gray-500/20",
  DEPLOY: "bg-purple-500/10 text-purple-300 border-purple-500/20",
  PAUSE: "bg-amber-500/10 text-amber-300 border-amber-500/20",
  STOP: "bg-rose-500/10 text-rose-300 border-rose-500/20",
  APPROVE: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
  REJECT: "bg-red-500/10 text-red-300 border-red-500/20",
};

const ACTION_ICONS = {
  CREATE: "✚",
  UPDATE: "✎",
  DELETE: "✕",
  LOGIN: "→",
  LOGOUT: "←",
  DEPLOY: "▶",
  PAUSE: "⏸",
  STOP: "■",
  APPROVE: "✓",
  REJECT: "✗",
};

function formatTimestamp(ts) {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function relativeTime(ts) {
  if (!ts) return "";
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

/* ── Expandable Log Row ── */
function LogRow({ log }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-b border-gray-800/50 last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-800/30 transition-colors text-left"
      >
        <span className="text-lg shrink-0 w-6 text-center">
          {ACTION_ICONS[log.action] || "•"}
        </span>
        <Badge className={`shrink-0 text-[10px] px-2 ${ACTION_COLORS[log.action] || ACTION_COLORS.UPDATE}`}>
          {log.action}
        </Badge>
        <span className="text-sm text-white font-medium truncate flex-1 min-w-0">
          {log.entity_name || `${log.entity_type} #${log.entity_id}`}
        </span>
        <span className="text-xs text-gray-500 shrink-0 hidden md:block">{log.entity_type}</span>
        <span className="text-xs text-gray-500 shrink-0">{relativeTime(log.timestamp)}</span>
        {open ? (
          <ChevronDown className="h-4 w-4 text-gray-500 shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-500 shrink-0" />
        )}
      </button>

      {open && (
        <div className="px-4 pb-4 pt-1 ml-9 space-y-3 animate-in slide-in-from-top-1 duration-200">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <DetailItem icon={User} label="User" value={log.user_name || "System"} />
            <DetailItem icon={Clock} label="Timestamp" value={formatTimestamp(log.timestamp)} />
            <DetailItem icon={Globe} label="IP Address" value={log.ip_address || "N/A"} />
            <DetailItem icon={Activity} label="Entity ID" value={`#${log.entity_id}`} />
          </div>

          {Object.keys(log.old_value || {}).length > 0 && (
            <div className="rounded-xl border border-gray-800 bg-black/30 p-3">
              <p className="text-xs uppercase tracking-widest text-gray-500 mb-2">Previous State</p>
              <pre className="text-xs text-gray-400 overflow-x-auto max-h-32 scrollbar-theme">
                {JSON.stringify(log.old_value, null, 2)}
              </pre>
            </div>
          )}

          {Object.keys(log.new_value || {}).length > 0 && (
            <div className="rounded-xl border border-gray-800 bg-black/30 p-3">
              <p className="text-xs uppercase tracking-widest text-gray-500 mb-2">New State</p>
              <pre className="text-xs text-emerald-400/70 overflow-x-auto max-h-32 scrollbar-theme">
                {JSON.stringify(log.new_value, null, 2)}
              </pre>
            </div>
          )}

          {log.user_agent && (
            <p className="text-xs text-gray-600 truncate" title={log.user_agent}>
              {log.user_agent}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function DetailItem({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <Icon className="h-3.5 w-3.5 text-gray-500 shrink-0" />
      <span className="text-gray-500">{label}:</span>
      <span className="text-gray-300 truncate">{value}</span>
    </div>
  );
}

/* ── Main Page ── */
export default function AuditLogs() {
  const { notify } = useNotifications();
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    search: "",
    action: "ALL",
    entity_type: "ALL",
    date_from: "",
    date_to: "",
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const params = {};
      if (filters.search) params.search = filters.search;
      if (filters.action !== "ALL") params.action = filters.action;
      if (filters.entity_type !== "ALL") params.entity_type = filters.entity_type;
      if (filters.date_from) params.date_from = filters.date_from;
      if (filters.date_to) params.date_to = filters.date_to;

      const [logsRes, statsRes] = await Promise.all([
        auditApi.getLogs(params),
        auditApi.getStats(),
      ]);
      const logsData = logsRes.data?.results || logsRes.data || [];
      setLogs(Array.isArray(logsData) ? logsData : []);
      setStats(statsRes.data);
    } catch (err) {
      notify.error("Failed to load audit data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleExport = async () => {
    try {
      const res = await auditApi.exportLogs();
      const data = res.data?.results || res.data || [];
      const csv = [
        ["ID", "Action", "Entity Type", "Entity Name", "User", "Timestamp", "IP"],
        ...data.map((r) => [
          r.id, r.action, r.entity_type, r.entity_name,
          r.user_name || "System", r.timestamp, r.ip_address || "",
        ]),
      ]
        .map((row) => row.map((c) => `"${c}"`).join(","))
        .join("\n");
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit_logs_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      notify.success("Audit logs exported");
    } catch {
      notify.error("Export failed");
    }
  };

  useSetPageActions(
    <>
      <Button
        variant="outline"
        onClick={handleExport}
        className="border-gray-700 text-gray-100"
      >
        <Download className="mr-2 h-4 w-4" />
        Export CSV
      </Button>
      <Button
        variant="outline"
        onClick={loadData}
        className="border-gray-700 text-gray-100"
      >
        <RefreshCw className="mr-2 h-4 w-4" />
        Refresh
      </Button>
    </>
  );

  /* Unique entity types from current data for the filter dropdown */
  const entityTypes = useMemo(() => {
    const set = new Set(logs.map((l) => l.entity_type));
    return Array.from(set).sort();
  }, [logs]);

  if (loading) {
    return (
      <GlobalLoader />
    );
  }

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      {/* ── Stats Cards ── */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {[
            { label: "Total Events", value: stats.total_logs, tone: "text-white", icon: Activity },
            { label: "Today", value: stats.today_logs, tone: "text-cyan-300", icon: Calendar },
            { label: "Pending Approvals", value: stats.pending_approvals, tone: "text-amber-300", icon: Shield },
            {
              label: "Compliance Rate",
              value: `${stats.compliance_pass_rate}%`,
              tone: stats.compliance_pass_rate >= 80 ? "text-emerald-300" : "text-red-300",
              icon: Shield,
            },
          ].map((item) => (
            <Card key={item.label} className="border-gray-800 bg-gray-900/60">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-500">{item.label}</p>
                  <item.icon className="h-4 w-4 text-gray-600" />
                </div>
                <p className={`mt-2 text-2xl font-semibold ${item.tone}`}>{item.value}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* ── Action Breakdown ── */}
      {stats?.action_breakdown && Object.keys(stats.action_breakdown).length > 0 && (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardHeader>
            <CardTitle className="text-white text-sm flex items-center gap-2">
              <Activity className="h-4 w-4 text-cyan-400" />
              Action Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats.action_breakdown).map(([action, count]) => (
                <div
                  key={action}
                  className="flex items-center gap-2 rounded-xl border border-gray-800 bg-black/20 px-3 py-2"
                >
                  <Badge className={`text-[10px] ${ACTION_COLORS[action] || ACTION_COLORS.UPDATE}`}>
                    {action}
                  </Badge>
                  <span className="text-sm font-medium text-white">{count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Filters ── */}
      <Card className="border-gray-800 bg-gray-900/60">
        <CardContent className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-5">
          <div className="relative">
            <Search className="absolute left-3 top-3.5 h-4 w-4 text-gray-500" />
            <Input
              value={filters.search}
              onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
              placeholder="Search entity, name..."
              className="border-gray-700 bg-black/20 pl-10 text-white"
            />
          </div>

          <Select
            value={filters.action}
            onValueChange={(v) => setFilters((f) => ({ ...f, action: v }))}
          >
            <SelectTrigger className="border-gray-700 bg-black/20 text-white">
              <SelectValue placeholder="Action" />
            </SelectTrigger>
            <SelectContent className="border-gray-800 bg-gray-900 text-white">
              <SelectItem value="ALL">All Actions</SelectItem>
              {["CREATE", "UPDATE", "DELETE", "LOGIN", "LOGOUT", "DEPLOY", "PAUSE", "STOP", "APPROVE", "REJECT"].map(
                (a) => (
                  <SelectItem key={a} value={a}>{a}</SelectItem>
                )
              )}
            </SelectContent>
          </Select>

          <Select
            value={filters.entity_type}
            onValueChange={(v) => setFilters((f) => ({ ...f, entity_type: v }))}
          >
            <SelectTrigger className="border-gray-700 bg-black/20 text-white">
              <SelectValue placeholder="Entity Type" />
            </SelectTrigger>
            <SelectContent className="border-gray-800 bg-gray-900 text-white">
              <SelectItem value="ALL">All Entities</SelectItem>
              {entityTypes.map((t) => (
                <SelectItem key={t} value={t}>{t}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <DatePicker
            date={filters.date_from ? new Date(filters.date_from + "T00:00:00") : null}
            setDate={(date) => setFilters((f) => ({ ...f, date_from: date ? format(date, "yyyy-MM-dd") : "" }))}
            placeholder="From Date"
            className="border-gray-700 bg-black/20 text-white"
          />

          <div className="flex gap-2">
            <DatePicker
              date={filters.date_to ? new Date(filters.date_to + "T00:00:00") : null}
              setDate={(date) => setFilters((f) => ({ ...f, date_to: date ? format(date, "yyyy-MM-dd") : "" }))}
              placeholder="To Date"
              className="border-gray-700 bg-black/20 text-white flex-1"
            />
            <Button
              onClick={loadData}
              className="bg-cyan-600 hover:bg-cyan-500 shrink-0"
            >
              <Filter className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* ── Logs List ── */}
      <Card className="border-gray-800 bg-gray-900/60">
        <CardHeader>
          <CardTitle className="text-white text-sm flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-cyan-400" />
              Event Timeline
            </span>
            <span className="text-xs text-gray-500 font-normal">{logs.length} events</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {logs.length === 0 ? (
            <div className="py-12 text-center text-gray-500">
              No audit events match the current filters.
            </div>
          ) : (
            <div className="divide-y divide-gray-800/30">
              {logs.map((log) => (
                <LogRow key={log.id} log={log} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
