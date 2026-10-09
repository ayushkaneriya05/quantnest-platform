/* eslint-disable react/prop-types */
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Brain,
  BarChart,
  Code,
  TestTube,
  Rocket,
  Terminal,
  CreditCard,
  Plug,
  Shield,
  BookOpen,
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
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSystemNotificationsContext } from "@/shared/context/SystemNotificationsContext";

const SidebarLink = ({ to, icon: Icon, label, currentPath }) => {
  // Section overview routes (e.g. /portfolio, /paper)
  // should only match exactly, not via startsWith, to avoid double-active.
  const isSectionIndex = ["/overview", "/strategies", "/backtests", "/paper", "/brokers", "/journal"].includes(to);
  const isActive = isSectionIndex
    ? currentPath === to
    : currentPath === to ||
      (to !== "/overview" && currentPath.startsWith(to + "/"));
  return (
    <Link
      to={to}
      className={`flex items-center gap-3 rounded-lg px-3 py-2 text-foreground transition-all hover:bg-secondary hover:text-foreground ${
        isActive ? "bg-secondary text-foreground font-medium" : ""
      }`}
    >
      <Icon className="h-5 w-5 flex-shrink-0" />
      <span>{label}</span>
    </Link>
  );
};

export default function Sidebar() {
  const dispatch = useDispatch();
  const { notify } = useNotifications();
  const { user } = useSelector((state) => state.auth);
  const navigate = useNavigate();
  const location = useLocation();
  const pathname = location.pathname;
  const { isOpen, isDesktop, close, closeMobile } = useSidebar();
  const [openSections, setOpenSections] = useState({
    analysis: false,
    strategy: false,
    trading: true,
    paperTrading: false,
    brokers: false,
    liveOps: false,
    journal: false,
  });
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const { unreadCount } = useSystemNotificationsContext();

  useEffect(() => {
    const section = pathname.startsWith("/research") || pathname.startsWith("/screener") ? "analysis"
      : pathname.startsWith("/strategies") || pathname.startsWith("/backtests") ? "strategy"
      : pathname.startsWith("/terminal") ? "trading"
      : pathname.startsWith("/paper") ? "paperTrading"
      : pathname.startsWith("/brokers") ? "brokers"
      : pathname.startsWith("/live") ? "liveOps"
      : pathname.startsWith("/journal") || pathname.startsWith("/reports") ? "journal" : null;
    if (section) setOpenSections((previous) => previous[section] ? previous : { ...previous, [section]: true });
  }, [pathname]);

  const toggleSection = (section) => {
    setOpenSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  if (!isOpen) {
    return null;
  }

  const handleLogout = async () => {
    try {
      await dispatch(logoutUser()).unwrap();
      navigate("/");
    } catch (error) {
      notify.error(typeof error === "string" ? error : "Could not sign out. Please retry.");
    }
  };

  const navigation = (
    <div className="flex h-full min-h-0 flex-col bg-card text-foreground">
      {!isDesktop && <Button variant="ghost" size="icon" className="absolute right-2 top-2 touch-target" onClick={close} aria-label="Close navigation"><X className="h-5 w-5" /></Button>}
      {/* Header */}
      <div className="flex items-center justify-center h-16 px-4 sm:px-6 border-b border-border/50 shrink-0">
        <Link
          to="/overview"
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
      <nav aria-label="Workspace" onClick={(event) => { if (event.target.closest("a")) closeMobile(); }} className="flex-1 overflow-y-auto py-4 px-3 sm:px-4 space-y-1 scrollbar-custom no-horizontal-scroll">
        {/* Top-Level Static Links */}
        <div className="space-y-1 mb-4">
          <SidebarLink
            to="/overview"
            icon={BarChart}
            label="Overview"
            currentPath={pathname}
          />
        </div>

        {/* Collapsible Sections */}
        <div className="space-y-1">
          <div>
            <Button
              variant="ghost"
              className="w-full justify-between text-foreground hover:bg-secondary/70 hover:text-foreground transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("analysis")}
            >
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 flex-shrink-0 text-purple-700 dark:text-purple-400" />
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
                  to="/research"
                  icon={Brain}
                  label="AI Research Assistant"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/screener"
                  icon={BarChart}
                  label="Market Screener"
                  currentPath={pathname}
                />
              </div>
            )}
          </div>

          <div>
            <Button
              variant="ghost"
              className="w-full justify-between text-foreground hover:bg-secondary/70 hover:text-foreground transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("strategy")}
            >
              <div className="flex items-center gap-2">
                <Code className="h-4 w-4 flex-shrink-0 text-indigo-700 dark:text-indigo-400" />
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
                  to="/strategies"
                  icon={Code}
                  label="My Strategies"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/backtests"
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
              className="w-full justify-between text-foreground hover:bg-secondary/70 hover:text-foreground transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("trading")}
            >
              <div className="flex items-center gap-2">
                <Terminal className="h-4 w-4 flex-shrink-0 text-emerald-700 dark:text-emerald-400" />
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
                  to="/terminal"
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
              className="w-full justify-between text-foreground hover:bg-secondary/70 hover:text-foreground transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("paperTrading")}
            >
              <div className="flex items-center gap-2">
                <CreditCard className="h-4 w-4 flex-shrink-0 text-green-700 dark:text-green-400" />
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
                  to="/paper"
                  icon={Activity}
                  label="Overview"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/paper/portfolio"
                  icon={Briefcase}
                  label="Portfolio"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/paper/capital"
                  icon={Wallet}
                  label="Capital & Wallet"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/paper/analytics"
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
              className="w-full justify-between text-foreground hover:bg-secondary/70 hover:text-foreground transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("brokers")}
            >
              <div className="flex items-center gap-2">
                <Plug className="h-4 w-4 flex-shrink-0 text-sky-700 dark:text-sky-400" />
                <span className="font-medium">Broker Integration</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${openSections.brokers ? "rotate-180" : ""}`}
              />
            </Button>
            {openSections.brokers && (
              <div className="ml-4 mt-2 space-y-1 animate-in slide-in-from-top-1 duration-200">
                <SidebarLink
                  to="/brokers"
                  icon={Plug}
                  label="Connections"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/brokers/charge-profiles"
                  icon={CreditCard}
                  label="Charge Profiles"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/brokers/logs"
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
              className="w-full justify-between text-foreground hover:bg-secondary/70 hover:text-foreground transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("liveOps")}
            >
              <div className="flex items-center gap-2">
                <Rocket className="h-4 w-4 flex-shrink-0 text-rose-700 dark:text-rose-400" />
                <span className="font-medium">Live Trading</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${openSections.liveOps ? "rotate-180" : ""}`}
              />
            </Button>
            {openSections.liveOps && (
              <div className="ml-4 mt-2 space-y-1 animate-in slide-in-from-top-1 duration-200">
                <SidebarLink
                  to="/live/portfolio"
                  icon={BarChart}
                  label="Portfolio"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/live/strategies"
                  icon={Rocket}
                  label="Deployments"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/live/logs"
                  icon={Terminal}
                  label="Execution Logs"
                  currentPath={pathname}
                />
              </div>
            )}
          </div>

          <div>
            <Button
              variant="ghost"
              className="w-full justify-between text-foreground hover:bg-secondary/70 hover:text-foreground transition-all duration-200 rounded-lg"
              onClick={() => toggleSection("journal")}
            >
              <div className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 flex-shrink-0 text-lime-700 dark:text-lime-400" />
                <span className="font-medium">Journal & Reports</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${openSections.journal ? "rotate-180" : ""}`}
              />
            </Button>
            {openSections.journal && (
              <div className="ml-4 mt-2 space-y-1 animate-in slide-in-from-top-1 duration-200">
                <SidebarLink
                  to="/journal"
                  icon={BookOpen}
                  label="Trade Journal"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/reports"
                  icon={BarChart}
                  label="Performance Reports"
                  currentPath={pathname}
                />
              </div>
            )}
          </div>



        </div>
      </nav>

      {/* Bottom Section (User Profile) - Clean design without borders */}
      <div className="p-3 sm:p-4 bg-background/50 shrink-0">
        <DropdownMenu open={dropdownOpen} onOpenChange={setDropdownOpen}>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="w-full justify-start text-foreground hover:bg-secondary/70 hover:text-foreground transition-all duration-200 rounded-lg p-2 sm:p-3"
            >
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500/20 to-purple-600/20 border border-border/50 shrink-0">
                <UserCircle className="h-4 w-4 sm:h-5 sm:w-5 text-indigo-700 dark:text-indigo-300" />
              </div>
              <div className="ml-2 sm:ml-3 flex flex-col items-start min-w-0 flex-1">
                <span className="font-medium text-foreground text-sm sm:text-base truncate w-full">
                  {user ? user.first_name + " " + user.last_name : "Guest User"}
                </span>
                <span className="text-xs text-muted-foreground truncate w-full">
                  Starter Plan
                </span>
              </div>
              <ChevronDown className="ml-2 h-4 w-4 shrink-0" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-48 sm:w-56 bg-card border border-border text-foreground shadow-2xl">
            <DropdownMenuItem className="hover:bg-secondary cursor-pointer transition-colors">
              <Link
                to="/settings/profile"
                className="flex items-center gap-2 w-full"
                onClick={() => setDropdownOpen(false)}
              >
                <Settings className="h-4 w-4" />
                <span className="text-sm">Profile & Settings</span>
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem className="hover:bg-secondary cursor-pointer transition-colors">
              <Link to="/activity" className="flex items-center gap-2 w-full" onClick={() => setDropdownOpen(false)}>
                <Shield className="h-4 w-4" /><span className="text-sm">Activity History</span>
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem className="hover:bg-secondary cursor-pointer transition-colors">
              <Link
                to="/notifications"
                className="flex items-center gap-2 w-full"
                onClick={() => setDropdownOpen(false)}
              >
                <Bell className="h-4 w-4" />
                <span className="text-sm">Notification Center</span>
                {unreadCount > 0 && (
                  <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-indigo-600 px-1.5 text-[10px] font-bold text-white">
                    {unreadCount > 99 ? "99+" : unreadCount}
                  </span>
                )}
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={handleLogout}
              className="hover:bg-secondary cursor-pointer transition-colors text-red-700 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
            >
              <LogOut className="h-4 w-4 mr-2" />
              <span className="text-sm">Logout</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
  if (isDesktop) return <aside className="fixed inset-y-0 left-0 z-30 w-64 border-r bg-card">{navigation}</aside>;
  return <Dialog.Root open={isOpen} onOpenChange={(open) => { if (!open) close(); }}>
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" />
      <Dialog.Content aria-describedby={undefined} onCloseAutoFocus={(event) => { event.preventDefault(); document.getElementById("workspace-navigation-toggle")?.focus(); }} className="fixed inset-y-0 left-0 z-50 w-[min(20rem,calc(100vw-3rem))] border-r bg-card shadow-xl focus:outline-none">
        <Dialog.Title className="sr-only">Workspace navigation</Dialog.Title>
        {navigation}
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}
