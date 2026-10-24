import { formatCurrency } from "@/shared/utils/formatters";
import { Link } from "react-router-dom";
import { Check, ArrowRight } from "lucide-react";
import { usePlatform } from "@/shared/context/platform";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { Button } from "@/shared/components/ui/button";
import PlanMarkets from "@/shared/components/PlanMarkets";

const highlights = [
  "strategies",
  "backtest_credits",
  "research_turns",
  "screens",
  "paper_deployments",
  "paper_instruments",
];
export default function PricingCards() {
  const { catalog, loading, error, refresh } = usePlatform();
  if (!catalog || error)
    return (
      <WorkspaceState
        loading={loading}
        error={error ? "Current plans could not be loaded. Please retry." : ""}
        onRetry={refresh}
      />
    );
  return (
    <>
      <div className="grid gap-4 lg:grid-cols-3">
        {Object.values(catalog.plans).map((plan) => (
          <article
            key={plan.code}
            className={`relative flex flex-col rounded-3xl border bg-card p-5 sm:p-6 ${plan.code === "build" ? "border-brand/50 shadow-[0_0_45px_-20px_hsl(var(--brand)/.3)]" : ""}`}
          >
            <p className="text-xs uppercase tracking-widest text-brand">
              {plan.code === "explore"
                ? "Discover the workflow"
                : plan.code === "build"
                  ? "Develop your practice"
                  : "More room to investigate"}
            </p>
            <h3 className="mt-3 text-2xl font-semibold">{plan.name}</h3>
            <p className="mt-4 text-4xl font-semibold">
              {plan.price_minor
                ? `${formatCurrency(plan.price_minor / 100, { minimumFractionDigits: 0 })}`
                : "Free"}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              {plan.price_minor
                ? "per month + applicable tax"
                : "allowances per calendar month"}
            </p>
            <section className="my-5 border-y py-4">
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Markets
              </h4>
              <PlanMarkets markets={plan.markets} />
            </section>
            <ul className="mb-5 space-y-3">
              {highlights.map((key) => (
                <li
                  key={key}
                  className="flex items-center justify-between gap-3 text-sm"
                >
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <Check className="h-4 w-4 shrink-0 text-brand" />
                    {catalog.limit_labels[key]}
                  </span>
                  <strong>{plan.limits[key]}</strong>
                </li>
              ))}
            </ul>
            <p className="mb-5 text-sm leading-6 text-muted-foreground">
              Terminal, journal, reports, versions and account security are included.
            </p>
            <Button
              asChild
              className="mt-auto w-full rounded-full"
              variant={plan.code === "build" ? "default" : "outline"}
            >
              <Link
                to={
                  plan.code === "explore"
                    ? "/register"
                    : `/settings/billing?plan=${plan.code}`
                }
              >
                {plan.code === "explore"
                  ? "Start Explore"
                  : `Review ${plan.name}`}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </article>
        ))}
      </div>
      <p className="mt-4 text-sm leading-7 text-muted-foreground">
        All public plans support NSE-stock workflows through Paper simulation.
        Futures and options are coming soon in Build and Pro; they are not
        available today and have no announced release date. Upgrading today adds
        capacity for current features. Review your workspace allowances
        before upgrading for a specific task. No rollover or automatic
        paid overages.
      </p>
      <p className="mt-2 text-sm leading-7 text-muted-foreground">
        Customer Live trading and QuantNest Private are not currently available.
      </p>
    </>
  );
}
