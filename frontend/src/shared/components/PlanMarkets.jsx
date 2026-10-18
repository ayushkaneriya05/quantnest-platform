import PropTypes from "prop-types";
import { Check, Clock3 } from "lucide-react";

export default function PlanMarkets({ markets }) {
  return (
    <div className="space-y-2" aria-label="Markets for this plan">
      {markets.map((market) => (
        <div
          className="flex items-center justify-between gap-2 text-sm"
          key={market.code}
          data-market={market.code}
          data-market-status={market.status}
        >
          <span className="flex items-center gap-2">
            {market.status === "available" ? (
              <Check className="h-4 w-4 shrink-0 text-brand" />
            ) : (
              <Clock3 className="h-4 w-4 shrink-0 text-muted-foreground" />
            )}
            <span>{market.name}</span>
          </span>
          {market.status === "coming_soon" && (
            <span className="shrink-0 rounded-full border bg-muted/50 px-2 py-1 text-[11px] text-muted-foreground">
              Coming soon
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
PlanMarkets.propTypes = {
  markets: PropTypes.arrayOf(
    PropTypes.shape({
      code: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      status: PropTypes.oneOf(["available", "coming_soon"]).isRequired,
    }),
  ).isRequired,
};
