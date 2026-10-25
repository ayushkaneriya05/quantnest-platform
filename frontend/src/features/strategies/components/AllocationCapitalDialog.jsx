import { LoaderMark } from '@/shared/components/ui/global-loader';
import { useState } from "react";
import PropTypes from "prop-types";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";

export default function AllocationCapitalDialog({ strategyName, currentAmount, onApply, onClose, onSuccess }) {
  const [amount, setAmount] = useState(String(currentAmount));
  const [saving, setSaving] = useState(false);
  const { notify } = useNotifications();
  async function save(event) {
    event.preventDefault();
    setSaving(true);
    try {
      await onApply(amount);
      notify.success("Allocated capital updated");
      onSuccess();
      onClose();
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to update allocated capital"));
    } finally {
      setSaving(false);
    }
  }
  return <Dialog open onOpenChange={(open) => !open && !saving && onClose()}>
    <DialogContent className="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>Update allocated capital</DialogTitle>
        <DialogDescription>Change the capital assigned to {strategyName}.</DialogDescription>
      </DialogHeader>
      <form onSubmit={save} className="space-y-5">
        <div className="space-y-2">
          <Label htmlFor="allocation-capital">Capital (₹)</Label>
          <Input id="allocation-capital" type="number" min="0.01" step="0.01" required
            value={amount} onChange={(event) => setAmount(event.target.value)} disabled={saving} />
        </div>
        <p className="text-sm text-muted-foreground">
          The running session receives this change automatically. Existing positions keep their quantities.
          Capital already committed to trades cannot be withdrawn.
        </p>
        <DialogFooter>
          <Button type="button" variant="ghost" disabled={saving} onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={saving || !(Number(amount) > 0)}>
            {saving && <LoaderMark className="mr-2 h-4 w-4" />}Save capital
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>;
}
AllocationCapitalDialog.propTypes = {
  strategyName: PropTypes.string.isRequired,
  currentAmount: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  onApply: PropTypes.func.isRequired, onClose: PropTypes.func.isRequired, onSuccess: PropTypes.func.isRequired,
};
