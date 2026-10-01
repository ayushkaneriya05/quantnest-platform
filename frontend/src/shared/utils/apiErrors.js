function firstMessage(value) {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (Array.isArray(value)) return value.map(firstMessage).filter(Boolean).join(" ");
  if (value && typeof value === "object") {
    return Object.values(value).map(firstMessage).filter(Boolean).join(" ");
  }
  return "";
}

export function getApiErrorDetails(error) {
  const data = error?.response?.data;
  if (data?.details !== undefined) return data.details;
  if (data?.errors !== undefined) return data.errors;
  if (!data || typeof data !== "object" || Array.isArray(data)) return {};

  return Object.fromEntries(
    Object.entries(data).filter(([key]) => !["code", "message", "detail", "error", "status"].includes(key)),
  );
}

export function getApiErrorMessage(error, fallback = "The request could not be completed.") {
  const data = error?.response?.data;
  const message = firstMessage(data?.message ?? data?.detail ?? data?.error ?? data);
  if (message) return message;

  const transportMessage = error?.response ? "" : error?.message;
  return transportMessage || fallback;
}
