import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  TrendingUp,
  Search,
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
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useSidebar } from "@/contexts/sidebar-context";
import { useDispatch, useSelector } from "react-redux";
import { logout, logoutUser } from "@/store/authSlice";

const SidebarLink = ({ to, icon: Icon, label, currentPath }) => {
  const isActive =
    currentPath === to ||
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
    trading: true, // Open by default as requested
    portfolio: false,
    community: false,
  });

  const toggleSection = (section) => {
    setOpenSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  if (!isOpen) {
    return null;
  }
  const handleLogout = async () => {
    try {
      dispatch(logoutUser());
    } catch (error) {
      console.error("Logout failed", error);
    } finally {
      dispatch(logout());
      navigate("/");
    }
  };
  return (
    <div className="fixed left-0 top-0 z-50 h-screen w-64 sm:w-72 lg:w-64 bg-gray-950 border-r border-gray-800 flex flex-col shadow-2xl animate-in slide-in-from-left duration-300">
      {/* Header */}
      <div className="flex items-center justify-center h-16 px-4 sm:px-6 border-b border-gray-800/50 shrink-0">
        <Link
          to="/dashboard"
          className="flex items-center space-x-2 transition-colors hover:opacity-80 min-w-0"
        >
          <div className="flex h-8 w-8 sm:h-10 sm:w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-600/20 shadow-[inset_0_2px_4px_rgba(255,255,255,0.1),inset_0_-2px_4px_rgba(0,0,0,0.2)] border border-gray-700/50 shrink-0">
            <TrendingUp className="h-4 w-4 sm:h-5 sm:w-5 text-indigo-300" />
          </div>
          <span className="font-bold text-lg sm:text-xl text-slate-100 font-heading truncate">
            QuantNest
          </span>
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
          <SidebarLink
            to="/dashboard/search"
            icon={Search}
            label="Search"
            currentPath={pathname}
          />
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
                  to="/dashboard/strategy/strategy-builder"
                  icon={Code}
                  label="Strategy Builder"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/strategy/backtesting-hub"
                  icon={TestTube}
                  label="Backtesting Hub"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/strategy/strategy-marketplace"
                  icon={Store}
                  label="Strategy Marketplace"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/strategy/my-live-algos"
                  icon={Rocket}
                  label="My Live Algos"
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
                  to="/dashboard/trading/trade-terminal"
                  icon={Terminal}
                  label="Trade Terminal"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/trading/paper-trading"
                  icon={CreditCard}
                  label="Paper Trading"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/trading/broker-connections"
                  icon={Plug}
                  label="Broker Connections"
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
                <span className="font-medium">Portfolio & Analytics</span>
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
                  to="/dashboard/portfolio/advanced-risk-hub"
                  icon={Shield}
                  label="Advanced Risk Hub"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/portfolio/trade-journal"
                  icon={BookOpen}
                  label="Trade Journal"
                  currentPath={pathname}
                />
                <SidebarLink
                  to="/dashboard/portfolio/tax-center"
                  icon={CreditCard}
                  label="Tax Center"
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
        <DropdownMenu>
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
              >
                <Settings className="h-4 w-4" />
                <span className="text-sm">Profile & Settings</span>
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem className="hover:bg-gray-800 cursor-pointer transition-colors text-red-400 hover:text-red-300">
              <LogOut className="h-4 w-4 mr-2" />
              <span className="text-sm">
                <button onClick={handleLogout}>Logout</button>
              </span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
