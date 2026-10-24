import {useStableCallback} from "@/shared/hooks/useStableCallback";
import PropTypes from "prop-types";
/**
 * EnumsContext — fetches all backend enum choices once and caches them.
 *
 * Usage:
 *   const { enums, values, loading } = useEnums();
 *   enums.StrategyType → [{name, value, label}, ...] for dropdowns.
 *   values.StrategyType.INTRADAY → the backend-defined value for comparisons.
 */
import { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { enumsApi } from '@/shared/services/enumsApi';

const EnumsContext = createContext({ enums: {}, values: {}, loading: true });

export function EnumsProvider({ children }) {
  const fetchEnums = useStableCallback(async (retryCount = 0) => {
    try {
      setLoading(true);
      const data = await enumsApi.getAll();
      setEnums(data);
      setError(null);
      setLoading(false);
    } catch (err) {
      console.error(`Failed to fetch enums (attempt ${retryCount + 1}):`, err);
      setError(err);

      // Retry up to 3 times with exponential backoff
      if (retryCount < 3) {
        const timeout = Math.pow(2, retryCount) * 1000; // 1s, 2s, 4s
        setTimeout(() => fetchEnums(retryCount + 1), timeout);
      } else {
        setLoading(false);
      }
    }
  });

  const [enums, setEnums] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const values = useMemo(() => Object.fromEntries(Object.entries(enums)
    .filter(([, choices]) => Array.isArray(choices))
    .map(([name, choices]) => [name, Object.fromEntries(choices.map((choice) => [choice.name, choice.value]))])), [enums]);
  useEffect(() => {
    fetchEnums();
  }, [fetchEnums]);

  const refreshEnums = () => fetchEnums(0);

  return (
    <EnumsContext.Provider value={{ enums, values, loading, error, refreshEnums }}>
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
 *   refreshEnums: () => Promise<void>
 * }}
 */
export function useEnums() {
  return useContext(EnumsContext);
}

export default EnumsContext;

EnumsProvider.propTypes = {
  ...EnumsProvider.propTypes,
  children: PropTypes.node,
};
