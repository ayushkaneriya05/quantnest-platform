import PropTypes from "prop-types";
import { useEnums } from "@/shared/context/EnumsContext";

import { hidden, fieldLabel, formatStrategyValue } from '@/shared/utils/strategyConfiguration';

export function ConfigurationFields({ value, enums = {} }) {
  return <dl className="space-y-2 text-sm">{Object.entries(value || {}).filter(([key]) => !hidden.has(key)).map(([key, item]) =>
    <div key={key} className="grid grid-cols-1 gap-1 border-b border-slate-800/60 pb-2 last:border-0 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)]">
      <dt className="text-slate-400">{fieldLabel(key)}</dt>
      <dd className="min-w-0 whitespace-pre-wrap break-words text-slate-200 sm:text-right">{formatStrategyValue(item, enums)}</dd>
    </div>)}</dl>;
}
ConfigurationFields.propTypes = { value: PropTypes.object, enums: PropTypes.object };

function Section({ title, children, open = false }) {
  return <details open={open} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
    <summary className="cursor-pointer text-sm font-semibold text-slate-100">{title}</summary>
    <div className="mt-4 space-y-4">{children}</div>
  </details>;
}
Section.propTypes = { title: PropTypes.string.isRequired, children: PropTypes.node, open: PropTypes.bool };

export default function StrategyConfiguration({ snapshot }) {
  const { enums } = useEnums();
  if (!snapshot) return null;
  const sections = [
    ["Entry settings", "entry_order_config"], ["Exit settings", "exit_order_config"],
    ["Position sizing", "position_sizing_rule"], ["Trading schedule", "time_rule"],
    ["Event restrictions", "special_event_filter"],
  ];
  const groupOperand = (rule, side) => {
    const type = rule[`operand_${side}_type`];
    const params = rule[`operand_${side}_params`] || {};
    return type === "CONSTANT" ? formatStrategyValue(params.value, enums) :
      `${formatStrategyValue(type, enums)}${Object.keys(params).length ? ` (${formatStrategyValue(params, enums)})` : ""}`;
  };
  return <div className="space-y-4">
    <Section title="Strategy details" open>
      <ConfigurationFields enums={enums} value={Object.fromEntries(Object.entries(snapshot).filter(([key]) =>
        !["rule_groups", "watchlist_instruments", "auto_disable_rules", ...sections.map(([, field]) => field)].includes(key)))} />
    </Section>
    <Section title={`Trading rules (${snapshot.rule_groups?.length || 0} groups)`} open>
      {!snapshot.rule_groups?.length && <p className="text-sm text-slate-400">No trading rules configured.</p>}
      {(snapshot.rule_groups || []).map((group, index) => <section key={index} className="space-y-3 border-b border-slate-800 pb-4 last:border-0 last:pb-0">
        <h4 className="font-medium text-slate-100">{formatStrategyValue(group.rule_type, enums)} · {group.name || `Group ${index + 1}`}</h4>
        <ConfigurationFields enums={enums} value={Object.fromEntries(Object.entries(group).filter(([key]) => key !== "rules"))} />
        {(group.rules || []).map((rule, position) => <div key={position} className="rounded-lg border border-slate-800 p-3">
          <p className="mb-2 text-sm leading-relaxed text-slate-200">{position + 1}. {groupOperand(rule, "a")} {formatStrategyValue(rule.comparison, enums)} {groupOperand(rule, "b")}</p>
          <details><summary className="cursor-pointer text-xs text-slate-400">Condition settings</summary><div className="mt-3"><ConfigurationFields value={rule} enums={enums} /></div></details>
        </div>)}
      </section>)}
    </Section>
    {sections.map(([title, key]) => snapshot[key] && <Section key={key} title={title} open={key === "position_sizing_rule"}><ConfigurationFields value={snapshot[key]} enums={enums} /></Section>)}
    <Section title={`Instruments and routes (${snapshot.watchlist_instruments?.length || 0})`} open>
      {!snapshot.watchlist_instruments?.length && <p className="text-sm text-slate-400">No instruments selected.</p>}
      {(snapshot.watchlist_instruments || []).map((item) => <section key={item.instrument_id} className="space-y-3">
        <h4 className="text-sm font-medium">{item.instrument_symbol || `Instrument #${item.instrument_id}`}{item.instrument_name ? ` · ${item.instrument_name}` : ""}</h4>
        {(item.execution_routes || []).map((route, index) => <div key={index} className="rounded-lg border border-slate-800 p-3"><h5 className="mb-3 text-sm text-slate-300">Route {index + 1}</h5><ConfigurationFields value={route} enums={enums} /></div>)}
        {!item.execution_routes?.length && <p className="text-sm text-slate-400">Trade the selected instrument directly.</p>}
      </section>)}
    </Section>
    <Section title={`Auto-disable rules (${snapshot.auto_disable_rules?.length || 0})`}>
      {!snapshot.auto_disable_rules?.length && <p className="text-sm text-slate-400">No auto-disable rules configured.</p>}
      {(snapshot.auto_disable_rules || []).map((rule, index) => <section key={index} className="space-y-3"><h4 className="text-sm font-medium">{rule.name || `Rule ${index + 1}`}</h4><ConfigurationFields value={rule} enums={enums} /></section>)}
    </Section>
  </div>;
}
StrategyConfiguration.propTypes = { snapshot: PropTypes.object };
