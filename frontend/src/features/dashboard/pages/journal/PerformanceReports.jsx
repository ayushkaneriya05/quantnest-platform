import { useEffect, useState } from "react";
import { BarChart3, GitCompareArrows, RefreshCw, Sparkles } from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { DatePicker } from "@/shared/components/ui/date-picker";
import { format } from "date-fns";
import { analyticsSuiteApi } from "@/shared/services/analyticsSuiteApi";
import { strategyApi } from "@/shared/services/strategyApi";

function formatNumber(value) {
  return Number(value || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function PerformanceReports() {
  const { notify } = useNotifications();
  const [dashboard, setDashboard] = useState(null);
  const [reports, setReports] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareForm, setCompareForm] = useState({ strategies: [], start_date: "", end_date: "" });
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const [dashboardRes, reportsRes, strategiesRes] = await Promise.all([
        analyticsSuiteApi.getAnalyticsDashboard(),
        analyticsSuiteApi.getDailyReports(),
        strategyApi.getAll(),
      ]);
      setDashboard(dashboardRes.data || {});
      setReports(Array.isArray(reportsRes.data?.results) ? reportsRes.data.results : reportsRes.data || []);
      setStrategies(Array.isArray(strategiesRes?.results) ? strategiesRes.results : strategiesRes || []);
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to load performance reports");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useSetPageActions(
    <>
      <Button
        variant="outline"
        onClick={async () => {
          try {
            await analyticsSuiteApi.refreshSnapshots({});
            notify.success("Analytics refreshed");
            await loadData();
          } catch (error) {
            notify.error(error?.response?.data?.detail || "Failed to refresh analytics");
          }
        }}
        className="border-gray-700 text-gray-100"
      >
        <RefreshCw className="mr-2 h-4 w-4" />
        Refresh Reports
      </Button>
      <Button className="bg-cyan-600 hover:bg-cyan-500" onClick={() => setCompareOpen(true)}>
        <GitCompareArrows className="mr-2 h-4 w-4" />
        Compare Strategies
      </Button>
    </>,
  );

  const latestReport = dashboard?.latest_report;
  const snapshots = dashboard?.snapshots || [];
  const comparisons = dashboard?.comparisons || [];
  const insights = dashboard?.insights || [];

  const saveComparison = async () => {
    try {
      await analyticsSuiteApi.createComparison(compareForm);
      notify.success("Strategy comparison generated");
      setCompareOpen(false);
      await loadData();
    } catch (error) {
      notify.error(error?.response?.data?.detail || "Failed to generate strategy comparison");
    }
  };

  const summaryCards = [
    { label: "Total P&L", value: `Rs ${formatNumber(latestReport?.total_pnl)}`, tone: Number(latestReport?.total_pnl || 0) >= 0 ? "text-emerald-300" : "text-red-300" },
    { label: "Trades", value: latestReport?.total_trades || 0, tone: "text-white" },
    { label: "Best Strategy", value: latestReport?.best_strategy_name || "N/A", tone: "text-cyan-300" },
    { label: "Unread Notifications", value: dashboard?.notification_summary?.unread || 0, tone: "text-amber-300" },
  ];

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map((item) => (
          <Card key={item.label} className="border-gray-800 bg-gray-900/60">
            <CardContent className="p-5">
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500">{item.label}</p>
              <p className={`mt-2 text-2xl font-semibold ${item.tone}`}>{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="border-gray-800 bg-gray-900/60">
          <CardHeader><CardTitle className="flex items-center gap-2 text-white"><BarChart3 className="h-4 w-4 text-cyan-300" /> Daily Reports</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <div className="py-8 text-center text-gray-400">Loading reports...</div>
            ) : reports.length === 0 ? (
              <div className="py-8 text-center text-gray-400">No reports yet. Run refresh to generate one.</div>
            ) : (
              reports.slice(0, 10).map((row) => (
                <div key={row.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-white">{row.date}</p>
                      <p className="mt-1 text-sm text-gray-400">Realized {row.realized_pnl} • Unrealized {row.unrealized_pnl}</p>
                    </div>
                    <Badge className={Number(row.total_pnl || 0) >= 0 ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20" : "bg-red-500/10 text-red-300 border-red-500/20"}>
                      Rs {formatNumber(row.total_pnl)}
                    </Badge>
                  </div>
                  <div className="mt-3 grid gap-3 sm:grid-cols-3 text-sm">
                    <div className="rounded-xl bg-gray-950/60 p-3"><p className="text-gray-500">Trades</p><p className="mt-1 text-white">{row.total_trades}</p></div>
                    <div className="rounded-xl bg-gray-950/60 p-3"><p className="text-gray-500">Wins / Losses</p><p className="mt-1 text-white">{row.winning_trades} / {row.losing_trades}</p></div>
                    <div className="rounded-xl bg-gray-950/60 p-3"><p className="text-gray-500">Best Strategy</p><p className="mt-1 text-white">{row.best_strategy_name || "N/A"}</p></div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader><CardTitle className="text-white">Strategy Snapshots</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {snapshots.map((snapshot) => (
                <div key={snapshot.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-white">{snapshot.strategy_name}</p>
                      <p className="mt-1 text-sm text-gray-400">Win rate {snapshot.win_rate}% • Trades {snapshot.trades_count}</p>
                    </div>
                    <Badge className="bg-cyan-500/10 text-cyan-300 border-cyan-500/20">Rs {formatNumber(snapshot.daily_pnl)}</Badge>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="border-gray-800 bg-gray-900/60">
            <CardHeader><CardTitle className="text-white">Comparisons & Insights</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {comparisons.slice(0, 3).map((comparison) => (
                <div key={comparison.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <p className="font-semibold text-white">{comparison.strategy_names?.join(", ") || "Strategy comparison"}</p>
                  <p className="mt-1 text-sm text-gray-400">{comparison.start_date} to {comparison.end_date}</p>
                </div>
              ))}
              {insights.slice(0, 2).map((insight) => (
                <div key={insight.id} className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                  <p className="flex items-center gap-2 font-semibold text-white"><Sparkles className="h-4 w-4 text-amber-300" /> {insight.title}</p>
                  <p className="mt-2 text-sm text-gray-300">{insight.description}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      <Dialog open={compareOpen} onOpenChange={setCompareOpen}>
        <DialogContent className="border-gray-800 bg-gray-950 text-white">
          <DialogHeader><DialogTitle>Compare Strategies</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Strategy IDs (comma separated)</Label>
              <Input
                value={compareForm.strategies.join(",")}
                onChange={(event) =>
                  setCompareForm((current) => ({
                    ...current,
                    strategies: event.target.value.split(",").map((item) => Number(item.trim())).filter(Boolean),
                  }))
                }
                placeholder={strategies.slice(0, 5).map((strategy) => `${strategy.id}:${strategy.name}`).join(" | ")}
                className="border-gray-700 bg-black/20 text-white"
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Start Date</Label>
                <DatePicker 
                  date={compareForm.start_date ? new Date(compareForm.start_date + "T00:00:00") : null} 
                  setDate={(date) => setCompareForm((current) => ({ ...current, start_date: date ? format(date, "yyyy-MM-dd") : "" }))} 
                  placeholder="Select Date"
                  className="border-gray-700 bg-black/20 text-white" 
                />
              </div>
              <div className="space-y-2">
                <Label>End Date</Label>
                <DatePicker 
                  date={compareForm.end_date ? new Date(compareForm.end_date + "T00:00:00") : null} 
                  setDate={(date) => setCompareForm((current) => ({ ...current, end_date: date ? format(date, "yyyy-MM-dd") : "" }))} 
                  placeholder="Select Date"
                  className="border-gray-700 bg-black/20 text-white" 
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" className="border-gray-700 text-gray-100" onClick={() => setCompareOpen(false)}>Cancel</Button>
            <Button className="bg-cyan-600 hover:bg-cyan-500" onClick={saveComparison}>Generate</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
