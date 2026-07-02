import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, ArrowRight, Mail, ShieldCheck } from "lucide-react";

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

export default function PasswordResetRequestPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setIsLoading(true);

    try {
      await api.post("users/auth/password/reset/", { email });
      setMessage("Password reset email sent. Please check your inbox.");
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to send password reset email.",
      );
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
          <CardHeader className="px-0 pb-5 text-center">
            <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-2xl border border-[#e5c461]/25 bg-[#e5c461]/10">
              <Mail className="h-5 w-5 text-[#e5c461]" />
            </div>
            <CardTitle className="text-2xl font-semibold tracking-[-0.035em] text-white">
              Reset your password
            </CardTitle>
            <CardDescription className="mt-2 text-sm leading-6 text-slate-400">
              Enter your account email and we will send a secure reset link.
            </CardDescription>
          </CardHeader>

          <CardContent className="px-0">
            <div className="mb-5 rounded-2xl border border-[#e5c461]/15 bg-[#e5c461]/[0.06] p-4">
              <div className="flex items-start gap-3">
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#e5c461]" />
                <p className="text-sm leading-6 text-slate-300">
                  Use this when you cannot access your QuantNest workspace. The
                  link will let you choose a new password.
                </p>
              </div>
            </div>

            {message && (
              <div className="mb-4 rounded-lg border border-green-800 bg-green-900/50 p-3 text-sm text-green-300">
                {message}
              </div>
            )}

            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="space-y-1.5">
                <Label
                  htmlFor="email"
                  className="text-sm font-medium text-slate-200"
                >
                  Email address
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="you@example.com"
                    className="h-11 border-white/10 bg-white/[0.06] pl-10 text-slate-100 placeholder:text-slate-500 focus-visible:ring-[#e5c461]/45"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>

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
                {isLoading ? "Sending..." : "Send reset email"}
                {!isLoading && <ArrowRight className="h-4 w-4" />}
              </Button>
            </form>

            <div className="mt-5 border-t border-white/10 pt-5 text-center text-sm text-slate-400">
              Remember your password?{" "}
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
