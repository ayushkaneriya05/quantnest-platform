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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Key,
  ShieldCheck,
  LogOut,
  Wifi,
  CheckCircle,
  AlertCircle,
  Loader2,
} from "lucide-react";
import TwoFASetupModal from "./two-fa-setup-modal";
import api from "@/services/api";
import { logout, logoutUser, fetchUserProfile } from "@/store/authSlice";
import { useNavigate } from "react-router-dom";

export default function SecurityTab() {
  const { user } = useSelector((state) => state.auth);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const [passwordData, setPasswordData] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  const [isTwoFAEnabled, setIsTwoFAEnabled] = useState(false);
  const [isTwoFASetupModalOpen, setIsTwoFASetupModalOpen] = useState(false);
  const [activeSessions, setActiveSessions] = useState([]);

  const [isLoadingPassword, setIsLoadingPassword] = useState(false);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [isLoading2FA, setIsLoading2FA] = useState(false);

  const [message, setMessage] = useState(null);
  const [passwordErrors, setPasswordErrors] = useState({});

  // Load security data on component mount
  useEffect(() => {
    loadSecurityData();
  }, []);

  const loadSecurityData = async () => {
    try {
      // Load 2FA status
      const twoFAResponse = await api.get("/users/auth/2fa/status/");
      setIsTwoFAEnabled(twoFAResponse.data.is_2fa_enabled);

      // Load active sessions
      // const sessionsResponse = await api.get("/users/auth/sessions/");
      // setActiveSessions(sessionsResponse.data.sessions || []);
    } catch (err) {
      console.error("Failed to load security data:", err);
      setMessage({
        type: "error",
        text: "Failed to load security information",
      });
    } finally {
      setIsLoadingSessions(false);
    }
  };

  const handlePasswordInputChange = (e) => {
    const { name, value } = e.target;
    setPasswordData((prev) => ({
      ...prev,
      [name]: value,
    }));

    // Clear field-specific error when user starts typing
    if (passwordErrors[name]) {
      setPasswordErrors((prev) => ({
        ...prev,
        [name]: null,
      }));
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setIsLoadingPassword(true);
    setMessage(null);
    setPasswordErrors({});

    // Client-side validation
    if (passwordData.new_password !== passwordData.confirm_password) {
      setPasswordErrors({
        confirm_password: "Passwords do not match",
      });
      setIsLoadingPassword(false);
      return;
    }

    if (passwordData.new_password.length < 8) {
      setPasswordErrors({
        new_password: "Password must be at least 8 characters long",
      });
      setIsLoadingPassword(false);
      return;
    }

    try {
      await api.post("/users/auth/password/change", {
        old_password: passwordData.current_password,
        new_password1: passwordData.new_password,
        new_password2: passwordData.confirm_password,
      });
      await dispatch(fetchUserProfile());
      setMessage({
        type: "success",
        text: "Password changed successfully!",
      });

      // Clear form
      setPasswordData({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });
    } catch (err) {
      console.error("Password change error:", err);

      if (err.response?.data) {
        const serverErrors = err.response.data;
        if (typeof serverErrors === "object") {
          setPasswordErrors(serverErrors);
        } else {
          setMessage({
            type: "error",
            text: serverErrors.detail || "Failed to change password",
          });
        }
      } else {
        setMessage({
          type: "error",
          text: "Network error. Please try again.",
        });
      }
    } finally {
      setIsLoadingPassword(false);
    }
  };

  const handleToggle2FA = async () => {
    if (isTwoFAEnabled) {
      // Disable 2FA
      setIsLoading2FA(true);
      try {
        await api.post("/users/2fa/disable/");
        setIsTwoFAEnabled(false);
        await dispatch(fetchUserProfile());
        setMessage({
          type: "success",
          text: "Two-factor authentication disabled successfully",
        });
      } catch (err) {
        console.error("Failed to disable 2FA:", err);
        setMessage({
          type: "error",
          text: "Failed to disable 2FA",
        });
      } finally {
        setIsLoading2FA(false);
      }
    } else {
      // Open setup modal for enabling 2FA
      setIsTwoFASetupModalOpen(true);
    }
  };

  const handle2FASetupComplete = async () => {
    setIsTwoFAEnabled(true);
    setIsTwoFASetupModalOpen(false);
    await dispatch(fetchUserProfile());
    setMessage({
      type: "success",
      text: "Two-factor authentication enabled successfully",
    });
  };

  const handleRevokeSession = async (sessionId) => {
    try {
      await api.delete(`/users/auth/sessions/${sessionId}/`);
      setActiveSessions((prev) => prev.filter((s) => s.id !== sessionId));
      setMessage({
        type: "success",
        text: "Session revoked successfully",
      });
    } catch (err) {
      console.error("Failed to revoke session:", err);
      setMessage({
        type: "error",
        text: "Failed to revoke session",
      });
    }
  };

  const handleLogoutEverywhere = async () => {
    try {
      await api.post("/users/auth/logout-all/");
      dispatch(logoutUser());
      dispatch(logout());
      navigate("/login", {
        state: { message: "You have been logged out from all devices." },
      });
    } catch (err) {
      console.error("Failed to logout everywhere:", err);
      setMessage({
        type: "error",
        text: "Failed to logout from all devices",
      });
    }
  };

  const getPasswordFieldError = (fieldName) => {
    if (passwordErrors[fieldName]) {
      if (Array.isArray(passwordErrors[fieldName])) {
        return passwordErrors[fieldName][0];
      }
      return passwordErrors[fieldName];
    }
    return null;
  };

  return (
    <Card className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-4 sm:p-6">
      <CardHeader className="mb-4 sm:mb-6 px-0 pt-0">
        <CardTitle className="text-xl sm:text-2xl font-bold text-slate-100">
          Security Settings
        </CardTitle>
        <CardDescription className="text-slate-400 text-sm sm:text-base">
          Manage your account security and active sessions.
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
              <AlertCircle className="h-4 w-4" />
            )}
            {message.text}
          </div>
        )}

        {/* Password Change */}
        <div className="space-y-4 sm:space-y-6">
          <h3 className="text-lg sm:text-xl font-bold text-slate-100 flex items-center gap-2">
            <Key className="h-4 w-4 sm:h-5 sm:w-5 text-purple-400" /> Password
            Change
          </h3>

          <form
            onSubmit={handlePasswordSubmit}
            className="space-y-4 sm:space-y-6"
          >
            <div className="grid gap-4 sm:gap-6 lg:grid-cols-2">
              <div className="space-y-2">
                <Label
                  htmlFor="current_password"
                  className="text-slate-200 text-sm sm:text-base"
                >
                  Current Password
                </Label>
                <Input
                  id="current_password"
                  name="current_password"
                  type="password"
                  value={passwordData.current_password}
                  onChange={handlePasswordInputChange}
                  placeholder="••••••••"
                  className="bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500"
                  required
                />
                {getPasswordFieldError("current_password") && (
                  <p className="text-red-400 text-xs">
                    {getPasswordFieldError("current_password")}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label
                  htmlFor="new_password"
                  className="text-slate-200 text-sm sm:text-base"
                >
                  New Password
                </Label>
                <Input
                  id="new_password"
                  name="new_password"
                  type="password"
                  value={passwordData.new_password}
                  onChange={handlePasswordInputChange}
                  placeholder="••••••••"
                  className="bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500"
                  required
                />
                {getPasswordFieldError("new_password") && (
                  <p className="text-red-400 text-xs">
                    {getPasswordFieldError("new_password")}
                  </p>
                )}
              </div>

              <div className="space-y-2 lg:col-span-2">
                <Label
                  htmlFor="confirm_password"
                  className="text-slate-200 text-sm sm:text-base"
                >
                  Confirm New Password
                </Label>
                <Input
                  id="confirm_password"
                  name="confirm_password"
                  type="password"
                  value={passwordData.confirm_password}
                  onChange={handlePasswordInputChange}
                  placeholder="••••••••"
                  className="bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500"
                  required
                />
                {getPasswordFieldError("confirm_password") && (
                  <p className="text-red-400 text-xs">
                    {getPasswordFieldError("confirm_password")}
                  </p>
                )}
              </div>
            </div>

            <div className="flex justify-start">
              <Button
                type="submit"
                disabled={isLoadingPassword}
                className="bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)] rounded-xl border-0 w-full sm:w-auto px-6 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoadingPassword ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Changing Password...
                  </>
                ) : (
                  "Change Password"
                )}
              </Button>
            </div>
          </form>
        </div>

        {/* Two-Factor Authentication (2FA) */}
        <div className="space-y-4 sm:space-y-6">
          <h3 className="text-lg sm:text-xl font-bold text-slate-100 flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 sm:h-5 sm:w-5 text-indigo-400" />{" "}
            Two-Factor Authentication (2FA)
          </h3>

          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 p-4 sm:p-6 bg-gray-800/50 border border-gray-700/50 rounded-lg">
            <div className="flex-1">
              <div className="text-slate-300 font-medium text-sm sm:text-base flex flex-wrap items-center gap-2">
                2FA Status:
                <Badge
                  className={`text-xs sm:text-sm ${
                    isTwoFAEnabled
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                      : "bg-orange-500/20 text-orange-300 border border-orange-500/30"
                  }`}
                >
                  {isTwoFAEnabled ? "Active" : "Disabled"}
                </Badge>
              </div>
              <p className="text-xs sm:text-sm text-slate-400 mt-2">
                {isTwoFAEnabled
                  ? "Your account is protected with 2FA."
                  : "Enhance your account security by enabling Two-Factor Authentication."}
              </p>
            </div>

            <Button
              onClick={handleToggle2FA}
              disabled={isLoading2FA}
              variant={isTwoFAEnabled ? "destructive" : "default"}
              className={`w-full lg:w-auto text-sm shrink-0 disabled:opacity-50 disabled:cursor-not-allowed ${
                isTwoFAEnabled
                  ? "bg-red-600/50 text-red-300 hover:bg-red-700/50 border border-red-600/50"
                  : "bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)] rounded-xl border-0"
              }`}
            >
              {isLoading2FA ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {isTwoFAEnabled ? "Disabling..." : "Enabling..."}
                </>
              ) : isTwoFAEnabled ? (
                "Disable 2FA"
              ) : (
                "Enable 2FA"
              )}
            </Button>
          </div>
        </div>

        {/* Active Sessions */}
        <div className="space-y-4 sm:space-y-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <h3 className="text-lg sm:text-xl font-bold text-slate-100 flex items-center gap-2">
              <Wifi className="h-4 w-4 sm:h-5 sm:w-5 text-cyan-400" /> Active
              Sessions
            </h3>
            <Button
              onClick={handleLogoutEverywhere}
              variant="destructive"
              className="bg-red-600/50 text-red-300 hover:bg-red-700/50 border border-red-600/50 w-full sm:w-auto text-sm"
            >
              <LogOut className="h-3 w-3 sm:h-4 sm:w-4 mr-2" /> Log Out
              Everywhere
            </Button>
          </div>

          {isLoadingSessions ? (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
            </div>
          ) : (
            <div className="space-y-3 sm:space-y-4">
              {activeSessions.length === 0 ? (
                <div className="text-center text-slate-400 p-8">
                  No active sessions found
                </div>
              ) : (
                activeSessions.map((session) => (
                  <div
                    key={session.id}
                    className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3 sm:p-4 bg-gray-800/50 border border-gray-700/50 rounded-lg"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-slate-300 font-medium text-sm sm:text-base">
                        {session.ip_address}
                      </p>
                      <p className="text-xs sm:text-sm text-slate-400 break-words">
                        {session.location} &bull; Last active:{" "}
                        {session.last_activity}
                      </p>
                      {session.user_agent && (
                        <p className="text-xs text-slate-500 truncate">
                          {session.user_agent}
                        </p>
                      )}
                    </div>

                    {!session.is_current && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRevokeSession(session.id)}
                        className="bg-gray-700/50 border-gray-600/50 text-slate-300 hover:bg-gray-600/50 w-full sm:w-auto text-sm shrink-0"
                      >
                        Revoke
                      </Button>
                    )}

                    {session.is_current && (
                      <Badge className="bg-blue-500/20 text-blue-300 border border-blue-500/30 text-xs shrink-0">
                        Current
                      </Badge>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </CardContent>

      <TwoFASetupModal
        isOpen={isTwoFASetupModalOpen}
        onClose={() => setIsTwoFASetupModalOpen(false)}
        onSetupComplete={handle2FASetupComplete}
      />
    </Card>
  );
}
