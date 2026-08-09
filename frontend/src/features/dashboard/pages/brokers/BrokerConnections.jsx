import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  BadgeCheck,
  Building2,
  Power,
  Radio,
  RefreshCw,
  ShieldCheck,
  Unplug,
  Wallet,
  Settings,
} from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useSetPageActions } from "@/shared/hooks/useSetPageActions";
import { brokersApi } from "@/shared/services/brokersApi";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
import { BrokerOrderSettingsModal } from "./BrokerOrderSettingsModal";


const providerTheme = {
  FYERS: {
    accent: "from-cyan-500/20 via-sky-500/10 to-transparent",
    badge: "bg-cyan-500/10 text-cyan-300 border-cyan-500/20",
    cta: "bg-cyan-600 hover:bg-cyan-500",
  },
  ZERODHA: {
    accent: "from-blue-500/20 via-blue-500/10 to-transparent",
    badge: "bg-blue-500/10 text-blue-300 border-blue-500/20",
    cta: "bg-blue-600 hover:bg-blue-500",
  },
  ANGEL: {
    accent: "from-rose-500/20 via-rose-500/10 to-transparent",
    badge: "bg-rose-500/10 text-rose-300 border-rose-500/20",
    cta: "bg-rose-600 hover:bg-rose-500",
  },
};

function statusLabel(provider) {
  if (provider.is_active && provider.is_verified && provider.session_valid) {
    return "LIVE CONNECTED";
  }
  if (provider.session_expired) return "RECONNECT REQUIRED";
  if (provider.is_verified) return "CONNECTED";
  if (provider.configured) return "AUTH REQUIRED";
  if (!provider.enabled) return "COMING SOON";
  return "NOT CONNECTED";
}

function normalizeProfile(payload) {
  if (!payload || typeof payload !== "object") return {};
  const data = payload.data || payload;
  return {
    name: data.name || data.display_name || data.fy_id || "Fyers Account",
    email: data.email_id || data.email || "-",
    mobile: data.mobile_number || data.mobile || "-",
    pan: data.PAN || data.pan || "-",
  };
}

function normalizeFunds(payload) {
  const rows = payload?.fund_limit || payload?.data?.fund_limit || [];
  return Array.isArray(rows) ? rows.slice(0, 6) : [];
}

function formatDateTime(value) {
  if (!value) return "Not connected";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function getExpiryMeta(provider) {
  if (!provider.session_expires_at) {
    return {
      label: provider.session_expired ? "Expired - reconnect required" : "Not connected",
      tone: "text-gray-500",
    };
  }

  const expiry = new Date(provider.session_expires_at);
  const diffMs = expiry.getTime() - Date.now();
  if (Number.isNaN(expiry.getTime()) || diffMs <= 0 || provider.session_expired) {
    return {
      label: "Expired - reconnect required",
      tone: "text-red-300",
    };
  }

  const diffMinutes = Math.floor(diffMs / 60000);
  if (diffMinutes < 60) {
    return {
      label: `Expires in ${Math.max(diffMinutes, 1)} min`,
      tone: "text-amber-300",
    };
  }

  const diffHours = Math.floor(diffMinutes / 60);
  return {
    label: `Active for ~${diffHours} hr`,
    tone: "text-emerald-300",
  };
}

export default function BrokerConnections() {
  const { notify } = useNotifications();
  const [searchParams, setSearchParams] = useSearchParams();
  const [catalog, setCatalog] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [profileMap, setProfileMap] = useState({});
  const [fundsMap, setFundsMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [busyBroker, setBusyBroker] = useState("");
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [settingsCredentialId, setSettingsCredentialId] = useState(null);
  const [settingsProviderName, setSettingsProviderName] = useState("");


  const loadBrokerState = async () => {
    try {
      setLoading((current) => (catalog.length ? current : true));
      const [catalogRes, sessionsRes] = await Promise.all([
        brokersApi.getCatalog(),
        brokersApi.getSessions(),
      ]);
      const nextCatalog = Array.isArray(catalogRes.data) ? catalogRes.data : [];
      const nextSessions = Array.isArray(sessionsRes.data?.results)
        ? sessionsRes.data.results
        : Array.isArray(sessionsRes.data)
          ? sessionsRes.data
          : [];
      setCatalog(nextCatalog);
      setSessions(nextSessions);

      await Promise.all(
        nextCatalog
          .filter((provider) => provider.credential_id && provider.is_verified)
          .map(async (provider) => {
            try {
              const [profileRes, fundsRes] = await Promise.all([
                brokersApi.getProfile(provider.credential_id),
                brokersApi.getFunds(provider.credential_id),
              ]);
              setProfileMap((current) => ({
                ...current,
                [provider.broker_name]: normalizeProfile(profileRes.data),
              }));
              setFundsMap((current) => ({
                ...current,
                [provider.broker_name]: normalizeFunds(fundsRes.data),
              }));
            } catch (error) {
              // Keep page resilient if one broker profile/funds call fails.
            }
          }),
      );
    } catch (error) {
      notify.error(
        error?.response?.data?.detail ||
          error?.response?.data?.error ||
          "Failed to load broker connections",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBrokerState();
  }, []);

  useEffect(() => {
    const status = searchParams.get("status");
    const broker = searchParams.get("broker");
    const message = searchParams.get("message");
    if (!status) return;

    if (status === "connected") {
      notify.success(`${broker || "Broker"} connected successfully`);
    } else {
      notify.error(message || `${broker || "Broker"} connection failed`);
    }
    setSearchParams({}, { replace: true });
    loadBrokerState();
  }, [searchParams, setSearchParams]);

  const activeSessionByCredential = useMemo(() => {
    const lookup = {};
    sessions.forEach((session) => {
      if (session.is_valid) {
        lookup[String(session.credential)] = session;
      }
    });
    return lookup;
  }, [sessions]);

  const connectBroker = async (brokerName) => {
    try {
      setBusyBroker(brokerName);
      const response = await brokersApi.connectBroker(brokerName);
      const authUrl = response.data?.auth_url;
      if (authUrl) {
        window.location.assign(authUrl);
        return;
      }
      notify.success(`${brokerName} connection started`);
      await loadBrokerState();
    } catch (error) {
      notify.error(
        error?.response?.data?.detail ||
          error?.response?.data?.error ||
          `${brokerName} connection failed`,
      );
    } finally {
      setBusyBroker("");
    }
  };



  const activateBroker = async (provider) => {
    if (!provider.credential_id) return;
    try {
      setBusyBroker(provider.broker_name);
      await brokersApi.activateCredential(provider.credential_id);
      notify.success(`${provider.display_name} activated for execution`);
      await loadBrokerState();
    } catch (error) {
      notify.error(
        error?.response?.data?.detail || `Failed to activate ${provider.display_name}`,
      );
    } finally {
      setBusyBroker("");
    }
  };

  const disconnectBroker = async (provider) => {
    if (!provider.credential_id) return;
    try {
      setBusyBroker(provider.broker_name);
      await brokersApi.disconnectCredential(provider.credential_id);
      notify.success(`${provider.display_name} disconnected`);
      await loadBrokerState();
    } catch (error) {
      notify.error(
        error?.response?.data?.detail ||
          `Failed to disconnect ${provider.display_name}`,
      );
    } finally {
      setBusyBroker("");
    }
  };

  const pageActions = useMemo(
    () => (
      <div className="flex gap-2">
        <Button
          variant="outline"
          onClick={loadBrokerState}
          className="border-gray-700 text-gray-100"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>
    ),
    [catalog.length],
  );

  useSetPageActions(pageActions);

  if (loading) {
    return (
      <GlobalLoader />
    );
  }

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      <div className="grid gap-5 xl:grid-cols-3">
        {catalog.map((provider) => {
          const theme = providerTheme[provider.broker_name] || providerTheme.FYERS;
          const status = statusLabel(provider);
          const session = provider.credential_id
            ? activeSessionByCredential[String(provider.credential_id)]
            : null;
          const profile = profileMap[provider.broker_name] || {};
          const funds = fundsMap[provider.broker_name] || [];
          const isBusy = busyBroker === provider.broker_name;
          const expiryMeta = getExpiryMeta(provider);

          return (
            <Card
              key={provider.broker_name}
              className="relative overflow-hidden border-gray-800 bg-gray-900/60"
            >
              <div
                className={`absolute inset-x-0 top-0 h-28 bg-gradient-to-br ${theme.accent}`}
              />
              <CardHeader className="relative">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-sm font-bold text-white">
                      {provider.logo_text}
                    </div>
                    <div>
                      <CardTitle className="text-white text-lg">
                        {provider.display_name}
                      </CardTitle>
                      <p className="mt-1 text-xs uppercase tracking-[0.22em] text-gray-500">
                        Trading Broker
                      </p>
                    </div>
                  </div>
                  <Badge className={theme.badge}>{status}</Badge>
                </div>
              </CardHeader>

              <CardContent className="relative space-y-5">
                <p className="text-sm leading-6 text-gray-400">
                  {provider.description}
                </p>

                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-2xl border border-gray-800 bg-black/20 p-3">
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <BadgeCheck className="h-3.5 w-3.5 text-emerald-300" />
                      Verification
                    </div>
                    <p className="mt-2 text-sm font-semibold text-white">
                      {provider.is_verified ? "Verified" : "Pending"}
                    </p>
                    <p className="text-xs text-gray-500">
                      {provider.last_verified_at || "No check yet"}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-gray-800 bg-black/20 p-3">
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <Radio className="h-3.5 w-3.5 text-cyan-300" />
                      Session
                    </div>
                    <p className="mt-2 text-sm font-semibold text-white">
                      {provider.session_expired ? "Expired" : session ? "Online" : "Offline"}
                    </p>
                    <p className={`text-xs ${expiryMeta.tone}`}>
                      {expiryMeta.label}
                    </p>
                    <p className="mt-1 text-[11px] text-gray-500">
                      {provider.session_expires_at
                        ? `Valid until ${formatDateTime(provider.session_expires_at)}`
                        : "No active broker session"}
                    </p>
                  </div>
                </div>

                {provider.is_verified ? (
                  <div className="rounded-2xl border border-gray-800 bg-black/20 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 text-sm font-semibold text-white">
                        <Wallet className="h-4 w-4 text-amber-300" />
                        Account Snapshot
                      </div>
                      {provider.is_active && (
                        <Badge className="bg-emerald-500/10 text-emerald-300 border-emerald-500/20">
                          EXECUTION DEFAULT
                        </Badge>
                      )}
                    </div>

                    <div className="mt-4 grid gap-3 text-sm">
                      <div className="flex items-center justify-between gap-4">
                        <span className="text-gray-500">Name</span>
                        <span className="truncate text-gray-200">
                          {profile.name || provider.label || provider.display_name}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-4">
                        <span className="text-gray-500">Email</span>
                        <span className="truncate text-gray-200">
                          {profile.email || "-"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-4">
                        <span className="text-gray-500">Broker Account</span>
                        <span className="truncate text-gray-200">
                          {provider.account_reference || provider.account_name || "-"}
                        </span>
                      </div>
                    </div>

                    <div className="mt-4 space-y-2">
                      {funds.length ? (
                        funds.slice(0, 3).map((item, index) => (
                          <div
                            key={`${provider.broker_name}-${item.title || index}`}
                            className="flex items-center justify-between rounded-xl bg-gray-900/40 px-3 py-2 text-xs"
                          >
                            <span className="text-gray-500">
                              {item.title || `Fund ${index + 1}`}
                            </span>
                            <span className="text-gray-200">
                              {item.equityAmount ?? item.commodityAmount ?? "-"}
                            </span>
                          </div>
                        ))
                      ) : (
                        <div className="rounded-xl bg-gray-900/40 px-3 py-3 text-xs text-gray-500">
                          Funds snapshot not available yet.
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-gray-800 bg-black/10 p-5 text-center text-sm text-gray-500">
                    <Building2 className="mx-auto mb-2 h-6 w-6 text-gray-600" />
                    {provider.enabled
                      ? "Click Connect to complete secure broker authorization."
                      : "This broker card is ready for future adapter rollout."}
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-2">
                  {provider.enabled && !provider.is_verified && (
                    <Button
                      className={theme.cta}
                      onClick={() => connectBroker(provider.broker_name)}
                      disabled={isBusy}
                    >
                      <ShieldCheck className="h-4 w-4 mr-2" />
                      Connect {provider.display_name}
                    </Button>
                  )}

                  {provider.enabled && provider.is_verified && !provider.is_active && (
                    <Button
                      className="bg-emerald-600 hover:bg-emerald-500"
                      onClick={() => activateBroker(provider)}
                      disabled={isBusy}
                    >
                      <Power className="h-4 w-4 mr-2" />
                      Use For Execution
                    </Button>
                  )}

                  {provider.enabled && provider.is_verified && (
                    <>
                      <Button
                        variant="outline"
                        className="border-indigo-800 text-indigo-300 hover:text-indigo-200"
                        onClick={() => {
                          setSettingsCredentialId(provider.credential_id);
                          setSettingsProviderName(provider.display_name);
                          setSettingsModalOpen(true);
                        }}
                        disabled={isBusy}
                      >
                        <Settings className="h-4 w-4 mr-2" />
                        Settings
                      </Button>
                      <Button
                        variant="outline"
                        className="border-gray-700 text-gray-100"
                        onClick={() => connectBroker(provider.broker_name)}
                        disabled={isBusy}
                      >
                        Reconnect
                      </Button>
                      <Button
                        variant="outline"
                        className="border-red-800 text-red-300 hover:text-red-200"
                        onClick={() => disconnectBroker(provider)}
                        disabled={isBusy}
                      >
                        <Unplug className="h-4 w-4 mr-2" />
                        Disconnect
                      </Button>
                    </>
                  )}

                  {!provider.enabled && (
                    <Button disabled variant="outline" className="border-gray-800 text-gray-500">
                      Coming Soon
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <BrokerOrderSettingsModal
        isOpen={settingsModalOpen}
        onClose={() => {
          setSettingsModalOpen(false);
          setSettingsCredentialId(null);
        }}
        credentialId={settingsCredentialId}
        providerName={settingsProviderName}
      />
    </div>
  );
}
