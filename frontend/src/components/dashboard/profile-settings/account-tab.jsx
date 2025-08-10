import { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Copy,
  KeyRound,
  CreditCard,
  AlertTriangle,
  CheckCircle,
  Loader2,
  Trash2,
  Plus,
} from "lucide-react";
import api from "@/services/api";
import { logout, logoutUser } from "@/store/authSlice";
import { useNavigate } from "react-router-dom";

export default function AccountTab() {
  const { user } = useSelector((state) => state.auth);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const [subscription, setSubscription] = useState(null);
  const [apiKeys, setApiKeys] = useState([]);
  const [isLoadingSubscription, setIsLoadingSubscription] = useState(true);
  const [isLoadingApiKeys, setIsLoadingApiKeys] = useState(true);
  const [isGeneratingKey, setIsGeneratingKey] = useState(false);
  const [message, setMessage] = useState(null);

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deactivateDialogOpen, setDeactivateDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isDeactivating, setIsDeactivating] = useState(false);

  // Load account data on component mount
  useEffect(() => {
    loadAccountData();
  }, []);

  const loadAccountData = async () => {
    try {
      // Load subscription data
      const subResponse = await api.get("/users/subscription/");
      setSubscription(subResponse.data);

      // Load API keys if user has pro plan
      if (subResponse.data.is_pro) {
        const keysResponse = await api.get("/users/api-keys/");
        setApiKeys(keysResponse.data.keys || []);
      }
    } catch (err) {
      console.error("Failed to load account data:", err);
      setMessage({
        type: "error",
        text: "Failed to load account information",
      });
    } finally {
      setIsLoadingSubscription(false);
      setIsLoadingApiKeys(false);
    }
  };

  const handleCopy = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setMessage({
        type: "success",
        text: "API key copied to clipboard!",
      });
      // Clear message after 3 seconds
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setMessage({
        type: "error",
        text: "Failed to copy to clipboard",
      });
    }
  };

  const handleGenerateApiKey = async () => {
    setIsGeneratingKey(true);
    try {
      const response = await api.post("/users/api-keys/");
      setApiKeys((prev) => [...prev, response.data]);
      setMessage({
        type: "success",
        text: "New API key generated successfully!",
      });
    } catch (err) {
      console.error("Failed to generate API key:", err);
      setMessage({
        type: "error",
        text: "Failed to generate API key",
      });
    } finally {
      setIsGeneratingKey(false);
    }
  };

  const handleDeleteApiKey = async (keyId) => {
    try {
      await api.delete(`/users/api-keys/${keyId}/`);
      setApiKeys((prev) => prev.filter((key) => key.id !== keyId));
      setMessage({
        type: "success",
        text: "API key deleted successfully",
      });
    } catch (err) {
      console.error("Failed to delete API key:", err);
      setMessage({
        type: "error",
        text: "Failed to delete API key",
      });
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
      dispatch(logoutUser());
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
      dispatch(logoutUser());
      dispatch(logout());
      navigate("/", {
        state: { message: "Your account has been permanently deleted." },
      });
    } catch (err) {
      console.error("Failed to delete account:", err);
      setMessage({
        type: "error",
        text: "Failed to delete account",
      });
      setIsDeleting(false);
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
    <Card className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-4 sm:p-6">
      <CardHeader className="mb-4 sm:mb-6 px-0 pt-0">
        <CardTitle className="text-xl sm:text-2xl font-bold text-slate-100">
          Account Settings
        </CardTitle>
        <CardDescription className="text-slate-400 text-sm sm:text-base">
          Manage your subscription, API keys, and account actions.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6 sm:space-y-8 px-0 pb-0">
        {/* Message Display */}
        {message && (
          <div
            className={`p-3 rounded-lg border ${
              message.type === "success"
                ? "bg-green-900/50 border-green-800 text-green-300"
                : "bg-red-900/50 border-red-800 text-red-300"
            } flex items-center gap-2 text-sm`}
          >
            {message.type === "success" ? (
              <CheckCircle className="h-4 w-4" />
            ) : (
              <AlertTriangle className="h-4 w-4" />
            )}
            {message.text}
          </div>
        )}

        {/* Subscription & Billing */}
        <div className="space-y-4 sm:space-y-6">
          <h3 className="text-lg sm:text-xl font-bold text-slate-100 flex items-center gap-2">
            <CreditCard className="h-4 w-4 sm:h-5 sm:w-5 text-emerald-400" />{" "}
            Subscription & Billing
          </h3>

          {isLoadingSubscription ? (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
            </div>
          ) : (
            <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 p-4 sm:p-6 bg-gray-800/50 border border-gray-700/50 rounded-lg">
              <div className="flex-1">
                <div className="text-slate-300 font-medium text-sm sm:text-base flex flex-wrap items-center gap-2">
                  Current Plan:
                  <Badge
                    className={`text-xs sm:text-sm ${
                      subscription?.is_pro
                        ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                        : "bg-gray-500/20 text-gray-300 border border-gray-500/30"
                    }`}
                  >
                    {subscription?.plan_name || "Starter"}
                  </Badge>
                </div>
                <p className="text-xs sm:text-sm text-slate-400 mt-2">
                  {subscription?.is_pro
                    ? `You have access to all professional features. ${
                        subscription?.expires_at
                          ? `Expires on ${formatDate(subscription.expires_at)}`
                          : ""
                      }`
                    : "Upgrade to unlock advanced features and API access."}
                </p>
                {subscription?.usage && (
                  <p className="text-xs text-slate-500 mt-1">
                    Usage this month: {subscription.usage.current} /{" "}
                    {subscription.usage.limit} requests
                  </p>
                )}
              </div>

              {subscription?.is_pro ? (
                <Button
                  variant="outline"
                  onClick={handleManageBilling}
                  className="bg-gray-700/50 border-gray-600/50 text-slate-300 hover:bg-gray-600/50 w-full lg:w-auto text-sm shrink-0"
                >
                  Manage Billing
                </Button>
              ) : (
                <Button
                  onClick={handleUpgradeToPro}
                  className="bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)] rounded-xl border-0 w-full lg:w-auto text-sm shrink-0"
                >
                  Upgrade to Pro
                </Button>
              )}
            </div>
          )}
        </div>

        {/* API Keys */}
        <div className="space-y-4 sm:space-y-6">
          <h3 className="text-lg sm:text-xl font-bold text-slate-100 flex items-center gap-2">
            <KeyRound className="h-4 w-4 sm:h-5 sm:w-5 text-purple-400" /> API
            Keys
          </h3>

          {!subscription?.is_pro ? (
            <div className="p-4 sm:p-6 bg-gray-800/50 border border-gray-700/50 rounded-lg text-center text-slate-400">
              <p className="font-medium mb-3 text-sm sm:text-base">
                API Keys are a Professional plan feature.
              </p>
              <Button
                onClick={handleUpgradeToPro}
                className="bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)] rounded-xl border-0 w-full sm:w-auto text-sm"
              >
                Upgrade to Pro
              </Button>
            </div>
          ) : (
            <>
              {isLoadingApiKeys ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
                </div>
              ) : (
                <>
                  <div className="space-y-3 sm:space-y-4">
                    {apiKeys.length === 0 ? (
                      <div className="text-center text-slate-400 p-8">
                        No API keys found. Generate your first API key to get
                        started.
                      </div>
                    ) : (
                      apiKeys.map((key) => (
                        <div
                          key={key.id}
                          className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-3 p-3 sm:p-4 bg-gray-800/50 border border-gray-700/50 rounded-lg"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <p className="text-slate-300 font-mono text-xs sm:text-sm break-all">
                                {key.masked_key}
                              </p>
                              {key.name && (
                                <Badge className="bg-blue-500/20 text-blue-300 border border-blue-500/30 text-xs">
                                  {key.name}
                                </Badge>
                              )}
                            </div>
                            <p className="text-xs text-slate-400">
                              Created: {formatDate(key.created_at)}
                              {key.last_used &&
                                ` • Last used: ${formatDate(key.last_used)}`}
                            </p>
                          </div>

                          <div className="flex gap-2 w-full lg:w-auto">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleCopy(key.key)}
                              className="bg-gray-700/50 border-gray-600/50 text-slate-300 hover:bg-gray-600/50 flex-1 lg:flex-none text-sm"
                            >
                              <Copy className="h-3 w-3 mr-1" /> Copy
                            </Button>
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => handleDeleteApiKey(key.id)}
                              className="bg-red-600/50 text-red-300 hover:bg-red-700/50 border border-red-600/50 text-sm"
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  <div className="flex justify-start">
                    <Button
                      onClick={handleGenerateApiKey}
                      disabled={isGeneratingKey}
                      className="bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)] rounded-xl border-0 w-full sm:w-auto text-sm px-6 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isGeneratingKey ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <Plus className="h-4 w-4 mr-2" />
                          Generate New API Key
                        </>
                      )}
                    </Button>
                  </div>
                </>
              )}
            </>
          )}
        </div>

        {/* Danger Zone */}
        <div className="space-y-4 sm:space-y-6 p-4 sm:p-6 border border-red-600/50 bg-red-900/20 rounded-xl">
          <h3 className="text-lg sm:text-xl font-bold text-red-400 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 sm:h-5 sm:w-5 text-red-400" />{" "}
            Danger Zone
          </h3>
          <p className="text-xs sm:text-sm text-red-300">
            These actions are irreversible and will affect your account
            permanently. Please proceed with caution.
          </p>

          <div className="grid gap-4 sm:gap-6 lg:grid-cols-2">
            {/* Deactivate Account */}
            <div className="space-y-3">
              <p className="text-slate-300 font-medium text-sm sm:text-base">
                Deactivate Account
              </p>
              <p className="text-xs sm:text-sm text-slate-400">
                Temporarily disable your account and hide your data. You can
                reactivate later.
              </p>

              <Dialog
                open={deactivateDialogOpen}
                onOpenChange={setDeactivateDialogOpen}
              >
                <DialogTrigger asChild>
                  <Button
                    variant="destructive"
                    className="w-full bg-red-600/50 text-red-300 hover:bg-red-700/50 border border-red-600/50 text-sm"
                  >
                    Deactivate Account
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-gray-900/95 border border-gray-800/50 text-slate-100">
                  <DialogHeader>
                    <DialogTitle>Deactivate Account</DialogTitle>
                    <DialogDescription className="text-slate-400">
                      Are you sure you want to deactivate your account? This
                      will temporarily disable your account and hide your data.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="flex gap-3 pt-4">
                    <Button
                      variant="outline"
                      onClick={() => setDeactivateDialogOpen(false)}
                      className="flex-1 bg-gray-800/50 border-gray-700/50 text-slate-200 hover:bg-gray-700/50"
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={handleDeactivateAccount}
                      disabled={isDeactivating}
                      className="flex-1 bg-red-600/50 text-red-300 hover:bg-red-700/50 border border-red-600/50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isDeactivating ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Deactivating...
                        </>
                      ) : (
                        "Deactivate"
                      )}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            {/* Delete Account */}
            <div className="space-y-3">
              <p className="text-slate-300 font-medium text-sm sm:text-base">
                Delete Account
              </p>
              <p className="text-xs sm:text-sm text-slate-400">
                Permanently delete your account and all associated data. This
                cannot be undone.
              </p>

              <Dialog
                open={deleteDialogOpen}
                onOpenChange={setDeleteDialogOpen}
              >
                <DialogTrigger asChild>
                  <Button
                    variant="destructive"
                    className="w-full bg-red-600/50 text-red-300 hover:bg-red-700/50 border border-red-600/50 text-sm"
                  >
                    Delete Account
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-gray-900/95 border border-gray-800/50 text-slate-100">
                  <DialogHeader>
                    <DialogTitle>Delete Account</DialogTitle>
                    <DialogDescription className="text-slate-400">
                      Are you sure you want to permanently delete your account?
                      This action cannot be undone and all your data will be
                      lost forever.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="flex gap-3 pt-4">
                    <Button
                      variant="outline"
                      onClick={() => setDeleteDialogOpen(false)}
                      className="flex-1 bg-gray-800/50 border-gray-700/50 text-slate-200 hover:bg-gray-700/50"
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={handleDeleteAccount}
                      disabled={isDeleting}
                      className="flex-1 bg-red-600/50 text-red-300 hover:bg-red-700/50 border border-red-600/50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isDeleting ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Deleting...
                        </>
                      ) : (
                        "Delete Forever"
                      )}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
