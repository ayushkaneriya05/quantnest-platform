import PropTypes from "prop-types";
import { useEnums } from "@/shared/context/EnumsContext";
import { Button } from "@/shared/components/ui/button";

import {
  hidden,
  fieldLabel,
  formatStrategyValue,
} from "@/shared/utils/strategyConfiguration";

export function ConfigurationFields({ value, enums = {} }) {
  return (
    <dl className="space-y-2 text-sm">
      {Object.entries(value || {})
        .filter(([key]) => !hidden.has(key))
        .map(([key, item]) => (
          <div
            key={key}
            className="grid grid-cols-1 gap-1 border-b border-border/60 pb-2 last:border-0 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)]"
          >
            <dt className="text-muted-foreground">{fieldLabel(key, enums)}</dt>
            <dd className="min-w-0 whitespace-pre-wrap break-words text-foreground sm:text-right">
              {formatStrategyValue(item, enums, key)}
            </dd>
          </div>
        ))}
    </dl>
  );
}
ConfigurationFields.propTypes = {
  value: PropTypes.object,
  enums: PropTypes.object,
};

function Section({ title, children, open = false, onEdit }) {
  return (
    <details
      open={open}
      className="rounded-xl border border-border bg-background/50 p-3"
    >
      <summary className="cursor-pointer text-sm font-semibold text-foreground">
        {title}
        {onEdit && (
          <Button
            variant="link"
            size="sm"
            className="ml-2 px-1"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              onEdit();
            }}
          >
            Edit {title.toLowerCase()}
          </Button>
        )}
      </summary>
      <div className="mt-3 space-y-3">{children}</div>
    </details>
  );
}
Section.propTypes = {
  title: PropTypes.string.isRequired,
  children: PropTypes.node,
  open: PropTypes.bool,
  onEdit: PropTypes.func,
};

function ExpressionSummary({ node, enums }) {
  if (node.op === "expression")
    return (
      <span className="font-medium text-primary">Formula {node.name}</span>
    );
  if (node.op === "capture")
    return (
      <span className="font-medium text-primary">Captured {node.name}</span>
    );
  if (node.op === "compare")
    return (
      <div className="rounded-lg border border-border bg-background/50 p-3 text-sm">
        <ExpressionSummary node={node.left} enums={enums} />{" "}
        <strong className="text-primary">
          {formatStrategyValue(node.comparison, enums, "comparison")}
        </strong>{" "}
        <ExpressionSummary node={node.right} enums={enums} />
      </div>
    );
  if (node.op === "input")
    return (
      <span>
        {node.type === "CONSTANT" ? (
          formatStrategyValue(node.params.value, enums)
        ) : (
          <>
            <span className="text-xs text-muted-foreground">
              {enums.StrategyStudio?.conditions.operands[node.type]
                ?.context === "position"
                ? "Owned traded position"
                : node.source === "trade"
                  ? "Traded contract"
                  : "Signal"}{" "}
              ·{" "}
            </span>
            {formatStrategyValue(node.type, enums, "type")}{" "}
            {Object.keys(node.params || {}).length > 0 && (
              <span className="text-muted-foreground">
                ({formatStrategyValue(node.params, enums, { parameters: enums.StrategyStudio?.conditions.operands[node.type]?.parameters })})
              </span>
            )}
            {node.timeframe && (
              <span className="ml-1 text-xs text-muted-foreground">
                @ {node.timeframe}
              </span>
            )}
          </>
        )}
      </span>
    );
  if (["all", "any", "not", "at_least"].includes(node.op))
    return (
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {formatStrategyValue(node.op, enums, "op")}{node.op === "at_least" ? `: ${node.count}` : ""}
        </p>
        <div className="space-y-2 border-l-2 border-primary/25 pl-3">
          {node.args.map((item, index) => (
            <ExpressionSummary key={index} node={item} enums={enums} />
          ))}
        </div>
      </div>
    );
  return (
    <span>
      {formatStrategyValue(node.op, enums, "op")}(
      {node.bars != null && <>{node.bars} bars, </>}
      {node.ddof != null && <>{node.ddof === 0 ? "population" : "sample"}, </>}
      {node.args.map((arg, index) => (
        <span key={index}>
          {index > 0 && ", "}
          <ExpressionSummary node={arg} enums={enums} />
        </span>
      ))}
      )
    </span>
  );
}
ExpressionSummary.propTypes = {
  node: PropTypes.object.isRequired,
  enums: PropTypes.object,
};

export default function StrategyConfiguration({ snapshot, onEditSection }) {
  const { enums } = useEnums();
  if (!snapshot) return null;
  const sections = [
    ["Entry settings", "entry_order_config"],
    ["Exit settings", "exit_order_config"],
    ["Position sizing", "position_sizing_rule"],
    ["Trading schedule", "time_rule"],
  ];

  return (
    <div className="space-y-3">
      <Section title="Strategy details" open>
        <ConfigurationFields
          enums={enums}
          value={Object.fromEntries(
            Object.entries(snapshot).filter(
              ([key]) =>
                ![
                  "rule_groups",
                  "watchlist_instruments",
                  "schema_version",
                  "semantics_version",
                  "expressions",
                  "initial_risk",
                  ...sections.map(([, field]) => field),
                ].includes(key),
            ),
          )}
        />
      </Section>
      {snapshot.initial_risk && (
        <Section
          title="Initial reward/risk distance"
          open
          onEdit={onEditSection && (() => onEditSection(0))}
        >
          <ExpressionSummary node={snapshot.initial_risk} enums={enums} />
          <p className="text-xs text-muted-foreground">
            Traded-contract price points, frozen at entry admission. Exit rules
            remain responsible for protection.
          </p>
        </Section>
      )}
      {Object.keys(snapshot.expressions || {}).length > 0 && (
        <Section
          title="Reusable formulas"
          open
          onEdit={onEditSection && (() => onEditSection(1))}
        >
          {Object.entries(snapshot.expressions).map(([name, value]) => (
            <div key={name} className="space-y-2 text-sm">
              <h4 className="break-all font-mono font-semibold">{name}</h4>
              <ExpressionSummary node={value} enums={enums} />
            </div>
          ))}
        </Section>
      )}
      <Section
        title={`Trading rules (${snapshot.rule_groups?.length || 0} groups)`}
        open
        onEdit={onEditSection && (() => onEditSection(1))}
      >
        {!snapshot.rule_groups?.length && (
          <p className="text-sm text-muted-foreground">
            No trading rules configured.
          </p>
        )}
        {(snapshot.rule_groups || []).map((group, index) => (
          <section
            key={index}
            className="space-y-3 border-b border-border pb-4 last:border-0 last:pb-0"
          >
            <h4 className="font-medium text-foreground">
              {formatStrategyValue(group.rule_type, enums, "rule_type")} ·{" "}
              {group.name || `Group ${index + 1}`}
            </h4>
            <ConfigurationFields
              enums={enums}
              value={Object.fromEntries(
                Object.entries(group).filter(
                  ([key]) => !["rules", "condition", "setup"].includes(key),
                ),
              )}
            />
            {group.setup && (
              <div className="space-y-3 rounded-lg border border-primary/20 p-3">
                <h5 className="text-sm font-semibold">Arm and remember</h5>
                <ExpressionSummary node={group.setup.arm} enums={enums} />
                {Object.entries(group.setup.captures).map(([name, value]) => (
                  <p key={name} className="text-sm">
                    <strong>{name}: </strong>
                    <ExpressionSummary node={value} enums={enums} />
                  </p>
                ))}
                {group.setup.steps.map((value, step) => (
                  <div key={step}>
                    <p className="text-xs text-muted-foreground">
                      Then confirmation {step + 1}
                    </p>
                    <ExpressionSummary node={value} enums={enums} />
                  </div>
                ))}
                {group.setup.invalidate && (
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Invalidate when
                    </p>
                    <ExpressionSummary
                      node={group.setup.invalidate}
                      enums={enums}
                    />
                  </div>
                )}
                <p className="text-xs text-muted-foreground">
                  Expires after {group.setup.expires_after_bars} new{" "}
                  {group.setup.timeframe} bars. Final entry confirmation:
                </p>
              </div>
            )}
            {group.condition && (
              <ExpressionSummary node={group.condition} enums={enums} />
            )}
          </section>
        ))}
      </Section>
      {sections.map(
        ([title, key]) =>
          snapshot[key] && (
            <Section
              key={key}
              title={title}
              open={key === "position_sizing_rule"}
              onEdit={
                onEditSection &&
                (() =>
                  onEditSection(
                    key === "time_rule"
                      ? 2
                      : key === "position_sizing_rule"
                        ? 0
                        : 1,
                  ))
              }
            >
              <ConfigurationFields value={snapshot[key]} enums={enums} />
            </Section>
          ),
      )}
      <Section
        title={`Instruments and routes (${snapshot.watchlist_instruments?.length || 0})`}
        open
        onEdit={onEditSection && (() => onEditSection(0))}
      >
        {!snapshot.watchlist_instruments?.length && (
          <p className="text-sm text-muted-foreground">
            No instruments selected.
          </p>
        )}
        {(snapshot.watchlist_instruments || []).map((item) => (
          <section
            key={`${item.route_id}:${item.leg_id}`}
            className="space-y-3"
          >
            <h4 className="text-sm font-medium">
              {item.instrument_symbol || `Instrument #${item.instrument_id}`}
              {item.instrument_name ? ` · ${item.instrument_name}` : ""}
            </h4>
            {item.contract_selection && (
              <div className="space-y-2 text-sm">
                <p className="text-muted-foreground">
                  Automatic contract policy · retains the selected contract
                  until flat
                </p>
                <ConfigurationFields
                  value={item.contract_selection}
                  enums={enums}
                />
              </div>
            )}
            {item.signal_instrument_id &&
              item.signal_instrument_id !== item.instrument_id && (
                <p className="text-sm text-muted-foreground">
                  Signal instrument:{" "}
                  {item.signal_instrument_name ||
                    `Instrument #${item.signal_instrument_id}`}
                </p>
              )}
            {(item.execution_routes || []).map((route, index) => (
              <div key={index} className="rounded-lg border border-border p-3">
                <h5 className="mb-3 text-sm text-foreground">
                  Route {index + 1}
                </h5>
                <ConfigurationFields value={route} enums={enums} />
              </div>
            ))}
            {!item.execution_routes?.length && !item.contract_selection && (
              <p className="text-sm text-muted-foreground">
                Trade this exact contract. Its own prices determine fills and
                P&amp;L.
              </p>
            )}
          </section>
        ))}
      </Section>
    </div>
  );
}
StrategyConfiguration.propTypes = {
  snapshot: PropTypes.object,
  onEditSection: PropTypes.func,
};
