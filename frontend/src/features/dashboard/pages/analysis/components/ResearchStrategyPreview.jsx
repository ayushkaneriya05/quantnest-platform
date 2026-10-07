import PropTypes from "prop-types";
import { formatNumber } from "@/shared/utils/formatters";

const title = (key) => key.replaceAll("_", " ");
export const choiceLabel = (enums, name, value) => enums?.[name]?.find((item) => item.value === value)?.label || value;

function readable(value) {
  if (value == null) return "N/A";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return formatNumber(value);
  if (Array.isArray(value)) return value.map(readable).join(", ");
  if (typeof value === "object") return Object.entries(value).map(([key, item]) => `${title(key)}: ${readable(item)}`).join("; ");
  return String(value);
}

export function describeOperand(type, params = {}, enums = {}) {
  if (type === "CONSTANT") return formatNumber(params.value);
  const label = choiceLabel(enums, "OperandType", type);
  const expression = params.expression;
  if (type === "MATH_EXPRESSION" && expression) {
    const variables = Object.entries(expression.variables || {}).map(([name, value]) =>
      `${name} = ${describeOperand(value.type, value.params, enums)}${value.timeframe ? ` (${value.timeframe})` : ""}`);
    return `${expression.expression} (${variables.join("; ")})`;
  }
  const fields = Object.entries(params).map(([key, value]) => `${title(key)}: ${key === "source" ? choiceLabel(enums, "OperandType", value) : readable(value)}`);
  return `${label}${fields.length ? ` (${fields.join(", ")})` : ""}`;
}

export function describeRule(rule, enums = {}) {
  return `${describeOperand(rule.operand_a_type, rule.operand_a_params, enums)}${rule.operand_a_timeframe ? ` [${rule.operand_a_timeframe}]` : ""} ${choiceLabel(enums, "ComparisonOperator", rule.comparison)} ${describeOperand(rule.operand_b_type, rule.operand_b_params, enums)}${rule.operand_b_timeframe ? ` [${rule.operand_b_timeframe}]` : ""}`;
}

export function ConfigFields({ value }) {
  return <dl className="space-y-2 text-sm">{Object.entries(value || {}).filter(([key]) => !["id", "strategy", "created_at", "updated_at"].includes(key)).map(([key, item]) =>
    <div key={key} className="flex justify-between gap-4"><dt className="capitalize text-slate-400">{title(key)}</dt><dd className="max-w-[65%] text-right break-words">{readable(item)}</dd></div>)}</dl>;
}
ConfigFields.propTypes = { value: PropTypes.object };

export default function ResearchStrategyPreview({ snapshot, enums = {} }) {
  if (!snapshot) return null;
  return <div className="space-y-4 text-slate-200">
    <div><h3 className="font-semibold">{snapshot.name}</h3><p className="mt-1 text-sm text-slate-400">{snapshot.description}</p></div>
    <p className="text-xs text-slate-400">{snapshot.exchange} · {snapshot.instrument_type} · {snapshot.strategy_type}. All configured values below include the backend defaults applied during validation.</p>
    {(snapshot.rule_groups || []).map((group, index) => <section key={index} className="rounded-lg border border-slate-800 p-3">
      <h4 className="text-sm font-semibold text-indigo-300">{choiceLabel(enums, "RuleType", group.rule_type)} · {group.name}</h4>
      <p className="my-2 text-xs text-slate-400">{group.logical_operator === "OR" ? "Any condition" : "All conditions"}{group.action ? ` · ${choiceLabel(enums, "RuleGroupAction", group.action)}` : ""}</p>
      <ul className="space-y-2 text-sm">{(group.rules || []).map((rule, position) => <li key={position} className="break-words">{describeRule(rule, enums)}{rule.is_active === false ? " (disabled)" : ""}</li>)}</ul>
      {Object.keys(group.action_params || {}).length > 0 && <div className="mt-3"><ConfigFields value={group.action_params} /></div>}
    </section>)}
    {[["Time and timeframe", "time_rule"], ["Position sizing", "position_sizing_rule"], ["Entry settings", "entry_order_config"], ["Exit settings", "exit_order_config"], ["Event restrictions", "special_event_filter"]].map(([label, key]) => snapshot[key] && <details key={key} className="rounded-lg border border-slate-800 p-3" open={key === "time_rule" || key === "position_sizing_rule"}><summary className="mb-3 cursor-pointer text-sm font-medium">{label}</summary><ConfigFields value={snapshot[key]} /></details>)}
    <section className="rounded-lg border border-slate-800 p-3"><h4 className="mb-2 text-sm font-medium">Instruments and routes</h4><ul className="text-sm text-slate-400">{(snapshot.watchlist_instruments || []).map((item) => <li key={item.instrument_id}>{item.instrument_symbol || item.symbol || `Instrument #${item.instrument_id}`} · {(item.execution_routes || []).map((route) => route.route_type).join(", ")}</li>)}</ul></section>
    {(snapshot.auto_disable_rules || []).map((item, index) => <details key={index} className="rounded-lg border border-slate-800 p-3"><summary className="mb-3 cursor-pointer text-sm">Auto-disable rule {index + 1}</summary><ConfigFields value={item} /></details>)}
  </div>;
}
ResearchStrategyPreview.propTypes = { snapshot: PropTypes.object, enums: PropTypes.object };
