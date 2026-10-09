import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  TrendingUp,
  BarChart3,
  RefreshCw,
  BookOpen,
  Terminal,
  Plus,
} from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { usePageActions } from "@/shared/context/pageActions";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { paperApi } from "@/shared/services/paperApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { usePageTitle } from "@/shared/hooks/use-page-title";

import PaperTradingDashboard from "@/features/paper/pages/PaperTradingDashboard.jsx";
import PaperPositions from "@/features/paper/components/PaperPositions.jsx";
import PaperOrderBook from "@/features/paper/components/PaperOrderBook.jsx";
import PaperTradeHistory from "@/features/paper/components/PaperTradeHistory.jsx";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { formatCurrency } from "@/shared/utils/formatters";
import { usePaperTradingWebSocket } from "@/shared/hooks/usePaperTradingWebSocket";

export default function PaperPortfolio() {
  usePaperTradingWebSocket();
  const { notify } = useNotifications();
  const { setPageHeader, clearPageHeader } = usePageActions();
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState("");

  const [searchParams] = useMemo(() => [new URLSearchParams(window.location.search)], []);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [accountsRes, activeRes] = await Promise.all([
        paperApi.getAccounts(),
        paperApi.getActiveAccount(),
      ]);
      
      const loadedAccounts = accountsRes.data || [];
      const accountIdFromUrl = searchParams.get("account_id");
      
      let active;
      if (accountIdFromUrl) {
        active = loadedAccounts.find(a => String(a.id) === String(accountIdFromUrl));
      }
      
      if (!active) {
        active = activeRes.data?.id
          ? activeRes.data
          : loadedAccounts[0];
      }
        
      setAccounts(loadedAccounts);
      if (active?.id) {
        setSelectedAccount(String(active.id));
      } else if (loadedAccounts.length > 0) {
        setSelectedAccount(String(loadedAccounts[0].id));
      }
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to load paper trading data"));
    } finally {
      setLoading(false);
    }
  }, [notify, searchParams]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAccountChange = (accountId) => {
    setSelectedAccount(String(accountId));
  };

  const selectedAccountData = useMemo(
    () => accounts.find((a) => String(a.id) === selectedAccount),
    [accounts, selectedAccount]
  );

  usePageTitle({
    title: "Paper Trading Portfolio",
    subtitle: selectedAccountData ? `Managing ${selectedAccountData.name}` : "Monitor virtual accounts and strategies",
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
                  <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Account</span>
                </div>
                <Select resource="paper-accounts"
                  value={selectedAccount?.toString()}
                  onValueChange={(val) => handleAccountChange(val)}
                  disabled={loading}
                >
                  <SelectTrigger className="w-[280px] bg-transparent border-none text-foreground text-sm focus:ring-0 outline-none shadow-none h-8 font-medium px-2 hover:bg-secondary/50">
                    <SelectValue placeholder="Select Account" />
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

          {activeTab === "overview" && !loading && accounts.length === 0 && (
             <div className="flex items-center gap-3">
                <h3 className="hidden sm:block text-sm font-bold text-foreground whitespace-nowrap">Active Virtual Accounts</h3>
                <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700 h-10 px-4 shadow-lg shadow-indigo-500/20 text-white" onClick={() => window.dispatchEvent(new CustomEvent('open-new-paper-account'))}>
                    <Plus className="h-4 w-4 mr-2" /> New Account
                </Button>
             </div>
          )}
        </div>
      </div>
    );

    setPageHeader(<HeaderContent />);

    return () => {
      clearPageHeader();
    };
  }, [activeTab, selectedAccount, accounts, loading, setPageHeader, clearPageHeader]);

  const handleRefresh = async () => {
    await fetchData();
    notify.success("Data refreshed");
  };

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
        {activeTab === "overview" && <PaperTradingDashboard selectedAccountId={selectedAccount} setActiveTab={setActiveTab} paperUpdatesManaged />}
        {activeTab === "positions" && <PaperPositions selectedAccountId={selectedAccount} />}
        {activeTab === "orders" && <PaperOrderBook selectedAccountId={selectedAccount} />}
        {activeTab === "trades" && <PaperTradeHistory selectedAccountId={selectedAccount} />}
      </div>
    </div>
  );
}
