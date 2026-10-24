import { useState } from "react";
import PropTypes from "prop-types";
import { AlertCircle, Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Alert, AlertDescription } from "@/shared/components/ui/alert";
import { Button } from "@/shared/components/ui/button";
import { Label } from "@/shared/components/ui/label";
import { SelectContent, SelectTrigger, SelectValue } from "@/shared/components/ui/select";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import StrategyVersionSelect from "./StrategyVersionSelect";

export default function ChangeStrategyVersionDialog({
  strategyId, strategyName, currentVersionId, currentVersionNumber, onApply, onClose, onSuccess,
}) {
  const [selectedVersion, setSelectedVersion] = useState(String(currentVersionId ?? ""));
  const [saving, setSaving] = useState(false);
  const { notify } = useNotifications();

  async function applyVersion(event) {
    event.preventDefault();
    if (!selectedVersion || saving) return;
    setSaving(true);
    try {
      await onApply(Number(selectedVersion));
      notify.success("Strategy version change submitted. The deployment will show when it is applied.");
      onSuccess?.();
      onClose();
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to change the deployed version"));
    } finally {
      setSaving(false);
    }
  }

  return <Dialog open onOpenChange={(open) => !open && !saving && onClose()}>
    <DialogContent className="sm:max-w-[425px] bg-background border-border text-foreground">
      <DialogHeader>
        <DialogTitle>Change strategy version</DialogTitle>
        <DialogDescription>Choose a saved version for {strategyName}.</DialogDescription>
      </DialogHeader>
      <form onSubmit={applyVersion} className="space-y-4">
        <Alert className="border-amber-800/50 bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="ml-2 text-xs">
            Review the new rules before applying them to an active deployment. Existing positions remain open; changes must retain their instruments.
          </AlertDescription>
        </Alert>
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <Label>Select version</Label>
            {currentVersionNumber && <span className="text-xs text-muted-foreground">Current: v{currentVersionNumber}</span>}
          </div>
          <StrategyVersionSelect filters={{ strategy_id: strategyId }} value={selectedVersion}
            onValueChange={setSelectedVersion} disabled={saving}>
            <SelectTrigger><SelectValue placeholder="Select a saved version" /></SelectTrigger>
            <SelectContent />
          </StrategyVersionSelect>
        </div>
        <DialogFooter className="gap-2">
          <Button type="button" variant="ghost" disabled={saving} onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={saving || !selectedVersion} className="bg-indigo-600 text-white hover:bg-indigo-700">
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Apply version
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>;
}

ChangeStrategyVersionDialog.propTypes = {
  strategyId: PropTypes.number.isRequired,
  strategyName: PropTypes.string.isRequired,
  currentVersionId: PropTypes.number,
  currentVersionNumber: PropTypes.number,
  onApply: PropTypes.func.isRequired,
  onClose: PropTypes.func.isRequired,
  onSuccess: PropTypes.func,
};

