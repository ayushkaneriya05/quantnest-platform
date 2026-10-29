import { GlobalLoader, LoaderMark } from '@/shared/components/ui/global-loader';
import { formatDateTime } from "@/shared/utils/formatters";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useEffect, useMemo, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Building2,
  Radio,
  RefreshCw,
  ShieldCheck,
  Settings2,
  Unplug,
  Wallet,
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
import FyersAppDialog from "@/features/brokers/components/FyersAppDialog.jsx";
import { BrokerDetailsModal } from "@/features/brokers/components/BrokerDetailsModal.jsx";
import { customConfirm } from "@/shared/components/ui/custom-dialog";


const brokerSetupDialogs = { FYERS: FyersAppDialog };

const providerTheme = {
  FYERS: {
    accent: "from-cyan-500/20 via-sky-500/10 to-transparent",
    badge: "bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border-cyan-500/20",
    cta: "bg-cyan-700 hover:bg-cyan-800",
  },
  ZERODHA: {
    accent: "from-blue-500/20 via-blue-500/10 to-transparent",
    badge: "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/20",
    cta: "bg-blue-600 hover:bg-blue-500",
  },
  ANGEL: {
    accent: "from-rose-500/20 via-rose-500/10 to-transparent",
    badge: "bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/20",
    cta: "bg-rose-600 hover:bg-rose-700",
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

function getExpiryMeta(provider) {
  if (!provider.session_expires_at) {
    return {
      label: provider.session_expired ? "Expired - reconnect required" : "Not connected",
      tone: "text-muted-foreground",
    };
  }

  const expiry = new Date(provider.session_expires_at);
  const diffMs = expiry.getTime() - Date.now();
  if (Number.isNaN(expiry.getTime()) || diffMs <= 0 || provider.session_expired) {
    return {
      label: "Expired - reconnect required",
      tone: "text-red-700 dark:text-red-300",
    };
  }

  const diffMinutes = Math.floor(diffMs / 60000);
  if (diffMinutes < 60) {
    return {
      label: `Expires in ${Math.max(diffMinutes, 1)} min`,
      tone: "text-amber-700 dark:text-amber-300",
    };
  }

  const diffHours = Math.floor(diffMinutes / 60);
  return {
    label: `Active for ~${diffHours} hr`,
    tone: "text-emerald-700 dark:text-emerald-300",
  };
}

export default function BrokerConnections() {
  const { notify } = useNotifications();
  const [searchParams, setSearchParams] = useSearchParams();
  const [catalog, setCatalog] = useState([]);
  const [appProvider, setAppProvider] = useState(null);
  const [profileMap, setProfileMap] = useState({});
  const [fundsMap, setFundsMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [busyBroker, setBusyBroker] = useState("");
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [detailsProvider, setDetailsProvider] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);


  const loadBrokerState = useCallback(async ({ initial = false } = {}) => {
    try {
      if (initial) setLoading(true);
      else setIsRefreshing(true);
      
      const { data: nextCatalog } = await brokersApi.getCatalog();
      setCatalog(nextCatalog);
      setProfileMap({});
      setFundsMap({});

      await Promise.all(
        nextCatalog
          .filter((provider) => provider.credential_id && provider.session_valid)
          .map(async (provider) => {
            try {
              const [profileRes, fundsRes] = await Promise.all([
                brokersApi.getProfile(provider.credential_id),
                brokersApi.getFunds(provider.credential_id),
              ]);
              setProfileMap((current) => ({
                ...current,
                [provider.broker_name]: profileRes.data,
              }));
              setFundsMap((current) => ({
                ...current,
                [provider.broker_name]: fundsRes.data,
              }));
            } catch (error) {
              // Keep page resilient if one broker profile/funds call fails.
            }
          }),
      );
    } catch (error) {
      console.error("Failed to load broker state", error);
      notify.error(
        getApiErrorMessage(error, "Failed to load broker connections"),
      );
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [notify]);

  useEffect(() => {
    loadBrokerState({ initial: true });
  }, [loadBrokerState]);

  useEffect(() => {
    const status = searchParams.get("status");
    const broker = searchParams.get("broker");
    const message = searchParams.get("message");
    if (!status) return;

    if (status === "connected") {
      // Successful authentication is announced by the persisted broker event.
    } else {
      notify.error(message || `${broker || "Broker"} connection failed`);
    }
    setSearchParams({}, { replace: true });
  }, [notify, searchParams, setSearchParams]);

  const startConnection = async (credentialId) => {
    const { data } = await brokersApi.connectBroker(credentialId);
    window.location.assign(data.auth_url);
  };

  const connectBroker = async (provider) => {
    if (!provider.enabled || !brokerSetupDialogs[provider.broker_name]) {
      notify.error("This broker integration is not available yet.");
      return;
    }
    if (!provider.configured) {
      setAppProvider(provider);
      return;
    }
    try {
      setBusyBroker(provider.broker_name);
      await startConnection(provider.credential_id);
    } catch (error) {
      notify.error(getApiErrorMessage(error, "Broker connection failed."));
    } finally {
      setBusyBroker("");
    }
  };

  const disconnectBroker = async (provider) => {
    if (!provider.credential_id) return;
    try {
      setBusyBroker(provider.broker_name);
      await brokersApi.disconnectCredential(provider.credential_id);
      await loadBrokerState();
    } catch (error) {
      notify.error(
        getApiErrorMessage(error, `Failed to disconnect ${provider.display_name}`),
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
          className="border-border text-foreground"
        >
          {isRefreshing ? <LoaderMark className="h-4 w-4 mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
          {isRefreshing ? "Refreshing..." : "Refresh"}
        </Button>
      </div>
    ),
    [isRefreshing, loadBrokerState],
  );

  useSetPageActions(pageActions);

  if (loading) {
    return (
      <GlobalLoader />
    );
  }

  const connectedBrokers = catalog.filter((p) => p.is_verified);
  const availableBrokers = catalog.filter((p) => !p.is_verified);
  const SetupDialog = appProvider ? brokerSetupDialogs[appProvider.broker_name] : null;

  return (
    <div className="container-padding py-6 lg:py-8 space-y-6">
      
      {/* My Connections Section */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-foreground flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-emerald-700 dark:text-emerald-400" />
          My Connections
        </h2>
        
        {connectedBrokers.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border bg-card/40 p-8 text-center text-sm text-muted-foreground">
            <Building2 className="mx-auto mb-3 h-8 w-8 text-foreground" />
            No brokers connected yet. Choose a broker below to securely connect your account.
          </div>
        ) : (
          <div className="grid gap-5 xl:grid-cols-2">
            {connectedBrokers.map((provider) => {
              const theme = providerTheme[provider.broker_name] || providerTheme.FYERS;
              const status = statusLabel(provider);
              const session = provider.session_valid;
              const isBusy = busyBroker === provider.broker_name;
              const expiryMeta = getExpiryMeta(provider);

              return (
                <Card
                  key={provider.broker_name}
                  className="relative overflow-hidden border-border bg-card/60"
                >
                  <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${theme.accent}`} />
                  <CardHeader className="relative pb-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-border bg-muted/50 text-sm font-bold text-foreground shadow-lg">
                          {provider.logo_text}
                        </div>
                        <div>
                          <CardTitle className="text-foreground text-lg flex items-center gap-2">
                            {provider.display_name}
                          </CardTitle>
                          <p className="mt-0.5 text-xs text-muted-foreground">
                            Verified: {provider.last_verified_at ? formatDateTime(provider.last_verified_at) : "N/A"}
                          </p>
                        </div>
                      </div>
                      <Badge className={theme.badge}>{status}</Badge>
                    </div>
                  </CardHeader>

                  <CardContent className="relative space-y-5">
                    <div className="flex items-center gap-4 rounded-xl border border-border/60 bg-muted/40 p-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary/50">
                        <Radio className={`h-4 w-4 ${session ? 'text-emerald-700 dark:text-emerald-400' : 'text-muted-foreground'}`} />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-foreground">
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
                        className="border-indigo-800 text-indigo-700 dark:text-indigo-300 hover:text-indigo-800 dark:hover:text-indigo-200 hover:bg-indigo-950/30"
                        onClick={() => {
                          setDetailsProvider(provider);
                          setDetailsModalOpen(true);
                        }}
                        disabled={isBusy}
                      >
                        <Wallet className="h-4 w-4 mr-2" />
                        Details
                      </Button>

                      <Button variant="outline" onClick={() => setAppProvider(provider)} disabled={isBusy || !brokerSetupDialogs[provider.broker_name]}>
                        <Settings2 className="mr-2 h-4 w-4" />Connection settings
                      </Button>

                      {(!session || provider.session_expired) && (
                        <Button
                          variant="ghost"
                          className="text-muted-foreground hover:text-foreground"
                          onClick={() => connectBroker(provider)}
                          disabled={isBusy}
                        >
                          {isBusy ? <LoaderMark className="h-4 w-4 mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                          Reconnect
                        </Button>
                      )}

                      <Button
                        variant="ghost"
                        className="text-red-700 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-950/30 ml-auto px-3"
                        onClick={async () => {
                          const confirmed = await customConfirm(
                            `Disconnect ${provider.display_name}? Stop its live sessions, close positions and finish pending orders first.`,
                            "Disconnect Broker?",
                            "Disconnect"
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
        <h2 className="text-lg font-medium text-foreground flex items-center gap-2">
          <Building2 className="h-4 w-4" />
          Available Brokers
        </h2>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {availableBrokers.map((provider) => {
            const isBusy = busyBroker === provider.broker_name;
            const canConnect = provider.enabled && Boolean(brokerSetupDialogs[provider.broker_name]);
            
            return (
              <div 
                key={provider.broker_name}
                className="group relative flex items-center gap-4 rounded-xl border border-border bg-card/40 p-4 transition-all hover:bg-secondary/40 hover:border-border"
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/50 text-xs font-bold text-foreground shadow-sm transition-colors group-hover:bg-muted/50 group-hover:text-foreground">
                  {provider.logo_text}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="truncate font-medium text-foreground">
                    {provider.display_name}
                  </h3>
                  <p className="truncate text-xs text-muted-foreground">
                    {canConnect ? provider.configured ? "Credentials saved · ready to connect" : "Set up your connection" : "Coming Soon"}
                  </p>
                </div>
                
                <div className="shrink-0">
                  {canConnect ? (
                    <Button 
                      size="sm" 
                      variant="outline" 
                      className="border-border h-8 px-3 text-xs hover:bg-secondary text-foreground"
                      onClick={() => connectBroker(provider)}
                      disabled={isBusy}
                    >
                      Connect
                    </Button>
                  ) : (
                    <Badge variant="outline" className="text-[10px] border-border text-muted-foreground bg-muted/40">
                      Soon
                    </Badge>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {SetupDialog && (
        <SetupDialog provider={appProvider} onClose={() => setAppProvider(null)} onConnect={startConnection} />
      )}

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
