import PageTabs from "@/shared/components/PageTabs";
import { useEffect, useState } from "react";
import ProfileTab from "@/features/settings/components/profile-tab";
import AccountTab from "@/features/settings/components/account-tab";
import SecurityTab from "@/features/settings/components/security-tab";
import NotificationsTab from "@/features/settings/components/notifications-tab";
import { User, CreditCard, Shield, Bell } from "lucide-react";
import { usePageActions } from "@/shared/context/pageActions";

export default function ProfileSettings() {
  const [activeTab, setActiveTab] = useState("profile");
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
  }, [setPageHeader, clearPageHeader, activeTab]);

  return (
    <div className="container-padding pt-6 pb-20 w-full min-h-dvh">
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
