import { createContext, useContext, useState, useCallback } from 'react';

const PageActionsContext = createContext();

export function PageActionsProvider({ children }) {
  const [actions, setActions] = useState(null);
  const [headerContent, setHeaderContent] = useState(null);

  const setPageActions = useCallback((actionElements) => {
    setActions(actionElements);
  }, []);

  const clearPageActions = useCallback(() => {
    setActions(null);
  }, []);

  const setPageHeader = useCallback((content) => {
    setHeaderContent(content);
  }, []);

  const clearPageHeader = useCallback(() => {
    setHeaderContent(null);
  }, []);

  return (
    <PageActionsContext.Provider value={{ 
      actions, 
      setPageActions, 
      clearPageActions,
      headerContent,
      setPageHeader,
      clearPageHeader
    }}>
      {children}
    </PageActionsContext.Provider>
  );
}

export function usePageActions() {
  const context = useContext(PageActionsContext);
  if (!context) {
    throw new Error('usePageActions must be used within a PageActionsProvider');
  }
  return context;
}
