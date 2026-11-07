import RefreshButton from "@/shared/components/RefreshButton";
import Pagination from "@/shared/components/Pagination";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { usePagination, useQueryState } from "@/shared/hooks/usePagination";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import {useStableCallback} from "@/shared/hooks/useStableCallback";
import { useState, useEffect, useRef } from "react";
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
import { formatCurrency, formatDateTime } from "@/shared/utils/formatters";

const TYPE_STYLES = {
  ADJUSTMENT: { icon: RefreshCw, color: "text-brand", bg: "bg-brand/5 dark:bg-brand/20" },
  PROFIT_BOOKING: { icon: ArrowUpCircle, color: "text-success", bg: "bg-success/5 dark:bg-success/20" },
  LOSS_SETTLEMENT: { icon: ArrowDownCircle, color: "text-loss", bg: "bg-loss/5 dark:bg-loss/20" },
  ALLOCATION: { icon: ArrowUpCircle, color: "text-brand", bg: "bg-brand/5 dark:bg-brand/20" },
  DEALLOCATION: { icon: ArrowDownCircle, color: "text-warning", bg: "bg-warning/5 dark:bg-warning/20" },
  DEPOSIT: { icon: ArrowUpCircle, color: "text-success", bg: "bg-success/5 dark:bg-success/20" },
  WITHDRAWAL: { icon: ArrowDownCircle, color: "text-loss", bg: "bg-loss/5 dark:bg-loss/20" },
};

export default function PaperTransactions() {
  const fetchData = useStableCallback(async () => {
    const generation = ++request.current;
    setError("");
    try {
      setLoading(true);
      const txData = await portfolioApi.getTransactions({ page, page_size: pageSize, search });
      if (generation !== request.current) return;
      setTransactions(txData.data.results); setMetadata(txData.data); accept(txData.data);
    } catch (error) {
      if (generation === request.current) setError(getApiErrorMessage(error, "Failed to load paper transactions"));
    } finally {
      if (generation === request.current) setLoading(false);
    }
  });

  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useQueryState("search", "", { namespace: "transactions", replace: true });
  const { page, pageSize, setPage, setPageSize, accept } = usePagination(search, 'transactions');
  const [metadata, setMetadata] = useState({ count: 0 });
  const request = useRef(0);



  useEffect(() => {
    const timer = setTimeout(fetchData, search ? 250 : 0);
    const guard = request;
    return () => { clearTimeout(timer); guard.current++; };
  }, [fetchData, page, pageSize, search]);


  if (error) return <WorkspaceState error={error} onRetry={fetchData} />;
  if (loading && !metadata.page) return <GlobalLoader fullHeight={false} />;

  return (
    <div className="space-y-3 animate-in fade-in duration-300">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-lg font-semibold text-foreground">Capital Movement Logs</h3>
        <RefreshButton onClick={fetchData} label="Refresh capital transactions" loading={loading} /><div className="relative min-w-36 flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search logs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-card/50 border-border text-sm"
          />
        </div>
      </div>

      <Card className="bg-card/50 border-border">
        <CardContent className="p-0">
          {transactions.length === 0 ? (
            <div className="text-center py-12">
              <Clock className="h-10 w-10 text-foreground mx-auto mb-3" />
              <p className="text-muted-foreground italic">No capital movements recorded yet</p>
            </div>
          ) : (
            <div className="divide-y divide-border/50">
              {transactions.map((tx) => {
                const style = TYPE_STYLES[tx.transaction_type] || TYPE_STYLES.ADJUSTMENT;
                const Icon = style.icon;
                return (
                  <div key={tx.id} className="flex items-center justify-between p-3 hover:bg-secondary/20 transition-colors">
                    <div className="flex items-center gap-3">
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
                      <p className={`text-sm font-bold ${tx.amount > 0 ? "text-success" : "text-loss"}`}>
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
      <Pagination {...metadata} page={page} pageSize={pageSize} loading={loading} onPageChange={setPage} onPageSizeChange={setPageSize} label="Capital transaction pages" />
    </div>
  );
}
