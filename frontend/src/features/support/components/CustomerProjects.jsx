import { useCallback, useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { ArrowLeft, FileCheck2, Loader2 } from 'lucide-react';
import api from '@/shared/services/api';
import { Button } from '@/shared/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/shared/components/ui/card';
import { Checkbox } from '@/shared/components/ui/checkbox';
import { Label } from '@/shared/components/ui/label';
import WorkspaceState from '@/shared/components/WorkspaceState';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';
import { loadRazorpaySdk } from '@/shared/services/razorpay';
import { useNotifications } from '@/shared/hooks/useNotifications';

const formatCurrencyMinorUnits = (amount, currency = 'INR') => new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format(amount / 100);
const formatLabel = value => value.replaceAll('_', ' ').replace(/^./, letter => letter.toUpperCase());
function TermValue({ value }) {
  if (value === null || value === '') return <span>Not specified</span>;
  if (Array.isArray(value)) return <ul className="list-inside list-disc space-y-1">{value.map((item, index) => <li key={index}><TermValue value={item} /></li>)}</ul>;
  if (typeof value === 'object') return <dl className="space-y-1">{Object.entries(value).map(([key, item]) => <div key={key}><dt className="inline font-medium">{formatLabel(key)}: </dt><dd className="inline"><TermValue value={item} /></dd></div>)}</dl>;
  return <span>{typeof value === 'boolean' ? value ? 'Yes' : 'No' : String(value)}</span>;
}
TermValue.propTypes = { value: PropTypes.any };

export default function CustomerProjects() {
  const { notify } = useNotifications();
  const [quotes, setQuotes] = useState([]), [quote, setQuote] = useState(null), [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false), [loading, setLoading] = useState(true), [error, setError] = useState(''), [checkoutOpen, setCheckoutOpen] = useState(false);
  const locked = useRef(false), checkoutActive = useRef(false);
  const loadProjects = useCallback(async () => {
    setLoading(true);
    try { const { data } = await api.get('/support/quotations/'); setQuotes(data); setError(''); }
    catch (failure) { setError(getApiErrorMessage(failure)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { loadProjects(); }, [loadProjects]);
  const openQuotation = async id => { const { data } = await api.get(`/support/quotations/${id}/accept/`); setQuote(data); setAccepted(false); };
  async function runProjectAction(callback) {
    if (locked.current || checkoutActive.current) return;
    locked.current = true; setBusy(true); setError('');
    try { await callback(); await loadProjects(); }
    catch (failure) { notify.error(getApiErrorMessage(failure)); }
    finally { locked.current = false; setBusy(false); }
  }
  async function startMilestoneCheckout(milestone) {
    const quoteId = quote.id;
    const { data } = await api.post(`/support/milestones/${milestone.id}/checkout/`, { approved_total_minor: milestone.amount_minor }, { headers: { 'Idempotency-Key': `milestone-${milestone.id}` } });
    if (data.status === 'provider_unknown' || !data.order_id) throw new Error('This payment is awaiting provider reconciliation. Contact support before attempting another payment.');
    const Razorpay = await loadRazorpaySdk();
    const finishCheckout = () => { checkoutActive.current = false; setCheckoutOpen(false); };
    const checkout = new Razorpay({ key: data.key_id, order_id: data.order_id, amount: data.total_minor, currency: data.currency, name: 'QuantNest', description: milestone.title,
      handler: async result => {
        setBusy(true);
        try { const response = await api.post('/billing/verify/', { payment_id: result.razorpay_payment_id }); notify.info(response.data.applied ? 'Milestone payment verified.' : 'Payment is awaiting capture. Its status will be reconciled.'); await openQuotation(quoteId); await loadProjects(); }
        catch (failure) { notify.error(getApiErrorMessage(failure)); }
        finally { setBusy(false); finishCheckout(); }
      }, modal: { ondismiss: () => { finishCheckout(); loadProjects(); openQuotation(quoteId).catch(failure => notify.error(getApiErrorMessage(failure))); } },
    });
    checkout.on('payment.failed', () => notify.error('Payment did not complete. Check the milestone status before retrying.'));
    checkoutActive.current = true; setCheckoutOpen(true);
    try { checkout.open(); } catch (failure) { finishCheckout(); throw failure; }
  }
  const disabled = busy || loading || checkoutOpen;
  return <Card><CardHeader className="p-5 pb-3"><CardTitle className="text-base">Quotations and milestones</CardTitle><CardDescription>Review agreed scope and track payments for custom development or a Private installation.</CardDescription></CardHeader><CardContent className="space-y-4 px-5 pb-5">
    {error && <WorkspaceState error={error} onRetry={loadProjects} />}
    {loading && !quote && !quotes.length && <WorkspaceState loading />}
    {!loading && !quote && !quotes.length && !error && <WorkspaceState title="No project quotations yet" description="Create a Custom development or Private deployment request. Your agreed requirements and staff-issued quotation will appear here." />}
    {!quote && <div className="grid gap-3 md:grid-cols-2">{quotes.map(row => <button disabled={disabled} className="flex items-center gap-3 rounded-xl border p-4 text-left transition-colors hover:bg-muted/40 focus-ring disabled:opacity-50" key={row.id} onClick={() => runProjectAction(() => openQuotation(row.id))}><FileCheck2 className="h-5 w-5 shrink-0 text-brand" /><span className="min-w-0"><strong className="text-sm">Quotation #{row.id}</strong><span className="mt-1 block text-xs text-muted-foreground">Revision {row.revision} · {formatCurrencyMinorUnits(row.total_minor, row.currency)}</span></span></button>)}</div>}
    {quote && <section className="space-y-4"><Button size="sm" variant="ghost" disabled={disabled} onClick={() => setQuote(null)}><ArrowLeft className="h-4 w-4" />All quotations</Button><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-lg font-semibold">Quotation #{quote.id}</h3><p className="text-lg font-semibold tabular-nums">{formatCurrencyMinorUnits(quote.total_minor, quote.currency)}</p></div><p className="text-xs text-muted-foreground">Revision {quote.revision} · {quote.accepted_at ? `Accepted ${new Date(quote.accepted_at).toLocaleDateString('en-IN')}` : `Valid until ${new Date(quote.valid_until).toLocaleString('en-IN')}`}</p>
      <div className="grid gap-3 md:grid-cols-2">{['scope', 'acceptance_criteria', 'ownership_terms', 'support_allowance'].map(name => <div className="rounded-lg border p-4" key={name}><h4 className="text-sm font-medium">{formatLabel(name)}</h4><p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-muted-foreground">{quote[name] || 'Not specified in this quotation.'}</p></div>)}</div>
      <section className="rounded-lg border p-4"><h4 className="mb-3 text-sm font-medium">Commercial terms</h4><div className="space-y-2 break-words text-sm text-muted-foreground"><TermValue value={quote.terms} /></div></section>
      {!quote.accepted_at ? <div className="space-y-3"><Label className="flex items-start gap-3"><Checkbox checked={accepted} disabled={disabled} onCheckedChange={value => setAccepted(value === true)} /><span className="text-sm font-normal leading-6">I accept this scope, acceptance criteria and commercial terms.</span></Label>{new Date(quote.valid_until) <= new Date() && <p className="text-sm text-destructive-text">This quotation has expired. Request an updated revision in your support conversation.</p>}<Button size="sm" disabled={disabled || !accepted || new Date(quote.valid_until) <= new Date()} onClick={() => runProjectAction(async () => { await api.post(`/support/quotations/${quote.id}/accept/`, { accepted: true }); await openQuotation(quote.id); notify.success('Quotation accepted.'); })}>{busy && <Loader2 className="h-4 w-4 animate-spin" />}Accept quotation</Button></div> : <p className="text-xs leading-5 text-muted-foreground">The accepted scope is saved. Contact support to agree any changes.</p>}
      {quote.milestones.length > 0 && <section className="space-y-3"><h4 className="text-sm font-medium">Payment milestones</h4>{quote.milestones.map(row => <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-4" key={row.id}><div><h5 className="text-sm font-medium">{row.title}</h5><p className="mt-1 text-xs text-muted-foreground">{formatCurrencyMinorUnits(row.amount_minor, quote.currency)} · {row.paid_at ? 'Payment captured' : row.approved_for_payment ? 'Approved for payment' : 'Awaiting milestone approval'}</p></div>{!row.paid_at && <Button size="sm" disabled={disabled || !row.approved_for_payment} onClick={() => runProjectAction(() => startMilestoneCheckout(row))}>{checkoutOpen ? 'Checkout is open' : 'Pay reviewed amount'}</Button>}</div>)}</section>}
    </section>}
  </CardContent></Card>;
}
