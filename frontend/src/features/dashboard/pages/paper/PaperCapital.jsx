import { useState, useEffect } from "react";
import { Wallet, History, PieChart, Activity } from "lucide-react";
import PaperAllocations from "./PaperAllocations";
import PaperTransactions from "./PaperTransactions";
import PaperWallet from "./PaperWallet";
import { Button } from "@/shared/components/ui/button";
import { usePageTitle } from "@/shared/hooks/use-page-title";
import { usePageActions } from "@/shared/context/PageActionsContext";

export default function PaperCapital() {
  const [activeTab, setActiveTab] = useState("allocations");
  const { setPageHeader, clearPageHeader } = usePageActions();

  usePageTitle({
    title: "Paper Capital",
    subtitle: "Manage allocations and track virtual fund settlements",
  });

  useEffect(() => {
    const HeaderContent = () => (
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 w-full">
        <div className="flex items-center gap-1 bg-gray-900/50 p-1 rounded-xl border border-gray-800 backdrop-blur-md overflow-x-auto no-scrollbar">
          <button
            onClick={() => setActiveTab("allocations")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap ${
              activeTab === "allocations"
                ? "bg-indigo-500/10 text-indigo-400 shadow-[0_0_15px_rgba(99,102,241,0.1)]"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
            }`}
          >
            <PieChart className="h-4 w-4" />
            Allocations
          </button>
          <button
            onClick={() => setActiveTab("wallet")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap ${
              activeTab === "wallet"
                ? "bg-emerald-500/10 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.1)]"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
            }`}
          >
            <Wallet className="h-4 w-4" />
            Paper Wallet
          </button>
          <button
            onClick={() => setActiveTab("transactions")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap ${
              activeTab === "transactions"
                ? "bg-amber-500/10 text-amber-400 shadow-[0_0_15px_rgba(245,158,11,0.1)]"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
            }`}
          >
            <History className="h-4 w-4" />
            Capital Logs
          </button>
        </div>

        {activeTab === "allocations" && (
          <div className="flex items-center gap-3">
             <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700 h-10 px-4 shadow-lg shadow-indigo-500/20 font-bold" onClick={() => window.dispatchEvent(new CustomEvent('open-new-allocation'))}>
                <PieChart className="h-4 w-4 mr-2" /> 
                <span>ADD ALLOCATION</span>
             </Button>
          </div>
        )}
      </div>
    );

    setPageHeader(<HeaderContent />);
    return () => clearPageHeader();
  }, [activeTab, setPageHeader, clearPageHeader]);

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6 animate-in fade-in duration-500">
      {activeTab === "allocations" && <PaperAllocations />}
      {activeTab === "wallet" && <PaperWallet />}
      {activeTab === "transactions" && <PaperTransactions />}
    </div>
  );
}
