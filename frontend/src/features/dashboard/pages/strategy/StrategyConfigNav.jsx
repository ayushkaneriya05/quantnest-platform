import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { Badge } from '@/shared/components/ui/badge';
import {
  Target, Shield, Clock, Layers, DollarSign, Lock, History, BarChart2, PowerOff,
} from 'lucide-react';

const NAV_ITEMS = [
  { path: 'edit', icon: BarChart2, label: 'Details', color: 'indigo' },
  { path: 'entry', icon: Target, label: 'Entry', color: 'emerald' },
  { path: 'exit', icon: Shield, label: 'Exit', color: 'rose' },
  { path: 'time', icon: Clock, label: 'Time', color: 'amber' },
  { path: 'assets', icon: Layers, label: 'Assets', color: 'blue' },
  { path: 'risk', icon: DollarSign, label: 'Risk', color: 'teal' },
  { path: 'auto-disable', icon: PowerOff, label: 'Auto-Disable', color: 'orange' },
  { path: 'permissions', icon: Lock, label: 'Permissions', color: 'violet' },
  { path: 'versions', icon: History, label: 'Versions', color: 'blue' },
];

const COLORS = {
  indigo: ['bg-indigo-600/20 text-indigo-400 border-indigo-500/40', 'hover:bg-indigo-600/10 hover:text-indigo-400'],
  emerald: ['bg-emerald-600/20 text-emerald-400 border-emerald-500/40', 'hover:bg-emerald-600/10 hover:text-emerald-400'],
  rose: ['bg-rose-600/20 text-rose-400 border-rose-500/40', 'hover:bg-rose-600/10 hover:text-rose-400'],
  amber: ['bg-amber-600/20 text-amber-400 border-amber-500/40', 'hover:bg-amber-600/10 hover:text-amber-400'],
  blue: ['bg-blue-600/20 text-blue-400 border-blue-500/40', 'hover:bg-blue-600/10 hover:text-blue-400'],
  teal: ['bg-teal-600/20 text-teal-400 border-teal-500/40', 'hover:bg-teal-600/10 hover:text-teal-400'],
  violet: ['bg-violet-600/20 text-violet-400 border-violet-500/40', 'hover:bg-violet-600/10 hover:text-violet-400'],
  orange: ['bg-orange-600/20 text-orange-400 border-orange-500/40', 'hover:bg-orange-600/10 hover:text-orange-400'],
};

const STATUS_BADGES = {
  DRAFT: ['Draft', 'text-gray-400 border-gray-500/30 bg-gray-500/10'],
  ACTIVE: ['Active', 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'],
  PAUSED: ['Paused', 'text-amber-400 border-amber-500/30 bg-amber-500/10'],
  ARCHIVED: ['Archived', 'text-gray-500 border-gray-600/30 bg-gray-600/10'],
};

export default function StrategyConfigNav({ strategy }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const currentPath = location.pathname.split('/').pop();
  const [label, badgeClass] = STATUS_BADGES[strategy?.status] || STATUS_BADGES.DRAFT;

  return (
    <div className="flex items-center justify-between gap-2 w-full min-w-0">
      <nav className="flex items-center gap-1 overflow-x-auto scrollbar-theme py-2 pb-3 min-w-0">
        {NAV_ITEMS.map(({ path, icon: Icon, label: itemLabel, color }) => {
          const active = currentPath === path;
          const [activeClass, hoverClass] = COLORS[color];
          return (
            <button
              key={path}
              onClick={() => navigate(`/dashboard/strategy/${id}/${path}`)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all border ${active ? activeClass : `border-transparent text-gray-500 ${hoverClass}`}`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="hidden sm:inline">{itemLabel}</span>
            </button>
          );
        })}
      </nav>
      <Badge variant="outline" className={`text-xs h-6 px-2 shrink-0 ${badgeClass}`}>
        {label}
      </Badge>
    </div>
  );
}
