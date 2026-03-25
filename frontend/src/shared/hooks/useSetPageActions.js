import { useEffect } from 'react';
import { usePageActions } from '@/shared/context/PageActionsContext';

/**
 * Hook to set page actions in the header
 * Usage: useSetPageActions(<Button>Action</Button>)
 * Actions will be automatically cleared when component unmounts
 */
export function useSetPageActions(actions) {
  const { setPageActions, clearPageActions } = usePageActions();

  useEffect(() => {
    if (actions) {
      setPageActions(actions);
    }
    return () => clearPageActions();
  }, [actions, setPageActions, clearPageActions]);
}
