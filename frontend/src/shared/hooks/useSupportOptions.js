import { useMemo } from 'react';
import { usePlatform } from '@/shared/context/platform';

export function useSupportOptions() {
  const { catalog, loading, error, refresh } = usePlatform();
  const options = useMemo(() => {
    const requestTypes = catalog?.support?.request_types || [];
    return {
      requestTypes,
      requestLabels: Object.fromEntries(requestTypes.map(({ value, label }) => [value, label])),
      ticketStatusLabels: catalog?.support?.ticket_status_labels || {},
    };
  }, [catalog?.support]);
  return { ...options, contact: catalog?.contact, loading, error, refresh };
}
