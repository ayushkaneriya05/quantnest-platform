import { useCallback, useEffect, useRef, useState } from 'react';
import api from '@/shared/services/api';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/components/ui/card';
import { Button } from '@/shared/components/ui/button';
import { Label } from '@/shared/components/ui/label';
import { Checkbox } from '@/shared/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select';

export default function PrivateSupportAccess() {
  const { notify } = useNotifications();
  const [data, setData] = useState(null);
  const [installation, setInstallation] = useState('');
  const [staff, setStaff] = useState('');
  const [approved, setApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const locked = useRef(false);
  const loadSupportAccess = useCallback(async () => {
    try { const response = await api.get('/installations/support-access/'); setData(response.data); setError(''); }
    catch (failure) { setError(getApiErrorMessage(failure)); }
  }, []);
  useEffect(() => { loadSupportAccess(); }, [loadSupportAccess]);
  const runSupportAccessAction = async (callback, message) => {
    if (locked.current) return;
    locked.current = true;
    setBusy(true);
    try { await callback(); setApproved(false); notify.success(message); await loadSupportAccess(); }
    catch (failure) { notify.error(getApiErrorMessage(failure)); }
    finally { locked.current = false; setBusy(false); }
  };
  if (!data?.installations.length && !error) return null;
  return <Card><CardHeader className="p-5 pb-3"><CardTitle className="text-base">Private support access</CardTitle></CardHeader><CardContent className="space-y-4 px-5 pb-5">
    <p className="text-sm text-muted-foreground">Approve a named support member for two hours of installation and licence diagnostics. This shares no trading records, broker credentials or remote access to your server.</p>
    {error && <p role="alert">{error} <Button variant="outline" onClick={loadSupportAccess}>Retry</Button></p>}
    {data && <>
      <div className="grid sm:grid-cols-2 gap-4">
        <div className="space-y-2"><Label htmlFor="support-installation">Installation</Label><Select value={installation} onValueChange={setInstallation}><SelectTrigger id="support-installation"><SelectValue placeholder="Choose installation" /></SelectTrigger><SelectContent>{data.installations.map(row => <SelectItem key={row.id} value={row.id}>{row.contract__reference}</SelectItem>)}</SelectContent></Select></div>
        <div className="space-y-2"><Label htmlFor="support-member">Support member</Label><Select value={staff} onValueChange={setStaff}><SelectTrigger id="support-member"><SelectValue placeholder="Choose support member" /></SelectTrigger><SelectContent>{data.staff.map(row => <SelectItem key={row.id} value={String(row.id)}>{[row.first_name, row.last_name].filter(Boolean).join(' ') || `Support member #${row.id}`}</SelectItem>)}</SelectContent></Select></div>
      </div>
      <Label className="flex items-start gap-3"><Checkbox checked={approved} onCheckedChange={value => setApproved(value === true)} /><span>I approve the selected member to access diagnostics for two hours.</span></Label>
      <Button disabled={busy || !approved || !installation || !staff} onClick={() => runSupportAccessAction(() => api.post('/installations/support-access/', { installation_id: installation, staff_id: Number(staff), scope: 'diagnostics', approved: true }), 'Support access approved for two hours.')}>Approve support window</Button>
      <ul className="space-y-3">{data.authorizations.map(row => {
        const active = !row.revoked_at && new Date(row.valid_until) > new Date();
        return <li key={row.id} className="flex flex-wrap justify-between gap-3 rounded-lg border border-border p-3"><div><p>Support member #{row.staff_id}</p><p className="text-sm text-muted-foreground">{row.revoked_at ? 'Revoked' : active ? 'Active until' : 'Expired'} {!row.revoked_at && new Date(row.valid_until).toLocaleString()}</p></div>{active && <Button disabled={busy} variant="outline" onClick={() => runSupportAccessAction(() => api.delete('/installations/support-access/', { data: { id: row.id } }), 'Support access revoked.')}>Revoke access</Button>}</li>;
      })}</ul>
    </>}
  </CardContent></Card>;
}
