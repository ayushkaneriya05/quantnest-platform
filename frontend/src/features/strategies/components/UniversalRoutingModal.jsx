import { GlobalLoader, LoaderMark } from '@/shared/components/ui/global-loader';
import { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { Route } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/shared/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { Label } from '@/shared/components/ui/label';
import { Switch } from '@/shared/components/ui/switch';
import { executionRoutesApi } from '@/shared/services/instrumentsApi';
import { useNotifications } from '@/shared/hooks/useNotifications';
import { getApiErrorMessage } from '@/shared/utils/apiErrors';

const defaults = { override_sizing: false, sizing_method: 'CAPITAL_BASED', capital_percentage: 10, fixed_quantity: 1 };

export default function UniversalRoutingModal({ open, onClose, watchlistInstrument }) {
  const { notify } = useNotifications();
  const [route, setRoute] = useState(null);
  const [form, setForm] = useState(defaults);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);
  const identity = watchlistInstrument?.id;

  useEffect(() => {
    if (!open || !identity) return;
    let cancelled = false;
    setLoading(true);
    setFailed(false);
    executionRoutesApi.getByWatchlistInstrument(identity).then((routes) => {
      if (cancelled) return;
      const current = routes[0] || null;
      setRoute(current);
      setForm(current ? { ...defaults, ...current } : defaults);
    }).catch((error) => {
      if (cancelled) return;
      setFailed(true);
      notify.error(getApiErrorMessage(error, 'Could not load instrument settings. Reopen this dialog to retry.'));
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [open, identity, notify]);

  async function save(event) {
    event.preventDefault();
    setSaving(true);
    try {
      if (!form.override_sizing) {
        if (route) await executionRoutesApi.delete(route.id);
      } else {
        const fixed = form.sizing_method === 'FIXED';
        await executionRoutesApi.createOrUpdate(identity, route?.id, {
          route_type: 'DIRECT', override_sizing: true, sizing_method: form.sizing_method,
          fixed_quantity: fixed ? Number(form.fixed_quantity) : null,
          capital_percentage: fixed ? null : Number(form.capital_percentage),
        });
      }
      notify.success('Instrument settings saved. Save a new strategy version to use these settings in a deployment.');
      onClose();
    } catch (error) {
      notify.error(getApiErrorMessage(error, 'Could not save instrument settings.'));
    } finally { setSaving(false); }
  }

  return (
    <Dialog open={open} onOpenChange={(value) => { if (!value && !saving) onClose(); }}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><Route className="h-5 w-5" /> Instrument execution</DialogTitle></DialogHeader>
        <form onSubmit={save} className="space-y-5">
          <p className="text-sm text-muted-foreground">Signals trade the selected NSE stock directly. Each instrument uses the strategy position size unless you set an override here.</p>
          {loading ? <GlobalLoader text="Loading settings…" fullHeight={false} /> : (
            <fieldset disabled={saving || failed} className="space-y-4">
              <div className="flex items-center justify-between gap-4 rounded-lg border p-4">
                <Label htmlFor="instrument-sizing">Use a different position size</Label>
                <Switch id="instrument-sizing" checked={form.override_sizing} onCheckedChange={(value) => setForm({ ...form, override_sizing: value })} />
              </div>
              {form.override_sizing && <>
                <div className="space-y-2">
                  <Label htmlFor="sizing-method">Position sizing</Label>
                  <Select value={form.sizing_method} onValueChange={(value) => setForm({ ...form, sizing_method: value })}>
                    <SelectTrigger id="sizing-method"><SelectValue /></SelectTrigger>
                    <SelectContent><SelectItem value="FIXED">Fixed quantity</SelectItem><SelectItem value="CAPITAL_BASED">Percentage of allocated capital</SelectItem></SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sizing-value">{form.sizing_method === 'FIXED' ? 'Number of shares' : 'Capital percentage'}</Label>
                  <Input id="sizing-value" type="number" required min={form.sizing_method === 'FIXED' ? 1 : 0.01} max={form.sizing_method === 'FIXED' ? undefined : 100} step={form.sizing_method === 'FIXED' ? 1 : 0.01}
                    value={form.sizing_method === 'FIXED' ? form.fixed_quantity : form.capital_percentage}
                    onChange={(event) => setForm({ ...form, [form.sizing_method === 'FIXED' ? 'fixed_quantity' : 'capital_percentage']: event.target.value })} />
                </div>
              </>}
            </fieldset>
          )}
          <DialogFooter><Button type="button" variant="outline" disabled={saving} onClick={onClose}>Cancel</Button><Button type="submit" disabled={loading || saving || failed}>{saving && <LoaderMark className="mr-2 h-4 w-4" />}Save settings</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

UniversalRoutingModal.propTypes = {
  open: PropTypes.bool.isRequired, onClose: PropTypes.func.isRequired,
  watchlistInstrument: PropTypes.shape({ id: PropTypes.number }),
};
