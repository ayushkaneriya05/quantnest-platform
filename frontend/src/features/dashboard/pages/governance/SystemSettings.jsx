import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Database,
  RefreshCw,
  Server,
  Settings,
  Shield,
} from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent } from "@/shared/components/ui/card";
import { Switch } from "@/shared/components/ui/switch";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { auditApi } from "@/shared/services/auditApi";
import { GlobalLoader } from '@/shared/components/ui/global-loader';

/* ── Setting Card Component ── */
function SettingCard({ icon: Icon, title, description, children, accent = "text-cyan-400" }) {
  return (
    <Card className="border-gray-800 bg-gray-900/60">
      <CardContent className="p-5 space-y-3">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-gray-800/50 shrink-0">
            <Icon className={`h-4 w-4 ${accent}`} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-medium text-white">{title}</h3>
            <p className="text-xs text-gray-400 mt-0.5">{description}</p>
          </div>
        </div>
        {children}
      </CardContent>
    </Card>
  );
}

/* ── Toggle Row ── */
function ToggleRow({ label, description, enabled, onChange }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2 border-t border-gray-800/50">
      <div>
        <p className="text-sm text-white">{label}</p>
        {description && <p className="text-xs text-gray-500">{description}</p>}
      </div>
      <Switch checked={enabled} onCheckedChange={onChange} />
    </div>
  );
}

export default function SystemSettings() {
  const { notify } = useNotifications();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  // Local UI state for toggle settings (simulated — these would connect to real API)
  const [settings, setSettings] = useState({
    auditEnabled: true,
    autoComplianceOnApproval: true,
    auditLoginLogout: true,
    auditStrategyChanges: true,
    auditBrokerChanges: true,
    auditLiveTrading: true,
    auditMarketplace: true,
    requireComplianceForApproval: true,
    notifyOnApproval: true,
    notifyOnViolation: true,
  });

  const loadStats = async () => {
    try {
      setLoading(true);
      const res = await auditApi.getStats();
      setStats(res.data);
    } catch {
      notify.error("Failed to load system stats");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  const toggleSetting = (key) => {
    setSettings((prev) => ({ ...prev, [key]: !prev[key] }));
    notify.info(`Setting "${key}" updated`);
  };

  useSetPageActions(
    <Button variant="outline" onClick={loadStats} className="border-gray-700 text-gray-100">
      <RefreshCw className="mr-2 h-4 w-4" />
      Refresh
    </Button>
  );

  if (loading) {
    return (
      <GlobalLoader />
    );
  }

  return (
    <div className="container-padding space-y-6 py-6 lg:py-8">
      {/* System Health Cards */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: "Audit System",
            value: settings.auditEnabled ? "Active" : "Disabled",
            tone: settings.auditEnabled ? "text-emerald-300" : "text-red-300",
            icon: Shield,
          },
          {
            label: "Events Recorded",
            value: stats?.total_logs || 0,
            tone: "text-white",
            icon: Activity,
          },
          {
            label: "Pending Actions",
            value: stats?.pending_approvals || 0,
            tone: stats?.pending_approvals > 0 ? "text-amber-300" : "text-emerald-300",
            icon: AlertTriangle,
          },
          {
            label: "Compliance Rate",
            value: `${stats?.compliance_pass_rate || 0}%`,
            tone: (stats?.compliance_pass_rate || 0) >= 80 ? "text-emerald-300" : "text-amber-300",
            icon: CheckCircle,
          },
        ].map((item) => (
          <Card key={item.label} className="border-gray-800 bg-gray-900/60">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <p className="text-xs uppercase tracking-[0.16em] text-gray-500">{item.label}</p>
                <item.icon className="h-4 w-4 text-gray-600" />
              </div>
              <p className={`mt-2 text-2xl font-semibold ${item.tone}`}>{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Audit Trail Configuration */}
        <SettingCard
          icon={Shield}
          title="Audit Trail Configuration"
          description="Control which events are tracked in the audit log"
          accent="text-cyan-400"
        >
          <ToggleRow
            label="Enable Audit System"
            description="Master switch for all audit logging"
            enabled={settings.auditEnabled}
            onChange={() => toggleSetting("auditEnabled")}
          />
          <ToggleRow
            label="Login / Logout Events"
            description="Track user authentication events"
            enabled={settings.auditLoginLogout}
            onChange={() => toggleSetting("auditLoginLogout")}
          />
          <ToggleRow
            label="Strategy Changes"
            description="Track strategy create, update, and delete"
            enabled={settings.auditStrategyChanges}
            onChange={() => toggleSetting("auditStrategyChanges")}
          />
          <ToggleRow
            label="Broker Credential Changes"
            description="Track broker connection modifications"
            enabled={settings.auditBrokerChanges}
            onChange={() => toggleSetting("auditBrokerChanges")}
          />
          <ToggleRow
            label="Live Trading Operations"
            description="Track deploy, pause, and stop actions"
            enabled={settings.auditLiveTrading}
            onChange={() => toggleSetting("auditLiveTrading")}
          />
          <ToggleRow
            label="Marketplace Activities"
            description="Track listing and subscription changes"
            enabled={settings.auditMarketplace}
            onChange={() => toggleSetting("auditMarketplace")}
          />
        </SettingCard>

        {/* Governance Policies */}
        <SettingCard
          icon={Settings}
          title="Governance Policies"
          description="Configure approval workflows and compliance requirements"
          accent="text-purple-400"
        >
          <ToggleRow
            label="Auto-run Compliance on Approval Request"
            description="Automatically run compliance checks when a strategy is submitted for approval"
            enabled={settings.autoComplianceOnApproval}
            onChange={() => toggleSetting("autoComplianceOnApproval")}
          />
          <ToggleRow
            label="Require Compliance Pass for Approval"
            description="Strategies must pass all compliance checks before they can be approved"
            enabled={settings.requireComplianceForApproval}
            onChange={() => toggleSetting("requireComplianceForApproval")}
          />
          <ToggleRow
            label="Notify on Approval Decision"
            description="Send in-app notification when an approval is decided"
            enabled={settings.notifyOnApproval}
            onChange={() => toggleSetting("notifyOnApproval")}
          />
          <ToggleRow
            label="Notify on Risk Violation"
            description="Alert when risk violations are detected"
            enabled={settings.notifyOnViolation}
            onChange={() => toggleSetting("notifyOnViolation")}
          />
        </SettingCard>

        {/* Entity Coverage */}
        <SettingCard
          icon={Database}
          title="Tracked Entities"
          description="Entities currently monitored by the audit system"
          accent="text-amber-400"
        >
          <div className="space-y-2 pt-2">
            {[
              { name: "Strategy", count: stats?.entity_breakdown?.Strategy || 0 },
              { name: "BrokerCredential", count: stats?.entity_breakdown?.BrokerCredential || 0 },
              { name: "TradingSession", count: stats?.entity_breakdown?.TradingSession || 0 },
              { name: "MarketplaceListing", count: stats?.entity_breakdown?.MarketplaceListing || 0 },
              { name: "StrategyApproval", count: stats?.entity_breakdown?.StrategyApproval || 0 },
            ].map((entity) => (
              <div
                key={entity.name}
                className="flex items-center justify-between rounded-lg border border-gray-800 bg-black/20 px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-cyan-400" />
                  <span className="text-sm text-white">{entity.name}</span>
                </div>
                <Badge className="bg-gray-800 text-gray-300 border-gray-700 text-xs">
                  {entity.count} events
                </Badge>
              </div>
            ))}
          </div>
        </SettingCard>

        {/* Platform Info */}
        <SettingCard
          icon={Server}
          title="Platform Information"
          description="System and environment details"
          accent="text-emerald-400"
        >
          <div className="space-y-2 pt-2">
            {[
              { label: "Platform", value: "QuantNest" },
              { label: "Version", value: "1.0.0" },
              { label: "Environment", value: "Development" },
              { label: "Audit Retention", value: "90 days" },
              { label: "Compliance Engine", value: "10 checks" },
              { label: "Celery Queue", value: "Active" },
            ].map((info) => (
              <div
                key={info.label}
                className="flex items-center justify-between text-sm py-1.5 border-b border-gray-800/30 last:border-b-0"
              >
                <span className="text-gray-500">{info.label}</span>
                <span className="text-white font-medium">{info.value}</span>
              </div>
            ))}
          </div>
        </SettingCard>
      </div>
    </div>
  );
}
