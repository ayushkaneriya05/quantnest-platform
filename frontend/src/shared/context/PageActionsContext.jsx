import { useState, useCallback, useMemo } from 'react';
import PropTypes from 'prop-types';
import { PageActionsContext, PageActionStateContext } from './pageActions';

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

  // Publishing a new header must not rerender its publisher.
  const commands = useMemo(() => ({
      setPageActions, 
      clearPageActions,
      setPageHeader,
      clearPageHeader
  }), [setPageActions, clearPageActions, setPageHeader, clearPageHeader]);
  const state = useMemo(() => ({ actions, headerContent }), [actions, headerContent]);

  return (
    <PageActionsContext.Provider value={commands}>
      <PageActionStateContext.Provider value={state}>
        {children}
      </PageActionStateContext.Provider>
    </PageActionsContext.Provider>
  );
}

PageActionsProvider.propTypes = { children: PropTypes.node.isRequired };
