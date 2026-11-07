import PropTypes from "prop-types";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { useStrategySpecification } from "@/shared/context/EnumsContext";
import ExpressionEditor, {
  NumberExpression,
  StudioSelect,
} from "./ExpressionEditor";
import { customConfirm } from "@/shared/components/ui/custom-dialog";

export default function SetupEditor({ group, onChange, operators, timeframe }) {
  const { enums, spec, inputNode, comparisonNode, captureSetup } = useStrategySpecification();
  const setup = group.setup;
  const pure = { ...operators, captures: [] };
  const change = (values) => onChange({ setup: { ...setup, ...values } });
  if (!setup)
    return (
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-2">
        <div>
          <p className="text-sm font-medium">Capture & confirmation: Off</p>
          {operators.setup_allowed === false && (
            <p className="studio-hint mt-1">
              Use one enabled Entry group for capture. Combine its filters or
              disable the other groups first.
            </p>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          aria-label="Configure capture and confirmation"
          disabled={operators.setup_allowed === false}
          title={
            operators.setup_allowed === false
              ? "Capture & confirmation needs one enabled Entry group. Combine filters inside that group or disable the other Entry groups first."
              : undefined
          }
          onClick={async () => {
            if (
              !(await customConfirm(
                "Use the current condition to arm a setup, remember its high/low, then enter on a later confirmation? You can edit each phase before saving.",
                "Configure capture & confirmation",
                "Configure",
              ))
            )
              return;
            onChange(captureSetup(group, timeframe));
          }}
        >
          Configure
        </Button>
      </div>
    );
  return (
    <div className="studio-setup space-y-3 border-l-2 border-border pl-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">Signal → remember → confirm → enter</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            One active setup per instrument. Each phase needs a later
            observation. A new occurrence needs a new arming edge.
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          disabled={operators.setup_referenced}
          aria-label="Use simple condition"
          title={
            operators.setup_referenced
              ? "Remove other groups' references to these captures first."
              : undefined
          }
          onClick={async () => {
            if (
              await customConfirm(
                "Restore the arming condition as a simple entry condition? This removes captured values, confirmations, invalidation and setup expiry from this group.",
                "Remove capture setup",
                "Use simple condition",
              )
            )
              onChange({ setup: undefined, condition: setup.arm });
          }}
        >
          Use simple condition
        </Button>
      </div>
      <section className="space-y-2">
        <h4 className="text-sm font-semibold">1. Arm when</h4>
        <ExpressionEditor
          node={setup.arm}
          onChange={(arm) => change({ arm })}
          operators={pure}
          ruleType="ENTRY"
        />
      </section>
      <section className="space-y-3">
        <h4 className="text-sm font-semibold">2. Remember these values</h4>
        <p className="text-xs text-muted-foreground">
          Values freeze at arming and remain available to exit rules while the
          position is open.
        </p>
        {Object.entries(setup.captures).map(([name, value]) => (
          <div key={name} className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-xs">{name}</span>
              <Button
                size="icon"
                variant="ghost"
                aria-label={`Remove ${name}`}
                disabled={operators.capture_referenced?.(name)}
                title={
                  operators.capture_referenced?.(name)
                    ? "Remove references to this captured value first."
                    : undefined
                }
                onClick={async () => {
                  if (
                    !(await customConfirm(
                      `Remove captured value ${name}?`,
                      "Remove captured value",
                      "Remove",
                    ))
                  )
                    return;
                  change({
                    captures: Object.fromEntries(
                      Object.entries(setup.captures).filter(
                        ([key]) => key !== name,
                      ),
                    ),
                  });
                }}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
            <NumberExpression
              node={value}
              onChange={(next) =>
                change({ captures: { ...setup.captures, [name]: next } })
              }
              operators={pure}
              ruleType="ENTRY"
            />
          </div>
        ))}
        <Button
          variant="outline"
          size="sm"
          disabled={Object.keys(setup.captures).length >= spec.setup.constraints.captures}
          onClick={() => {
            let index = 1;
            while (`value_${index}` in setup.captures) index++;
            change({
              captures: { ...setup.captures, [`value_${index}`]: inputNode() },
            });
          }}
        >
          <Plus className="mr-1 h-4 w-4" />
          Remember another value
        </Button>
      </section>
      <section className="space-y-3">
        <h4 className="text-sm font-semibold">
          3. Wait for these steps in order
        </h4>
        {setup.steps.map((condition, index) => (
          <div key={index} className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                Confirmation {index + 1}
              </span>
              <Button
                size="icon"
                variant="ghost"
                aria-label={`Remove confirmation ${index + 1}`}
                onClick={async () => {
                  if (
                    await customConfirm(
                      "Remove this intermediate confirmation?",
                      "Remove confirmation",
                      "Remove",
                    )
                  )
                    change({
                      steps: setup.steps.filter((_, i) => i !== index),
                    });
                }}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
            <ExpressionEditor
              node={condition}
              onChange={(next) =>
                change({
                  steps: setup.steps.map((item, i) =>
                    i === index ? next : item,
                  ),
                })
              }
              operators={operators}
              ruleType="ENTRY"
            />
          </div>
        ))}
        <Button
          variant="outline"
          size="sm"
          disabled={setup.steps.length >= spec.setup.constraints.steps}
          onClick={() => change({ steps: [...setup.steps, comparisonNode()] })}
        >
          <Plus className="mr-1 h-4 w-4" />
          Intermediate confirmation
        </Button>
      </section>
      <section className="space-y-3">
        <h4 className="text-sm font-semibold">Cancel the setup when</h4>
        {setup.invalidate ? (
          <>
            <ExpressionEditor
              node={setup.invalidate}
              onChange={(invalidate) => change({ invalidate })}
              operators={operators}
              ruleType="ENTRY"
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={async () => {
                if (
                  await customConfirm(
                    "Remove the setup invalidation condition?",
                    "Remove invalidation",
                    "Remove",
                  )
                )
                  change({ invalidate: null });
              }}
            >
              Remove invalidation condition
            </Button>
          </>
        ) : (
          <Button
            variant="outline"
            size="sm"
            onClick={() => change({ invalidate: comparisonNode() })}
          >
            Add invalidation condition
          </Button>
        )}
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span>Expire at the completion of</span>
          <Input
            aria-label="Setup expiry bars"
            type="number"
            min="1"
            max={spec.setup.constraints.expiry_bars}
            className="w-20"
            value={setup.expires_after_bars}
            onChange={(event) =>
              change({ expires_after_bars: Number(event.target.value) })
            }
          />
          <StudioSelect
            label="Setup expiry timeframe"
            options={enums.CandleTimeframe || []}
            value={setup.timeframe}
            onChange={(value) => change({ timeframe: value })}
            className="w-32"
          />
          <span>new bars</span>
        </div>
        <p className="text-xs text-muted-foreground">
          Expiry wins at the boundary. Pausing or losing observations resets an
          unfilled setup; a filled position keeps its captured protection
          values.
        </p>
      </section>
    </div>
  );
}
SetupEditor.propTypes = {
  group: PropTypes.object,
  onChange: PropTypes.func,
  operators: PropTypes.object,
  timeframe: PropTypes.string,
};
