export const getDefaultParams = (type, parameterConfig = {}) => {
  return (parameterConfig[type] || []).reduce(
    (params, parameter) => ({
      ...params,
      [parameter.key]: parameter.default,
    }),
    {},
  );
};
