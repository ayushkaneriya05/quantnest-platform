import { formatNumber } from "@/shared/utils/formatters";
export const title = (key) => key.replaceAll("_", " ");
export const choiceLabel = (enums, name, value) => enums?.[name]?.find((item) => item.value === value)?.label || value;

export function readable(value) {
  if (value == null) return "N/A";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return formatNumber(value);
  if (Array.isArray(value)) return value.map(readable).join(", ");
  if (typeof value === "object") return Object.entries(value).map(([key, item]) => `${title(key)}: ${readable(item)}`).join("; ");
  return String(value);
}

export function describeOperand(type, params = {}, enums = {}) {
  if (type === "CONSTANT") return formatNumber(params.value);
  const label = choiceLabel(enums, "OperandType", type);
  const expression = params.expression;
  if (type === "MATH_EXPRESSION" && expression) {
    const variables = Object.entries(expression.variables || {}).map(([name, value]) =>
      `${name} = ${describeOperand(value.type, value.params, enums)}${value.timeframe ? ` (${value.timeframe})` : ""}`);
    return `${expression.expression} (${variables.join("; ")})`;
  }
  const fields = Object.entries(params).map(([key, value]) => `${title(key)}: ${key === "source" ? choiceLabel(enums, "OperandType", value) : readable(value)}`);
  return `${label}${fields.length ? ` (${fields.join(", ")})` : ""}`;
}

export function describeRule(rule, enums = {}) {
  return `${describeOperand(rule.operand_a_type, rule.operand_a_params, enums)}${rule.operand_a_timeframe ? ` [${rule.operand_a_timeframe}]` : ""} ${choiceLabel(enums, "ComparisonOperator", rule.comparison)} ${describeOperand(rule.operand_b_type, rule.operand_b_params, enums)}${rule.operand_b_timeframe ? ` [${rule.operand_b_timeframe}]` : ""}`;
}

