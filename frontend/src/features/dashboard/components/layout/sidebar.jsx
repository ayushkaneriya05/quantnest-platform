/* eslint-disable react/prop-types */
import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Brain,
  BarChart,
  Database,
  Code,
  TestTube,
  Store,
  Rocket,
  Terminal,
  CreditCard,
  Plug,
  Shield,
  BookOpen,
  Users,
  Trophy,
  GraduationCap,
  UserCircle,
  Settings,
  LogOut,
  ChevronDown,
  Activity,
  Briefcase,
  Wallet,
  Bell,
} from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/shared/components/ui/dropdown-menu";
import { useSidebar } from "@/shared/hooks/useSidebar";
import { useDispatch, useSelector } from "react-redux";
import { logoutUser } from "@/shared/store/authSlice";
import { useSystemNotificationsContext } from "@/shared/context/SystemNotificationsContext";

const SidebarLink = ({ to, icon: Icon, label, currentPath }) => {
  // Section overview routes (e.g. /dashboard/portfolio, /dashboard/paper)
  // should only match exactly, not via startsWith, to avoid double-active.
  const isSectionIndex = /^\/dashboard\/[^/]+$/.test(to) && to !== "/dashboard";
  const isActive = isSectionIndex
    ? currentPath === to
    : currentPath === to ||
      (to !== "/dashboard" && currentPath.startsWith(to + "/"));
  return (
    <Link
      to={to}
      className={`flex items-center gap-3 rounded-lg px-3 py-2 text-slate-300 transition-all hover:bg-gray-800 hover:text-slate-100 ${
        isActive ? "bg-gray-800 text-slate-100 font-medium" : ""
      }`}
    >
      <Icon className="h-5 w-5 flex-shrink-0" />
      <span>{label}</span>
    </Link>
  );
};

export default function Sidebar() {
  const dispatch = useDispatch();
  const { user } = useSelector((state) => state.auth);
  const navigate = useNavigate();
  const location = useLocation();
  const pathname = location.pathname;
  const { isOpen } = useSidebar();
  const [openSections, setOpenSections] = useState({
    analysis: false,
    strategy: false,
    trading: true,
    paperTrading: false,
    brokers: false,
    liveOps: false,
    journal: false,
    ai: false,
    marketplace: false,
    governance: false,
    portfolio: false,
    community: false,
  });
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const { unreadCount } = useSystemNotificationsContext();

  const toggleSection = (section) => {
    setOpenSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  if (!isOpen) {
    return null;
  }

  const handleLogout = async () => {
    try {
      // The thunk now handles full cleanup in authSlice extraReducers
      await dispatch(logoutUser());
    } catch (error) {
      console.error("Logout failed", error);
    } finally {
      navigate("/");
    }
  };

  return (
    <div className="fixed left-0 top-0 z-50 h-screen w-64 sm:w-72 lg:w-64 bg-gray-950 border-r border-gray-800 flex flex-col shadow-2xl animate-in slide-in-from-left duration-300">
      {/* Header */}
      <div className="flex items-center justify-center h-16 px-4 sm:px-6 border-b border-gray-800/50 shrink-0">
        <Link
          to="/dashboard"
          className="flex min-w-0 items-center justify-center transition-opacity hover:opacity-80"
        >
          <img
            src="/logo_1-wordmark.png"
            alt="QuantNest"
            className="h-auto w-[170px] object-contain"
          />
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 sm:px-4 space-y-1 scrollbar-custom no-horizontal-scroll">
        {/* Top-Level Static Links */}
        <div className="space-y-1 mb-4">
          <SidebarLink
            to="/dashboard"
            icon={BarChart}
            label="Dashboard"
            currentPath={pathname}
          />
          {/* <SidebarLink
            to="/dashboard/search"
            icon={Search}
            label="Search"
            currentPath={pathname}
          /> */}
        </div>

        {/* Collapsible Sections */}
        <div className="space-y-1">
          <div>
            <Button
              variant="ghost"
              className="w-full justify-between text-slate-300 hover:bg-gray-800/70 hover:text-slate-100 transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("analysis")}
            >
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 flex-shrink-0 text-purple-400" />
                <span className="font-medium">Analysis & Research</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${
                  openSections.analysis ? "rotate-180" : ""
                }`}
              />
            </Button>
            {openSections.analysis && (
              <div className="ml-4 mt-2 space-y-1 animate-in slide-in-from-top-1 duration-200">
                <SidebarLink
                  to="/dashboard/analysis/ai-research-assistant"
                  icon={Brain}
                  label="AI Research Assistant"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/analysis/market-screener"
                  icon={BarChart}
                  label="Market Screener"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/analysis/alternative-data-hub"
                  icon={Database}
                  label="Alternative Data Hub"
                  currentPath={pathname}
                />
              </div>
            )}
          </div>

          <div>
            <Button
              variant="ghost"
              className="w-full justify-between text-slate-300 hover:bg-gray-800/70 hover:text-slate-100 transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("strategy")}
            >
              <div className="flex items-center gap-2">
                <Code className="h-4 w-4 flex-shrink-0 text-indigo-400" />
                <span className="font-medium">Strategy & Automation</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${
                  openSections.strategy ? "rotate-180" : ""
                }`}
              />
            </Button>
            {openSections.strategy && (
              <div className="ml-4 mt-2 space-y-1 animate-in slide-in-from-top-1 duration-200">
                <SidebarLink
                  to="/dashboard/strategy/list"
                  icon={Code}
                  label="My Strategies"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/backtest"
                  icon={TestTube}
                  label="Backtesting Lab"
                  currentPath={pathname}
                />
              </div>
            )}
          </div>

          <div>
            <Button
              variant="ghost"
              className="w-full justify-between text-slate-300 hover:bg-gray-800/70 hover:text-slate-100 transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("trading")}
            >
              <div className="flex items-center gap-2">
                <Terminal className="h-4 w-4 flex-shrink-0 text-emerald-400" />
                <span className="font-medium">Trading & Execution</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${
                  openSections.trading ? "rotate-180" : ""
                }`}
              />
            </Button>
            {openSections.trading && (
              <div className="ml-4 mt-2 space-y-1 animate-in slide-in-from-top-1 duration-200">
                <SidebarLink
                  to="/dashboard/trading/paper-trading"
                  icon={CreditCard}
                  label="Trading Terminal"
                  currentPath={pathname}
                />
              </div>
            )}
          </div>

          <div>
            <Button
              variant="ghost"
              className="w-full justify-between text-slate-300 hover:bg-gray-800/70 hover:text-slate-100 transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("paperTrading")}
            >
              <div className="flex items-center gap-2">
                <CreditCard className="h-4 w-4 flex-shrink-0 text-green-400" />
                <span className="font-medium">Paper Trading</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${
                  openSections.paperTrading ? "rotate-180" : ""
                }`}
              />
            </Button>
            {openSections.paperTrading && (
              <div className="ml-4 mt-2 space-y-1 animate-in slide-in-from-top-1 duration-200">
                <SidebarLink
                  to="/dashboard/paper"
                  icon={Activity}
                  label="Dashboard"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/paper/portfolio"
                  icon={Briefcase}
                  label="Portfolio"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/paper/capital"
                  icon={Wallet}
                  label="Capital & Wallet"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/paper/analytics"
                  icon={BarChart}
                  label="Analytics"
                  currentPath={pathname}
                />
              </div>
            )}
          </div>

          <div>
            <Button
              variant="ghost"
              className="w-full justify-between text-slate-300 hover:bg-gray-800/70 hover:text-slate-100 transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("brokers")}
            >
              <div className="flex items-center gap-2">
                <Plug className="h-4 w-4 flex-shrink-0 text-sky-400" />
                <span className="font-medium">Broker Integration</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${openSections.brokers ? "rotate-180" : ""}`}
              />
            </Button>
            {openSections.brokers && (
              <div className="ml-4 mt-2 space-y-1 animate-in slide-in-from-top-1 duration-200">
                <SidebarLink
                  to="/dashboard/brokers"
                  icon={Plug}
                  label="Connections"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/brokers/settings"
                  icon={Settings}
                  label="Order Settings"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/brokers/logs"
                  icon={Terminal}
                  label="API Logs"
                  currentPath={pathname}
                />
              </div>
            )}
          </div>

          <div>
            <Button
              variant="ghost"
              className="w-full justify-between text-slate-300 hover:bg-gray-800/70 hover:text-slate-100 transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("liveOps")}
            >
              <div className="flex items-center gap-2">
                <Rocket className="h-4 w-4 flex-shrink-0 text-rose-400" />
                <span className="font-medium">Live Trading</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${openSections.liveOps ? "rotate-180" : ""}`}
              />
            </Button>
            {openSections.liveOps && (
              <div className="ml-4 mt-2 space-y-1 animate-in slide-in-from-top-1 duration-200">
                <SidebarLink
                  to="/dashboard/live/portfolio"
                  icon={BarChart}
                  label="Portfolio"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/live/strategies"
                  icon={Rocket}
                  label="Deployments"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/live/logs"
                  icon={Terminal}
                  label="Execution Logs"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/live/emergency"
                  icon={Shield}
                  label="Emergency Control"
                  currentPath={pathname}
                />
              </div>
            )}
          </div>

          <div>
            <Button
              variant="ghost"
              className="w-full justify-between text-slate-300 hover:bg-gray-800/70 hover:text-slate-100 transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("portfolio")}
            >
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 flex-shrink-0 text-cyan-400" />
                <span className="font-medium">Global Risk Hub</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${
                  openSections.portfolio ? "rotate-180" : ""
                }`}
              />
            </Button>
            {openSections.portfolio && (
              <div className="ml-4 mt-2 space-y-1 animate-in slide-in-from-top-1 duration-200">
                <SidebarLink
                  to="/dashboard/portfolio/risk"
                  icon={Shield}
                  label="Risk Profiles"
                  currentPath={pathname}
                />
              </div>
            )}
          </div>

          <div>
            <Button
              variant="ghost"
              className="w-full justify-between text-slate-300 hover:bg-gray-800/70 hover:text-slate-100 transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("journal")}
            >
              <div className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 flex-shrink-0 text-lime-400" />
                <span className="font-medium">Journal & Reports</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${openSections.journal ? "rotate-180" : ""}`}
              />
            </Button>
            {openSections.journal && (
              <div className="ml-4 mt-2 space-y-1 animate-in slide-in-from-top-1 duration-200">
                <SidebarLink
                  to="/dashboard/journal"
                  icon={BookOpen}
                  label="Trade Journal"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/journal/reports"
                  icon={BarChart}
                  label="Performance Reports"
                  currentPath={pathname}
                />
              </div>
            )}
          </div>

          <div>
            <Button
              variant="ghost"
              className="w-full justify-between text-slate-300 hover:bg-gray-800/70 hover:text-slate-100 transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("ai")}
            >
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 flex-shrink-0 text-fuchsia-400" />
                <span className="font-medium">AI Engine</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${openSections.ai ? "rotate-180" : ""}`}
              />
            </Button>
            {openSections.ai && (
              <div className="ml-4 mt-2 space-y-1 animate-in slide-in-from-top-1 duration-200">
                <SidebarLink
                  to="/dashboard/ai/advisor"
                  icon={Brain}
                  label="Advisor"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/ai/scores"
                  icon={BarChart}
                  label="Health Scores"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/ai/regime"
                  icon={Database}
                  label="Market Regime"
                  currentPath={pathname}
                />
              </div>
            )}
          </div>

          <div>
            <Button
              variant="ghost"
              className="w-full justify-between text-slate-300 hover:bg-gray-800/70 hover:text-slate-100 transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("marketplace")}
            >
              <div className="flex items-center gap-2">
                <Store className="h-4 w-4 flex-shrink-0 text-orange-400" />
                <span className="font-medium">Marketplace</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${openSections.marketplace ? "rotate-180" : ""}`}
              />
            </Button>
            {openSections.marketplace && (
              <div className="ml-4 mt-2 space-y-1 animate-in slide-in-from-top-1 duration-200">
                <SidebarLink
                  to="/dashboard/marketplace"
                  icon={Store}
                  label="Explore"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/marketplace/creator"
                  icon={Trophy}
                  label="Creator Earnings"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/marketplace/subscriptions"
                  icon={CreditCard}
                  label="Subscriptions"
                  currentPath={pathname}
                />
              </div>
            )}
          </div>

          <div>
            <Button
              variant="ghost"
              className="w-full justify-between text-slate-300 hover:bg-gray-800/70 hover:text-slate-100 transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("governance")}
            >
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 flex-shrink-0 text-red-400" />
                <span className="font-medium">Governance</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${openSections.governance ? "rotate-180" : ""}`}
              />
            </Button>
            {openSections.governance && (
              <div className="ml-4 mt-2 space-y-1 animate-in slide-in-from-top-1 duration-200">
                <SidebarLink
                  to="/dashboard/settings/audit"
                  icon={Terminal}
                  label="Audit Logs"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/settings/governance"
                  icon={Shield}
                  label="Approvals"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/settings/compliance"
                  icon={BookOpen}
                  label="Compliance"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/settings/system"
                  icon={Settings}
                  label="System Settings"
                  currentPath={pathname}
                />
              </div>
            )}
          </div>

          <div>
            <Button
              variant="ghost"
              className="w-full justify-between text-slate-300 hover:bg-gray-800/70 hover:text-slate-100 transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("community")}
            >
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 flex-shrink-0 text-amber-400" />
                <span className="font-medium">Community & Learning</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${
                  openSections.community ? "rotate-180" : ""
                }`}
              />
            </Button>
            {openSections.community && (
              <div className="ml-4 mt-2 space-y-1 animate-in slide-in-from-top-1 duration-200">
                <SidebarLink
                  to="/dashboard/community/social-hub"
                  icon={Users}
                  label="Social Hub"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/community/leaderboards"
                  icon={Trophy}
                  label="Leaderboards"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/community/learning-center"
                  icon={GraduationCap}
                  label="Learning Center"
                  currentPath={pathname}
                />
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Bottom Section (User Profile) - Clean design without borders */}
      <div className="p-3 sm:p-4 bg-gray-950/50 shrink-0">
        <DropdownMenu open={dropdownOpen} onOpenChange={setDropdownOpen}>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="w-full justify-start text-slate-300 hover:bg-gray-800/70 hover:text-slate-100 transition-all duration-200 rounded-lg p-2 sm:p-3"
            >
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500/20 to-purple-600/20 border border-gray-700/50 shrink-0">
                <UserCircle className="h-4 w-4 sm:h-5 sm:w-5 text-indigo-300" />
              </div>
              <div className="ml-2 sm:ml-3 flex flex-col items-start min-w-0 flex-1">
                <span className="font-medium text-slate-100 text-sm sm:text-base truncate w-full">
                  {user ? user.first_name + " " + user.last_name : "Guest User"}
                </span>
                <span className="text-xs text-slate-400 truncate w-full">
                  Starter Plan
                </span>
              </div>
              <ChevronDown className="ml-2 h-4 w-4 shrink-0" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-48 sm:w-56 bg-gray-900 border border-gray-800 text-slate-100 shadow-2xl">
            <DropdownMenuItem className="hover:bg-gray-800 cursor-pointer transition-colors">
              <Link
                to="/dashboard/profile-settings"
                className="flex items-center gap-2 w-full"
                onClick={() => setDropdownOpen(false)}
              >
                <Settings className="h-4 w-4" />
                <span className="text-sm">Profile & Settings</span>
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem className="hover:bg-gray-800 cursor-pointer transition-colors">
              <Link
                to="/dashboard/notification-center"
                className="flex items-center gap-2 w-full"
                onClick={() => setDropdownOpen(false)}
              >
                <Bell className="h-4 w-4" />
                <span className="text-sm">Notification Center</span>
                {unreadCount > 0 && (
                  <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-indigo-500 px-1.5 text-[10px] font-bold text-white">
                    {unreadCount > 99 ? "99+" : unreadCount}
                  </span>
                )}
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={handleLogout}
              className="hover:bg-gray-800 cursor-pointer transition-colors text-red-400 hover:text-red-300"
            >
              <LogOut className="h-4 w-4 mr-2" />
              <span className="text-sm">Logout</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
