import { useNavigate, useLocation } from 'react-router-dom';
import {
  ShieldAlert, Activity, Settings, AlertTriangle, DollarSign, PowerOff
} from 'lucide-react';

const NAV_ITEMS = [
  { path: 'risk',              icon: Settings,      label: 'Risk Profile',  color: 'indigo' },
  { path: 'halt-conditions',   icon: ShieldAlert,   label: 'Halt Rules',    color: 'orange' },
  { path: 'risk-violations',   icon: AlertTriangle, label: 'Violations',    color: 'amber' },
  // { path: 'advanced-risk-hub', icon: Activity,      label: 'Advanced Hub',  color: 'blue' },
];

const COLOR_MAP = {
  indigo:  { active: 'bg-indigo-600/20 text-indigo-400 border-indigo-500/40',  hover: 'hover:bg-indigo-600/10 hover:text-indigo-400' },
  teal:    { active: 'bg-teal-600/20 text-teal-400 border-teal-500/40',       hover: 'hover:bg-teal-600/10 hover:text-teal-400' },
  orange:  { active: 'bg-orange-600/20 text-orange-400 border-orange-500/40', hover: 'hover:bg-orange-600/10 hover:text-orange-400' },
  rose:    { active: 'bg-rose-600/20 text-rose-400 border-rose-500/40',       hover: 'hover:bg-rose-600/10 hover:text-rose-400' },
  amber:   { active: 'bg-amber-600/20 text-amber-400 border-amber-500/40',    hover: 'hover:bg-amber-600/10 hover:text-amber-400' },
  blue:    { active: 'bg-blue-600/20 text-blue-400 border-blue-500/40',       hover: 'hover:bg-blue-600/10 hover:text-blue-400' },
};

export default function PortfolioRiskNav() {
  const navigate = useNavigate();
  const location = useLocation();

  const currentPath = location.pathname.split('/').pop();

  return (
    <div className="flex items-center justify-between gap-2 w-full">
      <nav className="flex items-center gap-1 overflow-x-auto scrollbar-theme py-2 pb-3">
        {NAV_ITEMS.map(item => {
          const Icon = item.icon;
          const isActive = currentPath === item.path;
          const colors = COLOR_MAP[item.color];

          return (
            <button
              key={item.path}
              onClick={() => navigate(`/dashboard/portfolio/${item.path}`)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all duration-200 border
                ${isActive
                  ? `${colors.active}`
                  : `border-transparent text-gray-500 ${colors.hover}`
                }
              `}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
