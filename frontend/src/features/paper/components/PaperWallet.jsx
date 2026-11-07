import { GlobalLoader } from '@/shared/components/ui/global-loader';
import {useStableCallback} from "@/shared/hooks/useStableCallback";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
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
import { formatCurrency } from "@/shared/utils/formatters";

export default function PaperWallet() {
  const fetchData = useStableCallback(async () => {
    try {
      setLoading(true);
      const res = await portfolioApi.getMyPortfolio();
      setPortfolio(res.data);
    } catch (err) {
      notify.error(getApiErrorMessage(err, "Failed to load paper wallet"));
    } finally {
      setLoading(false);
    }
  });

  const { notify } = useNotifications();
  const [portfolio, setPortfolio] = useState(null);
  const [amount, setAmount] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);



  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAction = async (type) => {
    if (!amount || parseFloat(amount) <= 0) {
      notify.error("Enter a valid amount");
      return;
    }
    try {
      setSaving(true);
      if (type === "DEPOSIT") {
        await portfolioApi.deposit(
          portfolio.id,
          parseFloat(amount),
          "Paper Fund Addition",
        );
        notify.success(`${formatCurrency(amount)} added to Paper Wallet`);
      } else {
        await portfolioApi.withdraw(
          portfolio.id,
          parseFloat(amount),
          "Paper Fund Removal",
        );
        notify.success(`${formatCurrency(amount)} removed from Paper Wallet`);
      }
      setAmount("");
      await fetchData();
    } catch (err) {
      notify.error(getApiErrorMessage(err, `${type === "DEPOSIT" ? "Addition" : "Removal"} failed`));
    } finally {
      setSaving(false);
    }
  };

  if (loading)
    return (
      <div className="h-40 flex items-center justify-center"><GlobalLoader inline text="Loading..." /></div>
    );

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Card>
          <CardContent className="pt-4">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-brand text-sm font-medium">
                  Virtual Balance
                </p>
                <h3 className="text-3xl font-black text-foreground mt-1">
                  {formatCurrency(Number(portfolio?.current_capital || 0))}
                </h3>
                <p className="text-xs text-brand mt-2 flex items-center gap-1">
                  <ShieldCheck className="h-3 w-3" />
                  Available for strategy allocation
                </p>
              </div>
              <div className="p-3 bg-brand/20 rounded-2xl">
                <DollarSign className="h-6 w-6 text-brand" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/40 border-border">
          <CardContent className="pt-4 space-y-3">
            <div className="space-y-2">
              <label className="text-xs font-bold text-muted-foreground uppercase tracking-widest">
                Adjust Paper Funds
              </label>
              <div className="flex gap-2">
                <Input
                  type="number"
                  min="0.01"
                  step="0.01"
                  placeholder="Amount (₹)"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  disabled={saving}
                  className="bg-secondary border-border text-foreground"
                />
                <Button variant="success"
                  onClick={() => handleAction("DEPOSIT")}
                  disabled={saving}
                  className="shrink-0"
                >
                  <Plus className="h-4 w-4" />
                </Button>
                <Button
                  onClick={() => handleAction("WITHDRAW")}
                  disabled={saving}
                  variant="destructive-outline"
                  className="shrink-0"
                >
                  <Minus className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-[10px] text-muted-foreground">
                This adds/removes virtual capital from your global vault.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="p-3 rounded-2xl bg-success/5 border border-success/10 flex items-center gap-3">
          <div className="p-2 bg-success/10 rounded-lg">
            <TrendingUp className="h-5 w-5 text-success" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Realized P&amp;L</p>
            <p className={`text-sm font-bold ${Number(portfolio?.realized_pnl || 0) >= 0 ? "text-success" : "text-loss"}`}>
              {formatCurrency(portfolio?.realized_pnl)}
            </p>
          </div>
        </div>
        <div className="p-3 rounded-2xl bg-loss/5 border border-loss/10 flex items-center gap-3">
          <div className="p-2 bg-loss/10 rounded-lg">
            <TrendingDown className="h-5 w-5 text-loss" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Total Capital Allocated</p>
            <p className="text-sm font-bold text-brand">
              {formatCurrency(Number(portfolio?.allocated_capital || 0))}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
