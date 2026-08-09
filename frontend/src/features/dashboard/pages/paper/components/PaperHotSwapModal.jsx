import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/shared/components/ui/dialog";
import { Alert, AlertDescription } from "@/shared/components/ui/alert";
import { Button } from "@/shared/components/ui/button";
import { Label } from "@/shared/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { paperApi } from "@/shared/services/paperApi";
import { strategyApi } from "@/shared/services/strategyApi";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { AlertCircle, Loader2 } from "lucide-react";
import { formatDateTime } from "@/shared/utils/formatters";

export default function PaperHotSwapModal({
  session,
  open,
  onOpenChange,
  onSuccess,
}) {
  const { notify } = useNotifications();
  const [loading, setLoading] = useState(false);
  const [versions, setVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState("");
  const [fetchingVersions, setFetchingVersions] = useState(false);

  useEffect(() => {
    if (open && session?.strategy) {
      const fetchVersions = async () => {
        try {
          setFetchingVersions(true);
          const response = await strategyApi.getVersions(session.strategy);
          setVersions(response || []);
          if (session?.deployed_version_detail?.id) {
            setSelectedVersion(String(session.deployed_version_detail.id));
          } else {
            setSelectedVersion("");
          }
        } catch (error) {
          notify.error("Failed to load strategy versions");
        } finally {
          setFetchingVersions(false);
        }
      };
      fetchVersions();
    }
  }, [open, session]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedVersion) return;
    try {
      setLoading(true);
      await paperApi.deployVersion(session.id, {
        version_id: selectedVersion,
      });
      notify.success("Paper Strategy version hot-swapped successfully");
      onSuccess?.();
      onOpenChange(false);
    } catch (error) {
      notify.error(error?.response?.data?.detail || error?.response?.data?.error || "Failed to hot-swap version");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px] bg-gray-950 border-gray-800 text-gray-100">
        <DialogHeader>
          <DialogTitle>Hot-Swap Paper Strategy Version</DialogTitle>
          <DialogDescription className="text-gray-400">
            Change the deployed version for {session?.strategy_name}.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <Alert className="bg-amber-900/20 border-amber-800/50 text-amber-300 mb-2">
            <AlertCircle className="h-4 w-4 text-amber-400" />
            <AlertDescription className="text-xs ml-2">
              <strong>Warning:</strong> Hot-swapping a paper strategy while it has active open positions may lead to unexpected behavior if the new version expects different state. It is recommended to flatten positions or pause the session before hot-swapping.
            </AlertDescription>
          </Alert>

          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <Label>Select Version</Label>
              {session?.deployed_version_detail?.version_number && (
                <span className="text-xs text-gray-400">
                  Current: <strong className="text-white">v{session.deployed_version_detail.version_number}</strong>
                </span>
              )}
            </div>
            {fetchingVersions ? (
              <div className="text-sm text-gray-500 flex items-center">
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Loading versions...
              </div>
            ) : (
              <Select
                value={selectedVersion}
                onValueChange={setSelectedVersion}
              >
                <SelectTrigger className="bg-gray-900 border-gray-700">
                  <SelectValue placeholder="Select a version" />
                </SelectTrigger>
                <SelectContent className="bg-gray-900 border-gray-700 text-white">
                  {versions.length === 0 && (
                    <div className="p-2 text-sm text-gray-500">No versions available</div>
                  )}
                  {versions.map((v) => (
                    <SelectItem key={v.id} value={String(v.id)}>
                      v{v.version_number} {v.created_at ? `(${formatDateTime(v.created_at)})` : ''} {session?.deployed_version_detail?.id === v.id ? '(Deployed)' : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <DialogFooter className="pt-4">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={loading}
              className="text-gray-300 hover:text-white hover:bg-gray-800"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={loading || !selectedVersion}
              className="bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Apply Version
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
