import PageTabs from "@/shared/components/PageTabs";
import { useEffect, useState } from "react";
import { History, Wallet } from "lucide-react";
import PaperTransactions from "@/features/paper/components/PaperTransactions.jsx";
import PaperWallet from "@/features/paper/components/PaperWallet.jsx";
import { usePageTitle } from "@/shared/hooks/use-page-title";
import { usePageActions } from "@/shared/context/pageActions";

const CAPITAL_TABS = [
  { value: "wallet", label: "Wallet", icon: Wallet },
  { value: "transactions", label: "Transactions", icon: History },
];

export default function PaperCapital() {
  const [activeTab, setActiveTab] = useState("wallet");
  const { setPageHeader, clearPageHeader } = usePageActions();
  usePageTitle({ title: "Paper wallet", subtitle: "Fund deployments and review virtual cash movements" });
  useEffect(() => {
    setPageHeader(<PageTabs items={CAPITAL_TABS} value={activeTab} onValueChange={setActiveTab} label="Paper capital sections" />);
    return clearPageHeader;
  }, [activeTab, setPageHeader, clearPageHeader]);
  return <div className="page-content">
    {activeTab === "wallet" ? <PaperWallet /> : <PaperTransactions />}
  </div>;
}
