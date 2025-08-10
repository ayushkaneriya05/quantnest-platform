import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import api from "@/services/api";
import {
  loginSuccess,
  set2FARequired,
  setLoading,
  fetchUserProfile,
} from "@/store/authSlice";
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
import { Mail, Lock } from "lucide-react";
import TwoFAModal from "@/components/auth/two-fa-modal";
import GoogleLoginButton, {
  GoogleLoginFallback,
} from "@/components/auth/GoogleLoginButton";
import MainHeader from "@/components/layout/main-header";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [userId, setUserId] = useState("");
  const [error, setError] = useState("");
  const [twoFAError, setTwoFAError] = useState("");
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const { is2FARequired, isLoading } = useSelector((state) => state.auth);

  // Get the page they were trying to visit, or default to dashboard
  const from = location.state?.from?.pathname || "/dashboard";

  // Show success message from registration or password reset
  const successMessage = location.state?.message;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    dispatch(setLoading(true));

    try {
      const payload = { username, password };
      const response = await api.post("/users/auth/login/", payload);

      if (
        response.status === 200 &&
        response.data.access &&
        response.data.refresh
      ) {
        dispatch(loginSuccess(response.data));
        await dispatch(fetchUserProfile());
        navigate(from, { replace: true });
      } else if (response.status === 200 && response.data.is_2fa_required) {
        setUserId(response.data.user_id);
        dispatch(set2FARequired(true));
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
      const payload = {
        username,
        password,
        otp_token: otpToken,
        user_id: userId,
      };
      const response = await api.post("/users/auth/verify-2fa/", payload);

      if (
        response.status === 200 &&
        response.data.access &&
        response.data.refresh
      ) {
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
    setUserId("");
  };

  const handleGoogleError = (errorMessage) => {
    setError(errorMessage);
  };

  const googleClientId = import.meta.env.VITE_REACT_APP_GOOGLE_CLIENT_ID;

  return (
    <div className="flex flex-col min-h-screen bg-black">
      <MainHeader />
      <div className="flex flex-1 items-center justify-center container-padding py-6 sm:py-8 md:py-12 lg:py-16">
        <Card className="w-full max-w-md bg-gray-900/50 border border-gray-800/50 shadow-lg rounded-xl p-4 sm:p-6">
          <CardHeader className="text-center pb-6">
            <CardTitle className="text-2xl sm:text-3xl font-bold text-slate-100">
              Welcome Back to QuantNest
            </CardTitle>
            <CardDescription className="text-slate-400 mt-2">
              Sign in to your account to continue trading.
            </CardDescription>
          </CardHeader>
          <CardContent className="content-spacing px-0">
            {/* Google login section */}
            <div className="space-y-3 sm:space-y-4">
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

            <div className="relative flex items-center my-6">
              <div className="flex-grow border-t border-gray-700" />
              <span className="mx-4 flex-shrink text-slate-400 text-sm">
                OR
              </span>
              <div className="flex-grow border-t border-gray-700" />
            </div>

            {successMessage && (
              <div className="mb-4 p-3 bg-green-900/50 border border-green-800 rounded-lg text-green-300 text-sm">
                {successMessage}
              </div>
            )}

            <form className="text-spacing" onSubmit={handleSubmit}>
              <div className="text-spacing-sm">
                <Label
                  htmlFor="username"
                  className="text-slate-200 text-sm font-medium"
                >
                  Username or Email
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="username"
                    name="username"
                    type="text"
                    placeholder="username or email"
                    className="pl-10 bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 h-11"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    autoComplete="username"
                  />
                </div>
              </div>
              <div className="text-spacing-sm">
                <Label
                  htmlFor="password"
                  className="text-slate-200 text-sm font-medium"
                >
                  Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="password"
                    name="password"
                    type="password"
                    placeholder="••••••••"
                    className="pl-10 bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 h-11"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                  />
                </div>
                <div className="text-right mt-2">
                  <Link
                    to="/password-reset"
                    className="text-sm text-indigo-400 hover:text-indigo-300 underline"
                  >
                    Forgot Password?
                  </Link>
                </div>
              </div>

              {error && (
                <div className="mb-4 p-3 bg-red-900/50 border border-red-800 rounded-lg text-red-300 text-sm">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)] h-11 mt-6 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? "Signing In..." : "Log In"}
              </Button>
            </form>
            <div className="text-center text-sm text-slate-400 pt-4 border-t border-gray-800/50">
              Don't have an account?{" "}
              <Link
                to="/register"
                className="underline text-indigo-400 hover:text-indigo-300 font-medium"
              >
                Sign Up
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
