import PropTypes from 'prop-types';
import { useEnums } from '@/shared/context/EnumsContext';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { Label } from '@/shared/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/shared/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select';
import { useTerminalPositionsPnL } from '@/shared/hooks/useLivePositionsPnL';
import brokersApi from '@/shared/services/brokersApi';
import api from '@/shared/services/api';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { formatCurrency, formatDateTime } from '@/shared/utils/formatters';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';
import terminalApi from '../services/tradingTerminalApi';

export default function AccountSummary({ account, positions, onSaved }) {
  const { values } = useEnums();
  const [profiles, setProfiles] = useState([]), [runtime, setRuntime] = useState(null);
  const [profile, setProfile] = useState(String(account.charge_profile || 'none'));
  const [futures, setFutures] = useState(account.futures_margin_pct);
  const [options, setOptions] = useState(account.short_option_margin_pct), [busy, setBusy] = useState(false);
  const { notify } = useNotifications();
  const { livePnLByPositionId, totals } = useTerminalPositionsPnL(positions);
  const marketValue = positions.reduce((total, row) => {
    const mark = livePnLByPositionId[row.id];
    return total + (mark ? row.instrument.instrument_type === values.InstrumentType.FUTURE ? mark.pnl : mark.livePrice * row.quantity * Number(row.instrument.qty_multiplier) : 0);
  }, 0);
  useEffect(() => {
    let mounted = true;
    brokersApi.getChargeProfiles().then((response) => { if (mounted) setProfiles(response.data); })
      .catch((error) => { if (mounted) notify.error(getApiErrorMessage(error, 'Could not load charge profiles.')); });
    api.get('/trading/status/').then((response) => { if (mounted) setRuntime(response.data); }).catch(() => {});
    return () => { mounted = false; };
  }, [notify]);
  const save = async (event) => {
    event.preventDefault(); setBusy(true);
    try {
      await terminalApi.updateAccount({ charge_profile: profile === 'none' ? null : Number(profile),
        futures_margin_pct: futures, short_option_margin_pct: options });
      notify.success('Account settings submitted for application'); onSaved();
    } catch (error) { notify.error(getApiErrorMessage(error, 'Could not save account settings.')); }
    finally { setBusy(false); }
  };
  const stats = [
    ['Account equity', Number(account.balance) + marketValue], ['Available capital', account.available_balance],
    ['Cash balance', account.balance], ['Open P&L · gross', totals.totalUnrealizedPnL],
    ['Position collateral', account.margin], ['Reserved for orders', account.reserved_cash],
    ['Realized P&L · net', account.realized_pnl], ['Recorded charges', account.charges_paid],
  ];
  return <div className="space-y-6">
    <div><h2 className="text-lg font-semibold">Simulation account</h2>
      <p className="mt-1 text-sm text-muted-foreground">Your terminal balance, recorded activity and account settings.</p></div>
    <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{stats.map(([label,value]) => <div key={label} className="rounded-xl border bg-card p-4">
      <dt className="text-xs text-muted-foreground">{label}</dt><dd className={'mt-2 text-xl font-semibold tabular-nums ' + (label.includes('P&L') ? Number(value) >= 0 ? 'text-emerald-500' : 'text-rose-500' : '')}>{formatCurrency(value)}</dd></div>)}</dl>
    <div className="grid items-start gap-6 lg:grid-cols-2">
      <Card><CardHeader><CardTitle>Charges and margin</CardTitle><CardDescription>Configure the estimates used by this simulation account.</CardDescription></CardHeader>
        <CardContent><form onSubmit={save} className="space-y-5">
          <div className="space-y-2"><Label htmlFor="terminal-charge-profile">Charge profile</Label>
            <Select value={profile} onValueChange={setProfile}><SelectTrigger id="terminal-charge-profile"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="none">No simulated charges</SelectItem>{profiles.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.name}</SelectItem>)}</SelectContent></Select>
            <Link className="inline-block text-xs text-primary underline underline-offset-4" to="/brokers/charge-profiles">Manage charge profiles</Link></div>
          <div className="space-y-2"><Label htmlFor="terminal-futures-margin">Futures margin (%)</Label>
            <Input id="terminal-futures-margin" type="number" min="1" max="100" step=".01" value={futures} onChange={(event) => setFutures(event.target.value)} required /></div>
          <div className="space-y-2"><Label htmlFor="terminal-option-margin">Short-option collateral (%)</Label>
            <Input id="terminal-option-margin" type="number" min="1" max="100" step=".01" value={options} onChange={(event) => setOptions(event.target.value)} required /></div>
          <p className="text-xs leading-relaxed text-muted-foreground">New orders use the selected fee profile. Margin changes recalculate positions and pending reservations. These percentages are simulation estimates.</p>
          <Button type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save settings'}</Button>
        </form></CardContent></Card>
      <Card><CardHeader><CardTitle>Account details</CardTitle><CardDescription>This account is separate from automated Paper deployments.</CardDescription></CardHeader>
        <CardContent><dl className="divide-y text-sm">
          {[['Created', formatDateTime(account.created_at)], ['Account type', 'Manual simulation'],
            ['Market data', runtime ? runtime.market_data ? 'Running' : 'Stopped' : 'Unavailable'],
            ['Order matching', runtime ? runtime.execution_running ? 'Running' : 'Stopped' : 'Unavailable']]
            .map(([label,value]) => <div key={label} className="flex justify-between gap-4 py-3 first:pt-0"><dt className="text-muted-foreground">{label}</dt><dd className="text-right font-medium">{value}</dd></div>)}
        </dl></CardContent></Card>
    </div>
  </div>;
}
AccountSummary.propTypes = { account: PropTypes.object.isRequired, positions: PropTypes.array.isRequired, onSaved: PropTypes.func.isRequired };
