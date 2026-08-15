import { useEffect, useMemo, useState, useCallback } from "react";
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
import { BrokerDetailsModal } from "./BrokerDetailsModal";
import { customConfirm } from "@/shared/components/ui/custom-dialog";


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
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [detailsProvider, setDetailsProvider] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);


  const loadBrokerState = useCallback(async () => {
    try {
      setLoading((current) => (catalog.length ? current : true));
      if (catalog.length > 0) setIsRefreshing(true);
      
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
      console.error("Failed to load broker state", error);
      notify.error(
        error?.response?.data?.detail ||
          error?.response?.data?.error ||
          "Failed to load broker connections",
      );
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [catalog.length, notify]);

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
          disabled={isRefreshing}
          className="border-gray-700 text-gray-100"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`} />
          {isRefreshing ? "Refreshing..." : "Refresh"}
        </Button>
      </div>
    ),
    [catalog.length, isRefreshing, loadBrokerState],
  );

  useSetPageActions(pageActions);

  if (loading) {
    return (
      <GlobalLoader />
    );
  }

  const connectedBrokers = catalog.filter((p) => p.is_verified);
  const availableBrokers = catalog.filter((p) => !p.is_verified);

  return (
    <div className="container-padding py-6 lg:py-8 space-y-10">
      
      {/* My Connections Section */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-white flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-emerald-400" />
          My Connections
        </h2>
        
        {connectedBrokers.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-gray-800 bg-gray-900/40 p-8 text-center text-sm text-gray-500">
            <Building2 className="mx-auto mb-3 h-8 w-8 text-gray-700" />
            No brokers connected yet. Choose a broker below to securely connect your account.
          </div>
        ) : (
          <div className="grid gap-5 xl:grid-cols-2">
            {connectedBrokers.map((provider) => {
              const theme = providerTheme[provider.broker_name] || providerTheme.FYERS;
              const status = statusLabel(provider);
              const session = activeSessionByCredential[String(provider.credential_id)];
              const isBusy = busyBroker === provider.broker_name;
              const expiryMeta = getExpiryMeta(provider);

              return (
                <Card
                  key={provider.broker_name}
                  className="relative overflow-hidden border-gray-800 bg-gray-900/60"
                >
                  <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${theme.accent}`} />
                  <CardHeader className="relative pb-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-sm font-bold text-white shadow-lg">
                          {provider.logo_text}
                        </div>
                        <div>
                          <CardTitle className="text-white text-lg flex items-center gap-2">
                            {provider.display_name}
                          </CardTitle>
                          <p className="mt-0.5 text-xs text-gray-400">
                            Verified: {provider.last_verified_at ? formatDateTime(provider.last_verified_at) : "N/A"}
                          </p>
                        </div>
                      </div>
                      <Badge className={theme.badge}>{status}</Badge>
                    </div>
                  </CardHeader>

                  <CardContent className="relative space-y-5">
                    <div className="flex items-center gap-4 rounded-xl border border-gray-800/60 bg-black/20 p-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gray-800/50">
                        <Radio className={`h-4 w-4 ${session ? 'text-emerald-400' : 'text-gray-500'}`} />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-200">
                          {provider.session_expired ? "Session Expired" : session ? "Active Session" : "Offline"}
                        </p>
                        <p className={`text-xs mt-0.5 ${expiryMeta.tone}`}>
                          {expiryMeta.label}
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      
                      <Button
                        variant="outline"
                        className="border-indigo-800 text-indigo-300 hover:text-indigo-200 hover:bg-indigo-950/30"
                        onClick={() => {
                          setDetailsProvider(provider);
                          setDetailsModalOpen(true);
                        }}
                        disabled={isBusy}
                      >
                        <Wallet className="h-4 w-4 mr-2" />
                        Details
                      </Button>

                      <Button
                        variant="outline"
                        className="border-gray-700 text-gray-300 hover:text-white"
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

                      {(!session || provider.session_expired) && (
                        <Button
                          variant="ghost"
                          className="text-gray-400 hover:text-white"
                          onClick={() => connectBroker(provider.broker_name)}
                          disabled={isBusy}
                        >
                          <RefreshCw className={`h-4 w-4 mr-2 ${isBusy ? 'animate-spin' : ''}`} />
                          Reconnect
                        </Button>
                      )}

                      <Button
                        variant="ghost"
                        className="text-red-400 hover:text-red-300 hover:bg-red-950/30 ml-auto px-3"
                        onClick={async () => {
                          const confirmed = await customConfirm(
                            `Are you sure you want to disconnect ${provider.display_name}? This will instantly stop any live running strategies that are currently using this broker.`,
                            "Disconnect Broker?",
                            "Disconnect & Stop Strategies"
                          );
                          if (confirmed) {
                            disconnectBroker(provider);
                          }
                        }}
                        disabled={isBusy}
                        title="Disconnect Broker"
                      >
                        <Unplug className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </section>

      {/* Available Brokers Section */}
      <section className="space-y-4">
        <h2 className="text-lg font-medium text-gray-300 flex items-center gap-2">
          <Building2 className="h-4 w-4" />
          Available Brokers
        </h2>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {availableBrokers.map((provider) => {
            const isBusy = busyBroker === provider.broker_name;
            
            return (
              <div 
                key={provider.broker_name}
                className="group relative flex items-center gap-4 rounded-xl border border-gray-800 bg-gray-900/40 p-4 transition-all hover:bg-gray-800/40 hover:border-gray-700"
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-white/5 bg-white/5 text-xs font-bold text-gray-300 shadow-sm transition-colors group-hover:bg-white/10 group-hover:text-white">
                  {provider.logo_text}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="truncate font-medium text-gray-200">
                    {provider.display_name}
                  </h3>
                  <p className="truncate text-xs text-gray-500">
                    {provider.enabled ? "Ready to connect" : "Coming Soon"}
                  </p>
                </div>
                
                <div className="shrink-0">
                  {provider.enabled ? (
                    <Button 
                      size="sm" 
                      variant="outline" 
                      className="border-gray-700 h-8 px-3 text-xs hover:bg-gray-800 text-gray-100"
                      onClick={() => connectBroker(provider.broker_name)}
                      disabled={isBusy}
                    >
                      Connect
                    </Button>
                  ) : (
                    <Badge variant="outline" className="text-[10px] border-gray-800 text-gray-500 bg-black/20">
                      Soon
                    </Badge>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <BrokerOrderSettingsModal
        isOpen={settingsModalOpen}
        onClose={() => {
          setSettingsModalOpen(false);
          setSettingsCredentialId(null);
        }}
        credentialId={settingsCredentialId}
        providerName={settingsProviderName}
      />

      <BrokerDetailsModal
        isOpen={detailsModalOpen}
        onClose={() => {
          setDetailsModalOpen(false);
          setDetailsProvider(null);
        }}
        provider={detailsProvider}
        profile={detailsProvider ? profileMap[detailsProvider.broker_name] : null}
        funds={detailsProvider ? fundsMap[detailsProvider.broker_name] : null}
      />
    </div>
  );
}
