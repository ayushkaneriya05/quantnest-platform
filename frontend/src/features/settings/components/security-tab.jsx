import { getApiErrorDetails, getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useState, useEffect, useCallback, useRef } from "react";
import { useDispatch } from "react-redux";
import { Button } from "@/shared/components/ui/button";
import { useNotifications } from "@/shared/hooks/useNotifications";

import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { Badge } from "@/shared/components/ui/badge";
import {
  ShieldCheck,
  LogOut,
  Monitor,
  Smartphone,
  Tablet,
  Loader2,
  Eye,
  EyeOff,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import TwoFASetupModal from "@/features/settings/components/two-fa-setup-modal.jsx";
import api from "@/shared/services/api";
import { loginSuccess, fetchUserProfile } from "@/shared/store/authSlice";
import { formatDateTime } from "@/shared/utils/formatters";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/shared/components/ui/card";
import WorkspaceState from '@/shared/components/WorkspaceState';

export default function SecurityTab() {
  const dispatch = useDispatch();
  const { notify } = useNotifications();

  const [passwordData, setPasswordData] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  const [showPassword, setShowPassword] = useState({
    current_password: false,
    new_password: false,
    confirm_password: false,
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
  const [securityError, setSecurityError] = useState('');
  const [statusKnown, setStatusKnown] = useState(false);
  const [sessionBusy, setSessionBusy] = useState(false);
  const passwordLock = useRef(false), twoFALock = useRef(false), sessionLock = useRef(false);

  const [passwordErrors, setPasswordErrors] = useState({});

  const loadSecurityData = useCallback(async () => {
    setIsLoadingSessions(true); setStatusKnown(false); setSecurityError('');
    const [status, sessions] = await Promise.allSettled([api.get('/users/auth/2fa/status/'), api.get('/users/auth/sessions/')]);
    if (status.status === 'fulfilled') { setIsTwoFAEnabled(status.value.data.is_2fa_enabled); setStatusKnown(true); }
    if (sessions.status === 'fulfilled') setActiveSessions(sessions.value.data.sessions || []);
    const errors = [status, sessions].filter(result => result.status === 'rejected');
    if (errors.length) setSecurityError(errors.map(result => getApiErrorMessage(result.reason)).join(' '));
    setIsLoadingSessions(false);
  }, []);
  useEffect(() => { loadSecurityData(); }, [loadSecurityData]);

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
    if (passwordLock.current) return;
    setIsLoadingPassword(true);
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

    passwordLock.current = true;
    try {
      const { data } = await api.post("/users/auth/password/change/", {
        old_password: passwordData.current_password,
        new_password1: passwordData.new_password,
        new_password2: passwordData.confirm_password,
      });
      dispatch(loginSuccess(data));
      await loadSecurityData();
      notify.success(data.message || "Your password has been changed.");

      // Clear form
      setPasswordData({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });
    } catch (err) {
      console.error("Password change error:", err);

      const serverErrors = getApiErrorDetails(err);
      setPasswordErrors({
        current_password: serverErrors.old_password,
        new_password: serverErrors.new_password1,
        confirm_password: serverErrors.new_password2,
      });
      notify.error(getApiErrorMessage(err, "Failed to change password"));
    } finally {
      passwordLock.current = false;
      setIsLoadingPassword(false);
    }
  };

  const handleToggle2FA = () => {
    if (isTwoFAEnabled) {
      setIsTwoFADisableModalOpen(true);
    } else {
      setIsTwoFASetupModalOpen(true);
    }
  };

  const handleDisable2FA = async (e) => {
    e.preventDefault();
    if (twoFALock.current) return;
    twoFALock.current = true;
    setIsLoading2FA(true);
    try {
      await api.post("/users/2fa/disable/", {
        password: disablePassword,
      });
      setIsTwoFAEnabled(false);
      setIsTwoFADisableModalOpen(false);
      setDisablePassword("");
      await dispatch(fetchUserProfile());
      notify.success("Two-factor authentication disabled successfully");
    } catch (err) {
      console.error("Failed to disable 2FA:", err);
      notify.error(getApiErrorMessage(err, "Failed to disable 2FA. Please check your password."));
    } finally {
      twoFALock.current = false;
      setIsLoading2FA(false);
    }
  };

  const handle2FASetupComplete = async () => {
    setIsTwoFAEnabled(true);
    setIsTwoFASetupModalOpen(false);
    await dispatch(fetchUserProfile());
    notify.success("Two-factor authentication enabled successfully");
  };

  const handleRevokeSession = async (sessionId) => {
    if (sessionLock.current) return;
    sessionLock.current = true; setSessionBusy(true);
    try {
      await api.delete(`/users/auth/sessions/${sessionId}/`);
      setActiveSessions((prev) => prev.filter((s) => s.id !== sessionId));
      
      notify.success("Session revoked successfully");
    } catch (err) {
      console.error("Failed to revoke session:", err);
      notify.error(getApiErrorMessage(err, "Failed to revoke session"));
    } finally { sessionLock.current = false; setSessionBusy(false); }
  };

  const handleLogoutEverywhere = async () => {
    if (sessionLock.current) return;
    sessionLock.current = true; setSessionBusy(true);
    try {
      await api.post("/users/auth/logout-all/");
      await loadSecurityData();
      notify.success("Logged out from all other devices successfully.");
    } catch (err) {
      console.error("Failed to logout everywhere:", err);
      notify.error(getApiErrorMessage(err, "Failed to end other sessions."));
    } finally { sessionLock.current = false; setSessionBusy(false); }
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
    <div className="min-w-0 space-y-5">
      {securityError && <WorkspaceState error={securityError} onRetry={loadSecurityData} />}
      <div className="grid items-start gap-5 xl:grid-cols-2">
        <Card className="min-w-0">
          <CardHeader className="p-5 pb-4">
            <CardTitle className="text-lg">Change password</CardTitle>
            <CardDescription>Update your password. Other signed-in sessions will be ended.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5 px-5 pb-5">
            <form onSubmit={handlePasswordSubmit} className="space-y-5" aria-busy={isLoadingPassword}>
              <div className="grid gap-4 sm:grid-cols-2">
                {[
                  ["current_password", "Current password", "current-password"],
                  ["new_password", "New password", "new-password"],
                  ["confirm_password", "Confirm new password", "new-password"],
                ].map(([field, label, autoComplete]) => {
                  const error = getPasswordFieldError(field);
                  return (
                    <div key={field} className={`min-w-0 space-y-2 ${field === "current_password" ? "sm:col-span-2" : ""}`}>
                      <Label htmlFor={field}>{label}</Label>
                      <div className="relative">
                        <Input
                          id={field}
                          name={field}
                          type={showPassword[field] ? "text" : "password"}
                          value={passwordData[field]}
                          onChange={handlePasswordInputChange}
                          autoComplete={autoComplete}
                          autoCapitalize="none"
                          spellCheck={false}
                          disabled={isLoadingPassword}
                          aria-invalid={Boolean(error)}
                          aria-describedby={error ? `${field}-error` : field === "new_password" ? "security-password-help" : undefined}
                          className="pr-10"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => togglePasswordVisibility(field)}
                          aria-label={`${showPassword[field] ? "Hide" : "Show"} ${label.toLowerCase()}`}
                          aria-pressed={showPassword[field]}
                          disabled={isLoadingPassword}
                          className="focus-ring absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-md text-muted-foreground hover:text-foreground disabled:opacity-50"
                        >
                          {showPassword[field]
                            ? <EyeOff aria-hidden="true" className="h-4 w-4" />
                            : <Eye aria-hidden="true" className="h-4 w-4" />}
                        </button>
                      </div>
                      {error && <p id={`${field}-error`} role="alert" className="text-xs text-destructive-text">{error}</p>}
                    </div>
                  );
                })}
              </div>
              <p id="security-password-help" className="text-xs leading-5 text-muted-foreground">
                Use at least 8 characters. Avoid common passwords, only numbers, and personal details.
              </p>
              <div className="flex justify-end border-t pt-4">
                <Button type="submit" disabled={isLoadingPassword} className="w-full sm:w-auto">
                  {isLoadingPassword && <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />}
                  {isLoadingPassword ? "Updating…" : "Change password"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card className="min-w-0">
          <CardHeader className="p-5 pb-4">
            <CardTitle className="text-lg">Two-factor authentication</CardTitle>
            <CardDescription>Require a code from your authenticator app when signing in.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 px-5 pb-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="flex items-center gap-2 text-sm font-medium">
                <ShieldCheck aria-hidden="true" className="h-4 w-4 text-brand" />
                Authenticator app
              </span>
              <Badge
                variant="outline"
                className={statusKnown && isTwoFAEnabled ? "border-success/25 bg-success/5 text-success" : "text-muted-foreground"}
              >
                {!statusKnown ? (isLoadingSessions ? "Loading…" : "Unavailable") : isTwoFAEnabled ? "Enabled" : "Not enabled"}
              </Badge>
            </div>
            <p className="text-sm leading-6 text-muted-foreground">
              {statusKnown && isTwoFAEnabled
                ? "Keep the backup codes from setup somewhere safe. Each code can be used once if you lose access to your app."
                : "Set up an authenticator app and save your backup codes to help protect access to your account."}
            </p>
            <div className="flex justify-end border-t pt-4">
              <Button
                type="button"
                onClick={handleToggle2FA}
                disabled={isLoading2FA || !statusKnown}
                variant={isTwoFAEnabled ? "outline" : "default"}
                className="w-full sm:w-auto"
              >
                {isTwoFAEnabled ? "Disable 2FA" : "Set up 2FA"}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="min-w-0">
        <CardHeader className="gap-3 p-5 pb-4 sm:flex-row sm:items-center sm:justify-between sm:space-y-0">
          <div className="min-w-0 space-y-1.5">
            <CardTitle className="text-lg">Authorized sessions</CardTitle>
            <CardDescription>Active browser sessions. Tabs in the same browser profile share one session.</CardDescription>
          </div>
          <Button
            type="button"
            onClick={handleLogoutEverywhere}
            disabled={sessionBusy || isLoadingSessions || !activeSessions.some((session) => !session.is_current)}
            variant="outline"
            size="sm"
            className="min-h-10 w-full shrink-0 sm:w-auto"
          >
            <LogOut aria-hidden="true" className="h-4 w-4" />
            End other sessions
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {isLoadingSessions ? (
            <div className="p-5"><WorkspaceState loading title="Loading browser sessions" /></div>
          ) : activeSessions.length === 0 ? (
            <p className="px-5 pb-5 text-sm text-muted-foreground">
              {securityError ? "Session details could not be loaded. Retry using the message above." : "No active sessions to display."}
            </p>
          ) : (
            <ul role="list" aria-label="Authorized browser sessions" className="divide-y border-t">
              {activeSessions.map((session) => {
                const DeviceIcon = session.device === "Mobile" ? Smartphone : session.device === "Tablet" ? Tablet : Monitor;
                return (
                  <li key={session.id} className="grid items-center gap-4 p-5 md:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)_auto]">
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                        <DeviceIcon aria-hidden="true" className="h-5 w-5" />
                      </span>
                      <div className="min-w-0">
                        <p className="text-sm font-medium">{session.device || "Browser"}</p>
                        <p className="mt-1 break-all font-mono text-xs text-muted-foreground">{session.ip_address || "IP unavailable"}</p>
                      </div>
                    </div>
                    <dl className="grid min-w-0 gap-3 sm:grid-cols-2">
                      <div className="min-w-0">
                        <dt className="text-xs text-muted-foreground">Browser / OS</dt>
                        <dd className="mt-1 break-words text-sm">{session.browser || "Unknown"} · {session.os || "Unknown"}</dd>
                      </div>
                      <div className="min-w-0">
                        <dt className="text-xs text-muted-foreground">Last active</dt>
                        <dd className="mt-1 text-sm">{formatDateTime(session.last_activity)}</dd>
                      </div>
                    </dl>
                    <div className="flex sm:justify-end">
                      {session.is_current ? (
                        <Badge variant="outline" className="border-brand/25 bg-brand/5 text-brand">Current session</Badge>
                      ) : (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => handleRevokeSession(session.id)}
                          disabled={sessionBusy || isLoadingSessions}
                          className="min-h-10 w-full sm:w-auto"
                        >
                          End session
                        </Button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>

      <TwoFASetupModal
        isOpen={isTwoFASetupModalOpen}
        onClose={() => setIsTwoFASetupModalOpen(false)}
        onSetupComplete={handle2FASetupComplete}
      />

      <Dialog open={isTwoFADisableModalOpen} onOpenChange={open => { if (!isLoading2FA) { setIsTwoFADisableModalOpen(open); if (!open) setDisablePassword(""); } }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Disable two-factor authentication?</DialogTitle>
            <DialogDescription>Confirm your account password to turn off authenticator verification when signing in.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleDisable2FA} className="space-y-4" aria-busy={isLoading2FA}>
            <div className="space-y-2">
              <Label htmlFor="disable-password">Account password</Label>
              <Input
                id="disable-password"
                type="password"
                value={disablePassword}
                onChange={(event) => setDisablePassword(event.target.value)}
                autoComplete="current-password"
                disabled={isLoading2FA}
                required
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => { setIsTwoFADisableModalOpen(false); setDisablePassword(""); }}
                disabled={isLoading2FA}
              >
                Cancel
              </Button>
              <Button type="submit" variant="destructive" disabled={isLoading2FA}>
                {isLoading2FA && <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />}
                {isLoading2FA ? "Disabling…" : "Disable 2FA"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
