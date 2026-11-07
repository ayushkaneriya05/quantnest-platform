import PropTypes from "prop-types";
import { createContext, useCallback, useContext, useState, useEffect } from 'react';
import { enumsApi } from '@/shared/services/enumsApi';
import { createStrategySpecification } from '@/shared/utils/strategySpecification';

const EnumsContext = createContext({ enums: {}, values: {}, specification: null, loading: true, error: null });

/** One metadata request and cache for shared choices and the Studio specification. */
export function EnumsProvider({ children }) {
  const [metadata, setMetadata] = useState({ enums: {}, values: {}, specification: null, loading: true, error: null });
  const [revision, setRevision] = useState(0);
  const refreshEnums = useCallback(() => setRevision((current) => current + 1), []);

  useEffect(() => {
    let active = true;
    let retryTimer;
    setMetadata((current) => ({ ...current, loading: true, error: null }));

    async function load(attempt = 0) {
      try {
        const enums = await enumsApi.getAll();
        if (!active) return;
        if (enums.StrategyStudio?.metadata_version !== 1)
          throw new Error('The Studio specification is unavailable. Reload after the API update.');
        // Assemble inside the error boundary so malformed metadata shows a
        // retry state instead of crashing every page that uses the provider.
        const specification = createStrategySpecification(enums);
        const values = Object.fromEntries(Object.entries(enums)
          .filter(([, choices]) => Array.isArray(choices))
          .map(([name, choices]) => [name, Object.fromEntries(choices.map((choice) => [choice.name, choice.value]))]));
        setMetadata({ enums, values, specification, loading: false, error: null });
      } catch (error) {
        if (!active) return;
        if (attempt < 3) retryTimer = setTimeout(() => load(attempt + 1), 2 ** attempt * 1000);
        else setMetadata((current) => ({ ...current, loading: false, error }));
      }
    }

    load();
    // Refresh and unmount invalidate older results and pending retries.
    return () => { active = false; clearTimeout(retryTimer); };
  }, [revision]);

  return (
    <EnumsContext.Provider value={{ ...metadata, refreshEnums }}>
      {children}
    </EnumsContext.Provider>
  );
}

/**
 * Hook to access enum choices anywhere in the component tree.
 * @returns {{
 *   enums: Record<string, {name: string, value: string, label: string}[]>,
 *   values: Record<string, Record<string, string>>,
 *   loading: boolean,
 *   error: Error | null,
 *   refreshEnums: () => void
 * }}
 */
export function useEnums() {
  return useContext(EnumsContext);
}

// A projection of the same cached response, not another provider or request.
export function useStrategySpecification() {
  const context = useEnums();
  return { ...context, ...context.specification };
}

export default EnumsContext;

EnumsProvider.propTypes = {
  ...EnumsProvider.propTypes,
  children: PropTypes.node,
};
