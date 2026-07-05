import { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Button } from "@/shared/components/ui/button";

import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Badge } from "@/shared/components/ui/badge";
import {
  Key,
  ShieldCheck,
  LogOut,
  Wifi,
  CheckCircle,
  AlertCircle,
  Loader2,
  Eye,
  EyeOff,
  Unlock,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/shared/components/ui/dialog";
import TwoFASetupModal from "./two-fa-setup-modal";
import api from "@/shared/services/api";
import { logout, logoutUser, fetchUserProfile } from "@/shared/store/authSlice";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/shared/components/ui/card";
import React from "react";
import { useNavigate } from "react-router-dom";
import { GlobalLoader } from '@/shared/components/ui/global-loader';

export default function SecurityTab() {
  const { user } = useSelector((state) => state.auth);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const [passwordData, setPasswordData] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  const [showPassword, setShowPassword] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  const togglePasswordVisibility = (field) => {
    setShowPassword((prev) => ({ ...prev, [field]: !prev[field] }));
  };

  const [isTwoFAEnabled, setIsTwoFAEnabled] = useState(false);
  const [isTwoFASetupModalOpen, setIsTwoFASetupModalOpen] = useState(false);
  const [isTwoFADisableModalOpen, setIsTwoFADisableModalOpen] = useState(false);
  const [disablePassword, setDisablePassword] = useState("");
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
      const sessionsResponse = await api.get("/users/auth/sessions/");
      setActiveSessions(sessionsResponse.data.sessions || []);
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
      setIsTwoFADisableModalOpen(true);
    } else {
      setIsTwoFASetupModalOpen(true);
    }
  };

  const handleDisable2FA = async (e) => {
    e.preventDefault();
    setIsLoading2FA(true);
    setMessage(null);
    try {
      await api.post("/users/2fa/disable/", {
        password: disablePassword,
      });
      setIsTwoFAEnabled(false);
      setIsTwoFADisableModalOpen(false);
      setDisablePassword("");
      await dispatch(fetchUserProfile());
      setMessage({
        type: "success",
        text: "Two-factor authentication disabled successfully",
      });
    } catch (err) {
      console.error("Failed to disable 2FA:", err);
      setMessage({
        type: "error",
        text: err.response?.data?.error || "Failed to disable 2FA. Please check your password.",
      });
    } finally {
      setIsLoading2FA(false);
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
    <div className="w-full space-y-6 max-w-full overflow-hidden">
      {/* Dynamic Status Message - Top-level alert */}
      {message && (
        <div
          className={`px-4 py-3 rounded-2xl border ${
            message.type === "success"
              ? "bg-green-900/40 border-green-800/50 text-green-300"
              : "bg-red-900/40 border-red-800/50 text-red-300"
          } flex items-center gap-3 text-sm animate-in fade-in slide-in-from-top-4 duration-300 shadow-lg mb-2`}
        >
          {message.type === "success" ? (
            <CheckCircle className="h-5 w-5 shrink-0" />
          ) : (
            <AlertCircle className="h-5 w-5 shrink-0" />
          )}
          <span className="font-medium">{message.text}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start pb-10">
        {/* Password Change - Left Column */}
        <div className="lg:col-span-12 xl:col-span-7">
          <Card className="bg-gray-900/50 border-gray-800/50 h-full">
            <CardHeader className="border-b border-gray-800/50">
              <div className="flex items-center gap-2">
                <Key className="h-5 w-5 text-purple-400" />
                <CardTitle className="text-lg font-semibold text-slate-200">Update Password</CardTitle>
              </div>
              <CardDescription className="text-slate-400">Ensure your account is using a long, random password to stay secure.</CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <form onSubmit={handlePasswordSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="current_password">Current Password</Label>
                    <div className="relative group">
                      <Input
                        id="current_password"
                        name="current_password"
                        type={showPassword.current_password ? "text" : "password"}
                        value={passwordData.current_password}
                        onChange={handlePasswordInputChange}
                        placeholder="••••••••"
                        className="bg-gray-800/40 border-gray-700/50 focus:border-purple-500/50 text-slate-100 pr-10"
                        required
                      />
                      <button
                        type="button"
                        onClick={() => togglePasswordVisibility("current_password")}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                      >
                        {showPassword.current_password ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                    {getPasswordFieldError("current_password") && <p className="text-red-400 text-xs">{getPasswordFieldError("current_password")}</p>}
                  </div>
                  <div className="hidden md:block"></div> {/* Spacer */}
                  
                  <div className="space-y-2">
                    <Label htmlFor="new_password">New Password</Label>
                    <div className="relative group">
                      <Input
                        id="new_password"
                        name="new_password"
                        type={showPassword.new_password ? "text" : "password"}
                        value={passwordData.new_password}
                        onChange={handlePasswordInputChange}
                        placeholder="••••••••"
                        className="bg-gray-800/40 border-gray-700/50 focus:border-purple-500/50 text-slate-100 pr-10"
                        required
                      />
                      <button
                        type="button"
                        onClick={() => togglePasswordVisibility("new_password")}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                      >
                        {showPassword.new_password ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                    {getPasswordFieldError("new_password") && <p className="text-red-400 text-xs">{getPasswordFieldError("new_password")}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirm_password">Confirm New Password</Label>
                    <div className="relative group">
                      <Input
                        id="confirm_password"
                        name="confirm_password"
                        type={showPassword.confirm_password ? "text" : "password"}
                        value={passwordData.confirm_password}
                        onChange={handlePasswordInputChange}
                        placeholder="••••••••"
                        className="bg-gray-800/40 border-gray-700/50 focus:border-purple-500/50 text-slate-100 pr-10"
                        required
                      />
                      <button
                        type="button"
                        onClick={() => togglePasswordVisibility("confirm_password")}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                      >
                        {showPassword.confirm_password ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                    {getPasswordFieldError("confirm_password") && <p className="text-red-400 text-xs">{getPasswordFieldError("confirm_password")}</p>}
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <Button
                    type="submit"
                    disabled={isLoadingPassword}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white min-w-[160px] rounded-xl border-0 shadow-lg shadow-indigo-500/10 transition-all active:scale-95"
                  >
                    {isLoadingPassword ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Updating...
                      </>
                    ) : (
                      "Change Password"
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>

        {/* 2FA Status - Right Column */}
        <div className="lg:col-span-12 xl:col-span-5">
          <Card className="bg-gray-900/50 border-gray-800/50 h-full">
            <CardHeader className="border-b border-gray-800/50">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-indigo-400" />
                <CardTitle className="text-lg font-semibold text-slate-200">Multi-Factor Security</CardTitle>
              </div>
              <CardDescription className="text-slate-400">Add an extra layer of protection to your account by requiring a code from your mobile device.</CardDescription>
            </CardHeader>
            <CardContent className="p-6 h-full flex flex-col justify-between">
              <div className="space-y-6">
                <div className="flex items-center justify-between p-4 bg-gray-800/30 border border-gray-700/30 rounded-xl transition-all hover:bg-gray-800/50">
                  <div className="flex items-center gap-4">
                    <div className={`p-2 rounded-lg ${isTwoFAEnabled ? 'bg-emerald-500/10 text-emerald-400' : 'bg-orange-500/10 text-orange-400'}`}>
                      <ShieldCheck className="h-6 w-6" />
                    </div>
                    <div>
                      <h4 className="font-medium text-slate-200">Authenticator App</h4>
                      <Badge variant="outline" className={`mt-1 py-0 px-2 text-[10px] ${isTwoFAEnabled ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20' : 'bg-orange-500/10 text-orange-300 border-orange-500/20'}`}>
                        {isTwoFAEnabled ? "Active & Protected" : "Security Recommended"}
                      </Badge>
                    </div>
                  </div>
                  <Button
                    onClick={handleToggle2FA}
                    disabled={isLoading2FA}
                    variant={isTwoFAEnabled ? "ghost" : "default"}
                    className={`rounded-lg ${
                      isTwoFAEnabled 
                        ? "text-red-400 hover:text-red-300 hover:bg-red-900/20" 
                        : "bg-indigo-600 hover:bg-indigo-700 text-white"
                    }`}
                  >
                    {isTwoFAEnabled ? "Disable" : "Enable 2FA"}
                  </Button>
                </div>

                <div className="p-4 bg-indigo-500/5 border border-indigo-500/20 rounded-xl">
                  <p className="text-xs text-indigo-300/80 leading-relaxed italic">
                    "We recommend using an app like Google Authenticator or Authy. This ensures that even if someone learns your password, they cannot access your account."
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Active Sessions - Bottom Row */}
        <div className="lg:col-span-12">
          <Card className="bg-gray-900/50 border-gray-800/50">
            <CardHeader className="border-b border-gray-800/50 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Wifi className="h-5 w-5 text-cyan-400" />
                  <CardTitle className="text-lg font-semibold text-slate-200">Authorized Sessions</CardTitle>
                </div>
                <CardDescription className="text-slate-400">A list of devices and locations where you are currently signed in.</CardDescription>
              </div>
              <Button
                onClick={handleLogoutEverywhere}
                variant="outline"
                className="bg-red-950/20 border-red-500/20 text-red-400 hover:bg-red-900/40 hover:text-red-300 rounded-xl"
              >
                <LogOut className="h-4 w-4 mr-2" /> 
                End All Other Sessions
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              {isLoadingSessions ? (
                <GlobalLoader />
              ) : activeSessions.length === 0 ? (
                <div className="p-12 text-center text-slate-500">No active sessions found. How are you even here?</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-gray-800/50 bg-gray-800/20">
                        <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Device & IP</th>
                        <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Browser / OS</th>
                        <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider">Last Activity</th>
                        <th className="px-6 py-4 text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800/30">
                      {activeSessions.map((session) => (
                        <tr key={session.id} className={`hover:bg-gray-800/20 transition-colors group ${session.is_current ? 'bg-indigo-500/5' : ''}`}>
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-3">
                              <div className={`p-2 rounded-lg bg-gray-800/50 ${session.is_current ? 'text-indigo-400' : 'text-slate-500'}`}>
                                <Wifi className="h-5 w-5" />
                              </div>
                              <div>
                                <p className="text-slate-200 text-sm font-medium">{session.device || "Generic Device"}</p>
                                <p className="text-xs text-slate-500 font-mono italic">{session.ip_address}</p>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex flex-col">
                              <span className="text-slate-300 text-sm font-medium">{session.browser}</span>
                              <span className="text-xs text-slate-500 uppercase tracking-tighter">{session.os}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <span className="text-slate-400 text-xs">{new Date(session.last_activity).toLocaleString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}</span>
                          </td>
                          <td className="px-6 py-4 text-right">
                            {session.is_current ? (
                              <Badge className="bg-indigo-500/20 text-indigo-300 border-indigo-500/30 text-[10px]">Current Session</Badge>
                            ) : (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleRevokeSession(session.id)}
                                className="border-red-500/30 text-red-400 hover:bg-red-900/20 hover:text-red-300 text-xs h-8 px-3 transition-colors"
                              >
                                Revoke Access
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <TwoFASetupModal
        isOpen={isTwoFASetupModalOpen}
        onClose={() => setIsTwoFASetupModalOpen(false)}
        onSetupComplete={handle2FASetupComplete}
      />

      <Dialog open={isTwoFADisableModalOpen} onOpenChange={setIsTwoFADisableModalOpen}>
        <DialogContent className="sm:max-w-[425px] bg-gray-900 border border-gray-800 text-slate-100 rounded-2xl p-8">
          <DialogHeader>
            <div className="flex justify-center mb-6">
              <div className="p-4 bg-red-500/10 rounded-full border-2 border-red-500/20">
                <Unlock className="h-10 w-10 text-red-500" />
              </div>
            </div>
            <DialogTitle className="text-2xl font-bold text-center">Disable Security Layer</DialogTitle>
            <DialogDescription className="text-slate-400 text-center pt-2">
              To proceed with disabling Two-Factor Authentication, please provide your account password for verification.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleDisable2FA} className="space-y-6 py-4">
            <div className="space-y-2">
              <Label htmlFor="disable-password">Account Password</Label>
              <Input
                id="disable-password"
                type="password"
                value={disablePassword}
                onChange={(e) => setDisablePassword(e.target.value)}
                placeholder="Enter your password"
                className="bg-gray-800/40 border-gray-700/50 focus:border-red-500/50 text-slate-100 h-12"
                required
              />
            </div>
            <div className="flex gap-3">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setIsTwoFADisableModalOpen(false)}
                className="flex-1 text-slate-400"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isLoading2FA}
                className="flex-2 bg-red-600 hover:bg-red-700 text-white shadow-lg shadow-red-600/10 border-0 h-12 px-8"
              >
                {isLoading2FA ? <Loader2 className="h-4 w-4 animate-spin" /> : "Disable MFA"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
