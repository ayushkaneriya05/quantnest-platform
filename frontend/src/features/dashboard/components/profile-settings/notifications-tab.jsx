import React, { useEffect, useState } from "react";
import { analyticsSuiteApi } from "@/shared/services/analyticsSuiteApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Switch } from "@/shared/components/ui/switch";
import { Bell, Mail } from "lucide-react";
import { useNotifications } from "@/shared/hooks/useNotifications";

export default function NotificationsTab() {
  const [preferences, setPreferences] = useState([]);
  const [loading, setLoading] = useState(true);
  const { notify } = useNotifications();

  useEffect(() => {
    loadPreferences();
  }, []);

  const loadPreferences = async () => {
    try {
      setLoading(true);
      const res = await analyticsSuiteApi.getNotificationPrefs();
      setPreferences(Array.isArray(res.data?.results) ? res.data.results : res.data || []);
    } catch (error) {
      notify.error("Failed to load notification preferences");
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (id, field, value) => {
    try {
      // Optimistic UI update
      setPreferences(prev => prev.map(p => p.id === id ? { ...p, [field]: value } : p));
      await analyticsSuiteApi.updateNotificationPref(id, { [field]: value });
      notify.success("Preference updated");
    } catch (error) {
      // Revert on error
      notify.error("Failed to update preference");
      loadPreferences();
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-slate-400">Loading preferences...</div>;
  }

  return (
    <div className="space-y-6 pb-12">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold text-slate-100">Notification Preferences</h2>
          <p className="text-sm text-slate-400 mt-1">Manage how and when you receive notifications from QuantNest.</p>
        </div>
      </div>

      <div className="grid gap-4">
        {preferences.map((pref) => (
          <Card key={pref.id} className="bg-gray-900 border-gray-800">
            <CardHeader className="py-4">
              <CardTitle className="text-base text-slate-200">
                {pref.notification_type.replace(/_/g, ' ')}
              </CardTitle>
            </CardHeader>
            <CardContent className="py-4 border-t border-gray-800 flex flex-col sm:flex-row gap-6">
              <div className="flex items-center justify-between w-full sm:w-1/2">
                <div className="flex items-center gap-2 text-slate-300">
                  <Bell className="w-4 h-4 text-indigo-400" />
                  <span className="text-sm">In-App Notifications</span>
                </div>
                <Switch 
                  checked={pref.in_app_enabled}
                  onCheckedChange={(val) => handleToggle(pref.id, 'in_app_enabled', val)}
                />
              </div>

              <div className="flex items-center justify-between w-full sm:w-1/2">
                <div className="flex items-center gap-2 text-slate-300">
                  <Mail className="w-4 h-4 text-indigo-400" />
                  <span className="text-sm">Email Notifications</span>
                </div>
                <Switch 
                  checked={pref.email_enabled}
                  onCheckedChange={(val) => handleToggle(pref.id, 'email_enabled', val)}
                />
              </div>
            </CardContent>
          </Card>
        ))}
        {preferences.length === 0 && (
          <div className="text-center p-8 text-slate-400 bg-gray-900 rounded-lg border border-gray-800">
            No preferences found. Backend might need to initialize them.
          </div>
        )}
      </div>
    </div>
  );
}
