import { createContext, useContext } from 'react';
export const PlatformContext = createContext({ executionScopes: [], catalog: null, loading: true, error: false, refresh: () => {} });
export const usePlatform = () => useContext(PlatformContext);
