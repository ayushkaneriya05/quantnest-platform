import { useCallback, useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Switch } from "@/shared/components/ui/switch";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { notificationApi } from "@/shared/services/notificationApi";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import WorkspaceState from '@/shared/components/WorkspaceState';

const labels = { INFO: "Information", WARNING: "Warnings", CRITICAL: "Critical alerts" };

export default function NotificationsTab() {
  const [preferences, setPreferences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingType, setSavingType] = useState("");
  const [error, setError] = useState('');
  const locked = useRef(false);
  const { notify } = useNotifications();

  const loadPreferences = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const response = await notificationApi.getPreferences();
      setPreferences(Array.isArray(response.data?.results) ? response.data.results : response.data || []);
    } catch (error) {
      setError(getApiErrorMessage(error, "Failed to load notification preferences"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPreferences();
  }, [loadPreferences]);

  const handleToggle = async (preference, enabled) => {
    if (locked.current) return;
    locked.current = true;
    setSavingType(preference.type);
    setPreferences((current) => current.map((item) => item.id === preference.id ? { ...item, in_app_enabled: enabled } : item));
    try {
      await notificationApi.updatePreference(preference.id, { in_app_enabled: enabled });
      notify.success(`${labels[preference.type] || preference.type} notifications ${enabled ? "enabled" : "disabled"}`);
    } catch (error) {
      setPreferences((current) => current.map((item) => item.id === preference.id ? { ...item, in_app_enabled: preference.in_app_enabled } : item));
      notify.error(getApiErrorMessage(error, "Failed to update notification preference"));
    } finally {
      locked.current = false;
      setSavingType("");
    }
  };

  if (loading || error) return <WorkspaceState loading={loading} error={error} title={loading ? 'Loading notification preferences' : undefined} onRetry={error ? loadPreferences : undefined} />;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-foreground">Notification Preferences</h2>
        <p className="mt-1 text-sm text-muted-foreground">Choose which in-app notification types appear in your feed and toast alerts.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {preferences.map((preference) => (
          <Card key={preference.id} className="border-border bg-card">
            <CardHeader className="py-4">
              <CardTitle className="text-base text-foreground">{labels[preference.type] || preference.type}</CardTitle>
            </CardHeader>
            <CardContent className="flex items-center justify-between gap-4 border-t border-border py-4">
              <div className="flex items-center gap-2 text-foreground">
                <Bell className="h-4 w-4 shrink-0 text-brand" />
                <span className="text-sm">In-app notifications</span>
              </div>
              <Switch aria-label={`${labels[preference.type] || preference.type} notifications`} checked={Boolean(preference.in_app_enabled)} onCheckedChange={(enabled) => handleToggle(preference, enabled)} disabled={Boolean(savingType)} />
            </CardContent>
          </Card>
        ))}
        {!preferences.length && <div className="rounded-lg border border-border bg-card p-8 text-center text-muted-foreground">No notification preferences are available.</div>}
      </div>
    </div>
  );
}
