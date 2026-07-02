import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, RefreshCw, ShieldAlert, TrendingUp } from "lucide-react";

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

function labelize(value) {
  return String(value || "")
    .split("_")
    .map((part) => part.charAt(0) + part.slice(1).toLowerCase())
    .join(" ");
}

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

const regimeTone = {
  TRENDING: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
  BREAKOUT: "bg-amber-500/10 text-amber-300 border-amber-500/20",
  HIGH_VOLATILITY: "bg-red-500/10 text-red-300 border-red-500/20",
  LOW_VOLATILITY: "bg-sky-500/10 text-sky-300 border-sky-500/20",
  RANGING: "bg-slate-500/10 text-slate-200 border-slate-500/20",
};

export default function MarketRegime() {
  const { notify } = useNotifications();
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState("");
  const [regimes, setRegimes] = useState([]);
  const [overfitDetections, setOverfitDetections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [regimesRes, overfitRes, strategiesRes] = await Promise.all([
        aiApi.getMarketRegimes(),
        aiApi.getOverfitDetections(),
        strategyApi.getAll(),
      ]);

      setRegimes(Array.isArray(regimesRes.data?.results) ? regimesRes.data.results : regimesRes.data || []);
      setOverfitDetections(Array.isArray(overfitRes.data?.results) ? overfitRes.data.results : overfitRes.data || []);

      const strategyRows = Array.isArray(strategiesRes?.results) ? strategiesRes.results : strategiesRes || [];
      setStrategies(strategyRows);
      if (!selectedStrategyId && strategyRows.length > 0) {
        setSelectedStrategyId(String(strategyRows[0].id));
      }
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load market regime data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const selectedStrategy = strategies.find((strategy) => String(strategy.id) === selectedStrategyId);

  const selectedOverfit = useMemo(() => {
    if (!selectedStrategyId) return overfitDetections;
    return overfitDetections.filter((item) => String(item.strategy) === String(selectedStrategyId));
  }, [overfitDetections, selectedStrategyId]);

  useSetPageActions(
    <>
      <Button variant="outline" onClick={loadData} className="border-gray-700 text-gray-100">
        <RefreshCw className="mr-2 h-4 w-4" />
        Refresh
      </Button>
      <Button
        variant="outline"
        className="border-gray-700 text-gray-100"
        onClick={async () => {
          if (!selectedStrategyId) return;
          try {
            setBusyAction("refresh-regime");
            await aiApi.refreshMarketRegimes(Number(selectedStrategyId));
            notify.success("Market regimes refreshed");
            await loadData();
          } catch (error) {
            notify.error(error?.response?.data?.detail || "Failed to refresh market regimes");
          } finally {
            setBusyAction("");
          }
        }}
        disabled={!selectedStrategyId || busyAction === "refresh-regime"}
      >
        <TrendingUp className="mr-2 h-4 w-4" />
        Refresh Regimes
      </Button>
      <Button
        className="bg-cyan-600 hover:bg-cyan-500"
        onClick={async () => {
          if (!selectedStrategyId) return;
          try {
            setBusyAction("refresh-overfit");
            await aiApi.refreshOverfitDetection(Number(selectedStrategyId));
            notify.success("Overfit detection refreshed");
            await loadData();
          } catch (error) {
            notify.error(error?.response?.data?.detail || "Failed to refresh overfit detection");
          } finally {
            setBusyAction("");
          }
        }}
        disabled={!selectedStrategyId || busyAction === "refresh-overfit"}
      >
        <ShieldAlert className="mr-2 h-4 w-4" />
        Refresh Overfit
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
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Selected Strategy</p>
              <p className="mt-2 text-lg font-semibold text-white">{selectedStrategy?.name || "Not selected"}</p>
            </div>
            <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Regime Signals</p>
              <p className="mt-2 text-2xl font-semibold text-cyan-300">{regimes.length}</p>
            </div>
            <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">Overfit Warnings</p>
              <p className="mt-2 text-2xl font-semibold text-amber-300">
                {selectedOverfit.filter((item) => Number(item.overfit_probability || 0) >= 60).length}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="border-gray-800 bg-gray-900/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <TrendingUp className="h-4 w-4 text-cyan-300" />
              Market Regime Signals
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <div className="py-10 text-center text-gray-400">Loading market regime signals...</div>
            ) : regimes.length === 0 ? (
              <div className="py-10 text-center text-gray-400">
                No regime signals available. Refresh regimes for a strategy to detect the current market structure.
              </div>
            ) : (
              regimes.map((row) => (
                <div key={row.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-white">{row.symbol}</p>
                      <p className="mt-1 text-sm text-gray-400">
                        {row.instrument_name || "Instrument"} | {row.timeframe}
                      </p>
                    </div>
                    <Badge className={regimeTone[row.regime_type] || regimeTone.RANGING}>
                      {labelize(row.regime_type)}
                    </Badge>
                  </div>

                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl bg-gray-950/60 p-3">
                      <div className="flex items-center justify-between text-xs uppercase tracking-[0.14em] text-gray-500">
                        <span>Confidence</span>
                        <span className="text-white">{formatPercent(row.confidence)}</span>
                      </div>
                      <Progress value={Number(row.confidence || 0)} className="mt-3 h-2 bg-gray-800" />
                    </div>
                    <div className="rounded-xl bg-gray-950/60 p-3 text-sm text-gray-400">
                      <p>
                        Direction <span className="text-white">{row.direction}</span>
                      </p>
                      <p className="mt-1">
                        Strength <span className="text-white">{row.strength}</span>
                      </p>
                    </div>
                  </div>

                  <div className="mt-3 text-xs text-gray-500">
                    Detected {formatDateTime(row.detected_at)} | Valid until {formatDateTime(row.valid_until)}
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="border-gray-800 bg-gray-900/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <AlertTriangle className="h-4 w-4 text-amber-300" />
              Overfit Diagnostics
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <div className="py-10 text-center text-gray-400">Loading diagnostics...</div>
            ) : selectedOverfit.length === 0 ? (
              <div className="py-10 text-center text-gray-400">
                No overfit diagnostics available for the selected strategy.
              </div>
            ) : (
              selectedOverfit.map((row) => (
                <div key={row.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-white">{row.strategy_name}</p>
                      <p className="mt-1 text-sm text-gray-400">
                        Backtest {row.backtest_run_name || row.backtest_run}
                      </p>
                    </div>
                    <Badge className="border-amber-500/20 bg-amber-500/10 text-amber-300">
                      {formatPercent(row.overfit_probability)}
                    </Badge>
                  </div>

                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl bg-gray-950/60 p-3 text-sm">
                      <p className="text-gray-500">In-sample Sharpe</p>
                      <p className="mt-1 text-white">{Number(row.in_sample_sharpe || 0).toFixed(2)}</p>
                    </div>
                    <div className="rounded-xl bg-gray-950/60 p-3 text-sm">
                      <p className="text-gray-500">Out-sample Sharpe</p>
                      <p className="mt-1 text-white">{Number(row.out_sample_sharpe || 0).toFixed(2)}</p>
                    </div>
                  </div>

                  <div className="mt-3 rounded-xl border border-gray-800 bg-gray-950/40 p-3 text-sm text-gray-400">
                    Degradation <span className="font-semibold text-white">{Number(row.degradation_pct || 0).toFixed(2)}%</span>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
