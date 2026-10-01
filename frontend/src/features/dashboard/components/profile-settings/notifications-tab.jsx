import { useCallback, useEffect, useState } from "react";
import { Bell } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Switch } from "@/shared/components/ui/switch";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { notificationApi } from "@/shared/services/notificationApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";

const labels = { INFO: "Information", WARNING: "Warnings", CRITICAL: "Critical alerts" };

export default function NotificationsTab() {
  const [preferences, setPreferences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingType, setSavingType] = useState("");
  const { notify } = useNotifications();

  const loadPreferences = useCallback(async () => {
    try {
      setLoading(true);
      const response = await notificationApi.getPreferences();
      setPreferences(Array.isArray(response.data?.results) ? response.data.results : response.data || []);
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Failed to load notification preferences"));
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    loadPreferences();
  }, [loadPreferences]);

  const handleToggle = async (preference, enabled) => {
    setSavingType(preference.type);
    setPreferences((current) => current.map((item) => item.id === preference.id ? { ...item, in_app_enabled: enabled } : item));
    try {
      await notificationApi.updatePreference(preference.id, { in_app_enabled: enabled });
      notify.success(`${labels[preference.type] || preference.type} notifications ${enabled ? "enabled" : "disabled"}`);
    } catch (error) {
      setPreferences((current) => current.map((item) => item.id === preference.id ? { ...item, in_app_enabled: preference.in_app_enabled } : item));
      notify.error(getApiErrorMessage(error, "Failed to update notification preference"));
    } finally {
      setSavingType("");
    }
  };

  if (loading) return <div className="p-8 text-center text-slate-400">Loading preferences...</div>;

  return (
    <div className="space-y-6 pb-12">
      <div>
        <h2 className="text-xl font-semibold text-slate-100">Notification Preferences</h2>
        <p className="mt-1 text-sm text-slate-400">Choose which in-app notification types appear in your feed and toast alerts.</p>
      </div>
      <div className="grid gap-4">
        {preferences.map((preference) => (
          <Card key={preference.id} className="border-gray-800 bg-gray-900">
            <CardHeader className="py-4">
              <CardTitle className="text-base text-slate-200">{labels[preference.type] || preference.type}</CardTitle>
            </CardHeader>
            <CardContent className="flex items-center justify-between gap-4 border-t border-gray-800 py-4">
              <div className="flex items-center gap-2 text-slate-300">
                <Bell className="h-4 w-4 text-indigo-400" />
                <span className="text-sm">In-app notifications</span>
              </div>
              <Switch checked={Boolean(preference.in_app_enabled)} onCheckedChange={(enabled) => handleToggle(preference, enabled)} disabled={savingType === preference.type} />
            </CardContent>
          </Card>
        ))}
        {!preferences.length && <div className="rounded-lg border border-gray-800 bg-gray-900 p-8 text-center text-slate-400">No notification preferences are available.</div>}
      </div>
    </div>
  );
}
