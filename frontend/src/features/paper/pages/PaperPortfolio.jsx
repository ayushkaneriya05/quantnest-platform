import {useStableCallback} from "@/shared/hooks/useStableCallback";
import { useState, useEffect, useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import {
  TrendingUp,
  BarChart3,
  RefreshCw,
  BookOpen,
  Terminal,
} from "lucide-react";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { usePageActions } from "@/shared/context/pageActions";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { paperApi } from "@/shared/services/paperApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { usePageTitle } from "@/shared/hooks/use-page-title";

import PaperPortfolioOverview from "@/features/paper/components/PaperPortfolioOverview.jsx";
import PaperPositions from "@/features/paper/components/PaperPositions.jsx";
import PaperOrderBook from "@/features/paper/components/PaperOrderBook.jsx";
import PaperTradeHistory from "@/features/paper/components/PaperTradeHistory.jsx";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { formatCurrency } from "@/shared/utils/formatters";
import { usePaperTradingUpdate, usePaperTradingWebSocket } from "@/shared/hooks/usePaperTradingWebSocket";

export default function PaperPortfolio() {
  const handleRefresh = useStableCallback(async () => {
    if (await fetchData()) notify.success("Data refreshed");
  });

  usePaperTradingWebSocket();
  const lastMessage = usePaperTradingUpdate();
  const { notify } = useNotifications();
  const { setPageHeader, clearPageHeader } = usePageActions();
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState([]);
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedAccount = searchParams.get("account_id");
  const selectedAccount = accounts.find((account) => String(account.id) === requestedAccount)?.id.toString()
    || accounts[0]?.id.toString() || "";

  const fetchData = useCallback(async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      const accountsRes = await paperApi.getAccounts();

      const loadedAccounts = accountsRes.data || [];
      setAccounts(loadedAccounts);
      return true;
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to load paper trading data"));
      return false;
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!lastMessage) return undefined;
    const timer = setTimeout(() => fetchData(false), 150);
    return () => clearTimeout(timer);
  }, [lastMessage, fetchData]);

  const handleAccountChange = useStableCallback((accountId) => {
    const next = new URLSearchParams(searchParams);
    next.set("account_id", accountId);
    setSearchParams(next, { replace: true });
  });

  const selectedAccountData = useMemo(
    () => accounts.find((a) => String(a.id) === selectedAccount),
    [accounts, selectedAccount]
  );

  usePageTitle({
    title: "Paper Trading Portfolio",
    subtitle: selectedAccountData ? `Managing ${selectedAccountData.name}` : "Monitor session positions, orders and trades",
  });

  useEffect(() => {
    const HeaderContent = () => (
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 min-w-0 w-full">
        <div className="flex min-w-0 max-w-full items-center gap-1 bg-card/50 p-1 rounded-xl border border-border backdrop-blur-md overflow-x-auto scrollbar-thin-theme">
          <button
            onClick={() => setActiveTab("overview")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap ${
              activeTab === "overview"
                ? "bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 shadow-[0_0_15px_rgba(99,102,241,0.1)]"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
            }`}
          >
            <BarChart3 className="h-4 w-4" />
            Overview
          </button>
          <button
            onClick={() => setActiveTab("positions")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap ${
              activeTab === "positions"
                ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.1)]"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
            }`}
          >
            <TrendingUp className="h-4 w-4" />
            Positions
          </button>
          <button
            onClick={() => setActiveTab("orders")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap ${
              activeTab === "orders"
                ? "bg-sky-500/10 text-sky-700 dark:text-sky-400 shadow-[0_0_15px_rgba(14,165,233,0.1)]"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
            }`}
          >
            <Terminal className="h-4 w-4" />
            Orders
          </button>
          <button
            onClick={() => setActiveTab("trades")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap ${
              activeTab === "trades"
                ? "bg-purple-500/10 text-purple-700 dark:text-purple-400 shadow-[0_0_15px_rgba(168,85,247,0.1)]"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
            }`}
          >
            <BookOpen className="h-4 w-4" />
            History
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Account Selector integrated in header */}
          {!loading && accounts.length > 0 && (
             <div className="flex items-center gap-2 bg-card/50 border border-border rounded-xl p-1 px-3 h-10">
                <div className="flex items-center gap-2 mr-2">
                  <div className="h-2 w-2 rounded-full bg-emerald-500 shrink-0" />
                  <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Session</span>
                </div>
                <Select resource="paper-accounts"
                  value={selectedAccount?.toString()}
                  onValueChange={(val) => handleAccountChange(val)}
                  disabled={loading}
                >
                  <SelectTrigger className="w-[280px] bg-transparent border-none text-foreground text-sm focus:ring-0 outline-none shadow-none h-8 font-medium px-2 hover:bg-secondary/50">
                    <SelectValue placeholder="Select session" />
                  </SelectTrigger>
                  <SelectContent className="bg-card border-border text-foreground">
                    {accounts.map((account) => (
                      <SelectItem key={account.id} value={account.id.toString()} className="focus:bg-secondary focus:text-foreground">
                        {account.name} ({formatCurrency(account.current_balance)})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <div className="h-4 w-[1px] bg-secondary mx-1" />
                <button
                  onClick={handleRefresh}
                  disabled={loading}
                  className="flex items-center gap-2 text-[10px] font-black text-muted-foreground hover:text-foreground transition-colors px-1 tracking-tighter"
                >
                  <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
                  <span>REFRESH</span>
                </button>
             </div>
          )}


        </div>
      </div>
    );

    setPageHeader(<HeaderContent />);

    return () => {
      clearPageHeader();
    };
  }, [activeTab, selectedAccount, accounts, loading, setPageHeader, clearPageHeader, handleRefresh, handleAccountChange]);



  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <GlobalLoader />
      </div>
    );
  }

  return (
    <div className="container-padding pb-8">

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === "overview" && <PaperPortfolioOverview account={selectedAccountData} />}
        {activeTab === "positions" && <PaperPositions selectedAccountId={selectedAccount} />}
        {activeTab === "orders" && <PaperOrderBook selectedAccountId={selectedAccount} />}
        {activeTab === "trades" && <PaperTradeHistory selectedAccountId={selectedAccount} />}
      </div>
    </div>
  );
}
