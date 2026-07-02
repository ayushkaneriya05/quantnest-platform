import { useEffect, useMemo, useState } from "react";
import { Gauge, RefreshCw, ShieldAlert } from "lucide-react";

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

function scoreTone(value) {
  const score = Number(value || 0);
  if (score >= 75) return "text-emerald-300";
  if (score >= 50) return "text-amber-300";
  return "text-red-300";
}

function formatPercent(value) {
  return `${Number(value || 0).toFixed(0)}%`;
}

const metricCards = [
  { key: "performance_score", label: "Performance" },
  { key: "risk_score", label: "Risk Discipline" },
  { key: "consistency_score", label: "Consistency" },
  { key: "execution_score", label: "Execution" },
];

export default function StrategyHealth() {
  const { notify } = useNotifications();
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState("");
  const [scores, setScores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [scoresRes, strategiesRes] = await Promise.all([
        aiApi.getHealthScores(),
        strategyApi.getAll(),
      ]);
      const scoreRows = Array.isArray(scoresRes.data?.results)
        ? scoresRes.data.results
        : scoresRes.data || [];
      const strategyRows = Array.isArray(strategiesRes?.results)
        ? strategiesRes.results
        : strategiesRes || [];
      setScores(scoreRows);
      setStrategies(strategyRows);
      if (!selectedStrategyId && strategyRows.length > 0) {
        setSelectedStrategyId(String(strategyRows[0].id));
      }
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load strategy health");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredScores = useMemo(() => {
    if (!selectedStrategyId) return scores;
    return scores.filter((item) => String(item.strategy) === String(selectedStrategyId));
  }, [scores, selectedStrategyId]);

  const latestSelectedScore = filteredScores[0] || null;

  useSetPageActions(
    <>
      <Button variant="outline" onClick={loadData} className="border-gray-700 text-gray-100">
        <RefreshCw className="mr-2 h-4 w-4" />
        Refresh
      </Button>
      <Button
        className="bg-cyan-600 hover:bg-cyan-500"
        onClick={async () => {
          if (!selectedStrategyId) return;
          try {
            setBusyAction("refresh-health");
            await aiApi.refreshHealthScore(Number(selectedStrategyId));
            notify.success("Strategy health refreshed");
            await loadData();
          } catch (error) {
            notify.error(error?.response?.data?.detail || "Failed to refresh health score");
          } finally {
            setBusyAction("");
          }
        }}
        disabled={!selectedStrategyId || busyAction === "refresh-health"}
      >
        <Gauge className="mr-2 h-4 w-4" />
        Refresh Health
      </Button>
    </>,
  );

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <Card className="border-gray-800 bg-gray-900/60">
        <CardContent className="grid gap-4 p-5 lg:grid-cols-[280px_1fr]">
          <div className="space-y-2">
            <p className="text-sm font-medium text-white">Strategy Filter</p>
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

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Current Score</p>
              <p className={`mt-2 text-2xl font-semibold ${scoreTone(latestSelectedScore?.overall_score)}`}>
                {formatPercent(latestSelectedScore?.overall_score)}
              </p>
            </div>
            <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Last Evaluated</p>
              <p className="mt-2 text-lg font-semibold text-white">{latestSelectedScore?.date || "Not generated"}</p>
            </div>
            <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Recommendations</p>
              <p className="mt-2 text-2xl font-semibold text-cyan-300">
                {latestSelectedScore?.recommendations?.length || 0}
              </p>
            </div>
            <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Strategy Records</p>
              <p className="mt-2 text-2xl font-semibold text-white">{filteredScores.length}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-400">Loading strategy health...</CardContent>
        </Card>
      ) : filteredScores.length === 0 ? (
        <Card className="border-gray-800 bg-gray-900/60">
          <CardContent className="py-12 text-center text-gray-400">
            No health scores available. Refresh a strategy to compute the first score.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[1fr_0.95fr]">
          <div className="space-y-4">
            {filteredScores.map((row) => (
              <Card key={row.id} className="border-gray-800 bg-gray-900/60">
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <CardTitle className="text-white">{row.strategy_name}</CardTitle>
                      <p className="mt-1 text-sm text-gray-400">{row.date}</p>
                    </div>
                    <Badge className={`border-current/20 bg-transparent ${scoreTone(row.overall_score)}`}>
                      {formatPercent(row.overall_score)}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    {metricCards.map((metric) => (
                      <div key={metric.key} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm text-gray-400">{metric.label}</p>
                          <p className={`text-sm font-semibold ${scoreTone(row[metric.key])}`}>
                            {formatPercent(row[metric.key])}
                          </p>
                        </div>
                        <Progress value={Number(row[metric.key] || 0)} className="mt-3 h-2 bg-gray-800" />
                      </div>
                    ))}
                  </div>

                  <div className="rounded-2xl border border-gray-800 bg-gray-950/40 p-4">
                    <p className="text-sm font-semibold text-white">AI Recommendations</p>
                    {(row.recommendations || []).length ? (
                      <div className="mt-3 space-y-2">
                        {row.recommendations.map((item) => (
                          <div key={item} className="rounded-xl bg-black/20 px-3 py-2 text-sm text-gray-300">
                            {item}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-3 text-sm text-gray-400">No AI recommendations stored for this score.</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <ShieldAlert className="h-4 w-4 text-amber-300" />
                Score Interpretation
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-gray-300">
              <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                <p className="font-medium text-emerald-300">75% and above</p>
                <p className="mt-2 text-gray-400">
                  Strategy is behaving with good balance across performance, risk discipline, and execution consistency.
                </p>
              </div>
              <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                <p className="font-medium text-amber-300">50% to 74%</p>
                <p className="mt-2 text-gray-400">
                  Strategy is tradable but should be reviewed for drawdown pressure, recent slippage, or unstable results.
                </p>
              </div>
              <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                <p className="font-medium text-red-300">Below 50%</p>
                <p className="mt-2 text-gray-400">
                  Strategy likely needs parameter tuning, risk tightening, or deployment pause before capital is exposed.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
