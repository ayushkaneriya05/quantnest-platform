// Pure accessors for the server-owned Studio contract. Metadata is fetched by
// EnumsProvider once; these helpers do no HTTP and never guess missing defaults.
export function createStrategySpecification(enums) {
  const spec = enums.StrategyStudio;
  if (!spec) return null;
  const operands = spec.conditions.operands;
  const choicesFor = (field) => {
    const choices = field.choices || spec.conditions.choices[field.choice_ref] || enums[field.choice_ref] || [];
    return field.values ? choices.filter((item) => field.values.includes(item.value)) : choices;
  };
  const defaultParams = (type) => Object.fromEntries(operands[type].parameters
    .map((field) => [field.key, structuredClone(field.default)]));
  const inputNode = (type = spec.defaults.templates.input.type, params = {}) => ({
    ...structuredClone(spec.defaults.templates.input), type,
    params: { ...defaultParams(type), ...structuredClone(params) },
  });
  const materialize = (node, setupId) => {
    if (!node || typeof node !== "object") return node;
    if (Array.isArray(node)) return node.map((item) => materialize(item, setupId));
    if (node.op === "input") {
      const input = inputNode(node.type, node.params);
      return { ...input, ...node, params: input.params };
    }
    const value = Object.fromEntries(Object.entries(node).map(([key, item]) => [key, materialize(item, setupId)]));
    if (value.op === "capture" && setupId) value.setup = setupId;
    return value;
  };
  return {
    spec, operands, choicesFor,
    operandOptions: Object.values(operands),
    parameterConfig: Object.fromEntries(Object.entries(operands).map(([key, item]) => [key,
      item.parameters.map((field) => field.choice_ref ? { ...field, options: choicesFor(field) } : field)])),
    operators: spec.conditions.operators,
    defaultParams, inputNode,
    comparisonNode: () => materialize(spec.defaults.templates.comparison),
    numericArgument: () => materialize(spec.defaults.templates.numeric_argument),
    initialRiskNode: () => materialize(spec.defaults.templates.initial_risk),
    screenCondition: () => {
      const { left, right, comparison } = materialize(spec.defaults.templates.screen_comparison);
      return {
        operand_a_type: left.type, operand_a_params: left.params, operand_a_timeframe: left.timeframe,
        operand_b_type: right.type, operand_b_params: right.params, operand_b_timeframe: right.timeframe,
        comparison, is_active: spec.defaults.templates.group.is_active,
      };
    },
    groupTemplate: () => materialize(spec.defaults.templates.group),
    defaultContractSelection: () => structuredClone(spec.defaults.templates.contract_selection),
    captureSetup: (group, timeframe) => ({
      setup: { ...materialize(spec.setup.template, group.id), arm: structuredClone(group.condition), timeframe },
      condition: materialize(spec.setup.confirmation, group.id),
    }),
    changePolicy: (value, key, next) => {
      const automatic = spec.markets.automatic;
      const change = { [key]: next };
      if (key === "instrument_type") Object.assign(change, automatic.family_resets[next]);
      if (key === "expiry") change.expiry_date = null;
      if (key === "strike") Object.assign(change, {
        distance: automatic.relative_strikes.includes(next) ? 1 : automatic.fields.distance.default,
        strike_price: automatic.fields.strike_price.default,
      });
      return { ...value, ...change };
    },
  };
}
