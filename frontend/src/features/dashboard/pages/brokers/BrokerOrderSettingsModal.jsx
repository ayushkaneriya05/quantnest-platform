import React, { useEffect, useState } from "react";
import { Save, ShieldAlert, Activity, Wifi, Clock, Settings, RefreshCw } from "lucide-react";

import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import { Switch } from "@/shared/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/shared/components/ui/dialog";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { brokersApi } from "@/shared/services/brokersApi";
import { GlobalLoader } from "@/shared/components/ui/global-loader";

const defaultSettings = {
  id: null,
  default_slippage_pct: "0.100",
  order_timeout_seconds: 30,
  max_retries: 2,
  retry_delay_ms: 500,
  partial_fill_action: "ACCEPT",
  use_amo_orders: false,
};

export function BrokerOrderSettingsModal({ isOpen, onClose, credentialId, providerName }) {
  const { notify } = useNotifications();
  const [settings, setSettings] = useState(defaultSettings);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (isOpen && credentialId) {
      loadSettings();
    }
  }, [isOpen, credentialId]);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const response = await brokersApi.getSettings({ credential_id: credentialId });
      setSettings({
        ...defaultSettings,
        ...(response.data || {}),
      });
    } catch (error) {
      notify.error(
        error?.response?.data?.error || "Failed to load execution settings",
      );
    } finally {
      setLoading(false);
    }
  };

  const updateField = (key, value) => {
    setSettings((current) => ({
      ...current,
      [key]: value,
    }));
  };

  const saveSettings = async () => {
    try {
      setBusy(true);
      const payload = {
        credential_id: credentialId,
        // default_slippage_pct: settings.default_slippage_pct,
        order_timeout_seconds: Number(settings.order_timeout_seconds || 0),
        // max_retries: Number(settings.max_retries || 0),
        // retry_delay_ms: Number(settings.retry_delay_ms || 0),
        // partial_fill_action: settings.partial_fill_action,
        // use_amo_orders: Boolean(settings.use_amo_orders),
      };
      
      const response = await brokersApi.updateSettings(settings.id || 0, payload);
      setSettings({
        ...defaultSettings,
        ...(response.data || {}),
      });
      notify.success("Execution settings saved securely");
      onClose();
    } catch (error) {
      notify.error(
        error?.response?.data?.error || "Failed to save execution settings",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[700px] border-slate-700/60 bg-slate-900/95 backdrop-blur-xl p-0 gap-0 overflow-hidden shadow-2xl">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 via-transparent to-cyan-500/10 pointer-events-none" />
        
        <DialogHeader className="px-6 py-5 border-b border-slate-800/60 bg-slate-950/40 relative z-10">
          <DialogTitle className="text-xl font-semibold flex items-center gap-2 text-slate-100">
            <Settings className="h-5 w-5 text-indigo-400" />
            Execution Engine Defaults
          </DialogTitle>
          <p className="text-sm text-slate-400 mt-1">
            Configure how the algorithm routes orders to {providerName || "your broker"}.
          </p>
        </DialogHeader>

        {loading ? (
          <div className="h-64 relative z-10">
            <GlobalLoader />
          </div>
        ) : (
          <div className="px-6 py-4 space-y-5 relative z-10 overflow-y-auto max-h-[70vh] scrollbar-theme">
            
            {/* Section 1: Network & Reliability */}
            {/* <div className="space-y-3">
              <h3 className="text-sm font-medium text-indigo-400 flex items-center gap-2 uppercase tracking-wider">
                <Wifi className="h-4 w-4" /> Network Resiliency
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5 p-3 rounded-xl border border-slate-800/60 bg-slate-900/50 hover:bg-slate-800/40 transition-colors">
                  <Label className="text-slate-300 text-xs">Max Retries</Label>
                  <Input
                    type="number"
                    min="0"
                    value={settings.max_retries}
                    onChange={(e) => updateField("max_retries", e.target.value)}
                    className="bg-slate-950/50 border-slate-700 text-slate-100 h-9"
                  />
                  <p className="text-[11px] text-slate-500 mt-1 leading-tight">
                    Attempts to bypass 502/Rate-Limit API errors.
                  </p>
                </div>
                <div className="space-y-1.5 p-3 rounded-xl border border-slate-800/60 bg-slate-900/50 hover:bg-slate-800/40 transition-colors">
                  <Label className="text-slate-300 text-xs">Retry Delay (ms)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={settings.retry_delay_ms}
                    onChange={(e) => updateField("retry_delay_ms", e.target.value)}
                    className="bg-slate-950/50 border-slate-700 text-slate-100 h-9"
                  />
                  <p className="text-[11px] text-slate-500 mt-1 leading-tight">
                    Wait time before re-firing a dropped order.
                  </p>
                </div>
              </div>
            </div> */}

            {/* Section 2: Execution Limits */}
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-emerald-400 flex items-center gap-2 uppercase tracking-wider">
                <Activity className="h-4 w-4" /> Execution Limits
              </h3>
              {/* <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5 p-3 rounded-xl border border-slate-800/60 bg-slate-900/50 hover:bg-slate-800/40 transition-colors">
                  <Label className="text-slate-300 text-xs">Default Slippage (%)</Label>
                  <Input
                    type="number"
                    step="0.001"
                    min="0"
                    value={settings.default_slippage_pct}
                    onChange={(e) => updateField("default_slippage_pct", e.target.value)}
                    className="bg-slate-950/50 border-slate-700 text-slate-100 h-9"
                  />
                  <p className="text-[11px] text-slate-500 mt-1 leading-tight">
                    Auto-adjusts Limit prices to guarantee fills.
                  </p>
                </div> */}
                <div className="space-y-1.5 p-3 rounded-xl border border-slate-800/60 bg-slate-900/50 hover:bg-slate-800/40 transition-colors">
                  <Label className="text-slate-300 text-xs">Order Timeout (sec)</Label>
                  <Input
                    type="number"
                    min="1"
                    value={settings.order_timeout_seconds}
                    onChange={(e) => updateField("order_timeout_seconds", e.target.value)}
                    className="bg-slate-950/50 border-slate-700 text-slate-100 h-9"
                  />
                  <p className="text-[11px] text-slate-500 mt-1 leading-tight">
                    Seconds before unacknowledged orders drop.
                  </p>
                </div>
                {/* <div className="space-y-1.5 p-3 rounded-xl border border-slate-800/60 bg-slate-900/50 hover:bg-slate-800/40 transition-colors col-span-2">
                  <Label className="text-slate-300 text-xs">Partial Fill Action</Label>
                  <Select
                    value={settings.partial_fill_action}
                    onValueChange={(value) => updateField("partial_fill_action", value)}
                  >
                    <SelectTrigger className="bg-slate-950/50 border-slate-700 text-slate-100 h-9 w-full">
                      <SelectValue placeholder="Partial fill action" />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-900 border-slate-800 text-slate-100">
                      <SelectItem value="ACCEPT">Accept Partial Fill (Ignore remainder)</SelectItem>
                      <SelectItem value="CANCEL_REMAINING">Cancel Remaining Quantity</SelectItem>
                      <SelectItem value="RETRY_REMAINING">Retry Remaining Quantity</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-[11px] text-slate-500 mt-1 leading-tight">
                    How the engine handles illiquid assets that only partially fill.
                  </p>
                </div> 
              </div>*/}
            </div>

            {/* Section 3: Off-Market */}
            {/* <div className="space-y-3">
              <h3 className="text-sm font-medium text-amber-400 flex items-center gap-2 uppercase tracking-wider">
                <Clock className="h-4 w-4" /> Off-Market Engine
              </h3>
              <div className="flex items-center justify-between p-3 rounded-xl border border-slate-800/60 bg-slate-900/50 hover:bg-slate-800/40 transition-colors">
                <div className="pr-4">
                  <Label className="text-slate-200 text-sm">Use AMO Orders</Label>
                  <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                    Automatically convert orders to After Market Orders (AMO) when the exchange is closed. Supported natively by Fyers.
                  </p>
                </div>
                <Switch
                  checked={Boolean(settings.use_amo_orders)}
                  onCheckedChange={(checked) => updateField("use_amo_orders", checked)}
                  className="data-[state=checked]:bg-amber-500 scale-90"
                />
              </div>
            </div> */}

          </div>
        )}

        <DialogFooter className="px-6 py-4 border-t border-slate-800/60 bg-slate-950/60 relative z-10 flex gap-3 sm:justify-end">
          <Button variant="ghost" onClick={onClose} disabled={busy} className="text-slate-300 hover:text-white hover:bg-slate-800">
            Cancel
          </Button>
          <Button 
            onClick={saveSettings} 
            disabled={busy || loading}
            className="bg-indigo-600 hover:bg-indigo-500 text-white min-w-[120px] transition-all shadow-[0_0_15px_rgba(79,70,229,0.3)] hover:shadow-[0_0_20px_rgba(79,70,229,0.5)]"
          >
            {busy ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            {busy ? "Saving..." : "Save Settings"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
