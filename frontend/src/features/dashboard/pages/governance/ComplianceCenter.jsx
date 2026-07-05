import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  FileCheck,
  Loader2,
  RefreshCw,
  Shield,
  ShieldAlert,
  XCircle,
} from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Progress } from "@/shared/components/ui/progress";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { auditApi } from "@/shared/services/auditApi";
import { GlobalLoader } from '@/shared/components/ui/global-loader';

function scoreTone(score) {
  if (score >= 80) return "text-emerald-300";
  if (score >= 50) return "text-amber-300";
  return "text-red-300";
}

function scoreBarColor(score) {
  if (score >= 80) return "bg-emerald-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-red-500";
}

function statusBadge(status) {
  const map = {
    DRAFT: "bg-gray-500/10 text-gray-400 border-gray-500/20",
    ACTIVE: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
    PAUSED: "bg-amber-500/10 text-amber-300 border-amber-500/20",
    ARCHIVED: "bg-gray-600/10 text-gray-400 border-gray-600/20",
  };
  return map[status] || map.DRAFT;
}

function visibilityBadge(vis) {
  const map = {
    PRIVATE: "bg-gray-500/10 text-gray-400 border-gray-500/20",
    PUBLIC: "bg-cyan-500/10 text-cyan-300 border-cyan-500/20",
    MARKETPLACE: "bg-purple-500/10 text-purple-300 border-purple-500/20",
  };
  return map[vis] || map.PRIVATE;
}

export default function ComplianceCenter() {
  const { notify } = useNotifications();
  const [summaries, setSummaries] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await auditApi.getComplianceSummary();
      setSummaries(Array.isArray(res.data) ? res.data : []);
    } catch {
      notify.error("Failed to load compliance data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useSetPageActions(
    <Button variant="outline" onClick={loadData} className="border-gray-700 text-gray-100">
      <RefreshCw className="mr-2 h-4 w-4" />
      Refresh
    </Button>
  );

  // Aggregate stats
  const totalStrategies = summaries.length;
  const avgScore =
    totalStrategies > 0
      ? Math.round(summaries.reduce((sum, s) => sum + (s.score || 0), 0) / totalStrategies)
      : 0;
  const fullyCompliant = summaries.filter((s) => s.score >= 100).length;
  const needsAttention = summaries.filter((s) => s.score > 0 && s.score < 80).length;
  const unchecked = summaries.filter((s) => s.total === 0).length;

  if (loading) {
    return (
      <GlobalLoader />
    );
  }

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      {/* Summary */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Total Strategies", value: totalStrategies, tone: "text-white", icon: Shield },
          { label: "Avg Compliance", value: `${avgScore}%`, tone: scoreTone(avgScore), icon: FileCheck },
          { label: "Fully Compliant", value: fullyCompliant, tone: "text-emerald-300", icon: CheckCircle },
          { label: "Needs Attention", value: needsAttention, tone: "text-amber-300", icon: AlertTriangle },
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

      {/* Info banner */}
      <Card className="border-cyan-800/30 bg-cyan-950/10">
        <CardContent className="p-4 flex items-start gap-3">
          <ShieldAlert className="h-5 w-5 text-cyan-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-white font-medium">Compliance checks ensure strategy quality</p>
            <p className="text-xs text-gray-400 mt-1">
              Each strategy is evaluated against rules coverage, risk configuration, backtesting history, and naming standards.
              Navigate to a strategy's approval to run or re-run the checks.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Strategy compliance cards */}
      {summaries.length === 0 ? (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-500">
            No strategies found. Create a strategy to see compliance data.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {summaries
            .sort((a, b) => (a.score || 0) - (b.score || 0))
            .map((strat) => (
              <Card key={strat.strategy_id} className="border-gray-800 bg-gray-900/60 hover:border-gray-700 transition-colors">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <CardTitle className="text-white text-sm flex items-center gap-2 truncate">
                      <Shield className="h-4 w-4 text-cyan-400 shrink-0" />
                      <span className="truncate">{strat.strategy_name}</span>
                    </CardTitle>
                    <div className="flex gap-1.5 shrink-0">
                      <Badge className={`text-[10px] ${statusBadge(strat.strategy_status)}`}>
                        {strat.strategy_status}
                      </Badge>
                      <Badge className={`text-[10px] ${visibilityBadge(strat.strategy_visibility)}`}>
                        {strat.strategy_visibility}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">Compliance Score</span>
                    <span className={`text-lg font-bold ${scoreTone(strat.score)}`}>
                      {strat.total > 0 ? `${strat.score}%` : "N/A"}
                    </span>
                  </div>

                  {strat.total > 0 ? (
                    <>
                      <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${scoreBarColor(strat.score)}`}
                          style={{ width: `${strat.score}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="flex items-center gap-1 text-emerald-400">
                          <CheckCircle className="h-3 w-3" />
                          {strat.passed} passed
                        </span>
                        <span className="flex items-center gap-1 text-red-400">
                          <XCircle className="h-3 w-3" />
                          {strat.failed} failed
                        </span>
                      </div>
                      {strat.last_checked && (
                        <p className="text-xs text-gray-600">
                          Last checked: {new Date(strat.last_checked).toLocaleString("en-IN", {
                            day: "2-digit",
                            month: "short",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                      )}
                    </>
                  ) : (
                    <div className="text-center py-3">
                      <p className="text-xs text-gray-500 mb-2">No compliance checks run yet</p>
                    </div>
                  )}

                  <Button
                    asChild
                    variant="outline"
                    size="sm"
                    className="w-full border-gray-700 text-gray-300"
                  >
                    <Link to={`/dashboard/strategy/${strat.strategy_id}/review`}>
                      View Strategy
                      <ArrowRight className="ml-2 h-3.5 w-3.5" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
        </div>
      )}
    </div>
  );
}
