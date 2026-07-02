/**
 * Portfolio Overview — Minimalist Global Vault View.
 * Performance analytics moved to Environment-specific sections (e.g. Paper Trading).
 */
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card,
  CardContent,
} from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import {
  Wallet,
  DollarSign,
  ShieldAlert,
  Loader2,
  AlertTriangle,
  Settings,
  Rocket,
} from "lucide-react";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/shared/components/ui/dialog";
import { portfolioApi } from "@/shared/services/portfolioApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { usePageTitle } from "@/shared/hooks/use-page-title";

export default function PortfolioOverview() {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editOpen, setEditOpen] = useState(false);
  const [editForm, setEditForm] = useState({ name: "", initial_capital: 0 });

  usePageTitle({
    title: "Global Vault Status",
    subtitle: "Manage your central capital pool and risk profile across all environments",
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const portRes = await portfolioApi.getMyPortfolio();
      setPortfolio(portRes.data);
      if (portRes.data) {
        setEditForm({
          name: portRes.data.name,
          initial_capital: portRes.data.initial_capital
        });
      }
    } catch (err) {
      notify.error("Failed to load vault data");
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (val) => {
    if (val == null) return "₹0";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(val);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (!portfolio) {
    return (
      <div className="container-padding py-6 lg:py-8">
        <Card className="bg-gray-900/50 border-gray-800 max-w-xl mx-auto text-center p-8">
          <AlertTriangle className="h-10 w-10 text-amber-400 mx-auto mb-4" />
          <p className="text-gray-300">
            Vault not initialized. Please set up your portfolio capital.
          </p>
        </Card>
      </div>
    );
  }

  const totalValue = parseFloat(portfolio.total_value || 0);
  const currentCapital = parseFloat(portfolio.current_capital || 0);
  const investedValue = parseFloat(portfolio.invested_value || 0);
  const initialCapital = parseFloat(portfolio.initial_capital || 0);
  const totalReturn = initialCapital > 0 ? ((totalValue - initialCapital) / initialCapital) * 100 : 0;

  return (
    <div className="container-padding py-6 lg:py-8 space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-1">
          <h2 className="text-2xl font-bold text-white tracking-tight">Global Governance Hub</h2>
          <p className="text-gray-400 text-sm">Centralized risk control and deployment status</p>
        </div>
        <button 
          onClick={() => setEditOpen(true)}
          className="p-2 rounded-lg bg-gray-900 border border-gray-800 text-gray-400 hover:text-white transition-colors"
        >
          <Settings className="h-5 w-5" />
        </button>
      </div>

      {/* ── Governance Hub KPI Row ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          {
            label: "Active Deployments",
            value: (portfolio?.active_deployments || 0).toString(),
            icon: Rocket,
            color: "indigo",
            sub: "Total running strategies",
          },
          {
            label: "Risk Violations",
            value: (portfolio?.risk_violations || 0).toString(),
            icon: ShieldAlert,
            color: "rose",
            sub: "Pending resolution",
          },
          {
            label: "Connected Brokers",
            value: (portfolio?.broker_count || 0).toString(),
            icon: Settings,
            color: "emerald",
            sub: "Ready for live ops",
          },
        ].map((kpi, i) => {
          const Icon = kpi.icon;
          return (
            <Card key={i} className="bg-gray-900/40 border-gray-800 backdrop-blur-sm overflow-hidden relative group">
              <div className={`absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 transition-opacity`}>
                <Icon className={`h-16 w-16 text-${kpi.color}-400`} />
              </div>
              <CardContent className="p-6 relative">
                <div className="flex items-center gap-3 mb-2">
                  <div className={`p-2 bg-${kpi.color}-500/10 rounded-xl`}>
                    <Icon className={`h-5 w-5 text-${kpi.color}-400`} />
                  </div>
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-widest">
                    {kpi.label}
                  </p>
                </div>
                <div className="flex items-baseline gap-3">
                  <p className="text-3xl font-black text-white">
                    {kpi.value}
                  </p>
                </div>
                <p className="text-[10px] text-gray-500 mt-2 font-medium italic">
                  {kpi.sub}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          {
            label: "Risk Profile Control",
            path: "/dashboard/portfolio/risk",
            icon: ShieldAlert,
            color: "orange",
          },
        ].map((link, i) => {
          const Icon = link.icon;
          return (
            <button
              key={i}
              onClick={() => navigate(link.path)}
              className={`flex items-center gap-3 p-4 bg-gray-900/50 border border-gray-800 rounded-2xl hover:bg-gray-800/70 transition-all text-left group`}
            >
              <div className={`p-3 bg-${link.color}-500/10 rounded-xl group-hover:bg-${link.color}-500/20 transition-colors`}>
                <Icon className={`h-6 w-6 text-${link.color}-400`} />
              </div>
              <span className="text-base text-gray-200 font-bold">
                {link.label}
              </span>
            </button>
          );
        })}
      </div>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="bg-gray-900 border-gray-800 text-white sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Vault Settings</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-gray-400">Vault Name</Label>
              <Input
                value={editForm.name}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                className="bg-gray-800 border-gray-700 text-white"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-gray-400">Initial Principal (₹)</Label>
              <Input
                type="number"
                value={editForm.initial_capital}
                onChange={(e) => setEditForm({ ...editForm, initial_capital: parseFloat(e.target.value) || 0 })}
                className="bg-gray-800 border-gray-700 text-white"
              />
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button variant="ghost" onClick={() => setEditOpen(false)}>Cancel</Button>
            <button
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-colors"
              onClick={async () => {
                try {
                  await portfolioApi.updatePortfolio(portfolio.id, editForm);
                  setPortfolio({ ...portfolio, ...editForm });
                  setEditOpen(false);
                  notify.success("Vault updated");
                } catch (err) {
                  notify.error("Update failed");
                }
              }}
            >
              Save Changes
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
