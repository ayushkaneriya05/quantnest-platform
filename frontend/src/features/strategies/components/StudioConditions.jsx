import PropTypes from "prop-types";
import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Switch } from "@/shared/components/ui/switch";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/shared/components/ui/tabs";
import { customConfirm } from "@/shared/components/ui/custom-dialog";
import { useStrategySpecification } from "@/shared/context/EnumsContext";
import { useNotifications } from "@/shared/hooks/useNotifications";
import ExpressionEditor, {
  NumberExpression,
  StudioSelect,
} from "./ExpressionEditor";
import SetupEditor from "./SetupEditor";
import {
  referencesFormula,
  referencesCapture,
} from "../strategyExpressions";
import { expressionContexts } from "../studioPresentation";

export default function StudioConditions({
  document,
  onChange,
  operators,
  ruleType,
  onRuleTypeChange,
}) {
  const { enums, spec, inputNode, groupTemplate } = useStrategySpecification();
  const { notify } = useNotifications();
  const [formulaName, setFormulaName] = useState("");
  const [expanded, setExpanded] = useState({});
  const groups = document.rule_groups.filter(
    (group) => group.rule_type === ruleType,
  );
  const [section, field] = spec.conditions.stages.find((stage) => stage.value === ruleType).combination;
  const groupChange = (id, changes) =>
    onChange({
      ...document,
      rule_groups: document.rule_groups.map((group) =>
        group.id === id ? { ...group, ...changes } : group,
      ),
    });
  const groupOperators = (group) => ({
    ...operators,
    default_timeframe: document.time_rule.candle_timeframe,
    expressions: Object.keys(document.expressions || {}),
    captures: document.rule_groups
      .filter(
        (item) =>
          item.setup &&
          (group.rule_type === "ENTRY"
            ? item.id === group.id
            : item.is_active !== false),
      )
      .flatMap((item) =>
        Object.keys(item.setup.captures).map((name) => ({
          setup: item.id,
          name,
          label: `${item.name} · ${name}`,
        })),
      ),
    capture_referenced: (name) =>
      referencesCapture(
        document.rule_groups.map((item) =>
          item.id === group.id
            ? { ...item, setup: { ...item.setup, captures: {} } }
            : item,
        ),
        group.id,
        name,
      ),
    setup_referenced: Boolean(
      group.setup &&
        Object.keys(group.setup.captures).some((name) =>
          referencesCapture(
            document.rule_groups.filter((item) => item.id !== group.id),
            group.id,
            name,
          ),
        ),
    ),
    setup_allowed:
      document.rule_groups.filter(
        (item) => item.rule_type === "ENTRY" && item.is_active !== false,
      ).length <= 1,
  });
  const addGroup = () => {
    const id = crypto.randomUUID();
    const template = groupTemplate();
    setExpanded((current) => ({ ...current, [id]: true }));
    onChange({
      ...document,
      rule_groups: [
        ...document.rule_groups,
        {
          ...template,
          id,
          name: `${template.name} ${groups.length + 1}`,
          rule_type: ruleType,
          priority: groups.length + 1,
        },
      ],
    });
  };
  const hasSeparateSignal = document.watchlist_instruments.some(
    (item) =>
      item.contract_selection ||
      (item.signal_instrument_id &&
        item.signal_instrument_id !== item.instrument_id),
  );
  return (
    <section
      className={`studio-conditions studio-action-${ruleType.toLowerCase()}`}
    >
      <Tabs
        value={ruleType}
        onValueChange={onRuleTypeChange}
        activationMode="manual"
      >
        <div className="overflow-x-auto pb-1">
          <TabsList

            aria-label="Condition action"
          >
            {spec.conditions.stages
              .map((kind) => {
                const count = document.rule_groups.filter(
                  (group) => group.rule_type === kind.value,
                ).length;
                return (
                  <TabsTrigger key={kind.value} value={kind.value}>
                    {kind.label}
                    <span className="studio-count ml-2">
                      {count
                        ? `${count} ${count === 1 ? "group" : "groups"}`
                        : "—"}
                    </span>
                  </TabsTrigger>
                );
              })}
          </TabsList>
        </div>
        <TabsContent value={ruleType} className="mt-0 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            {groups.length > 1 ? (
              <label className="flex flex-wrap items-center gap-2 text-sm">
                <span>Match</span>
                <StudioSelect
                  label="Combine action groups"
                  className="w-auto"
                  value={document[section][field]}
                  options={(enums.LogicalOperator || []).map((item) => ({
                    ...item,
                    label:
                      item.value === "AND"
                        ? "All enabled groups"
                        : "Any enabled group",
                  }))}
                  onChange={(next) =>
                    onChange({
                      ...document,
                      [section]: { ...document[section], [field]: next },
                    })
                  }
                />
              </label>
            ) : (
              <span className="text-sm font-medium">
                {groups.length
                  ? "Conditions for this action"
                  : "No conditions configured"}
              </span>
            )}
            {groups.length > 0 && (
              <Button variant="outline" size="sm" onClick={addGroup} disabled={document.rule_groups.length >= spec.constraints.groups}>
                <Plus className="mr-1 h-4 w-4" />
                Add group
              </Button>
            )}
          </div>
          {!groups.length && (
            <div className="studio-empty studio-surface">
              <p>
                {ruleType === "ENTRY"
                  ? "Add a comparison to define when this strategy enters."
                  : "This exit category has no configured conditions."}
              </p>
              <Button variant="outline" size="sm" onClick={addGroup} disabled={document.rule_groups.length >= spec.constraints.groups}>
                <Plus className="mr-1 h-4 w-4" />
                Add condition
              </Button>
            </div>
          )}
          {ruleType !== "ENTRY" && groups.length > 0 && (
            <p className="studio-hint">
              These conditions close the owned position when execution can act.
              They do not place a resting broker stop order.
            </p>
          )}
          {groups.map((group, index) => {
            const otherGroups = document.rule_groups.filter(
              (item) => item.id !== group.id,
            );
            const referenced =
              group.setup &&
              Object.keys(group.setup.captures).some((name) =>
                referencesCapture(otherGroups, group.id, name),
              );
            const contexts = expressionContexts(
              group.condition,
              enums,
              document.expressions,
            );
            const usesPosition = contexts.some(
              (input) => input.context === "position",
            );
            const usesSignal = contexts.some(
              (input) =>
                input.context === "market" && input.source === "signal",
            );
            return (
              <details
                key={group.id}
                open={expanded[group.id] ?? index === 0}
                onToggle={(event) => {
                  const open = event.currentTarget.open;
                  setExpanded((current) =>
                    current[group.id] === open
                      ? current
                      : { ...current, [group.id]: open },
                  );
                }}
                className="studio-group"
                data-group-id={group.id}
              >
                <summary className="studio-group-summary">
                  <strong className="min-w-0 flex-1 break-words text-sm">
                    {group.name}
                  </strong>
                  <span className="studio-tag">
                    {group.is_active === false ? "Disabled" : "Enabled"}
                  </span>
                </summary>
                <div className="space-y-3 border-t border-border p-3 sm:p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Input
                      aria-label="Group name"
                      className="min-w-0 flex-1 basis-48"
                      value={group.name}
                      onChange={(event) =>
                        groupChange(group.id, { name: event.target.value })
                      }
                    />
                    <label className="flex items-center gap-2 text-xs">
                      <Switch
                        aria-label={`Enable ${group.name}`}
                        checked={group.is_active !== false}
                        onCheckedChange={(is_active) =>
                          groupChange(group.id, { is_active })
                        }
                      />
                      Enabled
                    </label>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Delete ${group.name}`}
                      disabled={Boolean(referenced)}
                      title={
                        referenced
                          ? "Remove references to this group's captured values first."
                          : "Delete group"
                      }
                      onClick={async () => {
                        if (
                          await customConfirm(
                            `Remove ${group.name} and its conditions from this draft?`,
                            "Delete condition group",
                            "Delete",
                          )
                        )
                          onChange({ ...document, rule_groups: otherGroups });
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                  {ruleType === "ENTRY" && (
                    <SetupEditor
                      group={group}
                      onChange={(changes) => groupChange(group.id, changes)}
                      operators={groupOperators(group)}
                      timeframe={document.time_rule.candle_timeframe}
                    />
                  )}
                  {group.setup && (
                    <h3 className="text-sm font-semibold">
                      Enter on a later observation when
                    </h3>
                  )}
                  <ExpressionEditor
                    node={group.condition}
                    onChange={(condition) =>
                      groupChange(group.id, { condition })
                    }
                    operators={groupOperators(group)}
                    ruleType={ruleType}
                  />
                  {ruleType !== "ENTRY" &&
                    hasSeparateSignal &&
                    usesPosition &&
                    usesSignal && (
                      <p className="studio-context-note">
                        This rule mixes the owned position with Signal market
                        inputs. Check each source: an underlying index price and
                        an option premium use different price scales.
                      </p>
                    )}
                </div>
              </details>
            );
          })}
        </TabsContent>
      </Tabs>
      <details
        className="studio-disclosure studio-surface mt-3 p-3"
        data-studio-formulas
      >
        <summary>
          Reusable formulas ({Object.keys(document.expressions || {}).length})
        </summary>
        <div className="mt-3 space-y-3">
          <p className="studio-hint">
            Define a calculation once and reference it in conditions or
            captures.
          </p>
          <div className="flex flex-wrap gap-2">
            <Input
              aria-label="New formula name"
              placeholder="e.g. premium_strength"
              className="min-w-0 max-w-sm"
              maxLength={spec.constraints.name_length}
              value={formulaName}
              onChange={(event) => setFormulaName(event.target.value)}
            />
            <Button
              variant="outline"
              size="sm"
              disabled={
                Object.keys(document.expressions || {}).length >=
                operators.max_expressions
              }
              onClick={() => {
                const name = formulaName.trim();
                if (
                  !new RegExp(spec.patterns.name).test(name) ||
                  Object.hasOwn(document.expressions || {}, name)
                ) {
                  notify.error(
                    "Use a unique name starting with a letter, followed by letters, numbers or underscores.",
                  );
                  return;
                }
                onChange({
                  ...document,
                  expressions: { ...document.expressions, [name]: inputNode() },
                });
                setFormulaName("");
              }}
            >
              <Plus className="mr-1 h-4 w-4" />
              Add formula
            </Button>
          </div>
          {Object.entries(document.expressions || {}).map(([name, formula]) => {
            const other = Object.fromEntries(
              Object.entries(document.expressions).filter(
                ([key]) => key !== name,
              ),
            );
            const referenced =
              referencesFormula(document.rule_groups, name) ||
              referencesFormula(other, name) ||
              referencesFormula(document.initial_risk, name);
            return (
              <div key={name} className="space-y-2 border-t border-border pt-3">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="break-all font-mono text-sm font-semibold">
                    {name}
                  </h3>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Remove formula ${name}`}
                    disabled={referenced}
                    title={
                      referenced
                        ? "Remove this formula's references first."
                        : "Remove formula"
                    }
                    onClick={async () => {
                      if (
                        await customConfirm(
                          `Remove formula ${name}?`,
                          "Remove formula",
                          "Remove",
                        )
                      )
                        onChange({ ...document, expressions: other });
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                <NumberExpression
                  node={formula}
                  operators={{
                    ...operators,
                    default_timeframe: document.time_rule.candle_timeframe,
                    captures: [],
                    expressions: Object.keys(other),
                  }}
                  ruleType="ENTRY"
                  onChange={(next) =>
                    onChange({
                      ...document,
                      expressions: { ...document.expressions, [name]: next },
                    })
                  }
                />
              </div>
            );
          })}
        </div>
      </details>
    </section>
  );
}
StudioConditions.propTypes = {
  document: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  operators: PropTypes.object.isRequired,
  ruleType: PropTypes.string.isRequired,
  onRuleTypeChange: PropTypes.func.isRequired,
};
