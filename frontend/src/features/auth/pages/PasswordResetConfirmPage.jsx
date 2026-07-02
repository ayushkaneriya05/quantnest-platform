/* eslint-disable react/prop-types */
import React, { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Eye, EyeOff, Lock, ShieldCheck } from "lucide-react";

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

export default function PasswordResetConfirmPage() {
  const { uid, token } = useParams();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    new_password1: "",
    new_password2: "",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const getPasswordStrength = (pwd) => {
    let strength = 0;
    if (pwd.length >= 8) strength += 25;
    if (/[A-Z]/.test(pwd)) strength += 25;
    if (/[a-z]/.test(pwd)) strength += 25;
    if (/[0-9]/.test(pwd) || /[^A-Za-z0-9]/.test(pwd)) strength += 25;
    return strength;
  };

  const passwordStrength = getPasswordStrength(formData.new_password1);

  const getStrengthColor = () => {
    if (passwordStrength < 50) return "bg-red-500";
    if (passwordStrength < 75) return "bg-amber-400";
    if (passwordStrength < 100) return "bg-blue-400";
    return "bg-emerald-500";
  };

  const getStrengthText = () => {
    if (formData.new_password1.length === 0) return "";
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
    setError("");

    if (formData.new_password1 !== formData.new_password2) {
      setError("Passwords do not match.");
      return;
    }

    if (formData.new_password1.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setIsLoading(true);
    try {
      await api.post("users/auth/password/reset/confirm/", {
        uid,
        token,
        new_password1: formData.new_password1,
        new_password2: formData.new_password2,
      });

      navigate("/login", {
        state: {
          message:
            "Password reset successful. Please log in with your new password.",
        },
      });
    } catch (err) {
      const errorData = err.response?.data;
      if (errorData) {
        if (typeof errorData === "string") {
          setError(errorData);
        } else {
          const messages = Object.values(errorData).flat().join(" ");
          setError(messages || "Password reset failed.");
        }
      } else {
        setError("Password reset failed. The link may be expired or invalid.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative flex h-screen flex-col overflow-hidden bg-[#050505] text-white">
      <div className="landing-market-animation absolute inset-0 opacity-70" />
      <div className="landing-grid absolute inset-0 opacity-25" />
      <MainHeader />

      <div className="relative flex min-h-0 flex-1 items-center justify-center px-4 py-4">
        <Card className="w-full max-w-md overflow-hidden rounded-3xl border border-white/10 bg-[#0b0d12]/90 p-5 shadow-[0_28px_80px_rgba(0,0,0,0.55)] backdrop-blur-xl">
          <CardHeader className="px-0 pb-4 text-center">
            <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-2xl border border-[#e5c461]/25 bg-[#e5c461]/10">
              <ShieldCheck className="h-5 w-5 text-[#e5c461]" />
            </div>
            <CardTitle className="text-2xl font-semibold tracking-[-0.035em] text-white">
              Set a new password
            </CardTitle>
            <CardDescription className="mt-2 text-sm leading-6 text-slate-400">
              Choose a strong password to protect your QuantNest workspace.
            </CardDescription>
          </CardHeader>

          <CardContent className="px-0">
            <form className="space-y-4" onSubmit={handleSubmit}>
              <PasswordInput
                id="new_password1"
                name="new_password1"
                label="New password"
                value={formData.new_password1}
                onChange={handleChange}
                showPassword={showPassword}
                setShowPassword={setShowPassword}
              />

              {formData.new_password1.length > 0 && (
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                  <div className="mb-2 flex items-center justify-between text-xs">
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
                  <p className="mt-2 text-xs leading-5 text-slate-500">
                    Use at least 8 characters with uppercase, lowercase,
                    number, or symbol.
                  </p>
                </div>
              )}

              <PasswordInput
                id="new_password2"
                name="new_password2"
                label="Confirm new password"
                value={formData.new_password2}
                onChange={handleChange}
                showPassword={showPassword}
                setShowPassword={setShowPassword}
              />

              {error && (
                <div className="rounded-lg border border-red-800 bg-red-900/50 p-3 text-sm text-red-300">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                disabled={isLoading}
                className="h-11 w-full rounded-xl bg-[#e5c461] font-semibold text-black shadow-[0_12px_40px_rgba(229,196,97,0.18)] hover:bg-[#f2da8e] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isLoading ? "Resetting..." : "Reset password"}
                {!isLoading && <ArrowRight className="h-4 w-4" />}
              </Button>
            </form>

            <div className="mt-5 border-t border-white/10 pt-5 text-center text-sm text-slate-400">
              <Link
                to="/login"
                className="font-medium text-[#e5c461] underline hover:text-[#f2da8e]"
              >
                Back to login
              </Link>
            </div>
            <Link
              to="/"
              className="mt-3 flex items-center justify-center gap-2 text-sm text-slate-400 transition-colors hover:text-[#f2da8e]"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to landing page
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function PasswordInput({
  id,
  name,
  label,
  value,
  onChange,
  showPassword,
  setShowPassword,
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id} className="text-sm font-medium text-slate-200">
        {label}
      </Label>
      <div className="relative">
        <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          id={id}
          name={name}
          type={showPassword ? "text" : "password"}
          placeholder="Enter password"
          className="h-11 border-white/10 bg-white/[0.06] pl-10 pr-10 text-slate-100 placeholder:text-slate-500 focus-visible:ring-[#e5c461]/45"
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
