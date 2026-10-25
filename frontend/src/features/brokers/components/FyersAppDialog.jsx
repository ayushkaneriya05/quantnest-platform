import { LoaderMark } from '@/shared/components/ui/global-loader';
import { useState } from "react";
import PropTypes from "prop-types";
import { Copy, ExternalLink, KeyRound, } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { brokersApi } from "@/shared/services/brokersApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";

export default function FyersAppDialog({ provider, onClose, onConnect }) {
  const { notify } = useNotifications();
  const [clientId, setClientId] = useState(provider.client_id);
  const [secret, setSecret] = useState("");
  const [savedClientId, setSavedClientId] = useState(provider.configured ? provider.client_id : null);
  const [saving, setSaving] = useState(false);
  const needsSecret = clientId.trim() !== savedClientId;

  const submit = async (event) => {
    event.preventDefault();
    try {
      setSaving(true);
      const { data } = await brokersApi.configureBroker({
        broker_name: provider.broker_name, client_id: clientId.trim(), api_secret: secret.trim(),
      });
      setSecret("");
      setSavedClientId(data.client_id);
      await onConnect(data.id);
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Could not configure your broker app."));
    } finally {
      setSaving(false);
    }
  };

  const copyCallback = async () => {
    try {
      await navigator.clipboard.writeText(provider.connection.redirect_uri);
      notify.success("Callback URL copied.");
    } catch {
      notify.error("Could not copy. Select and copy the callback URL shown below.");
    }
  };

  return (
    <Dialog open onOpenChange={(open) => { if (!open && !saving) onClose(); }}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><KeyRound className="h-5 w-5 text-primary" />Your {provider.display_name} app</DialogTitle>
          <DialogDescription>Connect your own account using the individual app you created in FYERS.</DialogDescription>
        </DialogHeader>
        <div className="rounded-xl border bg-muted/30 p-4 text-sm">
          <ol className="list-decimal space-y-2 pl-4 text-muted-foreground">
            <li>Create an individual app in the FYERS API dashboard.</li>
            <li>Register this exact callback URL and your execution server’s approved static IP.</li>
            <li>Enable Order Placement permissions, then enter the app credentials below.</li>
          </ol>
          <a className="mt-3 inline-flex items-center gap-1 font-medium text-primary" href="https://fyers.in/api-docs/v3/getting-started/create-an-app/individual-app/" target="_blank" rel="noreferrer">FYERS setup instructions<ExternalLink className="h-3.5 w-3.5" /></a>
        </div>
        <div className="space-y-2">
          <Label htmlFor="broker-callback">Callback URL</Label>
          <div className="flex gap-2">
            <Input id="broker-callback" readOnly value={provider.connection.redirect_uri} className="min-w-0 font-mono text-xs" />
            <Button type="button" variant="outline" size="icon" aria-label="Copy callback URL" onClick={copyCallback}><Copy className="h-4 w-4" /></Button>
          </div>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="broker-app-id">App ID</Label>
            <Input id="broker-app-id" value={clientId} onChange={(event) => setClientId(event.target.value)} required maxLength={120} autoComplete="off" spellCheck={false} disabled={saving} />
            <p className="text-xs text-muted-foreground">Use the App ID from your API dashboard, including its suffix. This is different from your trading account ID.</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="broker-app-secret">App Secret</Label>
            <Input id="broker-app-secret" type="password" value={secret} onChange={(event) => setSecret(event.target.value)} required={needsSecret} maxLength={512} autoComplete="new-password" placeholder={needsSecret ? "Enter your App Secret" : "Leave blank to keep the saved secret"} disabled={saving} />
            <p className="text-xs text-muted-foreground">Stored encrypted. Your saved secret is never returned to this page. Password and OTP entry happens on FYERS.</p>
          </div>
          <p className="text-xs text-muted-foreground">FYERS sessions expire daily at 6:30 am IST. Use Reconnect to sign in again with your saved app.</p>
          <p className="text-xs text-muted-foreground">Changing app credentials requires stopped live sessions, no open positions and settled orders. Your next sign-in must belong to the same linked trading account.</p>
          <div className="flex justify-end gap-2 border-t pt-4">
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>Cancel</Button>
            <Button type="submit" disabled={saving}>{saving && <LoaderMark className="mr-2 h-4 w-4" />}Save and connect</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

FyersAppDialog.propTypes = {
  provider: PropTypes.object.isRequired,
  onClose: PropTypes.func.isRequired,
  onConnect: PropTypes.func.isRequired,
};
