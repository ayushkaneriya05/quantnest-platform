/* eslint-disable react/prop-types */
import * as Dialog from "@radix-ui/react-dialog";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Beaker,
  Bell,
  Blocks,
  BookOpen,
  Bot,
  BrainCircuit,
  BriefcaseBusiness,
  Cable,
  CandlestickChart,
  ChartNoAxesCombined,
  ChevronDown,
  CreditCard,
  FileChartColumn,
  FileJson2,
  FlaskConical,
  Headset,
  History,
  Landmark,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Logs,
  Network,
  NotebookPen,
  NotebookTabs,
  Radio,
  ReceiptText,
  Rocket,
  ScanSearch,
  Settings,
  Wallet,
  Waypoints,
  Wrench,
  X,
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
import UserAvatar from '@/shared/components/UserAvatar';
import { usePlatform } from '@/shared/context/platform';

const navigationSections = [
  {
    id: 'research', label: 'Research & Analysis', icon: BrainCircuit,
    iconClassName: 'text-purple-700 dark:text-purple-400',
    links: [
      { to: '/research', label: 'AI Research Assistant', icon: Bot },
      { to: '/screener', label: 'Market Screener', icon: ScanSearch },
    ],
  },
  {
    id: 'strategies', label: 'Strategy Lab', icon: Waypoints,
    iconClassName: 'text-indigo-700 dark:text-indigo-400',
    links: [
      { to: '/strategies', label: 'My Strategies', icon: Blocks },
      { to: '/backtests', label: 'Backtesting Lab', icon: FlaskConical },
    ],
  },
  {
    id: 'tools', label: 'Trading Tools', icon: Wrench,
    iconClassName: 'text-teal-700 dark:text-teal-400',
    links: [
      { to: '/terminal', label: 'Trading Terminal', icon: CandlestickChart, scope: 'paper' },
      { to: '/brokers/charge-profiles', label: 'Charge Profiles', icon: ReceiptText },
    ],
  },
  {
    id: 'paper', label: 'Paper Trading', icon: Beaker, scope: 'paper',
    iconClassName: 'text-green-700 dark:text-green-400',
    links: [
      { to: '/paper', label: 'Deployments', icon: ListChecks, exact: true },
      { to: '/paper/portfolio', label: 'Portfolio', icon: BriefcaseBusiness },
      { to: '/paper/capital', label: 'Wallet', icon: Wallet },
      { to: '/paper/analytics', label: 'Analytics', icon: ChartNoAxesCombined },
    ],
  },
  {
    id: 'brokers', label: 'Broker Integration', icon: Network, scope: 'live',
    iconClassName: 'text-sky-700 dark:text-sky-400',
    links: [
      { to: '/brokers', label: 'Connections', icon: Cable, exact: true },
      { to: '/brokers/logs', label: 'API Logs', icon: FileJson2 },
    ],
  },
  {
    id: 'live', label: 'Live Trading', icon: Radio, scope: 'live',
    iconClassName: 'text-rose-700 dark:text-rose-400',
    links: [
      { to: '/live/portfolio', label: 'Portfolio', icon: Landmark },
      { to: '/live/strategies', label: 'Deployments', icon: Rocket },
      { to: '/live/logs', label: 'Execution Logs', icon: Logs },
    ],
  },
  {
    id: 'journal', label: 'Journal & Reports', icon: NotebookTabs,
    iconClassName: 'text-amber-700 dark:text-amber-400',
    links: [
      { to: '/journal', label: 'Trade Journal', icon: NotebookPen },
      { to: '/reports', label: 'Performance Reports', icon: FileChartColumn },
    ],
  },
];

function isNavigationPathActive(currentPath, to, exact = false) {
  return currentPath === to || (!exact && currentPath.startsWith(`${to}/`));
}

const SidebarLink = ({ to, icon: Icon, label, currentPath, exact = false }) => {
  const isActive = isNavigationPathActive(currentPath, to, exact);
  return (
    <Link
      to={to}
      aria-current={isActive ? 'page' : undefined}
      className={`flex min-w-0 items-center gap-3 rounded-lg px-3 py-2 text-sm text-foreground transition-colors hover:bg-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
        isActive ? "bg-secondary text-foreground font-medium" : ""
      }`}
    >
      <Icon aria-hidden="true" className="h-5 w-5 shrink-0" />
      <span className="min-w-0 truncate">{label}</span>
    </Link>
  );
};

export default function Sidebar() {
  const { executionScopes } = usePlatform();
  const visibleSections = navigationSections
    .filter(section => !section.scope || executionScopes.includes(section.scope))
    .map(section => ({ ...section, links: section.links.filter(link => !link.scope || executionScopes.includes(link.scope)) }));
  const dispatch = useDispatch();
  const { notify } = useNotifications();
  const { user } = useSelector((state) => state.auth);
  const navigate = useNavigate();
  const location = useLocation();
  const pathname = location.pathname;
  const { isOpen, isDesktop, close, closeMobile } = useSidebar();
  const [openSections, setOpenSections] = useState({ tools: true });
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const { unreadCount } = useSystemNotificationsContext();

  useEffect(() => {
    const section = navigationSections.find(({ links }) => links.some(({ to, exact }) => isNavigationPathActive(pathname, to, exact)));
    if (section) setOpenSections((previous) => previous[section.id] ? previous : { ...previous, [section.id]: true });
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

      {/* Workspace navigation stays visible; execution access is enforced by the route guard. */}
      <nav aria-label="Workspace" onClick={(event) => { if (event.target.closest("a")) closeMobile(); }} className="flex-1 overflow-y-auto px-3 py-4 sm:px-4 scrollbar-custom no-horizontal-scroll">
        <div className="mb-3">
          <SidebarLink to="/overview" icon={LayoutDashboard} label="Overview" currentPath={pathname} exact />
        </div>
        <div className="space-y-1">
          {visibleSections.map(({ id, label, icon: Icon, iconClassName, links }) => {
            const expanded = Boolean(openSections[id]);
            return (
              <div key={id}>
                <Button
                  type="button"
                  variant="ghost"
                  aria-expanded={expanded}
                  aria-controls={`workspace-navigation-${id}`}
                  className="w-full justify-between rounded-lg px-3 text-foreground hover:bg-secondary/70"
                  onClick={() => toggleSection(id)}
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <Icon aria-hidden="true" className={`h-4 w-4 shrink-0 ${iconClassName}`} />
                    <span className="truncate font-medium">{label}</span>
                  </span>
                  <ChevronDown aria-hidden="true" className={`h-4 w-4 shrink-0 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`} />
                </Button>
                {expanded && (
                  <div id={`workspace-navigation-${id}`} className="ml-4 mt-1 space-y-1 animate-in slide-in-from-top-1 duration-200 motion-reduce:animate-none">
                    {links.map((link) => <SidebarLink key={link.to} {...link} currentPath={pathname} />)}
                  </div>
                )}
              </div>
            );
          })}
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
              <UserAvatar className="h-8 w-8 shrink-0 text-xs" />
              <div className="ml-2 sm:ml-3 flex flex-col items-start min-w-0 flex-1">
                <span className="font-medium text-foreground text-sm sm:text-base truncate w-full">
                  {[user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || 'Your account'}
                </span>
                <span className="text-xs text-muted-foreground truncate w-full">
                  {user?.workspace_plan?.name ? `${user.workspace_plan.name} Plan` : 'Loading plan…'}
                </span>
              </div>
              <ChevronDown className="ml-2 h-4 w-4 shrink-0" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-48 sm:w-56 bg-card border border-border text-foreground shadow-2xl">
            <DropdownMenuItem asChild className="hover:bg-secondary cursor-pointer transition-colors">
              <Link
                to="/settings/profile"
                className="flex items-center gap-2 w-full"
              >
                <Settings className="h-4 w-4" />
                <span className="text-sm">Profile & Settings</span>
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild className="hover:bg-secondary cursor-pointer transition-colors">
              <Link to="/settings/billing" className="flex items-center gap-2 w-full"><CreditCard className="h-4 w-4" /><span className="text-sm">Billing and Usage</span></Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild className="hover:bg-secondary cursor-pointer transition-colors">
              <Link to="/support" className="flex items-center gap-2 w-full"><Headset className="h-4 w-4" /><span className="text-sm">Support</span></Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild className="hover:bg-secondary cursor-pointer transition-colors">
              <Link to="/docs/getting-started/" className="flex items-center gap-2 w-full"><BookOpen className="h-4 w-4" /><span className="text-sm">User guide</span></Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild className="hover:bg-secondary cursor-pointer transition-colors">
              <Link to="/activity" className="flex items-center gap-2 w-full">
                <History className="h-4 w-4" /><span className="text-sm">Activity History</span>
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild className="hover:bg-secondary cursor-pointer transition-colors">
              <Link
                to="/notifications"
                className="flex items-center gap-2 w-full"
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
              onSelect={handleLogout}
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
