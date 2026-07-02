import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  ArrowLeft,
  ArrowRight,
  Eye,
  EyeOff,
  Lock,
  Mail,
} from "lucide-react";

import TwoFAModal from "@/features/auth/components/two-fa-modal";
import GoogleLoginButton, {
  GoogleLoginFallback,
} from "@/features/auth/components/GoogleLoginButton";
import MainHeader from "@/shared/components/layout/main-header";
import { Button } from "@/shared/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import api from "@/shared/services/api";
import {
  fetchUserProfile,
  loginSuccess,
  set2FARequired,
  setLoading,
} from "@/shared/store/authSlice";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loginToken, setLoginToken] = useState("");
  const [error, setError] = useState("");
  const [twoFAError, setTwoFAError] = useState("");
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const { is2FARequired, isLoading } = useSelector((state) => state.auth);

  const from = location.state?.from?.pathname || "/dashboard";
  const successMessage = location.state?.message;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    dispatch(setLoading(true));

    try {
      const response = await api.post("/users/auth/login/", {
        username,
        password,
      });

      if (response.status === 200 && response.data.is_2fa_required) {
        setLoginToken(response.data.login_token);
        dispatch(set2FARequired(true));
      } else if (response.status === 200) {
        dispatch(loginSuccess(response.data));
        await dispatch(fetchUserProfile());
        navigate(from, { replace: true });
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed.");
      console.error(err.response?.data);
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handle2FAVerify = async (otpToken) => {
    setTwoFAError("");
    dispatch(setLoading(true));

    try {
      const response = await api.post("/users/auth/verify-2fa/", {
        login_token: loginToken,
        otp_token: otpToken,
      });

      if (response.status === 200) {
        dispatch(loginSuccess(response.data));
        dispatch(set2FARequired(false));
        navigate(from, { replace: true });
      }
    } catch (err) {
      setTwoFAError(err.response?.data?.detail || "2FA verification failed.");
      console.error(err.response?.data);
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handle2FAClose = () => {
    dispatch(set2FARequired(false));
    setTwoFAError("");
    setLoginToken("");
  };

  const handleGoogleError = (errorMessage) => {
    setError(errorMessage);
  };

  const googleClientId = import.meta.env.VITE_REACT_APP_GOOGLE_CLIENT_ID;

  return (
    <div className="relative flex h-screen flex-col overflow-hidden bg-[#050505] text-white">
      <div className="landing-market-animation absolute inset-0 opacity-70" />
      <div className="landing-grid absolute inset-0 opacity-25" />
      <MainHeader />

      <div className="relative flex min-h-0 flex-1 items-center justify-center px-4 py-3">
        <Card className="w-full max-w-[420px] overflow-hidden rounded-3xl border border-white/10 bg-[#0b0d12]/90 p-4 shadow-[0_28px_80px_rgba(0,0,0,0.55)] backdrop-blur-xl">
          <CardHeader className="px-0 pb-2 text-center">
            <img src="/favicon.png" alt="QuantNest" className="mx-auto mb-2 h-12 w-12 sm:h-14 sm:w-14" />
            <CardTitle className="text-[1.65rem] font-semibold leading-tight tracking-[-0.035em] text-white">
              Welcome back
            </CardTitle>
            <CardDescription className="mt-1 text-xs leading-5 text-slate-400">
              Continue researching, testing, and managing your strategies.
            </CardDescription>
          </CardHeader>

          <CardContent className="px-0">
            <div className="space-y-3">
              {googleClientId ? (
                <GoogleLoginButton
                  onError={handleGoogleError}
                  isLoading={isLoading}
                  type="login"
                />
              ) : (
                <GoogleLoginFallback type="login" />
              )}
            </div>

            <div className="relative my-3 flex items-center">
              <div className="flex-grow border-t border-white/10" />
              <span className="mx-4 flex-shrink text-sm text-slate-400">
                OR
              </span>
              <div className="flex-grow border-t border-white/10" />
            </div>

            {successMessage && (
              <div className="mb-3 rounded-lg border border-green-800 bg-green-900/50 p-2.5 text-sm text-green-300">
                {successMessage}
              </div>
            )}

            <form className="space-y-2.5" onSubmit={handleSubmit}>
              <div className="space-y-1">
                <Label
                  htmlFor="username"
                  className="text-xs font-medium text-slate-200"
                >
                  Username or email
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    id="username"
                    name="username"
                    type="text"
                    placeholder="username or email"
                    className="h-10 border-white/10 bg-white/[0.06] pl-10 text-slate-100 placeholder:text-slate-500 focus-visible:ring-[#e5c461]/45"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    autoComplete="username"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label
                  htmlFor="password"
                  className="text-xs font-medium text-slate-200"
                >
                  Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter password"
                    className="h-10 border-white/10 bg-white/[0.06] pl-10 pr-10 text-slate-100 placeholder:text-slate-500 focus-visible:ring-[#e5c461]/45"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 transition-colors hover:text-slate-200 focus:outline-none"
                    aria-label={
                      showPassword ? "Hide password" : "Show password"
                    }
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
                <div className="text-right">
                  <Link
                    to="/password-reset"
                    className="text-xs text-[#e5c461] underline hover:text-[#f2da8e]"
                  >
                    Forgot password?
                  </Link>
                </div>
              </div>

              {error && (
                <div className="rounded-lg border border-red-800 bg-red-900/50 p-2.5 text-sm text-red-300">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                disabled={isLoading}
                className="mt-2 h-10 w-full rounded-xl bg-[#e5c461] font-semibold text-black shadow-[0_12px_40px_rgba(229,196,97,0.18)] hover:bg-[#f2da8e] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isLoading ? "Signing in..." : "Log in"}
                {!isLoading && <ArrowRight className="h-4 w-4" />}
              </Button>
            </form>

            <div className="mt-3 border-t border-white/10 pt-3 text-center text-sm text-slate-400">
              Don&apos;t have an account?{" "}
              <Link
                to="/register"
                className="font-medium text-[#e5c461] underline hover:text-[#f2da8e]"
              >
                Create one
              </Link>
              <Link
                to="/"
                className="mx-auto mt-2 flex w-fit items-center gap-1.5 text-xs text-slate-500 transition-colors hover:text-[#f2da8e]"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Back to landing page
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      <TwoFAModal
        isOpen={is2FARequired}
        onClose={handle2FAClose}
        onVerify={handle2FAVerify}
        isLoading={isLoading}
        error={twoFAError}
      />
    </div>
  );
}
