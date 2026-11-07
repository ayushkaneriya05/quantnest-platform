// Read-only summaries for the editor. These never evaluate a trading rule.
export function expressionText(node, enums, defaultTimeframe) {
  if (!node) return "Not configured";
  const label = (family, value) =>
    enums[family]?.find((item) => item.value === value)?.label || value;
  if (node.op === "input") {
    if (node.type === "CONSTANT") return String(node.params?.value ?? "—");
    const operand = enums.StrategyStudio?.conditions.operands[node.type];
    const position = operand?.context === "position";
    const period = node.params?.period;
    const context = position ? "Position" : enums.StrategyStudio?.markets.source_roles
      .find((item) => item.value === node.source)?.label || node.source;
    const timing = position
      ? ""
      : node.type === "LTP"
        ? " · Live price"
        : ` · ${node.timeframe || defaultTimeframe || "Default"}`;
    return `${label("OperandType", node.type)}${period != null ? ` (${period})` : ""} [${context}${timing}]`;
  }
  if (node.op === "expression") return `Formula: ${node.name}`;
  if (node.op === "capture") return `Captured: ${node.name}`;
  if (node.op === "compare")
    return `${expressionText(node.left, enums, defaultTimeframe)} ${label("ComparisonOperator", node.comparison)} ${expressionText(node.right, enums, defaultTimeframe)}`;
  const operation = enums.StrategyStudio?.fields.op.choices.find((item) => item.value === node.op);
  const children = (node.args || []).map((child) =>
    expressionText(child, enums, defaultTimeframe),
  );
  return operation?.display_symbol
    ? `(${children.join(` ${operation.display_symbol} `)})`
    : `${operation?.label || node.op}${node.bars != null ? ` ${node.bars} bars` : ""} (${children.join(", ")})`;
}

// Inline-math variables inherit their parent source; tree leaves own theirs.
export function expressionContexts(
  node,
  enums,
  formulas = {},
  source = "signal",
  seen = new Set(),
  timeframe = null,
) {
  if (!node) return [];
  if (node.op === "capture") return [{ context: "capture", rolling: false }];
  if (node.op === "expression") {
    if (seen.has(node.name)) return [];
    return expressionContexts(
      formulas[node.name],
      enums,
      formulas,
      source,
      new Set([...seen, node.name]),
      timeframe,
    );
  }
  if (node.op === "input" || node.type) {
    if (node.type === "MATH_EXPRESSION")
      return Object.values(node.params?.expression?.variables || {}).flatMap(
        (variable) =>
          expressionContexts(
            variable,
            enums,
            formulas,
            node.source || source,
            seen,
            node.timeframe || timeframe,
          ),
      );
    const operand = enums.StrategyStudio?.conditions.operands[node.type];
    const context = operand?.context;
    return context
      ? [
          {
            context,
            rolling: operand.allowed_in.rolling,
            source: node.source || source,
            type: node.type,
            timeframe: node.timeframe || timeframe,
          },
        ]
      : [];
  }
  return [node.left, node.right, ...(node.args || [])].flatMap((child) =>
    expressionContexts(child, enums, formulas, source, seen, timeframe),
  );
}

// Mirror the compiler's authoring restriction, not its numerical calculation.
// Existing invalid drafts stay editable; validation on the server remains authoritative.
export function rollingInputIssue(node, enums, formulas, defaultTimeframe) {
  const contexts = expressionContexts(node, enums, formulas);
  const invalid = contexts.find((input) => !input.rolling);
  if (invalid) {
    const label =
      enums.StrategyStudio?.conditions.operands[invalid.type]?.label ||
      "Captured value";
    return `${label} has no completed-candle history for this rolling calculation. Move it outside the window and combine it with the rolling result.`;
  }
  const clocks = new Set(
    contexts
      .filter((input) => input.context === "market")
      .map((input) => `${input.source}:${input.timeframe || defaultTimeframe}`),
  );
  return clocks.size > 1
    ? "Inputs inside this window must share one market source and candle timeframe. Compute separate rolling values, then combine their results outside the windows."
    : "";
}

export function sizingText(value, enums) {
  if (value.sizing_method !== "FIXED")
    return `${value.capital_percentage ?? "—"}% of available capital`;
  const unit =
    enums.QuantityUnit?.find((item) => item.value === value.quantity_unit)
      ?.label || value.quantity_unit;
  return `${value.fixed_quantity ?? "—"} ${unit || "units"}`;
}

export function policyText(policy, enums) {
  const label = (family, value) =>
    enums[family]?.find((item) => item.value === value)?.label || value;
  const strike =
    policy.strike === "FIXED"
      ? `Strike ${policy.strike_price ?? "—"}`
      : `${policy.strike}${enums.StrategyStudio?.markets.automatic.relative_strikes.includes(policy.strike) ? ` ${policy.distance} listed strikes` : ""}`;
  return [
    label("InstrumentType", policy.instrument_type),
    policy.instrument_type === "OPTION" &&
      label("OptionType", policy.option_type),
    policy.instrument_type === "OPTION" && strike,
    policy.expiry === "FIXED"
      ? `Expiry ${policy.expiry_date || "not selected"}`
      : label("ExpirySelection", policy.expiry),
    policy.allow_expiry_day ? "Includes expiry day" : "Excludes expiry day",
  ]
    .filter(Boolean)
    .join(" · ");
}

export function scheduleIssues(timing, customDays) {
  const errors = [];
  const seconds = (value) =>
    value
      .split(":")
      .reduce(
        (total, part, index) => total + Number(part) * [3600, 60, 1][index],
        0,
      );
  if (customDays && !timing.trading_days.length)
    errors.push({
      selector: "[data-schedule-days]",
      message: "Choose at least one weekday, or use All exchange trading days.",
    });
  if (
    timing.start_time &&
    timing.end_time &&
    seconds(timing.start_time) >= seconds(timing.end_time)
  )
    errors.push({
      selector: "#studio-entry-end",
      message:
        "Entry end must be after entry start. Overnight entry windows are not supported.",
    });
  (timing.no_trade_windows || []).forEach((window, index) => {
    if (
      !window.start ||
      !window.end ||
      seconds(window.start) >= seconds(window.end)
    )
      errors.push({
        selector: `[data-window-index="${index}"] input`,
        message: `Excluded window ${index + 1} needs a start time followed by a later end time.`,
      });
  });
  return errors.map((error) => ({ ...error, step: 2 }));
}
