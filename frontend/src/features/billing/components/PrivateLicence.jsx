import { useCallback, useEffect, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import api from '@/shared/services/api';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/shared/components/ui/card';
import { Button } from '@/shared/components/ui/button';
import { Textarea } from '@/shared/components/ui/textarea';
import { Label } from '@/shared/components/ui/label';
import WorkspaceState from '@/shared/components/WorkspaceState';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';

const formatUnixDateTime = value => value ? new Date(value * 1000).toLocaleString('en-IN') : 'Unavailable';
export default function PrivateLicence() {
  const { notify } = useNotifications();
  const admin = useSelector(state => state.auth.user?.is_staff);
  const [licence, setLicence] = useState(null), [token, setToken] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const locked = useRef(false);
  const loadLicenceStatus = useCallback(async () => {
    try { const { data } = await api.get('/installations/local/'); setLicence(data); setError(''); }
    catch (failure) { setError(getApiErrorMessage(failure)); }
  }, []);
  useEffect(() => { loadLicenceStatus(); }, [loadLicenceStatus]);
  async function runLicenceAction(callback, message) {
    if (locked.current) return; locked.current = true; setBusy(true); setError('');
    try { await callback(); setToken(''); notify.success(message); await loadLicenceStatus(); }
    catch (failure) { notify.error(getApiErrorMessage(failure)); }
    finally { locked.current = false; setBusy(false); }
  }
  return <Card><CardHeader className="p-5 pb-3"><CardTitle className="text-base">Private installation licence</CardTitle><CardDescription>View your installation rights and permission to start new work.</CardDescription></CardHeader><CardContent className="space-y-4 px-5 pb-5">
    {error && <WorkspaceState error={error} onRetry={loadLicenceStatus} />}{!licence && !error && <WorkspaceState loading />}
    {licence && <><p className="rounded-lg border bg-muted/30 p-3 text-sm">New work: <strong>{licence.allow_entries ? 'Permitted' : 'Blocked'}</strong>{licence.reason && ` · ${licence.reason.replaceAll('_', ' ')}`}</p><dl className="grid gap-3 text-sm sm:grid-cols-2">{[['Revision', licence.revision || 'Unavailable'], ['Continuing-use rights', licence.rights || 'Unavailable'], ['Lease expires', formatUnixDateTime(licence.lease_expires)], ['Paid through', formatUnixDateTime(licence.paid_through)], ['Live qualification', licence.live_approved ? 'Current' : 'Not activated or expired'], ['Qualified brokers', licence.qualified_integrations?.join(', ') || 'None'], ['Software usage', 'Unlimited while the licence is active']].map(([label, value]) => <div key={label}><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1 break-words">{value}</dd></div>)}</dl><p className="text-xs leading-6 text-muted-foreground">{licence.in_grace ? 'The installation is using its limited outage grace. Refresh before it ends.' : 'Licence refresh runs every six hours.'} Running strategies continue without a background expiry check. New deploy/resume actions require valid rights; recorded results and exports remain available. Maintenance is separate from continuing-use rights.</p></>}
    {admin && <section className="space-y-3 border-t pt-4"><Label htmlFor="private-licence">Import an approved signed licence</Label><Textarea id="private-licence" value={token} onChange={event => setToken(event.target.value)} maxLength={32768} rows={3} autoComplete="off" spellCheck={false} disabled={busy} /><div className="flex flex-wrap gap-2"><Button size="sm" disabled={busy || !token.trim()} onClick={() => runLicenceAction(() => api.post('/installations/local/', { licence: token.trim() }), 'The signed licence was verified and imported.')}>Verify and import</Button><Button size="sm" variant="outline" disabled={busy || !licence || licence.allow_entries} onClick={() => runLicenceAction(() => api.post('/installations/resume/'), 'New work has been enabled.')}>Enable new work</Button></div></section>}
    <div className="flex flex-wrap items-center gap-3"><Button size="sm" variant="outline" disabled={busy} onClick={loadLicenceStatus}>Refresh status</Button><Link to="/docs/private/" className="text-sm text-brand underline">Private operating guide</Link></div>
  </CardContent></Card>;
}
