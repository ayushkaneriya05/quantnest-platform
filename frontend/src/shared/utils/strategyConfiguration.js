import { formatNumber } from "@/shared/utils/formatters";
export const hidden = new Set(["id", "user", "user_id", "strategy", "rule_group", "watchlist_instrument", "created_at", "updated_at"]);
const descriptor = (field, enums) => typeof field === "object" && field
  ? field : enums.StrategyStudio?.fields[field] || {};
export const fieldLabel = (key, enums = {}) => descriptor(key, enums).label ||
  key.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());

export function formatStrategyValue(value, enums = {}, field) {
  const spec = descriptor(field, enums);
  if (value == null || value === "") return "Not set";
  const choices = spec.choices || spec.options ||
    enums.StrategyStudio?.conditions.choices[spec.choice_ref] || enums[spec.choice_ref || spec.enumKey] || [];
  const selected = choices.find((item) => item.value === value);
  if (selected) return selected.label;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return formatNumber(value, { minimumFractionDigits: 0, maximumFractionDigits: 8 });
  if (Array.isArray(value)) return value.length ? value.map((item) => formatStrategyValue(item, enums, spec)).join(" · ") : "None";
  if (typeof value === "object") return Object.entries(value).filter(([key]) => !hidden.has(key))
    .map(([key, item]) => {
      const child = spec.parameters?.find((parameter) => parameter.key === key) || descriptor(key, enums);
      const nested = key === "source_params" ? {
        ...child, parameters: enums.StrategyStudio?.conditions.operands[value.source]?.parameters,
      } : child;
      return `${child.label || fieldLabel(key, enums)}: ${formatStrategyValue(item, enums, nested)}`;
    }).join("; ") || "None";
  // Resolve within the declared vocabulary; identical identifiers can have
  // different meanings for expiry, sizing, operands and terminal actions.
  return String(value);
}
