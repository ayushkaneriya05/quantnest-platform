import PropTypes from "prop-types";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { useStrategySpecification } from "@/shared/context/EnumsContext";
import OperandSelector from "./OperandSelector";
import { customConfirm } from "@/shared/components/ui/custom-dialog";
import { rollingInputIssue } from "../studioPresentation";

export function StudioSelect({
  value,
  onChange,
  options,
  label,
  className = "",
  triggerText,
}) {
  return (
    <Select value={String(value ?? "")} onValueChange={onChange}>
      <SelectTrigger
        aria-label={label}
        className={`min-w-0 max-w-full ${className}`}
      >
        <SelectValue>{triggerText}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {options.map((item) => (
          <SelectItem
            key={item.value}
            value={String(item.value)}
            disabled={item.disabled}
          >
            {item.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
StudioSelect.propTypes = {
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onChange: PropTypes.func,
  options: PropTypes.array,
  label: PropTypes.string,
  className: PropTypes.string,
  triggerText: PropTypes.string,
};

export function NumberExpression({
  node,
  onChange,
  operators,
  ruleType,
  depth = 0,
  candleOnly = false,
}) {
  const { enums, operands, defaultParams, inputNode, numericArgument, spec } = useStrategySpecification();
  const window = operators.windows.find((item) => item.value === node.op);
  const insideWindow = candleOnly || Boolean(window);
  const rollingIssue = window
    ? rollingInputIssue(
        node.args?.[0],
        enums,
        operators.formulas,
        operators.default_timeframe,
      )
    : "";
  const replaceKind = async (op) => {
    if (op === node.op) return;
    if (
      node.op !== "input" &&
      ["input", "capture", "expression"].includes(op) &&
      !(await customConfirm(
        "Replace this calculation and its child inputs with one value?",
        "Replace expression",
        "Replace",
      ))
    )
      return;
    if (op === "input")
      return onChange({
        ...inputNode(),
        source: operators.default_source || spec.defaults.templates.input.source,
      });
    if (op === "expression") {
      return onChange({ op, name: operators.expressions?.[0] || "" });
    }
    if (op === "capture") {
      const first = operators.captures?.[0];
      return onChange({
        op,
        setup: first?.setup || "",
        name: first?.name || "",
      });
    }
    const window = (operators.windows || []).find((item) => item.value === op);
    const operation = window || operators.numeric.find((item) => item.value === op);
    onChange({
      op,
      ...(window ? { bars: window.default_bars } : {}),
      ...(window?.variance ? { ddof: window.default_ddof } : {}),
      args: Array.from({ length: operation.arity }, (_, i) =>
        i === 0 ? node : {
          ...numericArgument(),
          source: operators.default_source || spec.defaults.templates.input.source,
        },
      ),
    });
  };
  return (
    <div className="studio-value min-w-0 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {node.op === "input" && (
          <OperandSelector
            compact
            candleOnly={insideWindow}
            value={node.type}
            params={node.params}
            timeframe={node.timeframe}
            defaultTimeframe={operators.default_timeframe}
            ruleType={ruleType}
            hideTimeframe={node.type === "LTP"}
            onChangeType={async (type) => {
              if (
                node.type === "MATH_EXPRESSION" &&
                type !== node.type &&
                !(await customConfirm(
                  "Replace this math expression and its variables?",
                  "Replace expression",
                  "Replace",
                ))
              )
                return;
              onChange({
                ...node,
                type,
                params: defaultParams(type),
              });
            }}
            onChangeParams={(params) => onChange({ ...node, params })}
            onChangeTimeframe={(timeframe) => onChange({ ...node, timeframe })}
          />
        )}
        <StudioSelect
          value={node.op}
          onChange={replaceKind}
          label="Expression operation"
          options={[
            operators.nodes.find((item) => item.value === "input"),
            ...(operators.expressions?.length || node.op === "expression"
              ? [operators.nodes.find((item) => item.value === "expression")]
              : []),
            ...((!insideWindow && operators.captures?.length) ||
            node.op === "capture"
              ? [
                  {
                    value: "capture",
                    label: operators.nodes.find((item) => item.value === "capture").label,
                    disabled: insideWindow,
                  },
                ]
              : []),
            ...operators.numeric,
            ...(operators.windows || []),
          ].filter(
            (item) =>
              depth < operators.max_depth - 2 ||
              item.value === node.op ||
              ["input", "capture", "expression"].includes(item.value),
          )}
          triggerText={node.op === "input" ? "ƒx" : undefined}
          className={
            node.op === "input" ? "h-8 w-14 text-xs" : "h-8 w-48 text-xs"
          }
        />
        {node.op === "input" &&
          node.type !== "CONSTANT" &&
          operands[node.type]?.context !== "position" && (
            <StudioSelect
              value={node.source || spec.defaults.templates.input.source}
              label="Input market"
              options={(operators.source_roles || [])}
              onChange={(source) => onChange({ ...node, source })}
              className="w-44"
            />
          )}
        {node.op === "input" &&
          operands[node.type]?.context === "position" && (
            <span className="studio-input-context">
              This route’s traded position
            </span>
          )}
        {node.op === "input" && node.type === "CONSTANT" && (
          <span className="studio-input-context">
            Constant · no market source
          </span>
        )}
        {node.op === "input" && node.type === "LTP" && (
          <span className="studio-input-context">Live price</span>
        )}
        {node.op === "capture" && (
          <StudioSelect
            label="Captured value"
            className="sm:w-auto sm:max-w-80"
            value={JSON.stringify([node.setup, node.name])}
            options={(operators.captures || []).map((item) => ({
              value: JSON.stringify([item.setup, item.name]),
              label: item.label,
            }))}
            onChange={(value) => {
              const [setup, name] = JSON.parse(value);
              onChange({ op: "capture", setup, name });
            }}
          />
        )}
        {node.op === "expression" && (
          <StudioSelect
            label="Named formula"
            className="sm:w-auto sm:max-w-80"
            value={node.name}
            options={(operators.expressions || []).map((name) => ({
              value: name,
              label: name,
            }))}
            onChange={(name) => onChange({ op: "expression", name })}
          />
        )}
        {(operators.windows || []).some((item) => item.value === node.op) && (
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            {node.op === "lag" ? "Bars ago" : "Window bars"}
            <Input
              aria-label={node.op === "lag" ? "Lag bars" : "Window bars"}
              type="number"
              min={1}
              max={operators.max_window}
              step={1}
              className="w-24"
              value={node.bars}
              onChange={(event) =>
                onChange({ ...node, bars: Number(event.target.value) })
              }
            />
          </label>
        )}
        {(operators.windows || []).find((item) => item.value === node.op)
          ?.variance && (
          <StudioSelect
            label="Variance divisor"
            value={String(node.ddof ?? window.default_ddof)}
            options={operators.variance_divisors}
            className="h-8 w-44 text-xs"
            onChange={(value) => onChange({ ...node, ddof: Number(value) })}
          />
        )}
      </div>
      {window && (
        <div className="space-y-1 text-xs text-muted-foreground">
          {window.description && <p>{window.description.replaceAll("{bars}", String(node.bars))}</p>}
          {!["lag", "return_pct"].includes(node.op) && (
            <p>
              Includes the newest completed candle. Wrap it in Lag by bars (1)
              to use the previous window.
            </p>
          )}
          <p>
            This rolling calculation uses one market source and one candle
            timeframe. Live prices, position state and captured values cannot be
            used inside it. Separate rolling calculations can be combined
            outside the window.
          </p>
          {rollingIssue && (
            <p
              role="alert"
              className="border-l-2 border-destructive pl-2 text-destructive"
            >
              {rollingIssue}
            </p>
          )}
        </div>
      )}
      {node.args && (
        <div className="grid gap-2 border-l border-border pl-3">
          {node.args.map((arg, index) => (
            <div key={index} className="min-w-0 space-y-1">
              <p className="studio-hint">
                {node.op === "subtract"
                  ? index === 0
                    ? "First value"
                    : "Subtract this value"
                  : node.op === "divide"
                    ? index === 0
                      ? "Numerator"
                      : "Denominator"
                    : `Input ${index + 1}`}
              </p>
              <NumberExpression
                node={arg}
                operators={operators}
                ruleType={ruleType}
                depth={depth + 1}
                candleOnly={insideWindow}
                onChange={(next) =>
                  onChange({
                    ...node,
                    args: node.args.map((value, i) =>
                      i === index ? next : value,
                    ),
                  })
                }
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
NumberExpression.propTypes = {
  node: PropTypes.object,
  onChange: PropTypes.func,
  operators: PropTypes.object,
  ruleType: PropTypes.string,
  depth: PropTypes.number,
  candleOnly: PropTypes.bool,
};

export default function ExpressionEditor({
  node,
  onChange,
  operators,
  ruleType,
  depth = 0,
}) {
  const { enums, comparisonNode } = useStrategySpecification();
  if (node.op === "compare")
    return (
      <div className="studio-comparison min-w-0 rounded-md bg-background/40 p-2.5">
        <div className="studio-comparison-fields grid min-w-0 items-start gap-2">
          <NumberExpression
            node={node.left}
            onChange={(left) => onChange({ ...node, left })}
            operators={operators}
            ruleType={ruleType}
            depth={depth + 1}
          />
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <StudioSelect
              value={node.comparison}
              onChange={(comparison) => onChange({ ...node, comparison })}
              options={enums.ComparisonOperator || []}
              label="Comparison"
              className="h-9 w-full text-xs"
            />
            <Button
              size="sm"
              variant="ghost"
              className="min-w-0 text-xs"
              aria-label="Combine with another condition"
              disabled={depth >= operators.max_depth - 3}
              onClick={() =>
                onChange({ op: "all", args: [node, comparisonNode()] })
              }
            >
              <Plus className="mr-1 h-3.5 w-3.5" /> Wrap in group
            </Button>
          </div>
          <NumberExpression
            node={node.right}
            onChange={(right) => onChange({ ...node, right })}
            operators={operators}
            ruleType={ruleType}
            depth={depth + 1}
          />
        </div>
      </div>
    );
  const update = (index, value) =>
    onChange({
      ...node,
      args: node.args.map((item, i) => (i === index ? value : item)),
    });
  const remove = async (index) => {
    if (
      !(await customConfirm(
        "Remove this condition and any nested inputs from this draft?",
        "Remove condition",
        "Remove",
      ))
    )
      return;
    const args = node.args.filter((_, i) => i !== index);
    onChange({
      ...node,
      args,
      ...(node.op === "at_least"
        ? { count: Math.min(node.count, Math.max(1, args.length)) }
        : {}),
    });
  };
  return (
    <div className="studio-logic min-w-0 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <StudioSelect
          value={node.op}
          label="Combine conditions in this group"
          className="w-48"
          options={operators.logic}
          onChange={(op) =>
            onChange({
              op,
              args: op === "not" ? [{ ...node }] : node.args,
              ...(op === "at_least" ? { count: 1 } : {}),
            })
          }
        />
        {node.op === "at_least" && (
          <Input
            aria-label="Required matching conditions"
            className="w-20"
            type="number"
            min={1}
            max={node.args.length}
            value={node.count}
            onChange={(event) =>
              onChange({ ...node, count: Number(event.target.value) })
            }
          />
        )}
        <span className="text-xs text-muted-foreground">
          {node.op === "not"
            ? "Invert the condition; unavailable data stays unavailable."
            : node.op === "at_least"
              ? `of ${node.args.length} conditions must match`
              : node.op === "all"
                ? "All conditions must match"
                : "Any condition may match"}
        </span>
        {node.args.length === 1 && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onChange(node.args[0])}
          >
            Remove group
          </Button>
        )}
      </div>
      <div className="studio-logic-children min-w-0 space-y-2 border-l border-border pl-2 sm:pl-3">
        {node.args.map((child, index) => (
          <div key={index} className="relative space-y-1">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Condition {index + 1}</span>
              {node.op !== "not" && node.args.length > 1 && (
                <Button
                  size="icon"
                  variant="ghost"
                  className="w-7"
                  aria-label={`Remove condition ${index + 1}`}
                  onClick={() => remove(index)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
            <ExpressionEditor
              node={child}
              onChange={(value) => update(index, value)}
              operators={operators}
              ruleType={ruleType}
              depth={depth + 1}
            />
          </div>
        ))}
      </div>
      {node.op !== "not" && depth < operators.max_depth - 3 && (
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              onChange({ ...node, args: [...node.args, comparisonNode()] })
            }
          >
            <Plus className="mr-1 h-4 w-4" />
            Condition
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              onChange({
                ...node,
                args: [...node.args, { op: "any", args: [comparisonNode()] }],
              })
            }
          >
            <Plus className="mr-1 h-4 w-4" />
            Nested group
          </Button>
        </div>
      )}
    </div>
  );
}
ExpressionEditor.propTypes = {
  node: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  operators: PropTypes.object.isRequired,
  ruleType: PropTypes.string,
  depth: PropTypes.number,
};
