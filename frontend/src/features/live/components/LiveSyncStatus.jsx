import PropTypes from "prop-types";
import { Badge } from "@/shared/components/ui/badge";
import { TooltipHint } from "@/shared/components/ui/tooltip";

export default function LiveSyncStatus({ isConnected }) {
  const label = isConnected ? "Live" : "Syncing";
  return (
    <TooltipHint content={isConnected ? "Live updates connected" : "Live updates reconnecting; automatic refresh remains active"}><span className="inline-flex" tabIndex={0}><Badge
      variant="outline"
      role="status"
      aria-label={isConnected ? "Live updates connected" : "Live updates reconnecting"}
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${isConnected ? "border-emerald-800/70 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300" : "border-amber-800/70 bg-amber-500/5 text-amber-700 dark:text-amber-200"}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? "bg-emerald-400" : "animate-pulse bg-amber-400"}`} />
      {label}
    </Badge></span></TooltipHint>
  );
}

LiveSyncStatus.propTypes = { isConnected: PropTypes.bool };
