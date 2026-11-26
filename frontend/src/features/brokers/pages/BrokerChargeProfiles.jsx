import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Edit2, Plus, Trash2 } from 'lucide-react';
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { Label } from '@/shared/components/ui/label';
import { Badge } from '@/shared/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/shared/components/ui/dialog';
import { customConfirm } from '@/shared/components/ui/custom-dialog';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { useSetPageActions } from '@/shared/hooks/useSetPageActions';
import { useStableCallback } from '@/shared/hooks/useStableCallback';
import { brokersApi } from '@/shared/services/brokersApi';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';
import { formatCurrency, formatNumber } from '@/shared/utils/formatters';

const percent = (value) => `${formatNumber(value, { minimumFractionDigits: 0, maximumFractionDigits: 8 })}%`;

export default function BrokerChargeProfiles() {
  const { notify } = useNotifications();
  const [profiles, setProfiles] = useState([]);
  const [specification, setSpecification] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editingProfile, setEditingProfile] = useState(null);
  const [formData, setFormData] = useState(null);

  const fetchProfiles = useStableCallback(async () => {
    try {
      const [profilesResponse, defaultsResponse] = await Promise.all([
        brokersApi.getChargeProfiles(), brokersApi.getChargeProfileDefaults(),
      ]);
      setProfiles(profilesResponse.data);
      setSpecification(defaultsResponse.data);
    } catch (error) {
      notify.error(getApiErrorMessage(error, 'Failed to load charge profiles'));
    } finally {
      setLoading(false);
    }
  });
  useEffect(() => { fetchProfiles(); }, [fetchProfiles]);

  // The backend supplies rates and field names for editing and new profiles.
  const handleOpenModal = useStableCallback((profile = null) => {
    if (!specification) return;
    const source = profile || specification.profile;
    const fields = Object.keys(specification.profile).filter((field) => field in specification.labels);
    setEditingProfile(profile);
    setFormData({ name: source.name,
      ...Object.fromEntries(fields.map((field) => [field, source[field]])),
      market_rates: structuredClone(source.market_rates) });
  });

  const handleSave = async () => {
    if (!formData.name.trim()) return notify.error('Name is required');
    setSaving(true);
    try {
      if (editingProfile) await brokersApi.updateChargeProfile(editingProfile.id, formData);
      else await brokersApi.createChargeProfile(formData);
      notify.success(editingProfile ? 'Charge profile updated' : 'Charge profile created');
      setFormData(null);
      await fetchProfiles();
    } catch (error) {
      notify.error(getApiErrorMessage(error, 'Failed to save charge profile'));
    } finally { setSaving(false); }
  };

  const handleDelete = async (profile) => {
    if (!await customConfirm(`Delete ${profile.name}? This cannot be undone.`, 'Delete charge profile', 'Delete')) return;
    try {
      await brokersApi.deleteChargeProfile(profile.id);
      notify.success('Charge profile deleted');
      await fetchProfiles();
    } catch (error) { notify.error(getApiErrorMessage(error, 'Failed to delete charge profile')); }
  };

  const handleSetDefault = async (id) => {
    try {
      await brokersApi.setDefaultChargeProfile(id);
      notify.success('Default profile updated');
      await fetchProfiles();
    } catch (error) { notify.error(getApiErrorMessage(error, 'Failed to set default profile')); }
  };

  const pageActions = useMemo(() => (
    <Button onClick={() => handleOpenModal()} disabled={!specification}>
      <Plus className="h-4 w-4" /> New profile
    </Button>
  ), [handleOpenModal, specification]);
  useSetPageActions(pageActions);
  if (loading) return <GlobalLoader />;

  const renderRateInput = (field, value, onChange, prefix) => (
    <div className="space-y-1" key={field}>
      <Label htmlFor={`${prefix}-${field}`}>{specification.labels[field]}</Label>
      <Input id={`${prefix}-${field}`} type="number" min="0" step="any" required
        value={value} onChange={(event) => onChange(event.target.value)} className="font-mono" />
    </div>
  );

  return (
    <div className="page-content">
      <p className="text-sm text-muted-foreground">
        New profiles use {specification?.basis}. Market rates select the exchange and contract automatically.
        Edit your default profile, or choose another before deleting it.
      </p>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {profiles.map((profile) => (
          <Card key={profile.id}>
            <CardHeader className="border-b border-border">
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  {profile.name} {profile.is_default && <Badge className="bg-success/10 text-success border-success/20">Default</Badge>}
                </CardTitle>
                <div className="flex gap-1">
                  <Button variant="ghost" size="icon" aria-label={`Edit ${profile.name}`} onClick={() => handleOpenModal(profile)}><Edit2 className="h-4 w-4" /></Button>
                  {!profile.is_default && <Button variant="ghost" size="icon" aria-label={`Delete ${profile.name}`} onClick={() => handleDelete(profile)}><Trash2 className="h-4 w-4" /></Button>}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 pt-3 text-sm">
              <dl className="grid grid-cols-2 gap-2">
                <dt className="text-muted-foreground">Order brokerage / cap</dt>
                <dd className="text-right tabular-nums">{formatCurrency(profile.brokerage_per_order)} / {formatCurrency(profile.brokerage_cap)}</dd>
                <dt className="text-muted-foreground">Stock STT · delivery / intraday</dt>
                <dd className="text-right tabular-nums">{percent(profile.stt_eq_delivery_pct)} / {percent(profile.stt_eq_intraday_pct)}</dd>
                <dt className="text-muted-foreground">Equity F&amp;O STT · futures / options</dt>
                <dd className="text-right tabular-nums">{percent(profile.stt_futures_pct)} / {percent(profile.stt_options_sell_pct)}</dd>
                <dt className="text-muted-foreground">Commodity CTT · futures / options</dt>
                <dd className="text-right tabular-nums">{percent(profile.ctt_futures_sell_pct)} / {percent(profile.ctt_options_sell_pct)}</dd>
                <dt className="text-muted-foreground">SEBI / GST</dt>
                <dd className="text-right tabular-nums">{percent(profile.sebi_turnover_pct)} / {percent(profile.gst_pct)}</dd>
              </dl>
              <details className="border-t border-border pt-2">
                <summary className="cursor-pointer text-muted-foreground">Market rates ({Object.keys(profile.market_rates).length})</summary>
                <div className="mt-2 max-h-64 space-y-2 overflow-y-auto">
                  {Object.entries(profile.market_rates).map(([market, rates]) => <div key={market}>
                    <p className="font-medium">{specification?.markets[market]}</p>
                    <p className="text-xs text-muted-foreground">Exchange {percent(rates.exchange_txn_pct)}
                      {rates.clearing_pct && ` · Clearing ${percent(rates.clearing_pct)}`}
                      {rates.ipft_pct && ` · IPFT ${percent(rates.ipft_pct)}`}
                    </p>
                  </div>)}
                </div>
              </details>
              {!profile.is_default && <Button variant="outline" className="w-full" onClick={() => handleSetDefault(profile.id)}><CheckCircle2 className="h-4 w-4" /> Set as default</Button>}
            </CardContent>
          </Card>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        Estimates cover normal trade exits. DP debits, exercise/physical delivery, penalties and funding interest
        are separate account costs. BSE special scrip groups and exempt agricultural contracts need tailored rates.
      </p>
      <Dialog open={Boolean(formData)} onOpenChange={(open) => { if (!open && !saving) setFormData(null); }}>
        <DialogContent className="sm:max-w-2xl max-h-[90dvh] overflow-y-auto scrollbar-theme">
          <DialogHeader><DialogTitle>{editingProfile ? 'Edit charge profile' : 'Create charge profile'}</DialogTitle></DialogHeader>
          {formData && <form id="charge-profile-form" onSubmit={(event) => { event.preventDefault(); handleSave(); }} className="space-y-3">
            <div className="space-y-1">
              <Label htmlFor="charge-profile-name">Profile name</Label>
              <Input id="charge-profile-name" value={formData.name} maxLength={100} required onChange={(event) => setFormData({ ...formData, name: event.target.value })} />
            </div>
            <details open>
              <summary className="cursor-pointer font-medium">Shared taxes and base rates</summary>
              <p className="my-2 text-xs text-muted-foreground">Market-specific values below override matching base rates. Zero brokerage percentage uses the flat order fee.</p>
              <div className="grid gap-3 sm:grid-cols-2">
                {Object.entries(formData).filter(([field]) => field in specification.labels).map(([field, value]) => renderRateInput(field, value, (next) => setFormData({ ...formData, [field]: next }), 'base'))}
              </div>
            </details>
            {Object.entries(formData.market_rates).map(([market, rates]) => <details key={market} className="border-t border-border pt-2">
              <summary className="cursor-pointer font-medium">{specification.markets[market]}</summary>
              <div className="mt-2 grid gap-3 sm:grid-cols-2">
                {Object.entries(rates).map(([field, value]) => renderRateInput(field, value,
                  (next) => setFormData({ ...formData, market_rates: { ...formData.market_rates, [market]: { ...rates, [field]: next } } }), market))}
              </div>
            </details>)}
          </form>}
          <DialogFooter>
            <Button variant="outline" disabled={saving} onClick={() => setFormData(null)}>Cancel</Button>
            <Button type="submit" form="charge-profile-form" disabled={saving}>{saving ? 'Saving…' : 'Save profile'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
