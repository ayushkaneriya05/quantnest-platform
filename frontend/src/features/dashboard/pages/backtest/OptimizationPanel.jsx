/**
 * Optimization Panel - configure and run parameter optimization
 */
import React from "react";
import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
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
import { Badge } from "@/shared/components/ui/badge";
import {
  Play,
  Plus,
  Trash2,
  BarChart2,
  SlidersHorizontal,
  Trophy,
} from "lucide-react";
import { backtestApi } from "@/shared/services/backtestApi";
import { strategyApi } from "@/shared/services/strategyApi";
import { useNotifications } from "@/shared/hooks/useNotifications";

const OPTIMIZATION_METRICS = [
  { value: "SHARPE", label: "Sharpe Ratio" },
  { value: "RETURN", label: "Total Return" },
  { value: "DRAWDOWN", label: "Min Drawdown" },
  { value: "WIN_RATE", label: "Win Rate" },
  { value: "PROFIT_FACTOR", label: "Profit Factor" },
];

export default function OptimizationPanel() {
  const location = useLocation();
  const { notify } = useNotifications();
  const [strategies, setStrategies] = useState([]);
  const [optimizations, setOptimizations] = useState([]);
  const [selectedOptimization, setSelectedOptimization] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const [formData, setFormData] = useState({
    name: "",
    strategy: "",
    start_date: "",
    end_date: "",
    initial_capital: 100000,
    optimization_metric: "SHARPE",
    parameters_to_optimize: [{ param_name: "", min: 0, max: 100, step: 1 }],
  });

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (location.state?.strategyId) {
      setFormData((current) => ({
        ...current,
        strategy: String(location.state.strategyId),
      }));
      setShowForm(true);
    }
  }, [location.state]);

  const fetchData = async () => {
    try {
      const [strategyData, optimizationData] = await Promise.all([
        strategyApi.getAll(),
        backtestApi.getOptimizations(),
      ]);
      const strategyList = Array.isArray(strategyData)
        ? strategyData
        : strategyData.data || [];
      setStrategies(strategyList.filter((strategy) => strategy.allow_backtest));
      setOptimizations(
        Array.isArray(optimizationData.data) ? optimizationData.data : [],
      );
    } catch (error) {
      notify.error("Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  const handleAddParam = () => {
    setFormData({
      ...formData,
      parameters_to_optimize: [
        ...formData.parameters_to_optimize,
        { param_name: "", min: 0, max: 100, step: 1 },
      ],
    });
  };

  const handleRemoveParam = (idx) => {
    setFormData({
      ...formData,
      parameters_to_optimize: formData.parameters_to_optimize.filter(
        (_, i) => i !== idx,
      ),
    });
  };

  const handleParamChange = (idx, field, value) => {
    const params = [...formData.parameters_to_optimize];
    params[idx][field] = value;
    setFormData({ ...formData, parameters_to_optimize: params });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.strategy || !formData.start_date || !formData.end_date) {
      notify.error("Please fill all required fields");
      return;
    }

    try {
      const response = await backtestApi.createOptimization(formData);
      notify.success("Optimization created! Starting...");
      await backtestApi.startOptimization(response.data.id);
      setShowForm(false);
      setSelectedOptimization(null);
      setResults([]);
      fetchData();
    } catch (error) {
      notify.error("Failed to create optimization");
    }
  };

  const handleViewResults = async (optimization) => {
    try {
      setSelectedOptimization(optimization);
      const response = await backtestApi.getOptimizationResults(
        optimization.id,
      );
      setResults(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      notify.error("Failed to load optimization results");
    }
  };

  const formatDate = (dateString) =>
    new Date(dateString).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });

  const formatMetric = (value) => {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "-";
    }
    return Number(value).toFixed(2);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Parameter Optimization
          </h1>
          <p className="text-sm text-gray-400">
            Create optimization runs and inspect the best parameter
            combinations.
          </p>
        </div>
        <Button
          type="button"
          onClick={() => setShowForm((current) => !current)}
          className="bg-indigo-600 hover:bg-indigo-500"
        >
          <SlidersHorizontal className="h-4 w-4 mr-2" />
          {showForm ? "Hide Form" : "New Optimization"}
        </Button>
      </div>

      {showForm && (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Configure Optimization</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="space-y-2">
                  <Label className="text-gray-400">Strategy *</Label>
                  <Select
                    value={formData.strategy}
                    onValueChange={(value) =>
                      setFormData({ ...formData, strategy: value })
                    }
                  >
                    <SelectTrigger className="bg-gray-800 border-gray-700">
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
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
                </div>
                <div className="space-y-2">
                  <Label className="text-gray-400">Name *</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    placeholder="Optimization name"
                    className="bg-gray-800 border-gray-700 text-white"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-gray-400">Start Date *</Label>
                  <Input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) =>
                      setFormData({ ...formData, start_date: e.target.value })
                    }
                    className="bg-gray-800 border-gray-700 text-white"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-gray-400">End Date *</Label>
                  <Input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) =>
                      setFormData({ ...formData, end_date: e.target.value })
                    }
                    className="bg-gray-800 border-gray-700 text-white"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label className="text-gray-400">Optimization Metric</Label>
                <Select
                  value={formData.optimization_metric}
                  onValueChange={(value) =>
                    setFormData({ ...formData, optimization_metric: value })
                  }
                >
                  <SelectTrigger className="bg-gray-800 border-gray-700 w-64">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {OPTIMIZATION_METRICS.map((metric) => (
                      <SelectItem key={metric.value} value={metric.value}>
                        {metric.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="text-gray-400">
                    Parameters to Optimize
                  </Label>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={handleAddParam}
                    className="border-gray-700"
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add
                  </Button>
                </div>
                {formData.parameters_to_optimize.map((param, idx) => (
                  <div key={idx} className="grid grid-cols-5 gap-3 items-end">
                    <div className="space-y-1">
                      <Label className="text-xs text-gray-500">
                        Parameter Name
                      </Label>
                      <Input
                        value={param.param_name}
                        onChange={(e) =>
                          handleParamChange(idx, "param_name", e.target.value)
                        }
                        placeholder="e.g., ema_period"
                        className="bg-gray-800 border-gray-700 text-white"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs text-gray-500">Min</Label>
                      <Input
                        type="number"
                        value={param.min}
                        onChange={(e) =>
                          handleParamChange(
                            idx,
                            "min",
                            parseFloat(e.target.value),
                          )
                        }
                        className="bg-gray-800 border-gray-700 text-white"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs text-gray-500">Max</Label>
                      <Input
                        type="number"
                        value={param.max}
                        onChange={(e) =>
                          handleParamChange(
                            idx,
                            "max",
                            parseFloat(e.target.value),
                          )
                        }
                        className="bg-gray-800 border-gray-700 text-white"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs text-gray-500">Step</Label>
                      <Input
                        type="number"
                        value={param.step}
                        onChange={(e) =>
                          handleParamChange(
                            idx,
                            "step",
                            parseFloat(e.target.value),
                          )
                        }
                        className="bg-gray-800 border-gray-700 text-white"
                      />
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => handleRemoveParam(idx)}
                      className="text-red-400"
                      disabled={formData.parameters_to_optimize.length === 1}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>

              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowForm(false)}
                  className="border-gray-700"
                >
                  Cancel
                </Button>
                <Button type="submit" className="bg-indigo-600">
                  <Play className="h-4 w-4 mr-1" />
                  Start Optimization
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <Card className="bg-gray-900/50 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white">Optimization Runs</CardTitle>
        </CardHeader>
        <CardContent>
          {optimizations.length === 0 ? (
            <div className="py-8 text-center text-gray-500">
              No optimization runs yet
            </div>
          ) : (
            <div className="space-y-3">
              {optimizations.map((opt) => (
                <div
                  key={opt.id}
                  className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg"
                >
                  <div>
                    <p className="text-white font-medium">{opt.name}</p>
                    <p className="text-sm text-gray-400">
                      {opt.strategy_name} • {formatDate(opt.start_date)} -{" "}
                      {formatDate(opt.end_date)}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-sm text-gray-400">Progress</p>
                      <p className="text-white font-medium">
                        {opt.progress_pct || 0}%
                      </p>
                    </div>
                    <Badge
                      className={
                        opt.status === "COMPLETED"
                          ? "bg-green-600"
                          : "bg-blue-600"
                      }
                    >
                      {opt.status}
                    </Badge>
                    {opt.status === "COMPLETED" && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => handleViewResults(opt)}
                        className="border-gray-700"
                      >
                        <BarChart2 className="h-4 w-4 mr-1" />
                        Results
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {selectedOptimization && (
        <Card className="bg-gray-900/50 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Trophy className="h-5 w-5 text-amber-400" />
              Optimization Results
            </CardTitle>
          </CardHeader>
          <CardContent>
            {results.length === 0 ? (
              <div className="py-8 text-center text-gray-500">
                No optimization results available for this run yet.
              </div>
            ) : (
              <div className="space-y-3">
                {results.map((result) => (
                  <div
                    key={result.id}
                    className="rounded-lg border border-gray-800 bg-gray-800/40 p-4"
                  >
                    <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                      <div>
                        <p className="text-sm font-semibold text-white">
                          Params
                        </p>
                        <pre className="mt-2 overflow-x-auto rounded bg-black/20 p-3 text-xs text-gray-300">
                          {JSON.stringify(result.params || {}, null, 2)}
                        </pre>
                      </div>
                      <div className="grid grid-cols-2 gap-3 text-sm md:min-w-[280px]">
                        <div>
                          <p className="text-gray-500">Sharpe</p>
                          <p className="font-semibold text-white">
                            {formatMetric(result.sharpe)}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Return %</p>
                          <p className="font-semibold text-green-400">
                            {formatMetric(result.total_return)}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Max Drawdown %</p>
                          <p className="font-semibold text-red-400">
                            {formatMetric(result.max_drawdown)}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Win Rate %</p>
                          <p className="font-semibold text-white">
                            {formatMetric(result.win_rate)}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Profit Factor</p>
                          <p className="font-semibold text-white">
                            {formatMetric(result.profit_factor)}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Trades</p>
                          <p className="font-semibold text-white">
                            {result.total_trades ?? 0}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
