import { LoaderMark } from '@/shared/components/ui/global-loader';
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useState } from "react";
import PropTypes from "prop-types";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { ArrowRight, Lock, LogIn, Mail } from "lucide-react";

import TwoFAModal from "@/features/auth/components/two-fa-modal";
import GoogleLoginButton from "@/features/auth/components/GoogleLoginButton";
import AuthLayout from "../components/AuthLayout";
import { AuthField } from "../components/AuthFields";
import { Button } from "@/shared/components/ui/button";
import api from "@/shared/services/api";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { loginSuccess, setLoading } from "@/shared/store/authSlice";

export default function LoginPage({ twoFactorChallenge = null }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginToken, setLoginToken] = useState(twoFactorChallenge?.login_token || "");
  const dispatch = useDispatch();
  const { notify } = useNotifications();
  const navigate = useNavigate();
  const location = useLocation();
  const { isLoading } = useSelector((state) => state.auth);

  const from = twoFactorChallenge?.next || (location.state?.from ? `${location.state.from.pathname}${location.state.from.search || ""}${location.state.from.hash || ""}` : "/overview");

  const handleSubmit = async (e) => {
    e.preventDefault();
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
      notify.error(getApiErrorMessage(err, "Could not sign in. Please try again."));
      console.error(err.response?.data);
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handle2FAVerify = async (otpToken) => {
    dispatch(setLoading(true));

    try {
      const response = await api.post("/users/auth/verify-2fa/", {
        login_token: loginToken,
        otp_token: otpToken,
      });

      dispatch(loginSuccess(response.data));
      navigate(from, { replace: true });
    } catch (err) {
      notify.error(getApiErrorMessage(err, "Could not verify your code. Please try again."));
      console.error(err.response?.data);
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handle2FAClose = () => {
    setLoginToken("");
    if (twoFactorChallenge) {
      navigate("/login", { replace: true, state: { from: { pathname: from } } });
    }
  };

  return (
    <AuthLayout authPage="login" title="Welcome back" description="Continue researching, testing, and managing your strategies." icon={LogIn}>
      <div className="space-y-4">
        <GoogleLoginButton onError={notify.error} isLoading={isLoading} />
      </div>
      <div className="my-5 flex items-center gap-3 text-xs text-muted-foreground"><span className="flex-1 border-t" />or sign in with your account<span className="flex-1 border-t" /></div>
      <form className="space-y-4" onSubmit={handleSubmit} aria-busy={isLoading}>
        <AuthField id="username" label="Username or email" icon={Mail} placeholder="Your username or email" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" autoCapitalize="none" spellCheck={false} required />
        <div>
          <AuthField id="password" label="Password" icon={Lock} type="password" placeholder="Enter your password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required />
          <div className="mt-1 flex justify-end"><Link to="/password-reset" className="focus-ring inline-flex min-h-9 items-center rounded-sm text-xs text-brand underline underline-offset-4">Forgot password?</Link></div>
        </div>
        <Button type="submit" disabled={isLoading} className="h-11 w-full rounded-full">
          {isLoading && <LoaderMark />}
          {isLoading ? "Signing in..." : "Sign in"}
          {!isLoading && <ArrowRight aria-hidden="true" className="h-4 w-4" />}
        </Button>
      </form>
      <p className="mt-5 border-t pt-5 text-center text-sm text-muted-foreground">
        Don&apos;t have an account?{" "}<Link to="/register" className="focus-ring rounded-sm font-medium text-brand underline underline-offset-4">Create one</Link>
      </p>

      <TwoFAModal
        isOpen={Boolean(loginToken)}
        onClose={handle2FAClose}
        onVerify={handle2FAVerify}
        isLoading={isLoading}
      />
    </AuthLayout>
  );
}

LoginPage.propTypes = {
  twoFactorChallenge: PropTypes.shape({
    login_token: PropTypes.string.isRequired,
    next: PropTypes.string,
  }),
};
