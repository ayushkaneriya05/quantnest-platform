import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useState, useEffect } from "react";
import { useDispatch } from "react-redux";
import { Button } from "@/shared/components/ui/button";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/shared/components/ui/dialog";
import {
  CreditCard,
  AlertTriangle,
  CheckCircle,
  Loader2,
} from "lucide-react";
import api from "@/shared/services/api";
import { logout } from "@/shared/store/authSlice";
import { useNavigate } from "react-router-dom";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/shared/components/ui/card";
import { GlobalLoader } from '@/shared/components/ui/global-loader';
export default function AccountTab() {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const [subscription, setSubscription] = useState(null);
  const [isLoadingSubscription, setIsLoadingSubscription] = useState(true);
  const [message, setMessage] = useState(null);

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deactivateDialogOpen, setDeactivateDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isDeactivating, setIsDeactivating] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [preflightData, setPreflightData] = useState(null);
  const [isLoadingPreflight, setIsLoadingPreflight] = useState(false);

  // Load account data on component mount
  useEffect(() => {
    loadAccountData();
  }, []);

  const loadAccountData = async () => {
    try {
      // Load subscription data
      const subResponse = await api.get("/users/subscription/");
      setSubscription(subResponse.data);
    } catch (err) {
      console.error("Failed to load account data:", err);
      setMessage({
        type: "error",
        text: "Failed to load account information",
      });
    } finally {
      setIsLoadingSubscription(false);
    }
  };

  const handleUpgradeToPro = () => {
    // Redirect to billing/upgrade page
    window.open("/upgrade", "_blank");
  };

  const handleManageBilling = () => {
    // Redirect to billing portal
    window.open("/billing", "_blank");
  };

  const handleDeactivateAccount = async () => {
    setIsDeactivating(true);
    try {
      await api.post("/users/account/deactivate/");
      dispatch(logout());
      navigate("/login", {
        state: { message: "Your account has been deactivated." },
      });
    } catch (err) {
      console.error("Failed to deactivate account:", err);
      setMessage({
        type: "error",
        text: "Failed to deactivate account",
      });
      setIsDeactivating(false);
    }
  };

  const handleDeleteAccount = async () => {
    setIsDeleting(true);
    try {
      await api.delete("/users/account/");
      dispatch(logout());
      navigate("/", {
        state: { message: "Your account has been permanently deleted." },
      });
    } catch (err) {
      console.error("Failed to delete account:", err);
      const errorMsg = getApiErrorMessage(err, "Failed to delete account. Please try again.");
      setMessage({
        type: "error",
        text: errorMsg,
      });
      setIsDeleting(false);
      setDeleteDialogOpen(false);
    }
  };

  const [preflightError, setPreflightError] = useState(false);

  const fetchPreflight = async () => {
    setIsLoadingPreflight(true);
    setPreflightError(false);
    try {
      const response = await api.get("/users/account/preflight/");
      setPreflightData(response.data);
    } catch (err) {
      console.error("Failed to fetch preflight data:", err);
      setPreflightError(true);
    } finally {
      setIsLoadingPreflight(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="w-full space-y-6 max-w-full overflow-hidden">
      {/* Dynamic Status Message - Top-level alert */}
      {message && (
        <div
          className={`px-4 py-3 rounded-2xl border ${
            message.type === "success"
              ? "bg-green-50 dark:bg-green-900/40 border-green-800/50 text-green-700 dark:text-green-300"
              : "bg-red-50 dark:bg-red-900/40 border-red-800/50 text-red-700 dark:text-red-300"
          } flex items-center gap-3 text-sm animate-in fade-in slide-in-from-top-4 duration-300 shadow-lg mb-2`}
        >
          {message.type === "success" ? (
            <CheckCircle className="h-5 w-5 shrink-0" />
          ) : (
            <AlertTriangle className="h-5 w-5 shrink-0" />
          )}
          <span className="font-medium">{message.text}</span>
        </div>
      )}

      <div className="space-y-6 pb-10">
        {/* Subscription & Billing */}
        <div>
          <Card className="bg-card/50 border-border/50 h-full">
            <CardHeader className="border-b border-border/50">
              <div className="flex items-center gap-2">
                <CreditCard className="h-5 w-5 text-emerald-700 dark:text-emerald-400" />
                <CardTitle className="text-lg font-semibold text-foreground">Subscription & Billing</CardTitle>
              </div>
              <CardDescription className="text-muted-foreground">View and manage your current subscription plan and billing cycles.</CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              {isLoadingSubscription ? (
                <GlobalLoader fullHeight={false} />
              ) : (
                <div className="flex flex-col sm:flex-row items-center justify-between gap-6 p-6 bg-secondary/30 border border-border/30 rounded-xl">
                  <div className="space-y-3 text-center sm:text-left">
                    <div className="flex flex-wrap items-center justify-center sm:justify-start gap-3">
                      <span className="text-foreground font-medium">Current Plan:</span>
                      <Badge
                        className={`text-sm py-1 px-3 ${
                          subscription?.is_pro
                            ? "bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 border-indigo-500/30"
                            : "bg-muted/50 text-muted-foreground border-border/50"
                        }`}
                      >
                        {subscription?.plan_name || "Starter"}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground max-w-md">
                      {subscription?.is_pro
                        ? `Full access to Pro features. ${subscription?.expires_at ? `Valid until ${formatDate(subscription.expires_at)}` : ""}`
                        : "Upgrade to unlock high-frequency data and advanced strategy builders."}
                    </p>
                    {subscription?.usage && (
                      <div className="pt-2">
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-muted-foreground font-mono">Usage Tracker</span>
                          <span className="text-muted-foreground">{subscription.usage.current} / {subscription.usage.limit}</span>
                        </div>
                        <div className="w-full bg-secondary rounded-full h-1.5 overflow-hidden">
                          <div 
                            className="bg-indigo-500 h-full rounded-full transition-all duration-500" 
                            style={{ width: `${Math.min((subscription.usage.current / subscription.usage.limit) * 100, 100)}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="shrink-0 w-full sm:w-auto">
                    {subscription?.is_pro ? (
                      <Button
                        variant="outline"
                        onClick={handleManageBilling}
                        className="w-full sm:w-auto bg-secondary/50 border-border/50 text-foreground hover:bg-muted/50"
                      >
                        Manage Billing
                      </Button>
                    ) : (
                      <Button
                        onClick={handleUpgradeToPro}
                        className="w-full sm:w-auto bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-600/10 border-0 rounded-xl px-8"
                      >
                        Upgrade to Pro
                      </Button>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Danger Zone */}
        <div>
          <div className="bg-red-950/10 border border-red-500/20 rounded-2xl p-6 sm:p-8 shadow-inner shadow-red-950/20">
            <div className="flex items-center gap-3 mb-8">
              <div className="w-10 h-10 bg-red-500/10 rounded-xl flex items-center justify-center border border-red-500/20">
                <AlertTriangle className="h-5 w-5 text-red-700 dark:text-red-400" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-red-900 dark:text-red-100">Critical Actions</h3>
                <p className="text-red-700 dark:text-red-400 text-sm">Managing account visibility and permanent data removal.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="p-6 bg-muted/40 border border-red-900/20 rounded-xl flex flex-col justify-between group transition-all hover:border-red-900/40">
                <div className="space-y-3 mb-8">
                  <h4 className="font-bold text-foreground">Account Deactivation</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">Temporary suspension. Your data is preserved but hidden from public results. You must contact support to reactivate.</p>
                </div>
                <Dialog open={deactivateDialogOpen} onOpenChange={setDeactivateDialogOpen}>
                  <DialogTrigger asChild>
                    <Button variant="outline" className="w-full border-red-900/30 text-red-700 dark:text-red-300 hover:bg-red-900/20 hover:text-red-800 dark:hover:text-red-200 transition-all">Deactivate Account</Button>
                  </DialogTrigger>
                  <DialogContent className="bg-card border-border text-foreground rounded-2xl p-8">
                    <DialogHeader>
                      <DialogTitle className="text-red-900 dark:text-red-100 text-2xl font-bold">Confirm Deactivation?</DialogTitle>
                      <DialogDescription className="text-muted-foreground pt-3 text-base">
                        Your account will be suspended and you will not be able to log in. Live trading sessions will be stopped, but your open live positions will remain open at your broker.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="flex gap-4 pt-8">
                      <Button variant="ghost" onClick={() => setDeactivateDialogOpen(false)} className="flex-1 text-muted-foreground h-12">Cancel</Button>
                      <Button 
                        onClick={handleDeactivateAccount} 
                        disabled={isDeactivating}
                        className="flex-2 bg-red-600 hover:bg-red-700 text-white border-0 px-8 h-12"
                      >
                        {isDeactivating ? <Loader2 className="h-4 w-4 animate-spin" /> : "Confirm Deactivation"}
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>
              </div>

              <div className="p-6 bg-red-50 dark:bg-red-900/10 border border-red-500/20 rounded-xl flex flex-col justify-between group transition-all hover:bg-red-900/20">
                <div className="space-y-3 mb-8">
                  <h4 className="font-bold text-red-900 dark:text-red-100">Permanent Account Deletion</h4>
                  <p className="text-sm text-red-700 dark:text-red-300 leading-relaxed">You will permanently lose access to all your trade history, strategy code, and portfolio metrics. Your personal data will be anonymized. <span className="underline font-bold text-red-700 dark:text-red-400">This action is irreversible.</span></p>
                </div>
                <Dialog open={deleteDialogOpen} onOpenChange={(open) => {
                  setDeleteDialogOpen(open);
                  if (open) {
                    fetchPreflight();
                  } else {
                    setDeleteConfirmText("");
                    setPreflightData(null);
                    setPreflightError(false);
                  }
                }}>
                  <DialogTrigger asChild>
                    <Button className="w-full bg-red-600 hover:bg-red-700 text-white border-0 shadow-lg shadow-red-600/10 h-11">Delete Forever</Button>
                  </DialogTrigger>
                  <DialogContent className="bg-card border-red-900/50 text-foreground rounded-2xl p-8 max-w-lg">
                    <DialogHeader>
                      <DialogTitle className="text-red-700 dark:text-red-400 text-2xl font-bold">Final Confirmation</DialogTitle>
                      <DialogDescription className="text-red-700 dark:text-red-300 pt-3 text-base">
                        You will permanently lose access to all your proprietary strategy code and historical performance. Your account will be irrevocably anonymized.
                      </DialogDescription>
                    </DialogHeader>

                    {/* Preflight Resource Summary */}
                    {isLoadingPreflight ? (
                      <div className="flex items-center justify-center py-6">
                        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                        <span className="ml-2 text-sm text-muted-foreground">Checking account status...</span>
                      </div>
                    ) : preflightError ? (
                      <div className="mt-4 flex items-start gap-3 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-500/20 rounded-xl">
                        <AlertTriangle className="h-5 w-5 text-amber-700 dark:text-amber-400 shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm font-semibold text-amber-700 dark:text-amber-300">Could not verify account status</p>
                          <p className="text-xs text-amber-700 dark:text-amber-400/70 mt-1">
                            The preflight check failed. For your safety, deletion is blocked until we can verify you have no open live positions. Please try again later.
                          </p>
                        </div>
                      </div>
                    ) : preflightData && (
                      <div className="mt-4 space-y-3">
                        {preflightData.open_live_positions > 0 && (
                          <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/30 border border-red-500/30 rounded-xl">
                            <AlertTriangle className="h-5 w-5 text-red-700 dark:text-red-400 shrink-0 mt-0.5" />
                            <div>
                              <p className="text-sm font-semibold text-red-700 dark:text-red-300">Deletion Blocked</p>
                              <p className="text-xs text-red-700 dark:text-red-400 mt-1">
                                You have {preflightData.open_live_positions} open live position{preflightData.open_live_positions > 1 ? "s" : ""}. Close all live positions before deleting your account.
                              </p>
                            </div>
                          </div>
                        )}

                        {(() => {
                          const items = [
                            { key: "active_strategies", label: "Active strategies will be paused" },
                            { key: "running_live_sessions", label: "Running live sessions will be stopped" },
                            { key: "pending_live_orders", label: "Pending live orders will be cancelled" },
                            { key: "active_paper_accounts", label: "Paper accounts will be deactivated" },
                            { key: "pending_paper_orders", label: "Pending paper orders will be cancelled" },
                            { key: "active_broker_connections", label: "Broker connections will be deactivated" },
                            { key: "running_backtests", label: "Running backtests will be cancelled" },
                          ];
                          const affected = items.filter(item => preflightData[item.key] > 0);
                          if (affected.length === 0) return null;
                          return (
                            <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-500/20 rounded-xl space-y-2">
                              <p className="text-sm font-semibold text-amber-700 dark:text-amber-300">The following will be affected:</p>
                              <ul className="space-y-1">
                                {affected.map(item => (
                                  <li key={item.key} className="text-xs text-amber-700 dark:text-amber-400/80 flex items-center gap-2">
                                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400/60 shrink-0" />
                                    {preflightData[item.key]} {item.label}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          );
                        })()}
                      </div>
                    )}

                    {/* DELETE Confirmation Input */}
                    {!isLoadingPreflight && (
                    <>
                    <div className="mt-6 space-y-2">
                      <label className="text-sm text-muted-foreground">
                        Type <span className="font-mono font-bold text-red-700 dark:text-red-400">DELETE</span> to confirm:
                      </label>
                      <Input
                        value={deleteConfirmText}
                        onChange={(e) => setDeleteConfirmText(e.target.value)}
                        placeholder="Type DELETE here"
                        className="bg-secondary/80 border-border text-foreground placeholder:text-muted-foreground font-mono h-11 focus:border-red-500/50 focus:ring-red-500/20"
                        disabled={preflightError || preflightData?.open_live_positions > 0}
                      />
                    </div>

                    <div className="flex gap-4 pt-6">
                      <Button variant="ghost" onClick={() => setDeleteDialogOpen(false)} className="flex-1 text-muted-foreground h-12">Cancel</Button>
                      <Button 
                        onClick={handleDeleteAccount} 
                        disabled={isDeleting || deleteConfirmText !== "DELETE" || preflightError || preflightData?.open_live_positions > 0}
                        className="flex-[2] bg-red-600 hover:bg-red-700 text-white border-0 px-8 font-bold h-12 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : "I Understand, Delete My Data"}
                      </Button>
                    </div>
                    </>
                    )}
                  </DialogContent>
                </Dialog>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
