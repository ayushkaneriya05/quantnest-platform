import { useEffect, useState } from "react";
import { History, Wallet } from "lucide-react";
import PaperTransactions from "@/features/paper/components/PaperTransactions.jsx";
import PaperWallet from "@/features/paper/components/PaperWallet.jsx";
import { usePageTitle } from "@/shared/hooks/use-page-title";
import { usePageActions } from "@/shared/context/pageActions";

export default function PaperCapital() {
  const [activeTab, setActiveTab] = useState("wallet");
  const { setPageHeader, clearPageHeader } = usePageActions();
  usePageTitle({ title: "Paper wallet", subtitle: "Fund deployments and review virtual cash movements" });
  useEffect(() => {
    setPageHeader(<div className="flex gap-1 rounded-xl border border-border bg-card/50 p-1">
      {[["wallet", "Wallet", Wallet], ["transactions", "Transactions", History]].map(([key, label, Icon]) =>
        <button key={key} onClick={() => setActiveTab(key)}
          className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium ${activeTab === key ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
          <Icon className="h-4 w-4" />{label}
        </button>)}
    </div>);
    return clearPageHeader;
  }, [activeTab, setPageHeader, clearPageHeader]);
  return <div className="container-padding space-y-6 py-6 lg:py-8">
    {activeTab === "wallet" ? <PaperWallet /> : <PaperTransactions />}
  </div>;
}
