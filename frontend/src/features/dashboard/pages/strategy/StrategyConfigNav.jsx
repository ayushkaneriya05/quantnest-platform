/**
 * StrategyConfigNav — horizontal navigation bar for strategy config pages.
 * Shows config section tabs + quick actions (Version History, Review, Deploy).
 */
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import {
  Target, Shield, Clock, Layers, DollarSign, Lock,
  History, Eye, Play, BarChart2, Pause, Archive, PowerOff
} from 'lucide-react';
import { strategyApi } from '@/shared/services/strategyApi';
import { useNotifications } from '@/shared/hooks/useNotifications';

const NAV_ITEMS = [
  { path: 'edit',        icon: BarChart2,   label: 'Details',     color: 'indigo' },
  { path: 'entry',       icon: Target,      label: 'Entry',       color: 'emerald' },
  { path: 'exit',        icon: Shield,      label: 'Exit',        color: 'rose' },
  { path: 'time',        icon: Clock,       label: 'Time',        color: 'amber' },
  { path: 'assets',      icon: Layers,      label: 'Assets',      color: 'blue' },
  { path: 'risk',        icon: DollarSign,  label: 'Risk',        color: 'teal' },
  { path: 'auto-disable',icon: PowerOff,    label: 'Auto-Disable',color: 'orange' },
  { path: 'permissions', icon: Lock,        label: 'Permissions', color: 'violet' },
];

const COLOR_MAP = {
  indigo:  { active: 'bg-indigo-600/20 text-indigo-400 border-indigo-500/40',  hover: 'hover:bg-indigo-600/10 hover:text-indigo-400' },
  emerald: { active: 'bg-emerald-600/20 text-emerald-400 border-emerald-500/40', hover: 'hover:bg-emerald-600/10 hover:text-emerald-400' },
  rose:    { active: 'bg-rose-600/20 text-rose-400 border-rose-500/40',       hover: 'hover:bg-rose-600/10 hover:text-rose-400' },
  amber:   { active: 'bg-amber-600/20 text-amber-400 border-amber-500/40',    hover: 'hover:bg-amber-600/10 hover:text-amber-400' },
  blue:    { active: 'bg-blue-600/20 text-blue-400 border-blue-500/40',       hover: 'hover:bg-blue-600/10 hover:text-blue-400' },
  teal:    { active: 'bg-teal-600/20 text-teal-400 border-teal-500/40',       hover: 'hover:bg-teal-600/10 hover:text-teal-400' },
  violet:  { active: 'bg-violet-600/20 text-violet-400 border-violet-500/40', hover: 'hover:bg-violet-600/10 hover:text-violet-400' },
  orange:  { active: 'bg-orange-600/20 text-orange-400 border-orange-500/40', hover: 'hover:bg-orange-600/10 hover:text-orange-400' },
};

const STATUS_BADGES = {
  DRAFT:    { label: 'Draft',    className: 'text-gray-400 border-gray-500/30 bg-gray-500/10' },
  ACTIVE:   { label: 'Active',   className: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' },
  PAUSED:   { label: 'Paused',   className: 'text-amber-400 border-amber-500/30 bg-amber-500/10' },
  ARCHIVED: { label: 'Archived', className: 'text-gray-500 border-gray-600/30 bg-gray-600/10' },
};

export default function StrategyConfigNav({ strategy }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { notify } = useNotifications();

  // Determine which tab is active from the current URL
  const currentPath = location.pathname.split('/').pop();
  const status = strategy?.status || 'DRAFT';

  const handleActivate = async () => {
    try {
      await strategyApi.activate(id);
      notify.success('Strategy activated!');
      navigate('/dashboard/strategy/list');
    } catch {
      notify.error('Failed to activate strategy');
    }
  };

  const handlePause = async () => {
    try {
      await strategyApi.pause(id);
      notify.success('Strategy paused');
      navigate('/dashboard/strategy/list');
    } catch {
      notify.error('Failed to pause strategy');
    }
  };

  const handleArchive = async () => {
    try {
      await strategyApi.archive(id);
      notify.success('Strategy archived');
      navigate('/dashboard/strategy/list');
    } catch {
      notify.error('Failed to archive strategy');
    }
  };

  const statusBadge = STATUS_BADGES[status] || STATUS_BADGES.DRAFT;

  return (
    <div className="flex items-center justify-between gap-2 w-full">
        {/* ── Section tabs ── */}
        <nav className="flex items-center gap-1 overflow-x-auto scrollbar-theme py-2 pb-3">
          {NAV_ITEMS.map(item => {
            const Icon = item.icon;
            const isActive = currentPath === item.path;
            const colors = COLOR_MAP[item.color];

            return (
              <button
                key={item.path}
                onClick={() => navigate(`/dashboard/strategy/${id}/${item.path}`)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all duration-200 border
                  ${isActive
                    ? `${colors.active}`
                    : `border-transparent text-gray-500 ${colors.hover}`
                  }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="hidden sm:inline">{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* ── Quick actions ── */}
        <div className="flex items-center gap-2 shrink-0">
          <Badge variant="outline" className={`text-xs h-6 px-2 ${statusBadge.className}`}>
            {statusBadge.label}
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`/dashboard/strategy/${id}/versions`)}
            className="text-gray-500 hover:text-white text-xs h-8 px-2.5"
          >
            <History className="h-4 w-4 sm:mr-1.5" />
            <span className="hidden lg:inline">History</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`/dashboard/strategy/${id}/review`)}
            className="text-gray-500 hover:text-white text-xs h-8 px-2.5"
          >
            <Eye className="h-4 w-4 sm:mr-1.5" />
            <span className="hidden lg:inline">Review</span>
          </Button>

          {/* Status-aware lifecycle buttons */}
          {(status === 'DRAFT' || status === 'PAUSED') && (
            <Button
              size="sm"
              onClick={handleActivate}
              className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs h-8 px-3"
            >
              <Play className="h-4 w-4 sm:mr-1.5" />
              <span className="hidden lg:inline">Activate</span>
            </Button>
          )}
          {status === 'ACTIVE' && (
            <Button
              size="sm"
              onClick={handlePause}
              className="bg-amber-600 hover:bg-amber-500 text-white text-xs h-8 px-3"
            >
              <Pause className="h-4 w-4 sm:mr-1.5" />
              <span className="hidden lg:inline">Pause</span>
            </Button>
          )}
        </div>
    </div>
  );
}
