/**
 * EnumsContext — fetches all backend enum choices once and caches them.
 *
 * Usage:
 *   const { enums, loading } = useEnums();
 *   enums.StrategyType → [{value: 'INTRADAY', label: 'Intraday'}, ...]
 */
import { createContext, useContext, useState, useEffect } from 'react';
import { enumsApi } from '@/shared/services/enumsApi';

const EnumsContext = createContext({ enums: {}, loading: true });

export function EnumsProvider({ children }) {
  const [enums, setEnums] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchEnums = async (retryCount = 0) => {
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
  };

  useEffect(() => {
    fetchEnums();
  }, []);

  const refreshEnums = () => fetchEnums(0);

  return (
    <EnumsContext.Provider value={{ enums, loading, error, refreshEnums }}>
      {children}
    </EnumsContext.Provider>
  );
}

/**
 * Hook to access enum choices anywhere in the component tree.
 * @returns {{ 
 *   enums: Record<string, {value: string, label: string}[]>, 
 *   loading: boolean, 
 *   error: Error | null,
 *   refreshEnums: () => Promise<void>
 * }}
 */
export function useEnums() {
  return useContext(EnumsContext);
}

export default EnumsContext;
