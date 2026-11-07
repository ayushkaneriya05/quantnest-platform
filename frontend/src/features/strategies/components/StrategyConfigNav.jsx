import { TabBar, TabButton } from "@/shared/components/ui/tabs";
import PropTypes from "prop-types";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { Badge } from "@/shared/components/ui/badge";
import { Layers, Lock, History, BarChart2 } from "lucide-react";

const NAV_ITEMS = [
  { path: "edit", icon: BarChart2, label: "Details" },
  { path: "studio", icon: Layers, label: "Studio" },
  { path: "permissions", icon: Lock, label: "Sharing" },
  { path: "versions", icon: History, label: "Versions" },
];

const STATUS_BADGES = {
  DRAFT: ["Draft", "text-muted-foreground border-border/30 bg-muted/10"],
  ACTIVE: [
    "Active",
    "text-success border-success/30 bg-success/10",
  ],
  PAUSED: [
    "Paused",
    "text-warning border-warning/30 bg-warning/10",
  ],
  ARCHIVED: ["Archived", "text-muted-foreground border-border/30 bg-muted/10"],
};

export default function StrategyConfigNav({ strategy }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const currentPath = location.pathname.split("/").pop();
  const [label, badgeClass] =
    STATUS_BADGES[strategy?.status] || STATUS_BADGES.DRAFT;

  return (
    <div className="strategy-config-nav flex min-w-0 items-center justify-between gap-3">
      <TabBar role="navigation" appearance="plain"
        aria-label="Strategy configuration"
      >
        {NAV_ITEMS.map(({ path, icon: Icon, label: itemLabel }) => {
          const active = currentPath === path;
          return (
            <TabButton active={active}
              key={path}
              aria-current={active ? "page" : undefined}
              onClick={() => navigate(`/strategies/${id}/${path}`)}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="inline">{itemLabel}</span>
            </TabButton>
          );
        })}
      </TabBar>
      <Badge
        variant="outline"
        className={`text-xs h-6 px-2 shrink-0 ${badgeClass}`}
      >
        {label}
      </Badge>
    </div>
  );
}

StrategyConfigNav.propTypes = {
  ...StrategyConfigNav.propTypes,
  strategy: PropTypes.object,
};
