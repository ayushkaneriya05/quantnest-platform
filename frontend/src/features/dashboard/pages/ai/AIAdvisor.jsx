import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Gauge,
  RefreshCw,
  Sparkles,
  Trash2,
  TrendingUp,
} from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Progress } from "@/shared/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { aiApi } from "@/shared/services/aiApi";
import { strategyApi } from "@/shared/services/strategyApi";

function formatPercent(value) {
  return `${Number(value || 0).toFixed(0)}%`;
}

function formatDateTime(value) {
  if (!value) return "Not available";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function labelize(value) {
  return String(value || "")
    .split("_")
    .map((part) => part.charAt(0) + part.slice(1).toLowerCase())
    .join(" ");
}

const priorityTone = {
  LOW: "bg-slate-500/10 text-slate-200 border-slate-500/20",
  MEDIUM: "bg-cyan-500/10 text-cyan-300 border-cyan-500/20",
  HIGH: "bg-red-500/10 text-red-300 border-red-500/20",
};

const regimeTone = {
  TRENDING: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
  BREAKOUT: "bg-amber-500/10 text-amber-300 border-amber-500/20",
  HIGH_VOLATILITY: "bg-red-500/10 text-red-300 border-red-500/20",
  LOW_VOLATILITY: "bg-sky-500/10 text-sky-300 border-sky-500/20",
  RANGING: "bg-slate-500/10 text-slate-200 border-slate-500/20",
};

export default function AIAdvisor() {
  const { notify } = useNotifications();
  const [overview, setOverview] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [overviewRes, recommendationsRes, strategiesRes] = await Promise.all([
        aiApi.getOverview(),
        aiApi.getRecommendations(),
        strategyApi.getAll(),
      ]);

      const overviewPayload = overviewRes.data || {};
      const recommendationRows = Array.isArray(recommendationsRes.data?.results)
        ? recommendationsRes.data.results
        : recommendationsRes.data || [];
      const strategyRows = Array.isArray(strategiesRes?.results)
        ? strategiesRes.results
        : strategiesRes || [];

      setOverview(overviewPayload);
      setRecommendations(recommendationRows);
      setStrategies(strategyRows);

      if (!selectedStrategyId && strategyRows.length > 0) {
        setSelectedStrategyId(String(strategyRows[0].id));
      }
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load AI advisor");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const runAction = async (actionKey, action, successMessage) => {
    try {
      setBusyAction(actionKey);
      await action();
      if (successMessage) notify.success(successMessage);
      await loadData();
    } catch (error) {
      notify.error(error?.response?.data?.detail || "AI action failed");
    } finally {
      setBusyAction("");
    }
  };

  const selectedStrategy = strategies.find((strategy) => String(strategy.id) === selectedStrategyId);
  const healthScores = overview?.health_scores || [];
  const marketRegimes = overview?.market_regimes || [];
  const overfitDetections = overview?.overfit_detections || [];

  const stats = [
    {
      label: "Active Recommendations",
      value: recommendations.filter((item) => !item.is_dismissed).length,
      tone: "text-cyan-300",
    },
    {
      label: "High Priority",
      value: recommendations.filter((item) => item.priority === "HIGH" && !item.is_dismissed).length,
      tone: "text-red-300",
    },
    {
      label: "Avg Health Score",
      value: healthScores.length
        ? formatPercent(
            healthScores.reduce((total, row) => total + Number(row.overall_score || 0), 0) / healthScores.length,
          )
        : "0%",
      tone: "text-emerald-300",
    },
    {
      label: "Overfit Warnings",
      value: overfitDetections.filter((item) => Number(item.overfit_probability || 0) >= 60).length,
      tone: "text-amber-300",
    },
  ];

  useSetPageActions(
    <>
      <Button variant="outline" onClick={loadData} className="border-gray-700 text-gray-100">
        <RefreshCw className="mr-2 h-4 w-4" />
        Refresh
      </Button>
      <Button
        variant="outline"
        className="border-gray-700 text-gray-100"
        onClick={() =>
          runAction(
            "refresh-suite",
            () => aiApi.refreshSuite(selectedStrategyId ? Number(selectedStrategyId) : null),
            selectedStrategyId ? "Strategy AI suite refreshed" : "AI suite refreshed for active strategies",
          )
        }
        disabled={busyAction === "refresh-suite"}
      >
        <Sparkles className="mr-2 h-4 w-4" />
        Refresh AI Suite
      </Button>
      <Button
        className="bg-cyan-600 hover:bg-cyan-500"
        onClick={() =>
          runAction(
            "generate",
            () => aiApi.generateRecommendation(Number(selectedStrategyId)),
            "Recommendation generated",
          )
        }
        disabled={!selectedStrategyId || busyAction === "generate"}
      >
        <Bot className="mr-2 h-4 w-4" />
        Generate Recommendation
      </Button>
    </>,
  );

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
        <CardContent className="grid gap-4 p-5 lg:grid-cols-[280px_1fr]">
          <div className="space-y-2">
            <p className="text-sm font-medium text-white">Target Strategy</p>
            <Select value={selectedStrategyId} onValueChange={setSelectedStrategyId}>
              <SelectTrigger className="border-gray-700 bg-black/20 text-white">
                <SelectValue placeholder="Select strategy" />
              </SelectTrigger>
              <SelectContent className="border-gray-800 bg-gray-900 text-white">
                {strategies.map((strategy) => (
                  <SelectItem key={strategy.id} value={String(strategy.id)}>
                    {strategy.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-white">{selectedStrategy?.name || "No strategy selected"}</p>
                <p className="mt-1 text-sm text-gray-400">
                  Recommendations combine health scoring, regime fit, backtest degradation, and recent risk pressure.
                </p>
              </div>
              {overview?.latest_report ? (
                <Badge className="border-cyan-500/20 bg-cyan-500/10 text-cyan-300">
                  Latest report {overview.latest_report.date}
                </Badge>
              ) : null}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="border-gray-800 bg-gray-900/60">
          <CardHeader>
            <CardTitle className="text-white">Recommendation Queue</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <div className="py-10 text-center text-gray-400">Loading AI recommendations...</div>
            ) : recommendations.length === 0 ? (
              <div className="py-10 text-center text-gray-400">
                No recommendations yet. Run the AI suite for a strategy to generate guidance.
              </div>
            ) : (
              recommendations.map((row) => (
                <div key={row.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-white">{row.title}</p>
                      <p className="mt-1 text-sm text-gray-400">
                        {row.strategy_name} | {labelize(row.type)}
                      </p>
                    </div>
                    <Badge className={priorityTone[row.priority] || priorityTone.MEDIUM}>{row.priority}</Badge>
                  </div>

                  <p className="mt-3 text-sm leading-6 text-gray-300">{row.description}</p>

                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl bg-gray-950/60 p-3">
                      <div className="flex items-center justify-between text-xs uppercase tracking-[0.14em] text-gray-500">
                        <span>Confidence</span>
                        <span className="text-white">{formatPercent(row.confidence_score)}</span>
                      </div>
                      <Progress value={Number(row.confidence_score || 0)} className="mt-3 h-2 bg-gray-800" />
                    </div>
                    <div className="rounded-xl bg-gray-950/60 p-3 text-sm text-gray-400">
                      <p>Created {formatDateTime(row.created_at)}</p>
                      <p className="mt-1">
                        Status{" "}
                        <span className="text-white">
                          {row.applied ? "Applied" : row.is_dismissed ? "Dismissed" : "Pending"}
                        </span>
                      </p>
                    </div>
                  </div>

                  {row.details && Object.keys(row.details).length ? (
                    <div className="mt-4 rounded-xl border border-gray-800 bg-gray-950/40 p-3 text-sm text-gray-400">
                      {Object.entries(row.details)
                        .slice(0, 3)
                        .map(([key, value]) => (
                          <p key={key}>
                            <span className="capitalize text-gray-500">{key.replaceAll("_", " ")}:</span>{" "}
                            <span className="text-white">{String(value)}</span>
                          </p>
                        ))}
                    </div>
                  ) : null}

                  <div className="mt-4 flex flex-wrap gap-2">
                    {!row.applied ? (
                      <Button
                        size="sm"
                        className="bg-emerald-600 hover:bg-emerald-500"
                        onClick={() =>
                          runAction(
                            `apply-${row.id}`,
                            () => aiApi.applyRecommendation(row.id),
                            "Recommendation marked as applied",
                          )
                        }
                        disabled={busyAction === `apply-${row.id}`}
                      >
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Apply
                      </Button>
                    ) : null}
                    {!row.is_dismissed ? (
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-gray-700 text-gray-100"
                        onClick={() =>
                          runAction(
                            `dismiss-${row.id}`,
                            () => aiApi.dismissRecommendation(row.id),
                            "Recommendation dismissed",
                          )
                        }
                        disabled={busyAction === `dismiss-${row.id}`}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Dismiss
                      </Button>
                    ) : null}
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <Gauge className="h-4 w-4 text-emerald-300" />
                Health Snapshot
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {healthScores.slice(0, 4).map((item) => (
                <div key={item.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-white">{item.strategy_name}</p>
                      <p className="mt-1 text-sm text-gray-400">Overall health {formatPercent(item.overall_score)}</p>
                    </div>
                    <Badge className="border-emerald-500/20 bg-emerald-500/10 text-emerald-300">{item.date}</Badge>
                  </div>
                  <Progress value={Number(item.overall_score || 0)} className="mt-3 h-2 bg-gray-800" />
                </div>
              ))}
              {!loading && !healthScores.length ? (
                <div className="py-8 text-center text-gray-400">No strategy health scores generated yet.</div>
              ) : null}
            </CardContent>
          </Card>

          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <TrendingUp className="h-4 w-4 text-cyan-300" />
                Market Regime Context
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {marketRegimes.slice(0, 4).map((item) => (
                <div key={item.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-white">{item.symbol}</p>
                      <p className="mt-1 text-sm text-gray-400">{item.instrument_name || "Instrument"}</p>
                    </div>
                    <Badge className={regimeTone[item.regime_type] || regimeTone.RANGING}>
                      {labelize(item.regime_type)}
                    </Badge>
                  </div>
                  <p className="mt-3 text-sm text-gray-300">
                    Direction {item.direction} | Confidence {formatPercent(item.confidence)}
                  </p>
                </div>
              ))}
              {!loading && !marketRegimes.length ? (
                <div className="py-8 text-center text-gray-400">No market regime context available yet.</div>
              ) : null}
            </CardContent>
          </Card>

          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <AlertTriangle className="h-4 w-4 text-amber-300" />
                Overfit Radar
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {overfitDetections.slice(0, 3).map((item) => (
                <div key={item.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-white">{item.strategy_name}</p>
                      <p className="mt-1 text-sm text-gray-400">Run {item.backtest_run_name || item.backtest_run}</p>
                    </div>
                    <Badge className="border-amber-500/20 bg-amber-500/10 text-amber-300">
                      {formatPercent(item.overfit_probability)}
                    </Badge>
                  </div>
                  <p className="mt-3 text-sm text-gray-300">
                    Degradation {Number(item.degradation_pct || 0).toFixed(2)}%
                  </p>
                </div>
              ))}
              {!loading && !overfitDetections.length ? (
                <div className="py-8 text-center text-gray-400">No overfit detections have been generated yet.</div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
