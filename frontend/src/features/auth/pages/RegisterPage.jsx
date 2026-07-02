/* eslint-disable react/prop-types */
import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Eye,
  EyeOff,
  Lock,
  Mail,
  User,
} from "lucide-react";

import EmailVerificationModal from "@/features/auth/components/email-verification-modal";
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
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import api from "@/shared/services/api";

const workflowSteps = [
  "AI research",
  "Backtest",
  "Paper trade",
  "Go live",
];

export default function RegisterPage() {
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState("");
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    username: "",
    email: "",
    password1: "",
    password2: "",
  });
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [agreeToTerms, setAgreeToTerms] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  const getPasswordStrength = (pwd) => {
    let strength = 0;
    if (pwd.length >= 8) strength += 25;
    if (/[A-Z]/.test(pwd)) strength += 25;
    if (/[a-z]/.test(pwd)) strength += 25;
    if (/[0-9]/.test(pwd) || /[^A-Za-z0-9]/.test(pwd)) strength += 25;
    return strength;
  };

  const passwordStrength = getPasswordStrength(formData.password1);

  const getStrengthColor = () => {
    if (passwordStrength < 50) return "bg-red-500";
    if (passwordStrength < 75) return "bg-amber-400";
    if (passwordStrength < 100) return "bg-blue-400";
    return "bg-emerald-500";
  };

  const getStrengthText = () => {
    if (formData.password1.length === 0) return "";
    if (passwordStrength < 50) return "Weak";
    if (passwordStrength < 75) return "Fair";
    if (passwordStrength < 100) return "Good";
    return "Strong";
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!agreeToTerms) {
      setError({
        detail: "You must agree to the Terms of Service and Privacy Policy.",
      });
      return;
    }

    if (formData.password1 !== formData.password2) {
      setError({ detail: "Passwords do not match." });
      return;
    }

    if (formData.password1.length < 8) {
      setError({ detail: "Password must be at least 8 characters long." });
      return;
    }

    setIsLoading(true);
    try {
      const { firstName, lastName, username, email, password1, password2 } =
        formData;
      await api.post("users/auth/registration/", {
        first_name: firstName,
        last_name: lastName,
        username,
        email,
        password1,
        password2,
      });

      setRegisteredEmail(email);
      setIsEmailModalOpen(true);
    } catch (err) {
      const errorData = err.response?.data;
      if (errorData) {
        if (typeof errorData === "string") {
          setError({ detail: errorData });
        } else {
          const messages = Object.values(errorData).flat().join(" ");
          setError({
            detail: messages || "An unknown registration error occurred.",
          });
        }
      } else {
        setError({ detail: "An unknown registration error occurred." });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleError = (errorMessage) => {
    setError({ detail: errorMessage });
  };

  const handleEmailVerificationComplete = () => {
    setIsEmailModalOpen(false);
    navigate("/login", {
      state: {
        message:
          "Registration successful! Please check your email to verify your account before logging in.",
      },
    });
  };

  const googleClientId = import.meta.env.VITE_REACT_APP_GOOGLE_CLIENT_ID;

  return (
    <div className="relative flex min-h-screen flex-col overflow-y-auto bg-[#050505] text-white lg:h-screen lg:overflow-hidden">
      <div className="landing-market-animation absolute inset-0 opacity-70" />
      <div className="landing-grid absolute inset-0 opacity-25" />
      <MainHeader authPage="register" />

      <div className="relative flex min-h-0 flex-1 items-start justify-center px-4 py-4 sm:items-center lg:py-3">
        <Card className="grid w-full max-w-4xl overflow-hidden rounded-3xl border border-white/10 bg-[#0b0d12]/90 shadow-[0_28px_80px_rgba(0,0,0,0.55)] backdrop-blur-xl lg:grid-cols-[0.82fr_1.18fr]">
          <div className="relative overflow-hidden border-b border-white/10 bg-[#111318]/80 p-5 lg:border-b-0 lg:border-r lg:p-6">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(229,196,97,0.13),transparent_40%)]" />
            <div className="relative flex h-full flex-col justify-center gap-5">
              <CardHeader className="px-0 pb-0 pt-0">
                <img src="/favicon.png" alt="QuantNest" className="mb-3 h-12 w-12 sm:h-14 sm:w-14 self-center" />
                <CardTitle className="max-w-sm text-[1.7rem] font-semibold leading-tight tracking-[-0.04em] text-white">
                  Create your QuantNest workspace
                </CardTitle>
                <CardDescription className="mt-2 max-w-sm text-sm leading-6 text-slate-400">
                  Create one account for AI research, strategy testing, paper
                  trading, and live deployment.
                </CardDescription>
              </CardHeader>

              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-2">
                {workflowSteps.map((step, index) => (
                  <div
                    key={step}
                    className="rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-2"
                  >
                    <div className="text-[0.65rem] font-semibold uppercase tracking-[0.18em] text-[#e5c461]">
                      0{index + 1}
                    </div>
                    <div className="mt-0.5 text-sm font-medium text-slate-200">
                      {step}
                    </div>
                  </div>
                ))}
              </div>

              <div className="rounded-2xl border border-[#e5c461]/15 bg-[#e5c461]/[0.06] p-3 text-xs leading-5 text-slate-300">
                Start safely in paper trading, then connect brokers only when
                your strategy and risk rules are ready.
              </div>
            </div>
          </div>

          <CardContent className="p-5 lg:p-6">
            <div className="mb-3">
              {googleClientId ? (
                <GoogleLoginButton
                  onError={handleGoogleError}
                  isLoading={isLoading}
                  type="registration"
                />
              ) : (
                <GoogleLoginFallback type="registration" />
              )}
            </div>

            <div className="relative mb-3 flex items-center">
              <div className="flex-grow border-t border-white/10" />
              <span className="mx-3 flex-shrink text-xs text-slate-500">
                OR
              </span>
              <div className="flex-grow border-t border-white/10" />
            </div>

            <form className="space-y-2.5" onSubmit={handleSubmit}>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field
                  id="firstName"
                  label="First name"
                  icon={User}
                  placeholder="John"
                  value={formData.firstName}
                  onChange={handleChange}
                />
                <Field
                  id="lastName"
                  label="Last name"
                  icon={User}
                  placeholder="Doe"
                  value={formData.lastName}
                  onChange={handleChange}
                />
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field
                  id="username"
                  label="Username"
                  icon={User}
                  placeholder="quant_trader"
                  value={formData.username}
                  onChange={handleChange}
                />
                <Field
                  id="email"
                  label="Email"
                  icon={Mail}
                  type="email"
                  placeholder="you@example.com"
                  value={formData.email}
                  onChange={handleChange}
                />
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <PasswordField
                  id="password"
                  name="password1"
                  label="Password"
                  value={formData.password1}
                  onChange={handleChange}
                  showPassword={showPassword}
                  setShowPassword={setShowPassword}
                />
                <PasswordField
                  id="confirmPassword"
                  name="password2"
                  label="Confirm password"
                  value={formData.password2}
                  onChange={handleChange}
                  showPassword={showPassword}
                  setShowPassword={setShowPassword}
                />
              </div>

              {formData.password1.length > 0 && (
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-2">
                  <div className="mb-1.5 flex items-center justify-between text-xs">
                    <span className="text-slate-400">Password strength</span>
                    <span
                      className={`font-medium ${
                        passwordStrength < 50
                          ? "text-red-400"
                          : passwordStrength < 75
                            ? "text-amber-400"
                            : passwordStrength < 100
                              ? "text-blue-400"
                              : "text-emerald-400"
                      }`}
                    >
                      {getStrengthText()}
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-800">
                    <div
                      className={`h-full transition-all duration-300 ${getStrengthColor()}`}
                      style={{ width: `${passwordStrength}%` }}
                    />
                  </div>
                  <p className="mt-1 text-xs leading-4 text-slate-500">
                    Use 8+ characters with uppercase, lowercase, number, or
                    symbol.
                  </p>
                </div>
              )}

              <div className="flex items-start gap-3">
                <Checkbox
                  id="terms"
                  checked={agreeToTerms}
                  onCheckedChange={(value) => setAgreeToTerms(Boolean(value))}
                  className="mt-0.5 border-gray-600 data-[state=checked]:bg-[#e5c461] data-[state=checked]:text-black"
                />
                <Label
                  htmlFor="terms"
                  className="text-xs leading-5 text-slate-300"
                >
                  I agree to the{" "}
                  <Link
                    to="/terms-of-service"
                    target="_blank"
                    className="text-[#e5c461] underline hover:text-[#f2da8e]"
                  >
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link
                    to="/privacy-policy"
                    target="_blank"
                    className="text-[#e5c461] underline hover:text-[#f2da8e]"
                  >
                    Privacy Policy
                  </Link>
                  .
                </Label>
              </div>

              {error && (
                <div className="rounded-lg border border-red-800 bg-red-900/50 p-2.5 text-sm text-red-300">
                  {error.detail}
                </div>
              )}

              <Button
                type="submit"
                disabled={isLoading || !agreeToTerms}
                className="mt-1 h-10 w-full rounded-xl bg-[#e5c461] font-semibold text-black shadow-[0_12px_40px_rgba(229,196,97,0.18)] hover:bg-[#f2da8e] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isLoading ? "Creating account..." : "Create account"}
                {!isLoading && <ArrowRight className="h-4 w-4" />}
              </Button>
            </form>

            <div className="mt-3 border-t border-white/10 pt-3 text-center text-sm text-slate-400">
              Already have an account?{" "}
              <Link
                to="/login"
                className="font-medium text-[#e5c461] underline hover:text-[#f2da8e]"
              >
                Log in
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

      <EmailVerificationModal
        isOpen={isEmailModalOpen}
        onClose={handleEmailVerificationComplete}
        email={registeredEmail}
      />
    </div>
  );
}

function Field({
  id,
  label,
  icon: Icon,
  type = "text",
  placeholder,
  value,
  onChange,
}) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id} className="text-xs font-medium text-slate-200">
        {label}
      </Label>
      <div className="relative">
        <Icon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          id={id}
          name={id}
          type={type}
          placeholder={placeholder}
          className="h-10 border-white/10 bg-white/[0.06] pl-10 text-slate-100 placeholder:text-slate-500 focus-visible:ring-[#e5c461]/45"
          value={value}
          onChange={onChange}
          required
        />
      </div>
    </div>
  );
}

function PasswordField({
  id,
  name,
  label,
  value,
  onChange,
  showPassword,
  setShowPassword,
}) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id} className="text-xs font-medium text-slate-200">
        {label}
      </Label>
      <div className="relative">
        <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          id={id}
          name={name}
          type={showPassword ? "text" : "password"}
          placeholder="Enter password"
          className="h-10 border-white/10 bg-white/[0.06] pl-10 pr-10 text-slate-100 placeholder:text-slate-500 focus-visible:ring-[#e5c461]/45"
          value={value}
          onChange={onChange}
          required
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 transition-colors hover:text-slate-200 focus:outline-none"
          aria-label={showPassword ? "Hide password" : "Show password"}
        >
          {showPassword ? (
            <EyeOff className="h-4 w-4" />
          ) : (
            <Eye className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}
