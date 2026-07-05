import React, { useEffect, useState } from "react";
import ProfileTab from "@/features/dashboard/components/profile-settings/profile-tab";
import AccountTab from "@/features/dashboard/components/profile-settings/account-tab";
import SecurityTab from "@/features/dashboard/components/profile-settings/security-tab";
import NotificationsTab from "@/features/dashboard/components/profile-settings/notifications-tab";
import { User, CreditCard, Shield, Bell } from "lucide-react";
import { usePageActions } from "@/shared/context/PageActionsContext";

export default function ProfileSettings() {
  const [activeTab, setActiveTab] = useState("profile");
  const { setPageHeader, clearPageHeader } = usePageActions();

  useEffect(() => {
    // Custom tab navigation to render inside MainContentHeader
    const HeaderTabs = () => (
      <div className="inline-flex items-center space-x-1 bg-gray-800/30 border border-gray-700/30 rounded-lg p-1 mx-auto sm:mx-0 sm:ml-4">
        <button
          onClick={() => setActiveTab("profile")}
          className={`flex-1 flex justify-center items-center gap-2 rounded-md px-3 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm font-medium transition-all duration-200 ${
            activeTab === "profile"
              ? "bg-gray-700 text-slate-100 shadow-sm"
              : "text-slate-400 hover:text-slate-200 hover:bg-gray-700/50"
          }`}
        >
          <User className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
          <span className="hidden sm:inline">Profile</span>
        </button>
        <button
          onClick={() => setActiveTab("account")}
          className={`flex-1 flex justify-center items-center gap-2 rounded-md px-3 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm font-medium transition-all duration-200 ${
            activeTab === "account"
              ? "bg-gray-700 text-slate-100 shadow-sm"
              : "text-slate-400 hover:text-slate-200 hover:bg-gray-700/50"
          }`}
        >
          <CreditCard className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
          <span className="hidden sm:inline">Account</span>
        </button>
        <button
          onClick={() => setActiveTab("security")}
          className={`flex-1 flex justify-center items-center gap-2 rounded-md px-3 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm font-medium transition-all duration-200 ${
            activeTab === "security"
              ? "bg-gray-700 text-slate-100 shadow-sm"
              : "text-slate-400 hover:text-slate-200 hover:bg-gray-700/50"
          }`}
        >
          <Shield className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
          <span className="hidden sm:inline">Security</span>
        </button>
        <button
          onClick={() => setActiveTab("notifications")}
          className={`flex-1 flex justify-center items-center gap-2 rounded-md px-3 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm font-medium transition-all duration-200 ${
            activeTab === "notifications"
              ? "bg-gray-700 text-slate-100 shadow-sm"
              : "text-slate-400 hover:text-slate-200 hover:bg-gray-700/50"
          }`}
        >
          <Bell className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
          <span className="hidden sm:inline">Notifications</span>
        </button>
      </div>
    );

    setPageHeader(<HeaderTabs />);

    return () => {
      clearPageHeader();
    };
  }, [setPageHeader, clearPageHeader, activeTab]);

  return (
    <div className="container-padding pt-6 pb-20 w-full min-h-screen">
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
