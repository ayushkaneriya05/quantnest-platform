/**
 * BacktestSetup — Professional backtest configuration form.
 * Step-grouped wizard-style layout with strategy info preview.
 */
import React, { useState, useEffect, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { DatePicker } from "@/shared/components/ui/date-picker";
import {
  Play,
  Settings,
  Calendar,
  DollarSign,
  Info,
  RefreshCw,
  ChevronLeft,
  Layers,
  Clock,
} from "lucide-react";
import { format } from "date-fns";
import { backtestApi } from "@/shared/services/backtestApi";
import { strategyApi } from "@/shared/services/strategyApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useEnums } from "@/shared/context/EnumsContext";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";

/* ─── Step Indicator ─── */
function StepIndicator({ number, title, active }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={`flex items-center justify-center h-8 w-8 rounded-full text-xs font-bold transition-all ${
          active
            ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/30"
            : "bg-gray-800 text-gray-500 border border-gray-700"
        }`}
      >
        {number}
      </div>
      <span
        className={`text-sm font-medium transition-colors ${
          active ? "text-white" : "text-gray-600"
        }`}
      >
        {title}
      </span>
    </div>
  );
}

/* ─── Date Duration Helper ─── */
function dateDuration(start, end) {
  if (!start || !end) return null;
  const s = new Date(start);
  const e = new Date(end);
  const diffMs = e - s;
  if (diffMs <= 0) return null;
  const days = Math.floor(diffMs / 86400000);
  if (days < 30) return `${days} day${days !== 1 ? "s" : ""}`;
  const months = Math.floor(days / 30);
  const remainDays = days % 30;
  let str = `${months} month${months !== 1 ? "s" : ""}`;
  if (remainDays > 0) str += `, ${remainDays}d`;
  return str;
}

export default function BacktestSetup() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { notify } = useNotifications();
  const { enums } = useEnums();
  const timeframes = enums.CandleTimeframe || [];
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(false);

  const preSelectedStrategy = searchParams.get("strategy") || "";

  const [formData, setFormData] = useState({
    name: "",
    strategy: preSelectedStrategy,
    start_date: "2024-01-01",
    end_date: new Date().toISOString().split("T")[0],
    initial_capital: 100000,
    slippage_pct: 0.05,
    brokerage_per_trade: 20,
    brokerage_pct: 0.03,
  });

  useEffect(() => {
    fetchStrategies();
  }, []);

  useEffect(() => {
    if (preSelectedStrategy && strategies.length > 0) {
      const strategy = strategies.find(
        (item) => item.id.toString() === preSelectedStrategy
      );
      if (strategy) {
        setFormData((current) => ({
          ...current,
          strategy: preSelectedStrategy,
          name: `${strategy.name} - Backtest ${new Date().getFullYear()}`,
        }));
      }
    }
  }, [preSelectedStrategy, strategies]);

  const fetchStrategies = async () => {
    try {
      const response = await strategyApi.getAll();
      const strategyList = Array.isArray(response)
        ? response
        : response.data || [];
      setStrategies(strategyList);
    } catch {
      notify.error("Failed to load strategies");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.strategy || !formData.start_date || !formData.end_date) {
      notify.error("Please fill all required fields");
      return;
    }
    if (!formData.name.trim()) {
      notify.error("Please enter a backtest name");
      return;
    }

    try {
      setLoading(true);
      const response = await backtestApi.createRun(formData);
      notify.success("Backtest created! Initializing simulation…");
      await backtestApi.startRun(response.data.id);
      navigate(`/dashboard/backtest/results/${response.data.id}`);
    } catch {
      notify.error("Failed to create backtest. Check required fields.");
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData({ ...formData, [field]: value });
  };

  /* Selected strategy info */
  const selectedStrategy = useMemo(
    () => strategies.find((s) => s.id.toString() === formData.strategy),
    [formData.strategy, strategies]
  );

  const duration = dateDuration(formData.start_date, formData.end_date);

  useSetPageActions(
    <Button
      variant="outline"
      size="sm"
      onClick={() => navigate("/dashboard/backtest")}
      className="bg-gray-900 border-gray-800 hover:bg-gray-800 h-9"
    >
      <ChevronLeft className="h-4 w-4 mr-2" />
      Back to List
    </Button>
  );

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-6 lg:py-8 space-y-6">
      {/* ── Step Indicators ── */}

      {/* ── Step Indicators ── */}
      <div className="flex items-center gap-8 px-1">
        <StepIndicator number={1} title="Strategy & Period" active />
        <div className="h-px flex-1 bg-gray-800" />
        <StepIndicator number={2} title="Capital & Costs" active />
        <div className="h-px flex-1 bg-gray-800" />
        <StepIndicator number={3} title="Launch" active />
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* ── STEP 1: Strategy & Period ── */}
        <div className="grid md:grid-cols-2 gap-6">
          <Card className="bg-gray-900/50 border-gray-800 backdrop-blur-sm">
            <CardHeader className="pb-4">
              <CardTitle className="text-base text-white flex items-center gap-2">
                <Settings className="h-4 w-4 text-indigo-400" />
                Strategy Selection
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label className="text-gray-400 text-xs uppercase tracking-wider font-semibold">
                  Strategy *
                </Label>
                <Select
                  value={formData.strategy}
                  onValueChange={(value) => handleChange("strategy", value)}
                >
                  <SelectTrigger className="bg-gray-800/80 border-gray-700 h-11">
                    <SelectValue placeholder="Select a strategy" />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-800 border-gray-700 text-white">
                    {strategies.map((strategy) => (
                      <SelectItem
                        key={strategy.id}
                        value={strategy.id.toString()}
                      >
                        {strategy.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {strategies.length === 0 && (
                  <p className="text-xs text-amber-300">
                    No strategies found. You need to create a strategy before you can run a backtest.
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label className="text-gray-400 text-xs uppercase tracking-wider font-semibold">
                  Backtest Name *
                </Label>
                <Input
                  value={formData.name}
                  onChange={(e) => handleChange("name", e.target.value)}
                  placeholder="e.g., Mean Reversion - Q1 2024"
                  className="bg-gray-800/80 border-gray-700 h-11 text-white focus:ring-indigo-500"
                />
              </div>

              {/* Strategy Info Card */}
              {selectedStrategy && (
                <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <Layers className="h-3.5 w-3.5 text-indigo-400" />
                    <span className="text-xs font-semibold text-indigo-300 uppercase tracking-wider">
                      Strategy Info
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-gray-500">Type: </span>
                      <span className="text-gray-300">
                        {selectedStrategy.strategy_type || "—"}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Market: </span>
                      <span className="text-gray-300">
                        {selectedStrategy.market_type || "—"}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Exchange: </span>
                      <span className="text-gray-300">
                        {selectedStrategy.exchange || "—"}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Status: </span>
                      <span className="text-gray-300">
                        {selectedStrategy.status || "—"}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="bg-gray-900/50 border-gray-800 backdrop-blur-sm">
            <CardHeader className="pb-4">
              <CardTitle className="text-base text-white flex items-center gap-2">
                <Calendar className="h-4 w-4 text-indigo-400" />
                Timeframe & Data
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-gray-400 text-xs uppercase tracking-wider font-semibold">
                    Start Date *
                  </Label>
                  <DatePicker
                    date={formData.start_date ? new Date(formData.start_date + "T00:00:00") : null}
                    setDate={(date) =>
                      handleChange("start_date", date ? format(date, "yyyy-MM-dd") : "")
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-gray-400 text-xs uppercase tracking-wider font-semibold">
                    End Date *
                  </Label>
                  <DatePicker
                    date={formData.end_date ? new Date(formData.end_date + "T00:00:00") : null}
                    setDate={(date) =>
                      handleChange("end_date", date ? format(date, "yyyy-MM-dd") : "")
                    }
                  />
                </div>
              </div>
              {duration && (
                <div className="flex items-center gap-2 text-xs text-indigo-400">
                  <Clock className="h-3.5 w-3.5" />
                  <span className="font-medium">Period: {duration}</span>
                </div>
              )}
              {/* Snapshot behavior note (subtle) */}
              <div className="flex gap-2 p-2.5 rounded-lg bg-gray-800/40 border border-gray-700/50">
                <Info className="h-3.5 w-3.5 text-gray-500 mt-0.5 shrink-0" />
                <p className="text-[11px] text-gray-500 leading-relaxed">
                  Entry/exit rules, time rules, and risk settings are captured
                  from the strategy snapshot at run time.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* ── STEP 2: Capital & Costs ── */}
        <Card className="bg-gray-900/50 border-gray-800 backdrop-blur-sm">
          <CardHeader className="pb-4">
            <CardTitle className="text-base text-white flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-emerald-400" />
              Capital & Transaction Costs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label className="text-gray-400 text-xs uppercase tracking-wider font-semibold">
                  Initial Capital (₹)
                </Label>
                <Input
                  type="number"
                  value={formData.initial_capital}
                  onChange={(e) =>
                    handleChange("initial_capital", parseFloat(e.target.value))
                  }
                  className="bg-gray-800/80 border-gray-700 text-white font-mono h-11"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-gray-400 text-xs uppercase tracking-wider font-semibold">
                  Brokerage / Trade (₹)
                </Label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.brokerage_per_trade}
                  onChange={(e) =>
                    handleChange(
                      "brokerage_per_trade",
                      parseFloat(e.target.value)
                    )
                  }
                  className="bg-gray-800/80 border-gray-700 text-white font-mono h-11"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-gray-400 text-xs uppercase tracking-wider font-semibold">
                  Slippage (%)
                </Label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.slippage_pct}
                  onChange={(e) =>
                    handleChange("slippage_pct", parseFloat(e.target.value))
                  }
                  className="bg-gray-800/80 border-gray-700 text-white font-mono h-11"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-gray-400 text-xs uppercase tracking-wider font-semibold">
                  Tx Cost (%)
                </Label>
                <Input
                  type="number"
                  step="0.001"
                  value={formData.brokerage_pct}
                  onChange={(e) =>
                    handleChange("brokerage_pct", parseFloat(e.target.value))
                  }
                  className="bg-gray-800/80 border-gray-700 text-white font-mono h-11"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ── STEP 3: Launch ── */}
        <div className="flex flex-col items-center gap-4 pt-2">
          <Button
            type="submit"
            disabled={loading || !formData.strategy || !formData.name.trim()}
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold h-12 px-10 shadow-lg shadow-indigo-500/20 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? (
              <RefreshCw className="h-5 w-5 animate-spin" />
            ) : (
              <>
                <Play className="h-4 w-4 mr-2 fill-current" />
                Launch Simulation
              </>
            )}
          </Button>
          <p className="text-[11px] text-gray-600 max-w-md text-center">
            A strategy snapshot will be created automatically. Changes to the
            live strategy after launch will not affect this run.
          </p>
        </div>
      </form>
    </div>
  );
}
