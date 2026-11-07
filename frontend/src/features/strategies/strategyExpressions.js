export const referencesFormula = (value, name) => {
  if (!value || typeof value !== "object") return false;
  if (value.op === "expression" && value.name === name) return true;
  return Object.values(value).some((child) => referencesFormula(child, name));
};
export const referencesCapture = (value, setup, name) => {
  if (!value || typeof value !== "object") return false;
  if (value.op === "capture" && value.setup === setup && value.name === name)
    return true;
  return Object.values(value).some((child) =>
    referencesCapture(child, setup, name),
  );
};
