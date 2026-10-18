import { useRef, useState } from 'react';
import { useDispatch } from 'react-redux';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowUpRight, BookOpen, CreditCard, Download, LifeBuoy, Loader2 } from 'lucide-react';
import api from '@/shared/services/api';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { logout } from '@/shared/store/authSlice';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { Label } from '@/shared/components/ui/label';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/shared/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/shared/components/ui/dialog';
import WorkspaceState from '@/shared/components/WorkspaceState';
import EmailPreferences from './email-preferences';

const resources = { live_positions: 'Live positions', live_orders: 'Pending Live orders', paper_positions: 'Paper positions', paper_orders: 'Pending Paper orders', terminal_positions: 'Terminal positions', terminal_orders: 'Open Terminal orders' };

export default function AccountTab() {
  const dispatch = useDispatch(), navigate = useNavigate();
  const { notify } = useNotifications();
  const [dialog, setDialog] = useState(''), [confirmation, setConfirmation] = useState('');
  const [preflight, setPreflight] = useState(null), [checking, setChecking] = useState(false);
  const [checkError, setCheckError] = useState(''), [busy, setBusy] = useState('');
  const locked = useRef(false), checkRequest = useRef(0);
  async function check() {
    const request = ++checkRequest.current; setChecking(true); setCheckError(''); setPreflight(null);
    try { const { data } = await api.get('/users/account/preflight/'); if (request === checkRequest.current) setPreflight(data); }
    catch (failure) { if (request === checkRequest.current) setCheckError(getApiErrorMessage(failure)); }
    finally { if (request === checkRequest.current) setChecking(false); }
  }
  function open(action) { setDialog(action); setConfirmation(''); check(); }
  async function exportAccount() {
    if (locked.current) return; locked.current = true; setBusy('export');
    try {
      const { data } = await api.post('/support/account/export/', {}, { responseType: 'blob' });
      const url = URL.createObjectURL(data), link = document.createElement('a');
      link.href = url; link.download = 'quantnest-account-export.json'; link.click(); notify.success('Your account export is ready to download.'); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (failure) { notify.error(getApiErrorMessage(failure)); }
    finally { locked.current = false; setBusy(''); }
  }
  async function disableAccount() {
    if (locked.current || !preflight?.can_shutdown || checking || (dialog === 'delete' && confirmation !== 'DELETE')) return;
    locked.current = true; setBusy(dialog);
    try {
      if (dialog === 'delete') await api.delete('/users/account/'); else await api.post('/users/account/deactivate/');
      dispatch(logout()); notify.success(dialog === 'delete' ? 'Your account has been disabled and your sign-in identity erased.' : 'Your account has been deactivated. Contact support to request reactivation.'); navigate('/login', { replace: true });
    } catch (failure) { notify.error(getApiErrorMessage(failure)); await check(); }
    finally { locked.current = false; setBusy(''); }
  }
  return <div className="space-y-5">
    <div className="grid gap-3 md:grid-cols-3">{[
      { to: '/settings/billing', icon: CreditCard, title: 'Billing and Usage', text: 'Plan, allowances, payments and renewal.' },
      { to: '/support', icon: LifeBuoy, title: 'Support', text: 'Requests, replies and project quotations.' },
      { to: '/docs/getting-started/', icon: BookOpen, title: 'User guide', text: 'Choose a first task and learn each workflow.' },
    ].map(item => <Link key={item.to} to={item.to} className="group flex min-w-0 items-start gap-3 rounded-xl border bg-card p-4 transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><item.icon className="mt-0.5 h-5 w-5 shrink-0 text-brand" /><div className="min-w-0 flex-1"><h2 className="text-sm font-semibold">{item.title}</h2><p className="mt-1 text-xs leading-5 text-muted-foreground">{item.text}</p></div><ArrowUpRight className="h-4 w-4 shrink-0 text-muted-foreground" /></Link>)}</div>
    <EmailPreferences />
    <Card><CardContent className="flex flex-wrap items-center justify-between gap-4 p-5"><div><h2 className="text-base font-semibold">Export your account records</h2><p className="mt-1 text-sm text-muted-foreground">Download your strategies, execution records, reviews and payment records. Secrets and recovery codes are excluded.</p><p className="mt-1 text-xs text-muted-foreground">Up to 1,000 records per category and 100 strategies, within 10 MiB. Limited to two exports per day.</p></div><Button variant="outline" size="sm" disabled={Boolean(busy)} onClick={exportAccount}>{busy === 'export' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}Export records</Button></CardContent></Card>
    <Card className="border-destructive/30"><CardHeader className="p-5 pb-3"><CardTitle className="text-base">Account access</CardTitle><CardDescription>Settle open positions and pending orders in Terminal, Paper and Live before disabling access.</CardDescription></CardHeader><CardContent className="grid gap-4 px-5 pb-5 md:grid-cols-2">{[
      { action: 'deactivate', title: 'Deactivate your account', text: 'Disable sign-in and stop new work. Your records remain saved. Contact support to request reactivation.', button: 'Deactivate account' },
      { action: 'delete', title: 'Erase your sign-in identity', text: 'Permanently disable sign-in and anonymise your identity. Required payment and execution records are retained. This action cannot be reversed.', button: 'Delete account' },
    ].map(item => <section key={item.action} className="space-y-3 rounded-lg border p-4"><h3 className="text-sm font-semibold">{item.title}</h3><p className="text-sm leading-6 text-muted-foreground">{item.text}</p><Button size="sm" variant={item.action === 'delete' ? 'destructive' : 'outline'} disabled={Boolean(busy)} onClick={() => open(item.action)}>{item.button}</Button></section>)}</CardContent></Card>
    <Dialog open={Boolean(dialog)} onOpenChange={value => { if (!busy && !value) { setDialog(''); ++checkRequest.current; } }}><DialogContent className="max-w-lg"><DialogHeader><DialogTitle>{dialog === 'delete' ? 'Delete your account?' : 'Deactivate your account?'}</DialogTitle><DialogDescription>{dialog === 'delete' ? 'Your sign-in identity will be erased. Required payment and execution records are retained. Export your records before continuing.' : 'Sign-in and new work will be disabled. Your saved records remain available if support reactivates the account.'}</DialogDescription></DialogHeader>
      {checking ? <WorkspaceState loading title="Checking trading activity" /> : checkError ? <WorkspaceState error={checkError} onRetry={check} /> : preflight && <div className="space-y-3"><p className={`text-sm ${preflight.can_shutdown ? 'text-muted-foreground' : 'text-destructive-text'}`}>{preflight.can_shutdown ? 'No open positions or pending orders were found.' : 'Settle the following activity before continuing. This action does not close or cancel your trades.'}</p>{Object.entries(preflight.exposure).filter(([, count]) => count > 0).map(([key, count]) => <div key={key} className="flex justify-between rounded-lg border px-3 py-2 text-sm"><span>{resources[key]}</span><strong>{count}</strong></div>)}<p className="text-xs leading-5 text-muted-foreground">Execution sessions will stop, broker connections will be disabled and running analysis will be cancelled. Cancel automatic subscription renewal in Billing and Usage before continuing. The server checks activity again when you confirm.</p></div>}
      {preflight?.automatic_renewal && <p className="text-sm text-destructive-text">Automatic renewal is still enabled. <Link className="underline" to="/settings/billing">Cancel future renewal in Billing and Usage</Link>, then check again. <Button size="sm" variant="outline" onClick={check} disabled={checking || Boolean(busy)}>Check again</Button></p>}
      {dialog === 'delete' && <div className="space-y-2"><Label htmlFor="delete-confirmation">Type DELETE to confirm</Label><Input id="delete-confirmation" value={confirmation} onChange={event => setConfirmation(event.target.value)} autoComplete="off" disabled={Boolean(busy) || !preflight?.can_shutdown} /></div>}
      <DialogFooter><Button variant="outline" disabled={Boolean(busy)} onClick={() => { setDialog(''); }}>Keep account</Button><Button variant="destructive" onClick={disableAccount} disabled={Boolean(busy) || checking || !preflight?.can_shutdown || (dialog === 'delete' && confirmation !== 'DELETE')}>{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}{dialog === 'delete' ? 'Delete account' : 'Deactivate account'}</Button></DialogFooter>
    </DialogContent></Dialog>
  </div>;
}
