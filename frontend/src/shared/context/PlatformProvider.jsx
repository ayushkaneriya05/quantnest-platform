import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import api from '@/shared/services/api';
import { PlatformContext } from './platform';

export default function PlatformProvider({ children }) {
  const [catalog, setCatalog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const pending = useRef(null);
  const refresh = useCallback(() => {
    if (pending.current) return pending.current.promise;
    const controller = new AbortController();
    const request = { controller };
    pending.current = request;
    request.promise = api.get('/public/catalog/', { signal: controller.signal, publicRequest: true }).then(({ data }) => {
      if (!Array.isArray(data.execution_enabled_scopes) || !data.plans || !Array.isArray(data.features)
        || !Array.isArray(data.support?.request_types) || !data.support.ticket_status_labels
        || !data.limit_labels || !data.privacy_policy_revision || !data.contact) {
        throw new Error('Missing platform configuration');
      }
      if (controller.signal.aborted) return null;
      setCatalog(data); setError(false);
      return data;
    }).catch(() => {
      if (!controller.signal.aborted) setError(true);
      return null;
    }).finally(() => {
      if (pending.current === request) { pending.current = null; setLoading(false); }
    });
    return request.promise;
  }, []);
  useEffect(() => {
    refresh();
    return () => {
      pending.current?.controller.abort(); pending.current = null;
    };
  }, [refresh]);
  const value = useMemo(() => ({ catalog, loading, error, refresh,
    executionScopes: catalog?.execution_enabled_scopes.filter(scope => ['paper', 'live'].includes(scope)) || [],
  }), [catalog, loading, error, refresh]);
  return <PlatformContext.Provider value={value}>{children}</PlatformContext.Provider>;
}
PlatformProvider.propTypes = { children: PropTypes.node.isRequired };
