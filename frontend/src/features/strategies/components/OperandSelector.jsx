import { Button } from "@/shared/components/ui/button";
import PropTypes from "prop-types";
import { useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectGroup,
  SelectLabel,
} from "@/shared/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/shared/components/ui/popover";
import {
  Dialog,
  DialogContent,
  DialogTrigger,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Input } from "@/shared/components/ui/input";
import { Settings, Clock } from "lucide-react";
import { useStrategySpecification } from "@/shared/context/EnumsContext";
import MathExpressionBuilder from "@/features/strategies/components/MathExpressionBuilder.jsx";

export default function OperandSelector({
  value,
  params,
  timeframe,
  onChangeType,
  onChangeParams,
  onChangeTimeframe,
  hideTimeframe = false,
  placeholder = "Select Operand",
  ruleType,
  allowedValues,
  compact = false,
  defaultTimeframe,
  candleOnly = false,
}) {
  const { enums, spec, operandOptions = [], parameterConfig = {} } = useStrategySpecification();
  const [popoverOpen, setPopoverOpen] = useState(false);

  const context = ruleType === "ENTRY" ? 'entry' : 'exit';
  const options = operandOptions.filter((item) => item.allowed_in[context] &&
    (!allowedValues || allowedValues.includes(item.value)));
  const mathVariableTypes = options.filter((item) => item.allowed_in.math &&
    (!candleOnly || item.allowed_in.rolling)).map((item) => item.value);
  const groupedOptions = Object.fromEntries((spec?.conditions.groups || []).map((group) => [
    group.label, options.filter((item) => group.operands.includes(item.value)),
  ]));

  const currentOption = options.find((option) => option.value === value);
  const paramConfig = (parameterConfig[value] || []).filter((field) => field.editable !== false);

  const getParamValue = (param) => {
    const current = params?.[param.key] ?? param.default;
    return param.type === "source" ? current.toUpperCase() : current;
  };

  // Format params for badge display
  const formatParams = () => {
    if (!paramConfig.length || !params) return "";
    if (value === "CONSTANT") return params.value?.toString() || "0";
    if (value === "MATH_EXPRESSION") {
      const expression = params.expression?.expression;
      return expression ? `(${expression})` : "";
    }
    const visible = paramConfig.filter(
      (param) => param.key !== "shift" || getParamValue(param),
    );
    if (!visible.length) return "Parameters";
    return `(${visible
      .map((param) => {
        const current = getParamValue(param);
        return (
          param.options?.find((option) => option.value === current)?.label ||
          current
        );
      })
      .join(", ")})`;
  };

  const handleParamChange = (key, val, isString = false) => {
    // Preserve numeric text while editing so negative values can be typed
    // through the intermediate "-" state before being saved.
    const parsed = isString ? val : val === "" ? null : parseFloat(val);
    onChangeParams({ ...(params || {}), [key]: parsed });
  };

  return (
    <div
      className={`flex min-w-0 max-w-full flex-wrap items-center gap-1.5 ${compact ? "operand-selector-compact" : ""}`}
    >
      {/* Type Selector */}
      <div className="min-w-0">
        <Select value={value || ""} onValueChange={onChangeType}>
          <SelectTrigger
            aria-label={compact ? "Value or indicator" : placeholder}
            className="w-auto min-w-[120px] max-w-[min(20rem,calc(100vw_-_5rem))] text-xs"
          >
            <SelectValue placeholder={placeholder} />
          </SelectTrigger>
          <SelectContent className="max-h-[300px]">
            {Object.entries(groupedOptions).map(
              ([groupName, groupOptions]) =>
                groupOptions.length > 0 && (
                  <SelectGroup key={groupName}>
                    <SelectLabel className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider">
                      {groupName}
                    </SelectLabel>
                    {groupOptions.map((opt) => (
                      <SelectItem
                        key={opt.value}
                        value={opt.value}
                        disabled={
                          candleOnly &&
                          !opt.allowed_in.rolling
                        }
                      >
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                ),
            )}
          </SelectContent>
        </Select>
      </div>

      {compact && value === "CONSTANT" && (
        <Input
          aria-label="Constant value"
          type="number"
          className="w-28"
          step="any"
          value={params?.value ?? ""}
          onChange={(event) => handleParamChange("value", event.target.value)}
        />
      )}

      {/* Parameter Settings Modal/Popover */}
      {value &&
        paramConfig.length > 0 &&
        !(compact && value === "CONSTANT") &&
        (paramConfig.some((p) => p.type === "math") ? (
          <Dialog open={popoverOpen} onOpenChange={setPopoverOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" type="button"
                aria-label={`Edit ${currentOption?.label} parameters`}
                className="max-w-[200px] text-xs"
              >
                {value === "CONSTANT" ? (
                  formatParams()
                ) : (
                  <span className="truncate">
                    {formatParams() || "Parameters"}
                  </span>
                )}
                <Settings className="h-3 w-3 ml-0.5 opacity-70 shrink-0" />
              </Button>
            </DialogTrigger>
            <DialogContent className="operand-parameters w-[calc(100%_-_2rem)] max-w-lg bg-card border border-border shadow-2xl p-3">
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-border">
                  <DialogTitle className="text-sm font-semibold text-foreground">
                    Build Math Expression
                  </DialogTitle>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {paramConfig.map((param) => (
                    <div key={param.key} className="col-span-2 w-full pt-1">
                      <MathExpressionBuilder
                        value={
                          params?.[param.key] || {
                            expression: "",
                            variables: {},
                          }
                        }
                                                allowedVariableTypes={mathVariableTypes}
                        ruleType={ruleType}
                        onChange={(val) =>
                          handleParamChange(param.key, val, true)
                        }
                      />
                    </div>
                  ))}
                </div>
              </div>
            </DialogContent>
          </Dialog>
        ) : (
          <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
            <PopoverTrigger asChild>
              <Button variant="outline" type="button"
                aria-label={`Edit ${currentOption?.label} parameters`}
                className="max-w-[200px] text-xs"
              >
                {value === "CONSTANT" ? (
                  formatParams()
                ) : (
                  <span className="truncate">
                    {formatParams() || "Parameters"}
                  </span>
                )}
                <Settings className="h-3 w-3 ml-0.5 opacity-70 shrink-0" />
              </Button>
            </PopoverTrigger>
            <PopoverContent
              className="operand-parameters w-64 max-w-[calc(100vw_-_2rem)] p-3 bg-card border border-border shadow-xl"
              sideOffset={5}
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-border">
                  <h4 className="text-xs font-semibold text-foreground">
                    Configure Parameters
                  </h4>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {paramConfig.map((param) => (
                    <div
                      key={param.key}
                      className={
                        param.type === "source" &&
                        parameterConfig[getParamValue(param)]
                          ? "col-span-2 space-y-1"
                          : "space-y-1"
                      }
                    >
                      <label className="text-[10px] text-muted-foreground font-medium">
                        {param.label}
                      </label>
                      {param.type === "source" ? (
                        <Select
                          value={getParamValue(param)}
                          onValueChange={(v) =>
                            handleParamChange(param.key, v, true)
                          }
                        >
                          <SelectTrigger className="text-xs bg-muted/60 border-border text-foreground">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectGroup>
                              <SelectLabel>Price</SelectLabel>
                              {param.options
                                .filter((source) => source.group === "Price")
                                .map((source) => (
                                  <SelectItem
                                    key={source.value}
                                    value={source.value}
                                  >
                                    {source.label}
                                  </SelectItem>
                                ))}
                            </SelectGroup>
                            <SelectGroup>
                              <SelectLabel>Indicators</SelectLabel>
                              {param.options
                                .filter(
                                  (source) => source.group === "Indicators",
                                )
                                .map((source) => (
                                  <SelectItem
                                    key={source.value}
                                    value={source.value}
                                  >
                                    {source.label}
                                  </SelectItem>
                                ))}
                            </SelectGroup>
                          </SelectContent>
                        </Select>
                      ) : param.type === "enum" ? (
                        <Select
                          value={getParamValue(param)}
                          onValueChange={(v) =>
                            handleParamChange(param.key, v, true)
                          }
                        >
                          <SelectTrigger className="text-xs bg-muted/60 border-border text-foreground">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {(enums[param.enumKey] || []).map((opt) => (
                              <SelectItem key={opt.value} value={opt.value}>
                                {opt.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : param.type === "select" ? (
                        <Select
                          value={getParamValue(param)}
                          onValueChange={(v) =>
                            handleParamChange(param.key, v, true)
                          }
                        >
                          <SelectTrigger className="text-xs bg-muted/60 border-border text-foreground">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {param.options.map((opt) => (
                              <SelectItem key={opt.value} value={opt.value}>
                                {opt.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        <Input
                          type={
                            param.key === "option_type" || value === "CONSTANT"
                              ? "text"
                              : "number"
                          }
                          inputMode={
                            value === "CONSTANT" ? "decimal" : undefined
                          }
                          value={params?.[param.key] ?? param.default}
                          onChange={(e) =>
                            handleParamChange(
                              param.key,
                              e.target.value,
                              param.key === "option_type" ||
                                value === "CONSTANT",
                            )
                          }
                          min={param.min}
                          max={param.max ?? undefined}
                          step={param.step ?? 1}
                          className="text-xs bg-muted/60 border-border text-foreground"
                        />
                      )}

                      {param.type === "source" &&
                        parameterConfig[getParamValue(param)] && (
                          <div className="mt-2 p-2 border border-border rounded bg-muted/40">
                            <span className="text-[10px] text-brand font-bold mb-1 block">
                              Source ({getParamValue(param)}) Settings
                            </span>
                            <div className="grid grid-cols-2 gap-2">
                              {parameterConfig[getParamValue(param)]
                                .filter(
                                  (sourceParam) =>
                                    sourceParam.type !== "source" &&
                                    sourceParam.key !== "shift",
                                )
                                .map((sp) => (
                                  <div
                                    key={`source_${sp.key}`}
                                    className="space-y-1"
                                  >
                                    <label className="text-[10px] text-muted-foreground font-medium">
                                      {sp.label}
                                    </label>
                                    {sp.type === "select" ? (
                                      <Select
                                        value={
                                          params?.source_params?.[sp.key] ??
                                          sp.default
                                        }
                                        onValueChange={(selected) =>
                                          onChangeParams({
                                            ...params,
                                            source_params: {
                                              ...(params?.source_params || {}),
                                              [sp.key]: selected,
                                            },
                                          })
                                        }
                                      >
                                        <SelectTrigger className="text-xs bg-muted/60 border-border text-foreground">
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          {sp.options.map((option) => (
                                            <SelectItem
                                              key={option.value}
                                              value={option.value}
                                            >
                                              {option.label}
                                            </SelectItem>
                                          ))}
                                        </SelectContent>
                                      </Select>
                                    ) : sp.type === "enum" ? (
                                      <Select
                                        value={
                                          params?.source_params?.[sp.key] ??
                                          sp.default
                                        }
                                        onValueChange={(selected) =>
                                          onChangeParams({
                                            ...params,
                                            source_params: {
                                              ...(params?.source_params || {}),
                                              [sp.key]: selected,
                                            },
                                          })
                                        }
                                      >
                                        <SelectTrigger className="text-xs bg-muted/60 border-border text-foreground">
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          {(enums[sp.enumKey] || []).map(
                                            (option) => (
                                              <SelectItem
                                                key={option.value}
                                                value={option.value}
                                              >
                                                {option.label}
                                              </SelectItem>
                                            ),
                                          )}
                                        </SelectContent>
                                      </Select>
                                    ) : (
                                      <Input
                                        type="number"
                                        value={
                                          params?.source_params?.[sp.key] ??
                                          sp.default
                                        }
                                        min={sp.min}
                                        max={sp.max ?? undefined}
                                        step={sp.step ?? 1}
                                        onChange={(e) => {
                                          const val =
                                            e.target.value === ""
                                              ? null
                                              : parseFloat(e.target.value);
                                          onChangeParams({
                                            ...params,
                                            source_params: {
                                              ...(params?.source_params || {}),
                                              [sp.key]: val,
                                            },
                                          });
                                        }}
                                        className="text-xs bg-muted/60 border-border text-foreground"
                                      />
                                    )}
                                  </div>
                                ))}
                            </div>
                          </div>
                        )}
                    </div>
                  ))}
                </div>
              </div>
            </PopoverContent>
          </Popover>
        ))}

      {/* Timeframe Selector */}
      {!hideTimeframe && currentOption?.supports_timeframe && (
        <div className="min-w-0">
          <Select
            value={timeframe || "NONE"}
            onValueChange={(v) => onChangeTimeframe(v === "NONE" ? null : v)}
          >
            <SelectTrigger
              aria-label="Input timeframe"
              className="w-auto text-xs"
            >
              <Clock className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
              <SelectValue placeholder="Default TF">
                {compact
                  ? timeframe
                    ? `Override · ${timeframe}`
                    : `Default · ${defaultTimeframe || "TF"}`
                  : undefined}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="NONE">
                {defaultTimeframe
                  ? `Default · ${defaultTimeframe}`
                  : "Default TF"}
              </SelectItem>
              {(enums.CandleTimeframe || []).map((tf) => (
                <SelectItem key={tf.value} value={tf.value}>
                  {tf.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
    </div>
  );
}

OperandSelector.propTypes = {
  ...OperandSelector.propTypes,
  allowedValues: PropTypes.array,
  hideTimeframe: PropTypes.bool,
  onChangeParams: PropTypes.func,
  onChangeTimeframe: PropTypes.func,
  onChangeType: PropTypes.func,
  params: PropTypes.object,
  placeholder: PropTypes.string,
  ruleType: PropTypes.string,
  timeframe: PropTypes.string,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  compact: PropTypes.bool,
  defaultTimeframe: PropTypes.string,
  candleOnly: PropTypes.bool,
};
