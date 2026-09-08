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
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import { Settings, Clock } from "lucide-react";
import { useEnums } from "@/shared/context/EnumsContext";
import MathExpressionBuilder from "./MathExpressionBuilder";

export const PARAM_CONFIG = {
  // Price Data & Basic
  // No params needed for base price data since shift is auto-appended

  // Indicators
  SMA: [
    { key: "period", label: "Period", default: 14 },
    { key: "source", label: "Source", type: "source", default: "close" },
  ],
  EMA: [
    { key: "period", label: "Period", default: 14 },
    { key: "source", label: "Source", type: "source", default: "close" },
  ],
  WMA: [
    { key: "period", label: "Period", default: 14 },
    { key: "source", label: "Source", type: "source", default: "close" },
  ],
  HMA: [
    { key: "period", label: "Period", default: 14 },
    { key: "source", label: "Source", type: "source", default: "close" },
  ],
  ALMA: [
    { key: "period", label: "Period", default: 14 },
    { key: "source", label: "Source", type: "source", default: "close" },
  ],
  KAMA: [
    { key: "period", label: "Period", default: 14 },
    { key: "source", label: "Source", type: "source", default: "close" },
  ],
  DEMA: [
    { key: "period", label: "Period", default: 14 },
    { key: "source", label: "Source", type: "source", default: "close" },
  ],
  TEMA: [
    { key: "period", label: "Period", default: 14 },
    { key: "source", label: "Source", type: "source", default: "close" },
  ],
  RSI: [
    { key: "period", label: "Period", default: 14 },
    { key: "source", label: "Source", type: "source", default: "close" },
  ],
  ROC: [
    { key: "period", label: "Period", default: 9 },
    { key: "source", label: "Source", type: "source", default: "close" },
  ],
  CCI: [{ key: "period", label: "Period", default: 20 }],
  ADX: [
    { key: "period", label: "Period", default: 14 },
    {
      key: "output_line",
      label: "Output",
      type: "select",
      options: ["ADX", "+DI", "-DI"],
      default: "ADX",
    },
  ],
  DMI: [
    { key: "period", label: "Period", default: 14 },
    {
      key: "output_line",
      label: "Output",
      type: "select",
      options: ["ADX", "+DI", "-DI"],
      default: "ADX",
    },
  ],
  MACD: [
    { key: "fast_period", label: "Fast", default: 12 },
    { key: "slow_period", label: "Slow", default: 26 },
    { key: "signal_period", label: "Sig", default: 9 },
    {
      key: "output_line",
      label: "Output",
      type: "select",
      options: ["MACD_LINE", "MACD_SIGNAL", "MACD_HISTOGRAM"],
      default: "MACD_LINE",
    },
  ],
  BOLLINGER_BANDS: [
    { key: "period", label: "Period", default: 20 },
    { key: "std_dev", label: "StdDev", default: 2 },
    {
      key: "output_line",
      label: "Output Line",
      type: "select",
      options: ["UPPER", "MIDDLE", "LOWER"],
      default: "UPPER",
    },
  ],
  KELTNER_CHANNEL: [
    { key: "period", label: "Period", default: 20 },
    { key: "multiplier", label: "Mult", default: 2 },
    {
      key: "output_line",
      label: "Output Line",
      type: "select",
      options: ["UPPER", "MIDDLE", "LOWER"],
      default: "UPPER",
    },
  ],
  DONCHIAN_CHANNEL: [
    { key: "period", label: "Period", default: 20 },
    {
      key: "output_line",
      label: "Output Line",
      type: "select",
      options: ["UPPER", "MIDDLE", "LOWER"],
      default: "UPPER",
    },
  ],
  STOCHASTIC: [
    { key: "k_period", label: "%K", default: 14 },
    { key: "d_period", label: "%D", default: 3 },
    { key: "smooth", label: "Smth", default: 3 },
    {
      key: "output_line",
      label: "Output Line",
      type: "select",
      options: ["K", "D"],
      default: "K",
    },
  ],
  SUPERTREND: [
    { key: "period", label: "Period", default: 7 },
    { key: "multiplier", label: "Mult", default: 3 },
  ],
  ATR: [{ key: "period", label: "Period", default: 14 }],
  MFI: [{ key: "period", label: "Period", default: 14 }],
  WILLIAMS_R: [{ key: "period", label: "Period", default: 14 }],
  PARABOLIC_SAR: [
    { key: "af", label: "Acceleration Factor", default: 0.02 },
    { key: "max_af", label: "Max AF", default: 0.2 },
  ],
  ICHIMOKU_CLOUD: [
    { key: "tenkan", label: "Tenkan (Conversion)", default: 9 },
    { key: "kijun", label: "Kijun (Base)", default: 26 },
    { key: "senkou", label: "Senkou B", default: 52 },
    {
      key: "output_line",
      label: "Output Line",
      type: "select",
      options: ["TENKAN", "KIJUN", "SENKOU_A", "SENKOU_B", "CHIKOU"],
      default: "TENKAN",
    },
  ],
  CONSTANT: [{ key: "value", label: "Value", default: 0 }],

  CANDLE_PATTERN: [
    {
      key: "pattern",
      label: "Pattern",
      type: "enum",
      enumKey: "CandlePatternType",
      default: "DOJI",
    },
  ],
  CANDLE_BODY_SIZE: [
    {
      key: "mode",
      label: "Mode",
      type: "select",
      options: ["POINTS", "PERCENTAGE"],
      default: "POINTS",
    },
  ],

  MATH_EXPRESSION: [
    {
      key: "expression",
      label: "Math Formula",
      type: "math",
      default: { expression: "", variables: {} },
    },
  ],
  VWAP: [
    {
      key: "anchor",
      label: "Anchor",
      type: "select",
      options: ["D", "W", "M"],
      default: "D",
    },
  ],
  OBV: [],
  PIVOT_POINT: [],
  POSITION_RR_RATIO: [],
  POSITION_PNL_PERCENTAGE: [],
  POSITION_PNL_POINTS: [],
  TRAILING_PEAK_OFFSET: [],
  ENTRY_PRICE: [],
};

export const getDefaultParams = (type) => {
  const config = PARAM_CONFIG[type] || [];
  return config.reduce(
    (acc, param) => ({ ...acc, [param.key]: param.default }),
    {},
  );
};

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
}) {
  const { enums } = useEnums();
  const [popoverOpen, setPopoverOpen] = useState(false);

  // Group enums for better selection
  const options = enums.OperandType || [];

  const priceData = [
    "LTP",
    "OPEN",
    "HIGH",
    "LOW",
    "CLOSE",
    "VOLUME",
    "VWAP",
    "HL2",
    "HLC3",
    "OHLC4",
    "CURRENT_DAY_OPEN",
    "PREV_WEEK_HIGH",
    "PREV_WEEK_LOW",
  ];
  const stateData = [
    "POSITION_PNL_PERCENTAGE",
    "POSITION_PNL_POINTS",
    "TRAILING_PEAK_OFFSET",
    "ENTRY_PRICE",
    "POSITION_RR_RATIO",
  ];
  const mathData = ["CONSTANT", "MATH_EXPRESSION"];

  const candleData = ["CANDLE_PATTERN", "CANDLE_BODY_SIZE"];

  const groupedOptions = {
    "Price Action & Volume": options.filter((o) => priceData.includes(o.value)),
    "Candle Analysis": options.filter((o) => candleData.includes(o.value)),
    ...(ruleType !== "ENTRY"
      ? {
          "Position State (Exit)": options.filter((o) =>
            stateData.includes(o.value),
          ),
        }
      : {}),
    "Math & Constants": options.filter((o) => mathData.includes(o.value)),
    "Technical Indicators": options.filter(
      (o) =>
        !priceData.includes(o.value) &&
        !stateData.includes(o.value) &&
        !mathData.includes(o.value) &&
        !candleData.includes(o.value),
    ),
  };

  // Try to find the label for the current value
  const currentOption = options.find((o) => o.value === value);
  const baseParamConfig = PARAM_CONFIG[value] || [];

  // Auto-append Shift parameter to all operands (except CONSTANT)
  const paramConfig =
    value && value !== "CONSTANT" && value !== "MATH_EXPRESSION"
      ? [
          ...baseParamConfig,
          {
            key: "shift",
            label: "Shift (Candles)",
            type: "number",
            default: 0,
          },
        ]
      : baseParamConfig;

  // Format params for badge display
  const formatParams = () => {
    if (!paramConfig.length || !params) return "";
    if (value === "CONSTANT") return params.value?.toString() || "0";
    if (value === "MATH_EXPRESSION") {
      if (params.expression && params.expression.expression) {
        return `(${params.expression.expression})`; // If it's nested
      } else if (params.expression && typeof params.expression === "string") {
        return `(${params.expression})`;
      }
      return "";
    }
    return `(${paramConfig.map((p) => params[p.key] ?? p.default).join(", ")})`;
  };

  const handleParamChange = (key, val, isString = false) => {
    // Preserve numeric text while editing so negative values can be typed
    // through the intermediate "-" state before being saved.
    const parsed = isString ? val : val === "" ? null : parseFloat(val);
    onChangeParams({ ...(params || {}), [key]: parsed });
  };

  return (
    <div className="flex items-center gap-1">
      {/* Type Selector */}
      <div className="flex items-center bg-black/20 rounded-lg p-0.5 border border-white/[0.05]">
        <Select value={value || ""} onValueChange={onChangeType}>
          <SelectTrigger
            className={`w-auto min-w-[120px] bg-transparent border-none hover:bg-white/5 text-xs h-7 px-2.5 shadow-none focus:ring-0 ${value ? "text-indigo-300" : "text-gray-500"} font-semibold`}
          >
            <SelectValue placeholder={placeholder} />
          </SelectTrigger>
          <SelectContent className="max-h-[300px]">
            {Object.entries(groupedOptions).map(
              ([groupName, groupOptions]) =>
                groupOptions.length > 0 && (
                  <SelectGroup key={groupName}>
                    <SelectLabel className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">
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
              <button className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-bold tracking-wider rounded-md bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 transition-colors border border-indigo-500/20 cursor-pointer max-w-[200px] truncate">
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
            <DialogContent className="w-[500px] max-w-3xl bg-[#0f1423] border border-gray-800 shadow-2xl p-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-gray-800">
                  <h4 className="text-xs font-semibold text-gray-300">
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
              <button className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-bold tracking-wider rounded-md bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 transition-colors border border-indigo-500/20 cursor-pointer max-w-[200px] truncate">
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
              className="w-64 p-3 bg-[#0f1423] border border-gray-800 shadow-xl"
              sideOffset={5}
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-gray-800">
                  <h4 className="text-xs font-semibold text-gray-300">
                    Configure Parameters
                  </h4>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {paramConfig.map((param) => (
                    <div
                      key={param.key}
                      className={
                        param.type === "source" &&
                        PARAM_CONFIG[params?.[param.key]]
                          ? "col-span-2 space-y-1"
                          : "space-y-1"
                      }
                    >
                      <label className="text-[10px] text-gray-400 font-medium">
                        {param.label}
                      </label>
                      {param.type === "source" ? (
                        <Select
                          value={params?.[param.key] ?? param.default}
                          onValueChange={(v) =>
                            handleParamChange(param.key, v, true)
                          }
                        >
                          <SelectTrigger className="h-7 text-xs bg-black/30 border-gray-800 text-gray-200 focus:ring-0">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectGroup>
                              <SelectLabel>Price</SelectLabel>
                              {[
                                "close",
                                "open",
                                "high",
                                "low",
                                "hl2",
                                "hlc3",
                                "ohlc4",
                              ].map((src) => (
                                <SelectItem key={src} value={src}>
                                  {src.toUpperCase()}
                                </SelectItem>
                              ))}
                            </SelectGroup>
                            <SelectGroup>
                              <SelectLabel>Indicators</SelectLabel>
                              {Object.keys(PARAM_CONFIG)
                                .filter((k) => k !== "CONSTANT")
                                .map((ind) => (
                                  <SelectItem key={ind} value={ind}>
                                    {ind}
                                  </SelectItem>
                                ))}
                            </SelectGroup>
                          </SelectContent>
                        </Select>
                      ) : param.type === "enum" ? (
                        <Select
                          value={params?.[param.key] ?? param.default}
                          onValueChange={(v) =>
                            handleParamChange(param.key, v, true)
                          }
                        >
                          <SelectTrigger className="h-7 text-xs bg-black/30 border-gray-800 text-gray-200 focus:ring-0">
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
                          value={params?.[param.key] ?? param.default}
                          onValueChange={(v) =>
                            handleParamChange(param.key, v, true)
                          }
                        >
                          <SelectTrigger className="h-7 text-xs bg-black/30 border-gray-800 text-gray-200 focus:ring-0">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {param.options.map((opt) => (
                              <SelectItem key={opt} value={opt}>
                                {opt}
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
                          className="h-7 text-xs bg-black/30 border-gray-800 text-gray-200"
                        />
                      )}

                      {param.type === "source" &&
                        PARAM_CONFIG[params?.[param.key]] && (
                          <div className="mt-2 p-2 border border-gray-800 rounded bg-black/20">
                            <span className="text-[10px] text-indigo-400 font-bold mb-1 block">
                              Source ({params?.[param.key]}) Settings
                            </span>
                            <div className="grid grid-cols-2 gap-2">
                              {PARAM_CONFIG[params?.[param.key]]
                                .filter((p) => p.type !== "source")
                                .map((sp) => (
                                  <div
                                    key={`source_${sp.key}`}
                                    className="space-y-1"
                                  >
                                    <label className="text-[10px] text-gray-400 font-medium">
                                      {sp.label}
                                    </label>
                                    <Input
                                      type={
                                        sp.key === "option_type"
                                          ? "text"
                                          : "number"
                                      }
                                      value={
                                        params?.source_params?.[sp.key] ??
                                        sp.default
                                      }
                                      onChange={(e) => {
                                        const val =
                                          sp.key === "option_type"
                                            ? e.target.value
                                            : e.target.value === ""
                                              ? null
                                              : parseFloat(e.target.value);
                                        const currentSourceParams =
                                          params?.source_params || {};
                                        onChangeParams({
                                          ...params,
                                          source_params: {
                                            ...currentSourceParams,
                                            [sp.key]: val,
                                          },
                                        });
                                      }}
                                      className="h-7 text-xs bg-black/30 border-gray-800 text-gray-200"
                                    />
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

      {/* Timeframe Selector (Only if not CONSTANT/State based) */}
      {!hideTimeframe &&
        value &&
        value !== "CONSTANT" &&
        !value.includes("POSITION") &&
        value !== "ENTRY_PRICE" && (
          <div className="flex items-center gap-1.5 bg-black/10 rounded-md px-1.5 py-0.5 border border-white/[0.02]">
            <Clock className="h-3 w-3 text-gray-500" />
            <Select
              value={timeframe || "NONE"}
              onValueChange={(v) => onChangeTimeframe(v === "NONE" ? null : v)}
            >
              <SelectTrigger className="w-auto bg-transparent border-none hover:bg-white/5 text-[10px] h-5 px-1 shadow-none focus:ring-0 text-gray-400 p-0 font-medium">
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
