import React, { useEffect, useMemo, useState } from "react";
import { Loader2, RefreshCw, Save, SlidersHorizontal } from "lucide-react";

import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
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
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { brokersApi } from "@/shared/services/brokersApi";

const defaultSettings = {
  id: 1,
  default_slippage_pct: "0.100",
  order_timeout_seconds: 30,
  max_retries: 2,
  retry_delay_ms: 500,
  partial_fill_action: "ACCEPT",
  use_amo_orders: false,
  primary_broker: "FYERS",
};

export default function BrokerOrderSettings() {
  const { notify } = useNotifications();
  const [settings, setSettings] = useState(defaultSettings);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const loadSettings = async () => {
    try {
      if (loading) setLoading(true);
      const response = await brokersApi.getSettings();
      setSettings({
        ...defaultSettings,
        ...(response.data || {}),
      });
    } catch (error) {
      notify.error(
        error?.response?.data?.detail ||
          error?.response?.data?.error ||
          "Failed to load broker order settings",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

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
        default_slippage_pct: settings.default_slippage_pct,
        order_timeout_seconds: Number(settings.order_timeout_seconds || 0),
        max_retries: Number(settings.max_retries || 0),
        retry_delay_ms: Number(settings.retry_delay_ms || 0),
        partial_fill_action: settings.partial_fill_action,
        use_amo_orders: Boolean(settings.use_amo_orders),
        primary_broker: settings.primary_broker,
      };
      const response = await brokersApi.updateSettings(settings.id, payload);
      setSettings({
        ...defaultSettings,
        ...(response.data || {}),
      });
      notify.success("Broker execution settings saved");
    } catch (error) {
      notify.error(
        error?.response?.data?.detail ||
          error?.response?.data?.error ||
          "Failed to save broker order settings",
      );
    } finally {
      setBusy(false);
    }
  };

  const pageActions = useMemo(
    () => (
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          onClick={loadSettings}
          disabled={busy}
          className="border-gray-700 text-gray-100"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${busy ? "animate-spin" : ""}`} />
          Refresh
        </Button>
        <Button
          onClick={saveSettings}
          disabled={busy}
          className="bg-cyan-600 hover:bg-cyan-500"
        >
          <Save className="h-4 w-4 mr-2" />
          Save Settings
        </Button>
      </div>
    ),
    [settings, busy],
  );

  useSetPageActions(pageActions);

  if (loading) {
    return (
      <div className="container-padding py-10 flex justify-center text-cyan-300">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      <Card className="bg-gray-900/60 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white text-lg flex items-center gap-2">
            <SlidersHorizontal className="h-5 w-5 text-cyan-300" />
            Broker Execution Defaults
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-5 lg:grid-cols-2">
          <div className="space-y-2">
            <Label className="text-gray-300">Primary Broker</Label>
            <Select
              value={settings.primary_broker}
              onValueChange={(value) => updateField("primary_broker", value)}
            >
              <SelectTrigger className="bg-gray-950/40 border-gray-700 text-white">
                <SelectValue placeholder="Primary broker" />
              </SelectTrigger>
              <SelectContent className="bg-gray-900 border-gray-800 text-white">
                <SelectItem value="FYERS">FYERS</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-gray-300">Partial Fill Action</Label>
            <Select
              value={settings.partial_fill_action}
              onValueChange={(value) => updateField("partial_fill_action", value)}
            >
              <SelectTrigger className="bg-gray-950/40 border-gray-700 text-white">
                <SelectValue placeholder="Partial fill action" />
              </SelectTrigger>
              <SelectContent className="bg-gray-900 border-gray-800 text-white">
                <SelectItem value="ACCEPT">Accept Partial Fill</SelectItem>
                <SelectItem value="CANCEL_REMAINING">Cancel Remaining Quantity</SelectItem>
                <SelectItem value="RETRY_REMAINING">Retry Remaining Quantity</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-gray-300">Default Slippage (%)</Label>
            <Input
              type="number"
              step="0.001"
              min="0"
              value={settings.default_slippage_pct}
              onChange={(event) =>
                updateField("default_slippage_pct", event.target.value)
              }
              className="bg-gray-950/40 border-gray-700 text-white"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-gray-300">Order Timeout (seconds)</Label>
            <Input
              type="number"
              min="1"
              value={settings.order_timeout_seconds}
              onChange={(event) =>
                updateField("order_timeout_seconds", event.target.value)
              }
              className="bg-gray-950/40 border-gray-700 text-white"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-gray-300">Max Retries</Label>
            <Input
              type="number"
              min="0"
              value={settings.max_retries}
              onChange={(event) => updateField("max_retries", event.target.value)}
              className="bg-gray-950/40 border-gray-700 text-white"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-gray-300">Retry Delay (ms)</Label>
            <Input
              type="number"
              min="0"
              value={settings.retry_delay_ms}
              onChange={(event) =>
                updateField("retry_delay_ms", event.target.value)
              }
              className="bg-gray-950/40 border-gray-700 text-white"
            />
          </div>

          <div className="flex items-center justify-between rounded-xl border border-gray-800 bg-gray-950/30 px-4 py-4">
            <div>
              <p className="text-sm font-medium text-white">Use AMO Orders</p>
              <p className="text-xs text-gray-500">
                Sends Fyers offline orders when supported
              </p>
            </div>
            <Switch
              checked={Boolean(settings.use_amo_orders)}
              onCheckedChange={(checked) => updateField("use_amo_orders", checked)}
            />
          </div>


        </CardContent>
      </Card>
    </div>
  );
}
