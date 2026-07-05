import { useEffect, useState } from "react";
import {
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  FileCheck,
  Loader2,
  RefreshCw,
  Shield,
  ShieldCheck,
  ShieldX,
  XCircle,
} from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";


import { Textarea } from "@/shared/components/ui/textarea";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { auditApi } from "@/shared/services/auditApi";
import { GlobalLoader } from '@/shared/components/ui/global-loader';

const STATUS_STYLES = {
  PENDING: "bg-amber-500/10 text-amber-300 border-amber-500/20",
  APPROVED: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
  REJECTED: "bg-red-500/10 text-red-300 border-red-500/20",
};

const STATUS_ICONS = {
  PENDING: Clock,
  APPROVED: CheckCircle,
  REJECTED: XCircle,
};

function formatDate(ts) {
  if (!ts) return "—";
  return new Date(ts).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/* ── Compliance Check Item ── */
function ComplianceItem({ check }) {
  return (
    <div
      className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm border ${
        check.passed
          ? "border-emerald-800/30 bg-emerald-950/20"
          : "border-red-800/30 bg-red-950/20"
      }`}
    >
      {check.passed ? (
        <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0" />
      ) : (
        <XCircle className="h-4 w-4 text-red-400 shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-white font-medium text-xs">{check.check_type.replace(/_/g, " ")}</p>
        <p className="text-gray-400 text-xs truncate">{check.details?.message}</p>
      </div>
    </div>
  );
}

/* ── Approval Card ── */
function ApprovalCard({ approval, onAction }) {
  const [expanded, setExpanded] = useState(false);
  const [checks, setChecks] = useState([]);
  const [checksLoading, setChecksLoading] = useState(false);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState("");
  const { notify } = useNotifications();

  const StatusIcon = STATUS_ICONS[approval.status] || Clock;
  const summary = approval.compliance_summary || {};

  const runChecks = async () => {
    try {
      setChecksLoading(true);
      const res = await auditApi.runCompliance(approval.id);
      setChecks(res.data || []);
      notify.success("Compliance checks completed");
    } catch {
      notify.error("Failed to run compliance checks");
    } finally {
      setChecksLoading(false);
    }
  };

  const handleDecision = async (action) => {
    try {
      setBusy(action);
      if (action === "approve") {
        await auditApi.approveRequest(approval.id, comment);
        notify.success("Strategy approved successfully");
      } else {
        await auditApi.rejectRequest(approval.id, comment);
        notify.success("Strategy rejected");
      }
      onAction();
    } catch (err) {
      notify.error(err?.response?.data?.detail || `Failed to ${action}`);
    } finally {
      setBusy("");
      setComment("");
    }
  };

  return (
    <Card className="border-gray-800 bg-gray-900/60">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-white text-base flex items-center gap-2">
              <Shield className="h-4 w-4 text-cyan-400 shrink-0" />
              <span className="truncate">{approval.strategy_name}</span>
            </CardTitle>
            <p className="text-xs text-gray-400 mt-1">
              Requested by {approval.requested_by_name} • {formatDate(approval.requested_at)}
            </p>
          </div>
          <Badge className={`shrink-0 ${STATUS_STYLES[approval.status]}`}>
            <StatusIcon className="h-3 w-3 mr-1" />
            {approval.status}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Summary cards */}
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-gray-800 bg-black/20 p-3">
            <p className="text-xs text-gray-500 uppercase tracking-widest">Compliance Score</p>
            <p className={`mt-1 text-lg font-semibold ${
              summary.score >= 80 ? "text-emerald-300" : summary.score >= 50 ? "text-amber-300" : "text-red-300"
            }`}>
              {summary.score ?? "—"}%
            </p>
          </div>
          <div className="rounded-xl border border-gray-800 bg-black/20 p-3">
            <p className="text-xs text-gray-500 uppercase tracking-widest">Checks Passed</p>
            <p className="mt-1 text-lg font-semibold text-emerald-300">
              {summary.passed ?? 0} / {summary.total ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-gray-800 bg-black/20 p-3">
            <p className="text-xs text-gray-500 uppercase tracking-widest">Decided By</p>
            <p className="mt-1 text-sm text-white font-medium truncate">
              {approval.approved_by_name || "Pending decision"}
            </p>
            {approval.decided_at && (
              <p className="text-xs text-gray-500 mt-0.5">{formatDate(approval.decided_at)}</p>
            )}
          </div>
        </div>

        {/* Comments */}
        {approval.comments && (
          <div className="rounded-xl border border-gray-800 bg-black/20 p-3">
            <p className="text-xs text-gray-500 uppercase tracking-widest mb-1">Comments</p>
            <p className="text-sm text-gray-300">{approval.comments}</p>
          </div>
        )}

        {/* Expandable compliance checks */}
        <div>
          <button
            onClick={() => {
              setExpanded(!expanded);
              if (!expanded && checks.length === 0) runChecks();
            }}
            className="flex items-center gap-2 text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            <FileCheck className="h-4 w-4" />
            Compliance Details
          </button>

          {expanded && (
            <div className="mt-3 space-y-2 animate-in slide-in-from-top-1 duration-200">
              {checksLoading ? (
                <div className="flex items-center gap-2 text-gray-400 text-sm py-4 justify-center">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Running compliance checks...
                </div>
              ) : checks.length === 0 ? (
                <div className="text-center py-4 text-sm text-gray-500">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={runChecks}
                    className="border-gray-700 text-gray-300"
                  >
                    <Shield className="mr-2 h-3.5 w-3.5" />
                    Run Compliance Checks
                  </Button>
                </div>
              ) : (
                <div className="grid gap-2 sm:grid-cols-2">
                  {checks.map((c) => (
                    <ComplianceItem key={c.id} check={c} />
                  ))}
                </div>
              )}

              {checks.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={runChecks}
                  disabled={checksLoading}
                  className="border-gray-700 text-gray-300 mt-2"
                >
                  <RefreshCw className={`mr-2 h-3.5 w-3.5 ${checksLoading ? "animate-spin" : ""}`} />
                  Re-run Checks
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Action area for PENDING approvals */}
        {approval.status === "PENDING" && (
          <div className="space-y-3 border-t border-gray-800 pt-4">
            <Textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Add a comment (optional)..."
              className="border-gray-700 bg-black/20 text-white placeholder:text-gray-600 min-h-[64px]"
            />
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() => handleDecision("approve")}
                disabled={!!busy}
                className="bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                {busy === "approve" ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <ShieldCheck className="mr-2 h-4 w-4" />
                )}
                Approve Strategy
              </Button>
              <Button
                onClick={() => handleDecision("reject")}
                disabled={!!busy}
                variant="outline"
                className="border-red-700 text-red-300 hover:bg-red-950/30"
              >
                {busy === "reject" ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <ShieldX className="mr-2 h-4 w-4" />
                )}
                Reject
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ── Main Page ── */
export default function StrategyApprovals() {
  const { notify } = useNotifications();
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("ALL");

  const loadApprovals = async () => {
    try {
      setLoading(true);
      const params = {};
      if (statusFilter !== "ALL") params.status = statusFilter;
      const res = await auditApi.getApprovals(params);
      const data = res.data?.results || res.data || [];
      setApprovals(Array.isArray(data) ? data : []);
    } catch {
      notify.error("Failed to load approvals");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApprovals();
  }, [statusFilter]);

  useSetPageActions(
    <Button variant="outline" onClick={loadApprovals} className="border-gray-700 text-gray-100">
      <RefreshCw className="mr-2 h-4 w-4" />
      Refresh
    </Button>
  );

  const counts = {
    all: approvals.length,
    pending: approvals.filter((a) => a.status === "PENDING").length,
    approved: approvals.filter((a) => a.status === "APPROVED").length,
    rejected: approvals.filter((a) => a.status === "REJECTED").length,
  };

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      {/* Summary row */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Total Requests", value: counts.all, tone: "text-white" },
          { label: "Pending Review", value: counts.pending, tone: "text-amber-300" },
          { label: "Approved", value: counts.approved, tone: "text-emerald-300" },
          { label: "Rejected", value: counts.rejected, tone: "text-red-300" },
        ].map((item) => (
          <Card key={item.label} className="border-gray-800 bg-gray-900/60">
            <CardContent className="p-5">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">{item.label}</p>
              <p className={`mt-2 text-2xl font-semibold ${item.tone}`}>{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        {["ALL", "PENDING", "APPROVED", "REJECTED"].map((s) => (
          <Button
            key={s}
            variant={statusFilter === s ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter(s)}
            className={
              statusFilter === s
                ? "bg-cyan-600 hover:bg-cyan-500 text-white"
                : "border-gray-700 text-gray-300 hover:bg-gray-800"
            }
          >
            {s === "ALL" ? "All" : s.charAt(0) + s.slice(1).toLowerCase()}
            {s === "PENDING" && counts.pending > 0 && (
              <span className="ml-1.5 inline-flex h-4 w-4 items-center justify-center rounded-full bg-amber-500 text-[10px] text-white font-semibold">
                {counts.pending}
              </span>
            )}
          </Button>
        ))}
      </div>

      {/* Approvals list */}
      {loading ? (
        <GlobalLoader />
      ) : approvals.length === 0 ? (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-500">
            {statusFilter === "ALL"
              ? "No approval requests found. Submit a strategy for marketplace listing to create one."
              : `No ${statusFilter.toLowerCase()} approval requests.`}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {approvals.map((a) => (
            <ApprovalCard key={a.id} approval={a} onAction={loadApprovals} />
          ))}
        </div>
      )}
    </div>
  );
}
