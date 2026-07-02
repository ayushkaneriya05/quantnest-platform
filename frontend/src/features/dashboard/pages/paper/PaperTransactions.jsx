import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import {
  ArrowUpCircle,
  ArrowDownCircle,
  RefreshCw,
  Clock,
  Search,
} from "lucide-react";
import { Input } from "@/shared/components/ui/input";
import { portfolioApi } from "@/shared/services/portfolioApi";
import { useNotifications } from "@/shared/hooks/useNotifications";

const TYPE_STYLES = {
  ADJUSTMENT: { icon: RefreshCw, color: "text-blue-400", bg: "bg-blue-900/20" },
  PROFIT_BOOKING: { icon: ArrowUpCircle, color: "text-emerald-400", bg: "bg-emerald-900/20" },
  LOSS_SETTLEMENT: { icon: ArrowDownCircle, color: "text-rose-400", bg: "bg-rose-900/20" },
  ALLOCATION: { icon: ArrowUpCircle, color: "text-indigo-400", bg: "bg-indigo-900/20" },
  DEALLOCATION: { icon: ArrowDownCircle, color: "text-amber-400", bg: "bg-amber-900/20" },
  DEPOSIT: { icon: ArrowUpCircle, color: "text-emerald-400", bg: "bg-emerald-900/20" },
  WITHDRAWAL: { icon: ArrowDownCircle, color: "text-rose-400", bg: "bg-rose-900/20" },
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
      // Filter for paper-trading related transactions: Allocations, Settlements, and Paper-specific Wallet moves
      const paperTxs = (txData.data || []).filter(tx => {
        const type = tx.transaction_type;
        const isPaperNote = (tx.notes || "").toLowerCase().includes("paper");
        return (
          ['ALLOCATION', 'DEALLOCATION', 'PROFIT_BOOKING', 'LOSS_SETTLEMENT', 'ADJUSTMENT'].includes(type) ||
          (['DEPOSIT', 'WITHDRAWAL'].includes(type))
        );
      });
      setTransactions(paperTxs);
    } catch (error) {
      notify.error("Failed to load paper transactions");
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

  const formatCurrency = (val) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(Math.abs(val || 0));
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString("en-IN", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading) return null;

  return (
    <div className="space-y-4 animate-in fade-in duration-300">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold text-white">Capital Movement Logs</h3>
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <Input 
            placeholder="Search logs..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-gray-900/50 border-gray-800 h-9 text-sm"
          />
        </div>
      </div>

      <Card className="bg-gray-900/50 border-gray-800">
        <CardContent className="p-0">
          {filteredTransactions.length === 0 ? (
            <div className="text-center py-12">
              <Clock className="h-10 w-10 text-gray-700 mx-auto mb-3" />
              <p className="text-gray-500 italic">No capital movements recorded yet</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-800/50">
              {filteredTransactions.map((tx) => {
                const style = TYPE_STYLES[tx.transaction_type] || TYPE_STYLES.ADJUSTMENT;
                const Icon = style.icon;
                return (
                  <div key={tx.id} className="flex items-center justify-between p-4 hover:bg-gray-800/20 transition-colors">
                    <div className="flex items-center gap-4">
                      <div className={`p-2 rounded-lg ${style.bg}`}>
                        <Icon className={`h-5 w-5 ${style.color}`} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-white font-medium text-sm">
                            {tx.transaction_type.replace(/_/g, " ")}
                          </p>
                          <span className="text-[10px] text-gray-500">•</span>
                          <p className="text-[11px] text-gray-500">
                            {formatDate(tx.created_at)}
                          </p>
                        </div>
                        {tx.notes && (
                          <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">
                            {tx.notes}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`text-sm font-bold ${tx.amount > 0 ? "text-emerald-400" : "text-rose-400"}`}>
                        {tx.amount > 0 ? "+" : "-"} {formatCurrency(tx.amount)}
                      </p>
                      <p className="text-[10px] text-gray-500 mt-0.5">
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
