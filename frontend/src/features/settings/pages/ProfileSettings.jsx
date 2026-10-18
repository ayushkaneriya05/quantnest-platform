import PageTabs from "@/shared/components/PageTabs";
import { useCallback, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import ProfileTab from "@/features/settings/components/profile-tab";
import AccountTab from "@/features/settings/components/account-tab";
import SecurityTab from "@/features/settings/components/security-tab";
import NotificationsTab from "@/features/settings/components/notifications-tab";
import { User, CreditCard, Shield, Bell } from "lucide-react";
import { usePageActions } from "@/shared/context/pageActions";

export default function ProfileSettings() {
  const [params, setParams] = useSearchParams();
  const activeTab = ["account", "security", "notifications"].includes(params.get("tab")) ? params.get("tab") : "profile";
  const setActiveTab = useCallback(value => setParams(current => {
    const next = new URLSearchParams(current);
    if (value === "profile") next.delete("tab"); else next.set("tab", value);
    return next;
  }, { replace: true }), [setParams]);
  const { setPageHeader, clearPageHeader } = usePageActions();
  
  useEffect(() => {
    // Custom tab navigation to render inside MainContentHeader
    const HeaderTabs = () => <PageTabs label="Profile settings" value={activeTab} onValueChange={setActiveTab} items={[
      { value: "profile", label: "Profile", icon: User },
      { value: "account", label: "Account", icon: CreditCard },
      { value: "security", label: "Security", icon: Shield },
      { value: "notifications", label: "Notifications", icon: Bell },
    ]} />;

    setPageHeader(<HeaderTabs />);

    return () => {
      clearPageHeader();
    };
  }, [setPageHeader, clearPageHeader, activeTab, setActiveTab]);

  return (
    <div className="container-padding py-5 w-full">
      {/* We use standard divs here instead of UI Tabs since the triggers are in the header */}
      <div className="w-full">
        {activeTab === "profile" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <ProfileTab />
          </div>
        )}

        {activeTab === "account" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <AccountTab />
          </div>
        )}

        {activeTab === "security" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <SecurityTab />
          </div>
        )}

        {activeTab === "notifications" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <NotificationsTab />
          </div>
        )}
      </div>
    </div>
  );
}
