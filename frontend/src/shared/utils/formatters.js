export function formatNumber(value) {
  const number = Number(value || 0);
  return number.toLocaleString("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
}

export function formatDateTime(value) {
  if (!value) return "Not started";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "medium" });
}

export function formatBrokerAccount(brokerName, accountLabel) {
  const broker = brokerName || "Broker";
  return accountLabel ? `${broker} · ${accountLabel}` : broker;
}

export function formatCurrency(value) {
  const amount = Number(value);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(Number.isFinite(amount) ? amount : 0);
}
