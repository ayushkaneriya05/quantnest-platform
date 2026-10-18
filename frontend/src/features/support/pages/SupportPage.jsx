import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ArrowLeft, ChevronLeft, ChevronRight, Loader2, MessageSquare, Plus, RefreshCw, Send } from 'lucide-react';
import api from '@/shared/services/api';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { Textarea } from '@/shared/components/ui/textarea';
import { Label } from '@/shared/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/shared/components/ui/dialog';
import WorkspaceState from '@/shared/components/WorkspaceState';
import { useSupportOptions } from '@/shared/hooks/useSupportOptions';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';
import { useNotifications } from '@/shared/hooks/useNotifications';
import CustomerProjects from '../components/CustomerProjects';
import PrivateSupportAccess from '../components/PrivateSupportAccess';

const formatDateTime = value => value ? new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '';
export default function SupportPage() {
  const { notify } = useNotifications();
  const [params] = useSearchParams();
  const { requestTypes, requestLabels, ticketStatusLabels, contact, loading: optionsLoading, error: optionsError, refresh: refreshOptions } = useSupportOptions();
  const [tab, setTab] = useState('requests');
  const [page, setPage] = useState(1);
  const [history, setHistory] = useState({ results: [], count: 0, next: null, previous: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [reply, setReply] = useState('');
  const [modal, setModal] = useState(false);
  const [kind, setKind] = useState(params.get('request') || 'support');
  const selectedKind = requestLabels[kind] ? kind : requestTypes[0]?.value || '';
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const mutation = useRef(false);
  const listRequest = useRef(0);
  const detailRequest = useRef(0);
  const loadSupportRequests = useCallback(async () => {
    const request = ++listRequest.current; setLoading(true); setError('');
    try {
      const { data } = await api.get('/support/tickets/', { params: { page } });
      if (request === listRequest.current) setHistory(data);
    } catch (failure) { if (request === listRequest.current) setError(getApiErrorMessage(failure)); }
    finally { if (request === listRequest.current) setLoading(false); }
  }, [page]);
  useEffect(() => { loadSupportRequests(); }, [loadSupportRequests]);
  useEffect(() => () => { detailRequest.current++; }, []);
  useEffect(() => { setKind(params.get('request') || 'support'); }, [params]);
  const openSupportRequest = async ticket => {
    const request = ++detailRequest.current; if (selected?.id !== ticket.id) setReply(''); setSelected(ticket); setDetailLoading(true); setDetailError('');
    try { const { data } = await api.get(`/support/tickets/${ticket.id}/`); if (request === detailRequest.current) setSelected(data); }
    catch (failure) { if (request === detailRequest.current) setDetailError(getApiErrorMessage(failure)); }
    finally { if (request === detailRequest.current) setDetailLoading(false); }
  };
  async function submitSupportRequest(event) {
    event.preventDefault(); if (mutation.current || !selectedKind || optionsError) return;
    mutation.current = true; setBusy(true);
    try {
      const { data } = await api.post('/support/tickets/', { subject: subject.trim(), body: body.trim(), request_type: selectedKind });
      detailRequest.current++; setDetailLoading(false); setSelected(data); setModal(false); setSubject(''); setBody(''); setReply(''); setDetailError('');
      notify.success('Your support request has been submitted.');
      if (page !== 1) setPage(1); else await loadSupportRequests();
    } catch (failure) { notify.error(getApiErrorMessage(failure)); }
    finally { mutation.current = false; setBusy(false); }
  }
  async function submitSupportReply(event) {
    event.preventDefault(); if (mutation.current || !selected) return;
    mutation.current = true; setBusy(true); setDetailError('');
    try { const { data } = await api.post(`/support/tickets/${selected.id}/reply/`, { body: reply.trim() }); setSelected(data); setReply(''); notify.success('Your reply has been sent.'); await loadSupportRequests(); }
    catch (failure) { notify.error(getApiErrorMessage(failure)); }
    finally { mutation.current = false; setBusy(false); }
  }
  const openRequestForm = () => { setModal(true); };
  return <div className="container-padding space-y-4 py-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-lg font-semibold">Support for your workspace</h2><p className="mt-1 text-xs leading-6 text-muted-foreground">{contact?.hours}</p></div><div className="flex gap-2"><Button size="sm" variant="outline" disabled={loading || busy} onClick={() => { loadSupportRequests(); if (selected) openSupportRequest(selected); }}><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />Refresh</Button><Button size="sm" onClick={openRequestForm}><Plus className="h-4 w-4" />New request</Button></div></div>
    <div role="tablist" aria-label="Support sections" className="flex w-fit gap-1 rounded-xl border bg-card p-1">{[['requests', 'Requests & replies'], ['projects', 'Projects & access']].map(([value, label]) => <button key={value} role="tab" id={`support-tab-${value}`} aria-controls={`support-panel-${value}`} aria-selected={tab === value} tabIndex={tab === value ? 0 : -1} onClick={() => setTab(value)} onKeyDown={event => { if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); const other = value === 'requests' ? 'projects' : 'requests'; setTab(other); document.getElementById(`support-tab-${other}`)?.focus(); } }} className={`rounded-lg px-3 py-2 text-sm ${tab === value ? 'bg-brand/10 font-medium text-brand' : 'text-muted-foreground hover:bg-accent'}`}>{label}</button>)}</div>
    {tab === 'requests' ? <section role="tabpanel" id="support-panel-requests" aria-labelledby="support-tab-requests" className={`grid items-start gap-4 ${selected ? 'lg:grid-cols-[320px_1fr]' : ''}`}>
      <div className={`min-w-0 rounded-xl border bg-card ${selected ? 'hidden lg:block' : ''}`}><div className="flex items-center justify-between border-b px-4 py-3"><h3 className="text-sm font-semibold">Your requests</h3>{!loading && !error && <span className="text-xs text-muted-foreground">{history.count} total</span>}</div><div className="p-3">
        {error ? <WorkspaceState error={error} onRetry={loadSupportRequests} /> : loading ? <WorkspaceState loading title="Loading requests" description="Fetching your latest messages and statuses." /> : history.results.length === 0 ? <div className="px-4 py-8 text-center"><MessageSquare className="mx-auto mb-3 h-8 w-8 text-brand" /><h3 className="font-medium">No support requests yet</h3><p className="mx-auto mb-5 mt-2 max-w-lg text-sm leading-6 text-muted-foreground">Ask about your account, send a suggestion, or discuss a custom tool or Private installation. Your requests and replies will appear here.</p><Button variant="outline" size="sm" onClick={openRequestForm}>Create your first request</Button></div> : <ul className="max-h-[480px] space-y-2 overflow-y-auto scrollbar-thin-theme">{history.results.map(ticket => <li key={ticket.id}><button disabled={busy} onClick={() => openSupportRequest(ticket)} className={`w-full rounded-lg border p-3 text-left transition-colors ${selected?.id === ticket.id ? 'border-brand/40 bg-brand/5' : 'hover:bg-accent'}`}><p className="break-words text-sm font-medium">{ticket.subject}</p><p className="mt-2 text-xs text-muted-foreground">{requestLabels[ticket.request_type]} · {ticketStatusLabels[ticket.status] || ticket.status.replaceAll('_', ' ')}</p><p className="mt-1 text-xs text-muted-foreground">{formatDateTime(ticket.updated_at)}</p></button></li>)}</ul>}
        {!error && !loading && (history.previous || history.next) && <nav aria-label="Request history pages" className="mt-3 flex items-center justify-between gap-2 border-t pt-3"><Button size="sm" variant="ghost" disabled={!history.previous || busy} onClick={() => setPage(value => value - 1)} aria-label="Previous request page"><ChevronLeft className="h-4 w-4" /></Button><span className="text-xs text-muted-foreground">Page {page}</span><Button size="sm" variant="ghost" disabled={!history.next || busy} onClick={() => setPage(value => value + 1)} aria-label="Next request page"><ChevronRight className="h-4 w-4" /></Button></nav>}
      </div></div>
      {selected && <article className="min-w-0 rounded-xl border bg-card"><header className="border-b p-4"><Button variant="ghost" size="sm" className="mb-2 lg:hidden" disabled={busy} onClick={() => { detailRequest.current++; setSelected(null); }}><ArrowLeft className="h-4 w-4" />All requests</Button><div className="flex items-start justify-between gap-3"><div className="min-w-0"><h3 className="break-words text-lg font-semibold">{selected.subject}</h3><p className="mt-1 text-xs text-muted-foreground">{requestLabels[selected.request_type]} · {ticketStatusLabels[selected.status] || selected.status.replaceAll('_', ' ')}</p></div><Button size="sm" variant="ghost" disabled={detailLoading || busy} onClick={() => openSupportRequest(selected)} aria-label="Refresh this request"><RefreshCw className="h-4 w-4" /></Button></div><p className="mt-2 break-all text-[11px] text-muted-foreground">Reference: {selected.id}</p></header><div className="space-y-4 p-4">
        {detailLoading && <p role="status" className="text-sm text-muted-foreground">Loading the conversation…</p>}{detailError && <WorkspaceState error={detailError} onRetry={() => openSupportRequest(selected)} />}
        <div className="max-h-[420px] space-y-3 overflow-y-auto pr-1 scrollbar-thin-theme"><div className="rounded-xl bg-muted/40 p-4"><p className="mb-2 text-xs font-medium text-muted-foreground">You · {formatDateTime(selected.created_at)}</p><p className="whitespace-pre-wrap break-words text-sm leading-7">{selected.body}</p></div>{selected.replies.map(item => <div key={item.id} className={`rounded-xl border p-4 ${item.staff ? 'border-brand/20 bg-brand/5' : 'bg-muted/30'}`}><p className="mb-2 text-xs font-medium text-muted-foreground">{item.staff ? 'QuantNest support' : 'You'} · {formatDateTime(item.created_at)}</p><p className="whitespace-pre-wrap break-words text-sm leading-7">{item.body}</p></div>)}</div>
        <form onSubmit={submitSupportReply} className="space-y-3 border-t pt-4"><Label htmlFor="support-reply">Your reply</Label><Textarea id="support-reply" rows={3} maxLength={10000} minLength={2} required value={reply} onChange={event => setReply(event.target.value)} disabled={busy || detailLoading} /><div className="flex justify-end"><Button type="submit" size="sm" disabled={busy || detailLoading || reply.trim().length < 2}>{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}Send reply</Button></div></form>
      </div></article>}
    </section> : <section role="tabpanel" id="support-panel-projects" aria-labelledby="support-tab-projects" className="space-y-4"><CustomerProjects /><PrivateSupportAccess /></section>}
    <Dialog open={modal} onOpenChange={value => { if (!busy) setModal(value); }}>
      <DialogContent className="max-h-[90dvh] max-w-xl overflow-y-auto scrollbar-thin-theme">
        <DialogHeader><DialogTitle>New support request</DialogTitle><DialogDescription>Keep passwords, broker credentials and recovery codes out of your message.</DialogDescription></DialogHeader>
        <form onSubmit={submitSupportRequest} className="space-y-4">
          {(optionsLoading || optionsError) && <WorkspaceState loading={optionsLoading} error={optionsError ? 'Request types could not load. Please try again.' : ''} title={optionsLoading ? 'Loading request types' : undefined} onRetry={optionsError ? refreshOptions : undefined} />}
          
          <div className="space-y-2"><Label htmlFor="support-kind">Request type</Label><Select value={selectedKind} onValueChange={setKind} disabled={busy || optionsLoading || optionsError || !selectedKind}><SelectTrigger id="support-kind"><SelectValue placeholder="Choose a request type" /></SelectTrigger><SelectContent>{requestTypes.map(({ value, label }) => <SelectItem key={value} value={value}>{label}</SelectItem>)}</SelectContent></Select></div>
          <div className="space-y-2"><Label htmlFor="support-subject">Subject</Label><Input id="support-subject" value={subject} onChange={event => setSubject(event.target.value)} minLength={3} maxLength={180} required disabled={busy} /></div>
          <div className="space-y-2"><Label htmlFor="support-details">What would you like to discuss?</Label><Textarea id="support-details" value={body} onChange={event => setBody(event.target.value)} minLength={10} maxLength={10000} rows={5} required disabled={busy} /></div>
          <div className="flex justify-end gap-2 border-t pt-4"><Button type="button" variant="outline" disabled={busy} onClick={() => setModal(false)}>Cancel</Button><Button type="submit" disabled={busy || optionsLoading || optionsError || !selectedKind || subject.trim().length < 3 || body.trim().length < 10}>{busy && <Loader2 className="h-4 w-4 animate-spin" />}Send request</Button></div>
        </form>
      </DialogContent>
    </Dialog>
  </div>;
}
