import { useState, useEffect } from "react";
import { Card, CardContent } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import {
  Plus,
  Minus,
  DollarSign,
  TrendingUp,
  TrendingDown,
  ShieldCheck,
} from "lucide-react";
import { portfolioApi } from "@/shared/services/portfolioApi";
import { useNotifications } from "@/shared/hooks/useNotifications";

export default function PaperWallet() {
  const { notify } = useNotifications();
  const [portfolio, setPortfolio] = useState(null);
  const [amount, setAmount] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await portfolioApi.getMyPortfolio();
      setPortfolio(res.data);
    } catch (err) {
      notify.error("Failed to load paper wallet");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAction = async (type) => {
    if (!amount || parseFloat(amount) <= 0) {
      notify.error("Enter a valid amount");
      return;
    }
    try {
      if (type === "DEPOSIT") {
        await portfolioApi.deposit(
          portfolio.id,
          parseFloat(amount),
          "Paper Fund Addition",
        );
        notify.success(`₹${amount} added to Paper Wallet`);
      } else {
        await portfolioApi.withdraw(
          portfolio.id,
          parseFloat(amount),
          "Paper Fund Removal",
        );
        notify.success(`₹${amount} removed from Paper Wallet`);
      }
      setAmount("");
      fetchData();
    } catch (err) {
      notify.error(`${type === "DEPOSIT" ? "Addition" : "Removal"} failed`);
    }
  };

  if (loading)
    return (
      <div className="h-40 flex items-center justify-center">Loading...</div>
    );

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="bg-gradient-to-br from-indigo-900/40 to-purple-900/40 border-indigo-800/50">
          <CardContent className="pt-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-indigo-300 text-sm font-medium">
                  Virtual Balance
                </p>
                <h3 className="text-3xl font-black text-white mt-1">
                  ₹
                  {Number(portfolio?.current_capital || 0).toLocaleString(
                    "en-IN",
                  )}
                </h3>
                <p className="text-xs text-indigo-400/80 mt-2 flex items-center gap-1">
                  <ShieldCheck className="h-3 w-3" />
                  Available for strategy allocation
                </p>
              </div>
              <div className="p-3 bg-indigo-500/20 rounded-2xl">
                <DollarSign className="h-6 w-6 text-indigo-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-900/40 border-gray-800">
          <CardContent className="pt-6 space-y-4">
            <div className="space-y-2">
              <label className="text-xs font-bold text-gray-500 uppercase tracking-widest">
                Adjust Paper Funds
              </label>
              <div className="flex gap-2">
                <Input
                  type="number"
                  placeholder="Amount (₹)"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="bg-gray-800 border-gray-700 text-white"
                />
                <Button
                  onClick={() => handleAction("DEPOSIT")}
                  className="bg-emerald-600 hover:bg-emerald-500 shrink-0"
                >
                  <Plus className="h-4 w-4" />
                </Button>
                <Button
                  onClick={() => handleAction("WITHDRAW")}
                  variant="outline"
                  className="border-rose-800 text-rose-400 hover:bg-rose-500/10 shrink-0"
                >
                  <Minus className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-[10px] text-gray-500">
                This adds/removes virtual capital from your global vault.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 rounded-2xl bg-emerald-500/5 border border-emerald-500/10 flex items-center gap-4">
          <div className="p-2 bg-emerald-500/10 rounded-lg">
            <TrendingUp className="h-5 w-5 text-emerald-400" />
          </div>
          <div>
            <p className="text-xs text-gray-500">Total Profits Settled</p>
            <p className="text-sm font-bold text-emerald-400">
              ₹{Number(portfolio?.realized_pnl || 0).toLocaleString("en-IN")}
            </p>
          </div>
        </div>
        <div className="p-4 rounded-2xl bg-rose-500/5 border border-rose-500/10 flex items-center gap-4">
          <div className="p-2 bg-rose-500/10 rounded-lg">
            <TrendingDown className="h-5 w-5 text-rose-400" />
          </div>
          <div>
            <p className="text-xs text-gray-500">Total Capital Allocated</p>
            <p className="text-sm font-bold text-indigo-400">
              ₹
              {Math.max(
                0,
                Number(portfolio?.total_value || 0) -
                  Number(portfolio?.current_capital || 0),
              ).toLocaleString("en-IN")}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
