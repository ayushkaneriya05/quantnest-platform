import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
} from "@/shared/components/ui/card";
import {
  ArrowUpCircle,
  ArrowDownCircle,
  RefreshCw,
  Clock,
  Search,
} from "lucide-react";
import { Input } from "@/shared/components/ui/input";
import { portfolioApi } from "@/shared/services/portfolioApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { formatCurrency, formatDateTime } from "@/shared/utils/formatters";

const TYPE_STYLES = {
  ADJUSTMENT: { icon: RefreshCw, color: "text-blue-700 dark:text-blue-400", bg: "bg-blue-50 dark:bg-blue-900/20" },
  PROFIT_BOOKING: { icon: ArrowUpCircle, color: "text-emerald-700 dark:text-emerald-400", bg: "bg-emerald-50 dark:bg-emerald-900/20" },
  LOSS_SETTLEMENT: { icon: ArrowDownCircle, color: "text-rose-700 dark:text-rose-400", bg: "bg-rose-50 dark:bg-rose-900/20" },
  ALLOCATION: { icon: ArrowUpCircle, color: "text-indigo-700 dark:text-indigo-400", bg: "bg-indigo-50 dark:bg-indigo-900/20" },
  DEALLOCATION: { icon: ArrowDownCircle, color: "text-amber-700 dark:text-amber-400", bg: "bg-amber-50 dark:bg-amber-900/20" },
  DEPOSIT: { icon: ArrowUpCircle, color: "text-emerald-700 dark:text-emerald-400", bg: "bg-emerald-50 dark:bg-emerald-900/20" },
  WITHDRAWAL: { icon: ArrowDownCircle, color: "text-rose-700 dark:text-rose-400", bg: "bg-rose-50 dark:bg-rose-900/20" },
};

export default function PaperTransactions() {
  const { notify } = useNotifications();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const fetchData = async () => {
    try {
      setLoading(true);
      const txData = await portfolioApi.getTransactions();
      setTransactions(txData.data || []);
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to load paper transactions"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const filteredTransactions = transactions.filter(tx => 
    tx.transaction_type.toLowerCase().includes(search.toLowerCase()) ||
    (tx.notes && tx.notes.toLowerCase().includes(search.toLowerCase()))
  );

  if (loading) return null;

  return (
    <div className="space-y-4 animate-in fade-in duration-300">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold text-foreground">Capital Movement Logs</h3>
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search logs..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-card/50 border-border h-9 text-sm"
          />
        </div>
      </div>

      <Card className="bg-card/50 border-border">
        <CardContent className="p-0">
          {filteredTransactions.length === 0 ? (
            <div className="text-center py-12">
              <Clock className="h-10 w-10 text-foreground mx-auto mb-3" />
              <p className="text-muted-foreground italic">No capital movements recorded yet</p>
            </div>
          ) : (
            <div className="divide-y divide-border/50">
              {filteredTransactions.map((tx) => {
                const style = TYPE_STYLES[tx.transaction_type] || TYPE_STYLES.ADJUSTMENT;
                const Icon = style.icon;
                return (
                  <div key={tx.id} className="flex items-center justify-between p-4 hover:bg-secondary/20 transition-colors">
                    <div className="flex items-center gap-4">
                      <div className={`p-2 rounded-lg ${style.bg}`}>
                        <Icon className={`h-5 w-5 ${style.color}`} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-foreground font-medium text-sm">
                            {tx.transaction_type.replace(/_/g, " ")}
                          </p>
                          <span className="text-[10px] text-muted-foreground">•</span>
                          <p className="text-[11px] text-muted-foreground">
                            {formatDateTime(tx.created_at)}
                          </p>
                        </div>
                        {tx.notes && (
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                            {tx.notes}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`text-sm font-bold ${tx.amount > 0 ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"}`}>
                        {tx.amount > 0 ? "+" : "-"} {formatCurrency(Math.abs(tx.amount))}
                      </p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                         Balance: {formatCurrency(tx.balance_after)}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
