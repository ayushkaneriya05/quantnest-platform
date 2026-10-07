export const hidden = new Set(["id", "user", "user_id", "strategy", "rule_group", "watchlist_instrument", "created_at", "updated_at"]);
export const fieldLabel = (key) => ({
  operand_a_type: "Left operand", operand_b_type: "Right operand",
  operand_a_params: "Left operand parameters", operand_b_params: "Right operand parameters",
  operand_a_timeframe: "Left operand timeframe", operand_b_timeframe: "Right operand timeframe",
  is_active: "Enabled", override_sizing: "Override position sizing", candle_timeframe: "Candle timeframe",
})[key] || key.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());

export function formatStrategyValue(value, enums = {}) {
  if (value == null || value === "") return "Not set";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 8 }).format(value);
  if (Array.isArray(value)) return value.length ? value.map((item) => formatStrategyValue(item, enums)).join(" · ") : "None";
  if (typeof value === "object") return Object.entries(value).filter(([key]) => !hidden.has(key))
    .map(([key, item]) => `${fieldLabel(key)}: ${formatStrategyValue(item, enums)}`).join("; ") || "None";
  const option = Object.values(enums).flatMap((items) => Array.isArray(items) ? items : []).find((item) => item.value === value);
  return option?.label || String(value);
}
