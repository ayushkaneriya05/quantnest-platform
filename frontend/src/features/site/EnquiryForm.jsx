import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useSelector } from 'react-redux';
import PropTypes from 'prop-types';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/shared/components/ui/select';
import { brand } from './config';
import api, { requestPublicApi } from '@/shared/services/api';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';
import Turnstile from './Turnstile';
import { useNotifications } from '@/shared/hooks/useNotifications';
import WorkspaceState from '@/shared/components/WorkspaceState';
import { useSupportOptions } from '@/shared/hooks/useSupportOptions';
export default function EnquiryForm({ feedback = false }) {
  const [params] = useSearchParams();
  const { notify } = useNotifications();
  const user = useSelector(state => state.auth.user);
  const { requestTypes, requestLabels, loading, error: optionsError, refresh } = useSupportOptions();
  const [kind, setKind] = useState(feedback ? 'feedback' : params.get('type') || 'general');
  const selectedKind = requestLabels[kind] ? kind : requestTypes[0]?.value || '';
  const [token, setToken] = useState(''); const [reset, setReset] = useState(0);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setKind(feedback ? 'feedback' : params.get('type') || 'general');
  }, [feedback, params]);
  const handleVerificationError = useCallback(value => notify.error(value), [notify]);
  async function submitEnquiry(event) {
    event.preventDefault(); if (busy || !selectedKind || optionsError) return;
    if (!user && brand.turnstile && !token) { notify.warning('Complete the verification before sending.'); return; }
    const form = event.currentTarget; const values = Object.fromEntries(new FormData(form));
    setBusy(true);
    try {
      const payload = { ...values, request_type: selectedKind };
      const data = user ? (await api.post('/support/tickets/', payload)).data
        : await requestPublicApi('public/enquiries/', { ...payload, turnstile_token: token });
      notify.success(`Request received. Reference: ${data.id}. ${user ? 'Track replies in workspace Support.' : 'We’ll reply by email.'}`);
      form.reset();
    }
    catch (failure) { notify.error(getApiErrorMessage(failure)); }
    finally { setBusy(false); setToken(''); setReset(value => value + 1); }
  }
  return <form className="site-card space-y-5" onSubmit={submitEnquiry}>
    <div className="grid gap-5 sm:grid-cols-2"><label className="space-y-2 text-sm"><span>Your name</span><Input key={user?.id || 'guest'} name="name" defaultValue={user ? [user.first_name, user.last_name].filter(Boolean).join(' ').slice(0, 120) : ''} autoComplete="name" maxLength={120} required /></label><label className="space-y-2 text-sm"><span>Email</span><Input key={user?.id || 'guest'} name="email" type="email" value={user ? user.email : undefined} readOnly={!!user} autoComplete="email" maxLength={254} required /></label></div>
    {(loading || optionsError) && <WorkspaceState loading={loading} error={optionsError ? 'Request types could not load. Please try again.' : ''} title={loading ? 'Loading request types' : undefined} onRetry={optionsError ? refresh : undefined} />}
    <label className="block space-y-2 text-sm"><span>Request type</span><Select value={selectedKind} onValueChange={setKind} disabled={busy || loading || optionsError || !selectedKind}><SelectTrigger><SelectValue placeholder="Choose a request type" /></SelectTrigger><SelectContent>{requestTypes.map(({ value, label }) => <SelectItem key={value} value={value}>{label}</SelectItem>)}</SelectContent></Select></label>
    <label className="block space-y-2 text-sm"><span>Subject</span><Input name="subject" minLength={3} maxLength={180} required /></label><label className="block space-y-2 text-sm"><span>What would you like to discuss?</span><textarea name="body" rows={7} minLength={10} maxLength={10000} required className="w-full resize-y rounded-xl border bg-background p-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" /></label><p className="text-xs leading-6 text-muted-foreground">Do not include passwords, broker credentials, tokens or recovery codes.</p>
    {!user && <Turnstile action="enquiry" onToken={setToken} onError={handleVerificationError} reset={reset} />}<Button type="submit" disabled={busy || loading || optionsError || !selectedKind}>{busy ? 'Sending…' : 'Send request'}</Button>
  </form>;
}
EnquiryForm.propTypes = { feedback: PropTypes.bool };
