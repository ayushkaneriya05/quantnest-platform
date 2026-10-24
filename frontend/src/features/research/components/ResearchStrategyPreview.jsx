import PropTypes from "prop-types";

import { title, readable, choiceLabel, describeRule } from "@/features/research/researchDescriptions";

export function ConfigFields({ value }) {
  return <dl className="space-y-2 text-sm">{Object.entries(value || {}).filter(([key]) => !["id", "strategy", "created_at", "updated_at"].includes(key)).map(([key, item]) =>
    <div key={key} className="flex justify-between gap-4"><dt className="capitalize text-muted-foreground">{title(key)}</dt><dd className="max-w-[65%] text-right break-words">{readable(item)}</dd></div>)}</dl>;
}
ConfigFields.propTypes = { value: PropTypes.object };

export default function ResearchStrategyPreview({ snapshot, enums = {} }) {
  if (!snapshot) return null;
  return <div className="space-y-4 text-foreground">
    <div><h3 className="font-semibold">{snapshot.name}</h3><p className="mt-1 text-sm text-muted-foreground">{snapshot.description}</p></div>
    <p className="text-xs text-muted-foreground">{snapshot.exchange} · {snapshot.instrument_type} · {snapshot.strategy_type}. All configured values below include the backend defaults applied during validation.</p>
    {(snapshot.rule_groups || []).map((group, index) => <section key={index} className="rounded-lg border border-border p-3">
      <h4 className="text-sm font-semibold text-indigo-700 dark:text-indigo-300">{choiceLabel(enums, "RuleType", group.rule_type)} · {group.name}</h4>
      <p className="my-2 text-xs text-muted-foreground">{group.logical_operator === "OR" ? "Any condition" : "All conditions"}</p>
      <ul className="space-y-2 text-sm">{(group.rules || []).map((rule, position) => <li key={position} className="break-words">{describeRule(rule, enums)}{rule.is_active === false ? " (disabled)" : ""}</li>)}</ul>
    </section>)}
    {[["Time and timeframe", "time_rule"], ["Position sizing", "position_sizing_rule"], ["Entry settings", "entry_order_config"], ["Exit settings", "exit_order_config"]].map(([label, key]) => snapshot[key] && <details key={key} className="rounded-lg border border-border p-3" open={key === "time_rule" || key === "position_sizing_rule"}><summary className="mb-3 cursor-pointer text-sm font-medium">{label}</summary><ConfigFields value={snapshot[key]} /></details>)}
    <section className="rounded-lg border border-border p-3"><h4 className="mb-2 text-sm font-medium">Instruments and routes</h4><ul className="text-sm text-muted-foreground">{(snapshot.watchlist_instruments || []).map((item) => <li key={item.instrument_id}>{item.instrument_symbol || item.symbol || `Instrument #${item.instrument_id}`} · {(item.execution_routes || []).map((route) => route.route_type).join(", ")}</li>)}</ul></section>
  </div>;
}
ResearchStrategyPreview.propTypes = { snapshot: PropTypes.object, enums: PropTypes.object };
