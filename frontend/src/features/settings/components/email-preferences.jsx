import { useCallback, useEffect, useRef, useState } from 'react';
import api from '@/shared/services/api';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/shared/components/ui/card';
import { Button } from '@/shared/components/ui/button';
import WorkspaceState from '@/shared/components/WorkspaceState';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';

export default function EmailPreferences() {
  const { notify } = useNotifications();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const locked = useRef(false);
  const load = useCallback(async () => {
    try { const response = await api.get('/support/consent/'); setData(response.data); setError(''); }
    catch (failure) { setError(getApiErrorMessage(failure)); }
  }, []);
  useEffect(() => { load(); }, [load]);
  const change = async () => {
    if (locked.current) return; locked.current = true; setBusy(true);
    try {
      const response = await api.post('/support/consent/', { purpose: 'marketing', granted: !data.marketing, policy_revision: data.policy_revision });
      notify.success(response.data.state === 'pending' ? 'Check your email to confirm product updates. The preference stays off until confirmation.' : 'Your email preference has been saved.');
      await load();
    } catch (failure) { notify.error(getApiErrorMessage(failure)); }
    finally { locked.current = false; setBusy(false); }
  };
  return (
    <Card>
      <CardHeader className="p-5 pb-3">
        <CardTitle className="text-base">Product update emails</CardTitle>
        <CardDescription>Optional updates, separate from essential account and service messages.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 px-5 pb-5">
        {error && <WorkspaceState error={error} onRetry={load} />}
        {!data && !error && <p role="status" className="text-sm text-muted-foreground">Loading email preference…</p>}
        {data && !error && (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
              {data.marketing ? 'Enabled' : 'Off'} · Email confirmation is required to subscribe. You can unsubscribe at any time.
            </p>
            <Button type="button" size="sm" variant="outline" disabled={busy} onClick={change}>
              {busy ? 'Saving…' : data.marketing ? 'Turn off' : 'Send confirmation'}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
