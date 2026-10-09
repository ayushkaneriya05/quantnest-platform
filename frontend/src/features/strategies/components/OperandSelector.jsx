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
} from "@/shared/components/ui/dialog";
import { Input } from "@/shared/components/ui/input";
import { Settings, Clock } from "lucide-react";
import { useEnums } from "@/shared/context/EnumsContext";
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
}) {
  const { enums } = useEnums();
  const [popoverOpen, setPopoverOpen] = useState(false);

  // Group enums for better selection
  const options = (enums.OperandType || []).filter(
    (option) => !allowedValues || allowedValues.includes(option.value),
  );
  const parameterConfig = enums.OperandParameterConfig || {};
  const mathVariableTypes =
    enums.MathExpressionOperandTypes?.[ruleType || "ENTRY"] || [];
  const positionStateTypes = enums.OperandGroups?.["Position State (Exit)"] || [];

  const groupedOptions = Object.fromEntries(
    Object.entries(enums.OperandGroups || {})
      .filter(
        ([groupName]) =>
          groupName !== "Position State (Exit)" || ruleType !== "ENTRY",
      )
      .map(([groupName, values]) => [
        groupName,
        options.filter((option) => values.includes(option.value)),
      ]),
  );

  const currentOption = options.find((option) => option.value === value);
  const paramConfig = parameterConfig[value] || [];

  // Format params for badge display
  const formatParams = () => {
    if (!paramConfig.length || !params) return "";
    if (value === "CONSTANT") return params.value?.toString() || "0";
    if (value === "MATH_EXPRESSION") {
      const expression =
        typeof params.expression === "string"
          ? params.expression
          : params.expression?.expression;
      return expression ? `(${expression})` : "";
    }
    return `(${paramConfig.map((p) => params[p.key] ?? p.default).join(", ")})`;
  };

  const handleParamChange = (key, val, isString = false) => {
    // Preserve numeric text while editing so negative values can be typed
    // through the intermediate "-" state before being saved.
    const parsed = isString ? val : val === "" ? null : parseFloat(val);
    onChangeParams({ ...(params || {}), [key]: parsed });
  };

  const getParamValue = (param) => {
    return params?.[param.key] ?? param.default;
  };

  return (
    <div className="flex min-w-0 max-w-full flex-wrap items-center gap-2 sm:gap-1">
      {/* Type Selector */}
      <div className="flex items-center bg-muted/40 rounded-lg p-0.5 border border-border">
        <Select value={value || ""} onValueChange={onChangeType}>
          <SelectTrigger
            className={`w-auto min-w-[120px] max-w-[min(20rem,calc(100vw_-_5rem))] bg-transparent border-none hover:bg-muted/50 text-xs min-h-10 px-2.5 sm:min-h-7 shadow-none focus:ring-0 ${value ? "text-indigo-700 dark:text-indigo-300" : "text-muted-foreground"} font-semibold`}
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
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                ),
            )}
          </SelectContent>
        </Select>
      </div>

      {/* Parameter Settings Modal/Popover */}
      {value &&
        paramConfig.length > 0 &&
        (paramConfig.some((p) => p.type === "math") ? (
          <Dialog open={popoverOpen} onOpenChange={setPopoverOpen}>
            <DialogTrigger asChild>
              <button className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-bold tracking-wider rounded-md bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 hover:bg-indigo-500/20 transition-colors border border-indigo-500/20 cursor-pointer max-w-[200px] truncate">
                {value === "CONSTANT" ? (
                  formatParams()
                ) : (
                  <span className="truncate">
                    {currentOption?.label} {formatParams()}
                  </span>
                )}
                <Settings className="h-3 w-3 ml-0.5 opacity-70 shrink-0" />
              </button>
            </DialogTrigger>
            <DialogContent className="w-[calc(100%_-_2rem)] max-w-lg bg-card border border-border shadow-2xl p-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-border">
                  <h4 className="text-xs font-semibold text-foreground">
                    Build Math Expression
                  </h4>
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
                        parameterConfig={parameterConfig}
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
              <button className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-bold tracking-wider rounded-md bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 hover:bg-indigo-500/20 transition-colors border border-indigo-500/20 cursor-pointer max-w-[200px] truncate">
                {value === "CONSTANT" ? (
                  formatParams()
                ) : (
                  <span className="truncate">
                    {currentOption?.label} {formatParams()}
                  </span>
                )}
                <Settings className="h-3 w-3 ml-0.5 opacity-70 shrink-0" />
              </button>
            </PopoverTrigger>
            <PopoverContent
              className="w-64 max-w-[calc(100vw_-_2rem)] p-3 bg-card border border-border shadow-xl"
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
                        parameterConfig[params?.[param.key]]
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
                          <SelectTrigger className="h-7 text-xs bg-muted/60 border-border text-foreground focus:ring-0">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectGroup>
                              <SelectLabel>Price</SelectLabel>
                              {param.options
                                .filter((source) => source.group === "Price")
                                .map((source) => (
                                  <SelectItem key={source.value} value={source.value}>
                                    {source.label}
                                  </SelectItem>
                                ))}
                            </SelectGroup>
                            <SelectGroup>
                              <SelectLabel>Indicators</SelectLabel>
                              {param.options
                                .filter((source) => source.group === "Indicators")
                                .map((source) => (
                                  <SelectItem key={source.value} value={source.value}>
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
                          <SelectTrigger className="h-7 text-xs bg-muted/60 border-border text-foreground focus:ring-0">
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
                          <SelectTrigger className="h-7 text-xs bg-muted/60 border-border text-foreground focus:ring-0">
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
                          className="h-7 text-xs bg-muted/60 border-border text-foreground"
                        />
                      )}

                      {param.type === "source" &&
                        parameterConfig[params?.[param.key]] && (
                          <div className="mt-2 p-2 border border-border rounded bg-muted/40">
                            <span className="text-[10px] text-indigo-700 dark:text-indigo-400 font-bold mb-1 block">
                              Source ({params?.[param.key]}) Settings
                            </span>
                            <div className="grid grid-cols-2 gap-2">
                              {parameterConfig[params?.[param.key]]
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
                                        value={params?.source_params?.[sp.key] ?? sp.default}
                                        onValueChange={(selected) => onChangeParams({
                                          ...params,
                                          source_params: { ...(params?.source_params || {}), [sp.key]: selected },
                                        })}
                                      >
                                        <SelectTrigger className="h-7 text-xs bg-muted/60 border-border text-foreground focus:ring-0">
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          {sp.options.map((option) => (
                                            <SelectItem key={option.value} value={option.value}>
                                              {option.label}
                                            </SelectItem>
                                          ))}
                                        </SelectContent>
                                      </Select>
                                    ) : sp.type === "enum" ? (
                                      <Select
                                        value={params?.source_params?.[sp.key] ?? sp.default}
                                        onValueChange={(selected) => onChangeParams({
                                          ...params,
                                          source_params: { ...(params?.source_params || {}), [sp.key]: selected },
                                        })}
                                      >
                                        <SelectTrigger className="h-7 text-xs bg-muted/60 border-border text-foreground focus:ring-0">
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          {(enums[sp.enumKey] || []).map((option) => (
                                            <SelectItem key={option.value} value={option.value}>
                                              {option.label}
                                            </SelectItem>
                                          ))}
                                        </SelectContent>
                                      </Select>
                                    ) : (
                                      <Input
                                        type="number"
                                        value={params?.source_params?.[sp.key] ?? sp.default}
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
                                            source_params: { ...(params?.source_params || {}), [sp.key]: val },
                                          });
                                        }}
                                        className="h-7 text-xs bg-muted/60 border-border text-foreground"
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
      {!hideTimeframe &&
        value &&
        value !== "CONSTANT" &&
        !positionStateTypes.includes(value) && (
          <div className="flex items-center gap-1.5 bg-muted/30 rounded-md px-1.5 py-0.5 border border-border">
            <Clock className="h-3 w-3 text-muted-foreground" />
            <Select
              value={timeframe || "NONE"}
              onValueChange={(v) => onChangeTimeframe(v === "NONE" ? null : v)}
            >
              <SelectTrigger className="w-auto bg-transparent border-none hover:bg-muted/50 text-[10px] h-5 px-1 shadow-none focus:ring-0 text-muted-foreground p-0 font-medium">
                <SelectValue placeholder="Default TF" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="NONE">Default TF</SelectItem>
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
