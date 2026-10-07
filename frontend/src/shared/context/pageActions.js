import { createContext, useContext } from 'react';

export const PageActionsContext = createContext(null);
export const PageActionStateContext = createContext(null);

export function usePageActions() {
  const context = useContext(PageActionsContext);
  if (!context) throw new Error('usePageActions must be used within a PageActionsProvider');
  return context;
}

export function usePageActionState() {
  const context = useContext(PageActionStateContext);
  if (!context) throw new Error('usePageActionState must be used within a PageActionsProvider');
  return context;
}
