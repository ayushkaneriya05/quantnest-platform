import { useQueryState } from "@/shared/hooks/usePagination";
import api from "@/shared/services/api";
import RefreshButton from "@/shared/components/RefreshButton";
import PageTabs from "@/shared/components/PageTabs";

import { GlobalLoader } from '@/shared/components/ui/global-loader';
import {useStableCallback} from "@/shared/hooks/useStableCallback";
import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { TrendingUp, BarChart3, BookOpen, Terminal } from "lucide-react";
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
import SettlementHistory from '@/shared/components/SettlementHistory';
import { formatCurrency } from "@/shared/utils/formatters";
import { usePaperTradingUpdate, usePaperTradingWebSocket } from "@/shared/hooks/usePaperTradingWebSocket";

const PORTFOLIO_TABS = [
  { value: "overview", label: "Overview", icon: BarChart3 },
  { value: "positions", label: "Positions", icon: TrendingUp },
  { value: "orders", label: "Orders", icon: Terminal },
  { value: "trades", label: "History", icon: BookOpen },
  { value: "settlements", label: "Settlements" },
];

export default function PaperPortfolio() {
  const handleRefresh = useStableCallback(async () => {
    if (await fetchData(false)) setRefreshRevision((value) => value + 1);
  });

  usePaperTradingWebSocket();
  const lastMessage = usePaperTradingUpdate();
  const { notify } = useNotifications();
  const { setPageHeader, clearPageHeader } = usePageActions();
  const [activeTab, setActiveTab] = useQueryState("section", "overview", { resetPage: false });
  const [loading, setLoading] = useState(true);
  const [refreshRevision, setRefreshRevision] = useState(0);
  const [accounts, setAccounts] = useState([]);
  const settlementRefresh = useMemo(() => ({ event: lastMessage, revision: refreshRevision }), [lastMessage, refreshRevision]);
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedAccount = searchParams.get("account_id");
  const selectedAccount = requestedAccount || accounts[0]?.id.toString() || "";

  const accountRequest = useRef(0);
  const fetchData = useCallback(async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      const request = ++accountRequest.current;
      let identity = requestedAccount;
      if (!identity) {
        const choices = await api.get('/common/choices/', { params: { resource: 'paper-accounts' } });
        identity = choices.data.results[0]?.id;
      }
      const loaded = identity ? await paperApi.getAccount(identity) : null;
      if (request !== accountRequest.current) return false;
      setAccounts(loaded ? [loaded.data] : []);
      return true;
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to load paper trading data"));
      return false;
    } finally {
      setLoading(false);
    }
  }, [notify, requestedAccount]);

  useEffect(() => {
    fetchData(); const guard = accountRequest;
    return () => { guard.current++; };
  }, [fetchData]);

  useEffect(() => {
    if (!lastMessage) return undefined;
    const timer = setTimeout(() => fetchData(false), 150);
    return () => clearTimeout(timer);
  }, [lastMessage, fetchData]);

  const handleAccountChange = useStableCallback((accountId) => {
    const next = new URLSearchParams(searchParams);
    next.set("account_id", accountId);
    for (const list of ["positions", "orders", "trades", "settlements"]) next.set(`${list}_page`, "1");
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
      <div className="flex min-w-0 w-full items-center justify-between gap-3">
        <PageTabs items={PORTFOLIO_TABS} value={activeTab} onValueChange={setActiveTab} label="Paper portfolio sections" />

        <div className="flex shrink-0 items-center gap-2">
          {/* Account Selector integrated in header */}
          {!loading && accounts.length > 0 && (
             <div className="flex items-center gap-2 rounded-md border border-border p-1 px-2">
                <div className="flex shrink-0 items-center gap-2 sm:mr-2">
                  <div className="h-2 w-2 rounded-full bg-success shrink-0" />
                  <span className="hidden sm:inline text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Session</span>
                </div>
                <Select resource="paper-accounts"
                  value={selectedAccount?.toString()}
                  onValueChange={(val) => handleAccountChange(val)}
                  disabled={loading}
                >
                  <SelectTrigger aria-label="Paper session" className="min-w-0 flex-1 sm:flex-none sm:w-[280px] bg-transparent border-none text-foreground text-sm outline-none font-medium px-2 [&>span]:truncate">
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
                <div className="h-4 w-[1px] shrink-0 bg-secondary mx-1" />
                <RefreshButton onClick={handleRefresh} label="Refresh paper portfolio" disabled={loading} loading={loading} />
             </div>
          )}


        </div>
      </div>
    );

    setPageHeader(<HeaderContent />);

    return () => {
      clearPageHeader();
    };
  }, [activeTab, setActiveTab, selectedAccount, accounts, loading, setPageHeader, clearPageHeader, handleRefresh, handleAccountChange]);



  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <GlobalLoader />
      </div>
    );
  }

  return (
    <div className="page-content">
      {activeTab === "overview" && <PaperPortfolioOverview account={selectedAccountData} refreshKey={refreshRevision} />}
      {activeTab === "positions" && <PaperPositions selectedAccountId={selectedAccount} refreshKey={refreshRevision} />}
      {activeTab === "orders" && <PaperOrderBook selectedAccountId={selectedAccount} refreshKey={refreshRevision} />}
      {activeTab === "trades" && <PaperTradeHistory selectedAccountId={selectedAccount} refreshKey={refreshRevision} />}
      {activeTab === 'settlements' && selectedAccount && <SettlementHistory key={selectedAccount} accountId={selectedAccount} refreshKey={settlementRefresh} />}
    </div>
  );
}
