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
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${isConnected ? "border-success/70 bg-success/5 text-success" : "border-warning/70 bg-warning/5 text-warning"}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? "bg-success" : "animate-pulse bg-warning"}`} />
      {label}
    </Badge></span></TooltipHint>
  );
}

LiveSyncStatus.propTypes = { isConnected: PropTypes.bool };
