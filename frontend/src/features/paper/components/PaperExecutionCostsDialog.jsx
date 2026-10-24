import { useState } from "react";
import PropTypes from "prop-types";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Switch } from "@/shared/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { paperApi } from "@/shared/services/paperApi";

export default function PaperExecutionCostsDialog({ session, onClose, onSuccess }) {
  const [slippage, setSlippage] = useState(String(session.slippage_pct));
  const [profile, setProfile] = useState(String(session.charge_profile || "none"));
  const [includeCharges, setIncludeCharges] = useState(session.include_charges);
  const [saving, setSaving] = useState(false);
  const { notify } = useNotifications();
  async function save(event) {
    event.preventDefault();
    setSaving(true);
    try {
      await paperApi.configureSessionCosts(session.id, {
        slippage_pct: slippage, charge_profile: profile === "none" ? null : Number(profile),
        include_charges: includeCharges,
      });
      notify.success("Execution costs updated");
      onSuccess();
      onClose();
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to update execution costs"));
    } finally { setSaving(false); }
  }
  return <Dialog open onOpenChange={(open) => !open && !saving && onClose()}>
    <DialogContent className="sm:max-w-md">
      <DialogHeader><DialogTitle>Paper execution costs</DialogTitle>
        <DialogDescription>Update costs for {session.name} while stopped and without open positions.</DialogDescription>
      </DialogHeader>
      <form onSubmit={save} className="space-y-4">
        <div className="space-y-2"><Label htmlFor="paper-slippage">Slippage (%)</Label>
          <Input id="paper-slippage" type="number" min="0" max="99.9999" step="0.0001" required
            value={slippage} onChange={(event) => setSlippage(event.target.value)} disabled={saving} />
        </div>
        <div className="flex items-center justify-between gap-3">
          <Label htmlFor="paper-charges">Include transaction charges</Label>
          <Switch id="paper-charges" checked={includeCharges} onCheckedChange={setIncludeCharges} disabled={saving} />
        </div>
        <div className="space-y-2"><Label>Charge profile</Label>
          <Select resource="charge-profiles" value={profile} onValueChange={setProfile} disabled={saving || !includeCharges}>
            <SelectTrigger><SelectValue placeholder="Select a charge profile" /></SelectTrigger>
            <SelectContent><SelectItem persistent value="none">No charge profile</SelectItem></SelectContent>
          </Select>
        </div>
        <DialogFooter>
          <Button type="button" variant="ghost" disabled={saving} onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={saving}>{saving ? "Saving…" : "Save costs"}</Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>;
}
PaperExecutionCostsDialog.propTypes = { session: PropTypes.object.isRequired, onClose: PropTypes.func.isRequired, onSuccess: PropTypes.func.isRequired };
