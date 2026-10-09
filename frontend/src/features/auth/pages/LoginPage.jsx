import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useState } from "react";
import PropTypes from "prop-types";
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
import GoogleLoginButton from "@/features/auth/components/GoogleLoginButton";
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
import { loginSuccess, setLoading } from "@/shared/store/authSlice";

export default function LoginPage({ twoFactorChallenge = null }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loginToken, setLoginToken] = useState(twoFactorChallenge?.login_token || "");
  const [error, setError] = useState("");
  const [twoFAError, setTwoFAError] = useState("");
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const { isLoading } = useSelector((state) => state.auth);

  const from = twoFactorChallenge?.next || (location.state?.from ? `${location.state.from.pathname}${location.state.from.search || ""}${location.state.from.hash || ""}` : "/overview");
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

      if (response.data.is_2fa_required) {
        setLoginToken(response.data.login_token);
      } else {
        dispatch(loginSuccess(response.data));
        navigate(from, { replace: true });
      }
    } catch (err) {
      setError(getApiErrorMessage(err, "Login failed."));
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

      dispatch(loginSuccess(response.data));
      navigate(from, { replace: true });
    } catch (err) {
      setTwoFAError(getApiErrorMessage(err, "2FA verification failed."));
      console.error(err.response?.data);
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handle2FAClose = () => {
    setTwoFAError("");
    setLoginToken("");
    if (twoFactorChallenge) {
      navigate("/login", { replace: true, state: { from: { pathname: from } } });
    }
  };

  const handleGoogleError = (errorMessage) => {
    setError(errorMessage);
  };

  return (
    <div className="relative flex h-[var(--viewport-height)] flex-col overflow-hidden bg-card text-foreground">
      <div className="landing-market-animation absolute inset-0 opacity-70" />
      <div className="landing-grid absolute inset-0 opacity-25" />
      <MainHeader authPage="login" />

      <div className="scrollbar-theme relative flex min-h-0 flex-1 items-start justify-center overflow-y-auto px-4 py-3">
        <Card className="my-auto shrink-0 w-full max-w-[420px] overflow-hidden rounded-3xl border border-border bg-card/90 p-4 shadow-card backdrop-blur-xl">
          <CardHeader className="px-0 pb-2 text-center">
            <img src="/favicon.png" alt="QuantNest" className="mx-auto mb-2 h-12 w-12 sm:h-14 sm:w-14" />
            <CardTitle className="text-[1.65rem] font-semibold leading-tight tracking-[-0.035em] text-foreground">
              Welcome back
            </CardTitle>
            <CardDescription className="mt-1 text-xs leading-5 text-muted-foreground">
              Continue researching, testing, and managing your strategies.
            </CardDescription>
          </CardHeader>

          <CardContent className="px-0">
            <div className="space-y-3">
              <GoogleLoginButton onError={handleGoogleError} isLoading={isLoading} />
            </div>

            <div className="relative my-3 flex items-center">
              <div className="flex-grow border-t border-border" />
              <span className="mx-4 flex-shrink text-sm text-muted-foreground">
                OR
              </span>
              <div className="flex-grow border-t border-border" />
            </div>

            {successMessage && (
              <div className="mb-3 rounded-lg border border-green-800 bg-green-50 dark:bg-green-900/50 p-2.5 text-sm text-green-700 dark:text-green-300">
                {successMessage}
              </div>
            )}

            <form className="space-y-2.5" onSubmit={handleSubmit}>
              <div className="space-y-1">
                <Label
                  htmlFor="username"
                  className="text-xs font-medium text-foreground"
                >
                  Username or email
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="username"
                    name="username"
                    type="text"
                    placeholder="username or email"
                    className="h-10 border-border bg-muted/50 pl-10 text-foreground placeholder:text-muted-foreground focus-visible:ring-ring"
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
                  className="text-xs font-medium text-foreground"
                >
                  Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter password"
                    className="h-10 border-border bg-muted/50 pl-10 pr-10 text-foreground placeholder:text-muted-foreground focus-visible:ring-ring"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground focus:outline-none"
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
                    className="text-xs text-brand underline hover:text-brand"
                  >
                    Forgot password?
                  </Link>
                </div>
              </div>

              {error && (
                <div className="rounded-lg border border-red-800 bg-red-50 dark:bg-red-900/50 p-2.5 text-sm text-red-700 dark:text-red-300">
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

            <div className="mt-3 border-t border-border pt-3 text-center text-sm text-muted-foreground">
              Don&apos;t have an account?{" "}
              <Link
                to="/register"
                className="font-medium text-brand underline hover:text-brand"
              >
                Create one
              </Link>
              <Link
                to="/"
                className="mx-auto mt-2 flex w-fit items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-brand"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Back to landing page
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      <TwoFAModal
        isOpen={Boolean(loginToken)}
        onClose={handle2FAClose}
        onVerify={handle2FAVerify}
        isLoading={isLoading}
        error={twoFAError}
      />
    </div>
  );
}

LoginPage.propTypes = {
  twoFactorChallenge: PropTypes.shape({
    login_token: PropTypes.string.isRequired,
    next: PropTypes.string,
  }),
};
