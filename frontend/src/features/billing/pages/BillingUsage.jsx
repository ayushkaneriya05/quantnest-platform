import { LoaderMark } from '@/shared/components/ui/global-loader';
import { formatCurrencyMinorUnits, formatDate as sharedFormatDate, formatNumber } from "@/shared/utils/formatters";
import { useCallback, useEffect, useRef, useState } from 'react';
import { useDispatch } from 'react-redux';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowUpRight, BarChart3, CreditCard, Download, FileText, RefreshCw } from 'lucide-react';
import api from '@/shared/services/api';
import { updateUser } from '@/shared/store/authSlice';
import { loadRazorpaySdk } from '@/shared/services/razorpay';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { Button } from '@/shared/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/shared/components/ui/card';
import { Checkbox } from '@/shared/components/ui/checkbox';
import { Input } from '@/shared/components/ui/input';
import { Label } from '@/shared/components/ui/label';
import { Textarea } from '@/shared/components/ui/textarea';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/shared/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/shared/components/ui/dialog';
import PageTabs from '@/shared/components/PageTabs';
import PlanMarkets from '@/shared/components/PlanMarkets';
import WorkspaceState from '@/shared/components/WorkspaceState';
import { usePlatform } from '@/shared/context/platform';

const formatDate = value => value ? sharedFormatDate(value, { timeZone: 'Asia/Kolkata', dateStyle: 'medium' }) : 'Not scheduled';
const statuses = { created: 'Checkout created', creating: 'Preparing checkout', provider_unknown: 'Awaiting payment provider', captured: 'Payment captured', applied: 'Plan activated', failed: 'Payment failed', authorised: 'Payment authorised', authorized: 'Payment authorised', requested: 'Requested', approved: 'Approved', rejected: 'Declined', refunded: 'Refund completed', processing: 'Processing', pending: 'Pending review' };

export default function BillingUsage() {
  const { refresh: refreshCatalog } = usePlatform();
  const dispatch = useDispatch(), { notify } = useNotifications();
  const [params, setParams] = useSearchParams();
  const tab = ['usage', 'payments'].includes(params.get('tab')) ? params.get('tab') : 'plan';
  const [account, setAccount] = useState(null), [catalog, setCatalog] = useState(null), [refunds, setRefunds] = useState([]);
  const [error, setError] = useState(''), [loading, setLoading] = useState(true), [busy, setBusy] = useState('');
  const [selected, setSelected] = useState(['build', 'pro'].includes(params.get('plan')) ? params.get('plan') : 'build');
  const [automatic, setAutomatic] = useState(false), [checkoutOpen, setCheckoutOpen] = useState(false);
  const [refundPayment, setRefundPayment] = useState(''), [reason, setReason] = useState(''), [confirm, setConfirm] = useState('');
  const key = useRef(crypto.randomUUID()), locked = useRef(false), checkoutActive = useRef(false), loadRequest = useRef(0);
  const loadBillingData = useCallback(async () => {
    const request = ++loadRequest.current; setLoading(true);
    try {
      const [a, c, r] = await Promise.all([api.get('/billing/account/'), refreshCatalog(), api.get('/billing/refund-requests/')]);
      if (request !== loadRequest.current) return;
      if (!c) throw new Error('Current plans could not be loaded. Please retry.');
      setAccount(a.data); setCatalog(c); setRefunds(r.data); setError('');
      dispatch(updateUser({ workspace_plan: { code: a.data.plan.code, name: a.data.plan.name } }));
    } catch (failure) { if (request === loadRequest.current) setError(getApiErrorMessage(failure)); }
    finally { if (request === loadRequest.current) setLoading(false); }
  }, [dispatch, refreshCatalog]);
  useEffect(() => { loadBillingData(); }, [loadBillingData]);
  const runBillingAction = async (name, callback) => {
    if (locked.current || checkoutActive.current) return;
    locked.current = true; setBusy(name);
    try { await callback(); await loadBillingData(); }
    catch (failure) { notify.error(getApiErrorMessage(failure)); }
    finally { locked.current = false; setBusy(''); }
  };
  function selectPlan(value) { setSelected(value); setAutomatic(false); key.current = crypto.randomUUID(); }
  async function startPlanCheckout() {
    const reviewed = account.checkout_terms[selected];
    const automaticRenewal = automatic && reviewed.automatic_renewal_available;
    const { data } = await api.post(automaticRenewal ? '/billing/checkout/' : '/billing/renew/', { plan: selected, catalog_revision: catalog.revision, approved_total_minor: reviewed.total_minor, renewal_consent: automaticRenewal }, { headers: { 'Idempotency-Key': key.current } });
    if (data.status === 'provider_unknown' || (!data.order_id && !data.subscription_id)) throw new Error('This checkout is awaiting provider reconciliation. Check payment history before trying another payment.');
    const Razorpay = await loadRazorpaySdk();
    const finishCheckout = () => { checkoutActive.current = false; setCheckoutOpen(false); };
    const checkout = new Razorpay({ key: data.key_id, order_id: data.order_id || undefined, subscription_id: data.subscription_id || undefined, amount: data.total_minor, currency: data.currency, name: 'QuantNest', description: `${catalog.plans[selected].name} Workspace`, handler: async result => {
      setBusy('verify');
      try {
        const response = await api.post('/billing/verify/', { payment_id: result.razorpay_payment_id });
        notify.info(response.data.applied ? 'Payment verified. Your purchased period is active.' : 'Payment is awaiting capture. Its status will be reconciled.');
        key.current = crypto.randomUUID(); await loadBillingData();
      } catch (failure) { notify.error(getApiErrorMessage(failure)); }
      finally { setBusy(''); finishCheckout(); }
    }, modal: { ondismiss: () => { finishCheckout(); loadBillingData(); } } });
    checkout.on('payment.failed', () => { notify.error('Payment did not complete. Check payment history before retrying.'); loadBillingData(); });
    checkoutActive.current = true; setCheckoutOpen(true);
    try { checkout.open(); } catch (failure) { finishCheckout(); throw failure; }
  }
  async function downloadInvoice(invoice, printable) {
    const tabWindow = printable ? window.open('about:blank', '_blank') : null;
    if (tabWindow) tabWindow.opener = null;
    try {
      const { data } = await api.get(`/billing/invoices/${invoice.id}/${printable ? '?download=html' : ''}`, printable ? { responseType: 'blob' } : {});
      const url = URL.createObjectURL(printable ? data : new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
      if (tabWindow) tabWindow.location.replace(url);
      else { const anchor = document.createElement('a'); anchor.href = url; anchor.download = `${invoice.number}.${printable ? 'html' : 'json'}`; anchor.click(); }
      setTimeout(() => URL.revokeObjectURL(url), printable ? 60000 : 1000);
    } catch (failure) { tabWindow?.close(); throw failure; }
  }
  if (!account || !catalog) return <div className="container-padding py-5"><WorkspaceState loading={loading} error={error} title={error ? undefined : 'Loading billing and usage'} onRetry={error ? loadBillingData : undefined} /></div>;
  const plan = catalog.plans[selected], reviewed = account.checkout_terms[selected];
  const labels = catalog.limit_labels;
  const disabled = Boolean(busy) || checkoutOpen || loading;
  const setTab = value => setParams(current => { const next = new URLSearchParams(current); next.set('tab', value); return next; }, { replace: true });
  return <div className="container-padding space-y-5 py-5">
    <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card p-4"><div><p className="text-xs text-muted-foreground">Current plan</p><h2 className="mt-1 text-xl font-semibold">{account.plan.name}</h2><p className="mt-1 text-xs text-muted-foreground">{account.period_start && account.period_end ? <>Allowance period: {formatDate(account.period_start)} – {formatDate(account.period_end)}</> : 'No allowance period'}</p></div><Button variant="outline" size="sm" disabled={disabled} onClick={loadBillingData}>{loading ? <LoaderMark className="h-4 w-4" /> : <RefreshCw className="h-4 w-4" />}Refresh</Button></section>
    <PageTabs label="Billing sections" value={tab} onValueChange={setTab} className="w-fit" items={[{ value: 'plan', label: 'Plan and renewal', icon: CreditCard }, { value: 'usage', label: 'Usage and limits', icon: BarChart3 }, { value: 'payments', label: 'Payments and invoices', icon: FileText }]} />
    {account.period_start && account.limits_enforced === false && <p role="status" className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm text-warning-text">Usage is recorded, but plan limits are not enforced in this workspace.</p>}
    {tab !== 'payments' && <section className="rounded-xl border bg-card p-4" aria-label="Execution scopes">
      <h2 className="text-sm font-semibold">Execution in this workspace</h2>
      <p className="mt-1 text-xs text-muted-foreground">Available execution follows the enabled scopes below. Supported instruments, account permissions and trading controls still apply.</p>
      <div className="mt-3 flex flex-wrap gap-2">{catalog.execution_enabled_scopes.map(scope => <span key={scope} className="rounded-lg border border-success/30 px-3 py-2 text-xs text-success">{scope === 'paper' ? 'Paper and simulated Terminal' : 'Live execution'} · Enabled</span>)}</div>
    </section>}
    {error && <WorkspaceState error={error} onRetry={loadBillingData} />}
    {tab === 'plan' && <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
      <Card><CardHeader className="p-5 pb-3"><CardTitle className="text-base">Review a plan</CardTitle><CardDescription>More capacity for research, historical testing and Paper practice.</CardDescription></CardHeader><CardContent className="space-y-4 px-5 pb-5">
        <Label htmlFor="billing-plan">Workspace plan</Label><Select value={selected} onValueChange={selectPlan} disabled={disabled}><SelectTrigger id="billing-plan"><SelectValue /></SelectTrigger><SelectContent>{['build', 'pro'].map(code => <SelectItem key={code} value={code}>{catalog.plans[code].name} · {formatCurrencyMinorUnits(catalog.plans[code].price_minor)} / month</SelectItem>)}</SelectContent></Select>
        <div className="rounded-lg border bg-muted/30 p-4"><PlanMarkets markets={plan.markets} /><p className="mt-3 text-xs leading-5 text-muted-foreground">NSE stocks are available. Futures and options are coming soon. Public subscriptions cover simulation through Paper; Customer Live trading is not currently available.</p></div>
        <dl className="space-y-2 text-sm"><div className="flex justify-between gap-2"><dt className="text-muted-foreground">Monthly plan</dt><dd>{formatCurrencyMinorUnits(reviewed.base_minor)}</dd></div><div className="flex justify-between gap-2"><dt className="text-muted-foreground">Applicable tax</dt><dd>{formatCurrencyMinorUnits(reviewed.tax_minor)}</dd></div><div className="flex justify-between gap-2 border-t pt-3 font-semibold"><dt>Total per monthly period</dt><dd>{formatCurrencyMinorUnits(reviewed.total_minor)}</dd></div></dl>
        <Label className="flex items-start gap-3 rounded-lg border p-3"><Checkbox checked={automatic && reviewed.automatic_renewal_available} disabled={disabled || !reviewed.automatic_renewal_available} onCheckedChange={value => { setAutomatic(value === true); key.current = crypto.randomUUID(); }} /><span className="text-sm font-normal leading-6">{reviewed.automatic_renewal_available ? <>Enable automatic monthly renewal at {formatCurrencyMinorUnits(reviewed.total_minor)}. Leave unchecked to pay manually.</> : 'Manual payment is available when checkout is open. Automatic renewal is not configured for this price.'}</span></Label>
        {reviewed.price_protected_until && <p className="text-xs text-muted-foreground">Founding price protected until {formatDate(reviewed.price_protected_until)}.</p>}
        <div className="flex flex-wrap items-center gap-3"><Button disabled={disabled || !plan.checkout_available} onClick={() => runBillingAction('checkout', startPlanCheckout)}>{busy === 'checkout' || busy === 'verify' ? <LoaderMark className="h-4 w-4" /> : <CreditCard className="h-4 w-4" />}{checkoutOpen ? 'Checkout is open' : plan.checkout_available ? 'Continue to secure payment' : 'Plan not open yet'}</Button><Link className="inline-flex items-center gap-1 text-sm text-brand underline" to="/pricing/">Compare plans<ArrowUpRight className="h-3.5 w-3.5" /></Link></div>
        <p className="text-xs leading-5 text-muted-foreground">No usage rollover or automatic overages. First purchase has a seven-day refund window, alongside applicable remedies.</p>
      </CardContent></Card>
      <Card><CardHeader className="p-5 pb-3"><CardTitle className="text-base">Your next renewal</CardTitle><CardDescription>Changes apply to a future period.</CardDescription></CardHeader><CardContent className="space-y-4 px-5 pb-5"><dl className="space-y-3 text-sm"><div className="flex justify-between"><dt className="text-muted-foreground">Payment method</dt><dd>{account.renewal.automatic ? 'Automatic renewal' : 'Manual payment'}</dd></div><div className="flex justify-between"><dt className="text-muted-foreground">Current period ends</dt><dd>{formatDate(account.period_end)}</dd></div>{account.renewal.scheduled_plan && <div className="flex justify-between"><dt className="text-muted-foreground">Scheduled plan</dt><dd>{catalog.plans[account.renewal.scheduled_plan].name}</dd></div>}</dl>
        <p className="text-sm leading-6 text-muted-foreground">Cancellation keeps your current paid period. Saved work and recorded results remain available. Manual payments require another reviewed checkout.</p>
        <div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" disabled={disabled || !plan.checkout_available || !account.renewal.automatic || (selected === account.plan.code && !account.renewal.scheduled_plan)} onClick={() => setConfirm('change')}>Schedule {plan.name}</Button><Button size="sm" variant="outline" disabled={disabled || !account.renewal.automatic} onClick={() => setConfirm('cancel')}>Cancel future renewal</Button></div><Link to="/support" className="inline-block text-sm text-brand underline">Ask about your subscription</Link>
      </CardContent></Card>
    </div>}
    {tab === 'usage' && <div className="space-y-5">{[
      { kind: 'period', title: 'This period', description: 'Successful work and reservations count towards these allowances. AI credits settle from reported tokens after a successful answer.' },
      { kind: 'inventory', title: 'Saved and deployed', description: 'Current saved items and active Paper deployments. These are capacity limits.' },
      { kind: 'per_request', title: 'Per-request limits', description: 'Maximum size of one request. These are not remaining credits.' },
    ].map(group => <section key={group.kind}><h2 className="text-base font-semibold">{group.title}</h2><p className="mt-1 text-xs text-muted-foreground">{group.description}</p><div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{Object.entries(account.usage).filter(([, value]) => value.kind === group.kind).map(([feature, value]) => {
      const unlimited = value.limit === null;
      const used = value.used + value.reserved;
      const percent = value.limit > 0 ? Math.min(100, Math.round(used / value.limit * 100)) : 0;
      return <div className="min-w-0 rounded-xl border bg-card p-4" key={feature}>
        <h3 className="text-xs text-muted-foreground">{labels[feature]}</h3>
        <p className="mt-2 text-xl font-semibold tabular-nums">{unlimited ? 'Unlimited' : <>{group.kind === 'per_request' ? 'Up to ' : `${formatNumber((value.used) / (value.display_divisor || 1), { minimumFractionDigits: 0, maximumFractionDigits: 3 })} / `}{formatNumber((value.limit) / (value.display_divisor || 1), { minimumFractionDigits: 0, maximumFractionDigits: 3 })}</>}</p>
        {group.kind !== 'per_request' && (unlimited
          ? <p className="mt-2 text-xs text-muted-foreground">{value.used === null ? 'Usage is not metered.' : `${formatNumber((used) / (value.display_divisor || 1), { minimumFractionDigits: 0, maximumFractionDigits: 3 })} used or reserved`}</p>
          : <><div role="progressbar" aria-label={labels[feature]} aria-valuemin={0} aria-valuemax={value.limit || 1} aria-valuenow={Math.min(value.limit || 1, used)} className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted"><div className={`h-full rounded-full ${used >= value.limit ? 'bg-warning' : 'bg-brand'}`} style={{ width: `${percent}%` }} /></div><p className="mt-2 text-xs text-muted-foreground">{value.reserved ? `${formatNumber((value.reserved) / (value.display_divisor || 1), { minimumFractionDigits: 0, maximumFractionDigits: 3 })} reserved · ` : ''}{formatNumber((Math.max(0, value.limit - used)) / (value.display_divisor || 1), { minimumFractionDigits: 0, maximumFractionDigits: 3 })} {group.kind === 'inventory' ? 'capacity left' : 'remaining'}</p></>)}
      </div>;
    })}</div></section>)}<p className="text-xs text-muted-foreground">Unused monthly allowances do not roll over. Backtest credits are reviewed before acceptance, charged on success and restored on failure or cancellation.</p></div>}
    {tab === 'payments' && <div className="space-y-5"><Card><CardHeader className="p-5 pb-3"><CardTitle className="text-base">Invoices</CardTitle><CardDescription>Issued after a payment is captured. The printable invoice can be saved as PDF from your browser.</CardDescription></CardHeader><CardContent className="space-y-3 px-5 pb-5">{!account.invoices.length ? <p className="text-sm text-muted-foreground">No invoices yet. Your first captured payment will appear here.</p> : account.invoices.map(invoice => <div key={invoice.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3"><div><h3 className="text-sm font-medium">{invoice.number}</h3><p className="mt-1 text-xs text-muted-foreground">{formatDate(invoice.issued_at)} · {formatCurrencyMinorUnits(invoice.snapshot.total_minor)}</p></div><div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" disabled={disabled} onClick={() => runBillingAction('invoice', () => downloadInvoice(invoice, true))}><FileText className="h-4 w-4" />Printable invoice</Button><Button size="sm" variant="ghost" disabled={disabled} onClick={() => runBillingAction('invoice', () => downloadInvoice(invoice, false))}><Download className="h-4 w-4" />JSON record</Button></div></div>)}</CardContent></Card>
      <Card><CardHeader className="p-5 pb-3"><CardTitle className="text-base">Recent checkout activity</CardTitle></CardHeader><CardContent className="space-y-3 px-5 pb-5">{!account.checkouts.length ? <p className="text-sm text-muted-foreground">You have not started a checkout.</p> : account.checkouts.map(attempt => <div key={attempt.id} className="flex flex-wrap items-start justify-between gap-2 rounded-lg border p-3"><div><p className="text-sm font-medium">{catalog.plans[attempt.plan]?.name || attempt.plan} · {formatCurrencyMinorUnits(attempt.total_minor)}</p><p className="mt-1 break-all text-xs text-muted-foreground">Reference #{attempt.id}{attempt.order_id && ` · ${attempt.order_id}`}</p></div><span className="text-xs text-muted-foreground">{statuses[attempt.status] || attempt.status.replaceAll('_', ' ')}</span></div>)}</CardContent></Card>
      <Card><CardHeader className="p-5 pb-3"><CardTitle className="text-base">Request a refund</CardTitle><CardDescription>Use the payment reference from your receipt, such as pay_… . Requests are reviewed against the refund policy.</CardDescription></CardHeader><CardContent className="grid gap-5 px-5 pb-5 lg:grid-cols-2"><form className="space-y-3" onSubmit={event => { event.preventDefault(); runBillingAction('refund', async () => { await api.post('/billing/refund-requests/', { payment_id: refundPayment.trim(), reason: reason.trim() }); setRefundPayment(''); setReason(''); notify.success('Refund request submitted.'); }); }}><div className="space-y-2"><Label htmlFor="refund-reference">Payment reference</Label><Input id="refund-reference" required maxLength={100} placeholder="pay_…" value={refundPayment} onChange={event => setRefundPayment(event.target.value)} disabled={disabled} /></div><div className="space-y-2"><Label htmlFor="refund-reason">Reason</Label><Textarea id="refund-reason" required minLength={5} maxLength={3000} rows={3} value={reason} onChange={event => setReason(event.target.value)} disabled={disabled} /></div><Button size="sm" type="submit" disabled={disabled || !refundPayment.trim() || reason.trim().length < 5}>Submit request</Button></form><section><h3 className="mb-3 text-sm font-medium">Your requests</h3>{!refunds.length ? <p className="text-sm text-muted-foreground">No refund requests yet.</p> : <div className="space-y-3">{refunds.map(row => <div key={row.id} className="rounded-lg border p-3 text-sm"><p className="flex justify-between gap-2"><strong>Request #{row.id}</strong><span>{statuses[row.status] || row.status.replaceAll('_', ' ')}</span></p><p className="mt-1 text-xs text-muted-foreground">{formatCurrencyMinorUnits(row.amount_minor)} · {formatDate(row.created_at)}</p><p className="mt-2 break-words text-xs leading-5 text-muted-foreground">{row.reason}</p>{row.credit_note?.number && <p className="mt-1 text-xs">Credit note: {row.credit_note.number}</p>}</div>)}</div>}</section></CardContent></Card>
    </div>}
    <Dialog open={Boolean(confirm)} onOpenChange={open => { if (!busy && !open) setConfirm(''); }}><DialogContent><DialogHeader><DialogTitle>{confirm === 'cancel' ? 'Cancel automatic renewal?' : `Schedule ${plan.name}?`}</DialogTitle><DialogDescription>{confirm === 'cancel' ? `Your current paid period remains active until ${formatDate(account.period_end)}. Future automatic renewal will be cancelled.` : `At the next renewal, your plan will change to ${plan.name} at ${formatCurrencyMinorUnits(reviewed.total_minor)} per month including applicable tax. New limits apply then.`}</DialogDescription></DialogHeader><DialogFooter><Button variant="outline" disabled={disabled} onClick={() => setConfirm('')}>Keep current renewal</Button><Button disabled={disabled} onClick={() => runBillingAction('renewal', async () => { await api.post(confirm === 'cancel' ? '/billing/cancel/' : '/billing/change/', confirm === 'cancel' ? {} : { plan: selected, approved_total_minor: reviewed.total_minor }); setConfirm(''); notify.success('Your renewal preference has been saved.'); })}>Confirm change</Button></DialogFooter></DialogContent></Dialog>
  </div>;
}
