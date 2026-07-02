/* eslint-disable react/prop-types */
import React, { useState } from "react";
import { CheckCircle, Mail, XCircle } from "lucide-react";

import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import api from "@/shared/services/api";

export default function EmailVerificationModal({ isOpen, onClose, email }) {
  const [isResending, setIsResending] = useState(false);
  const [resendMessage, setResendMessage] = useState("");
  const [resendError, setResendError] = useState("");

  const handleResendEmail = async () => {
    setIsResending(true);
    setResendMessage("");
    setResendError("");

    try {
      await api.post("users/auth/registration/resend-email/", { email });
      setResendMessage("Verification email sent. Please check your inbox.");
    } catch (err) {
      setResendError(
        err.response?.data?.detail || "Failed to resend verification email.",
      );
    } finally {
      setIsResending(false);
    }
  };

  const resetAndClose = () => {
    setResendMessage("");
    setResendError("");
    onClose();
  };

  const handleOpenChange = (open) => {
    if (!open) {
      resetAndClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="overflow-hidden rounded-[2rem] border border-white/10 bg-[#08090d]/95 p-0 text-slate-100 shadow-[0_28px_90px_rgba(0,0,0,0.6)] backdrop-blur-2xl sm:max-w-[440px]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(229,196,97,0.18),transparent_36%),radial-gradient(circle_at_bottom_right,rgba(20,184,166,0.12),transparent_34%)]" />
        <div className="relative p-6">
          <DialogHeader className="items-center text-center">
            <div className="mb-2 flex h-14 w-14 items-center justify-center rounded-2xl border border-[#e5c461]/30 bg-[#e5c461]/10 shadow-[0_18px_42px_rgba(229,196,97,0.16)]">
              <Mail className="h-7 w-7 text-[#f0d676]" />
            </div>
            <DialogTitle className="text-2xl font-semibold tracking-[-0.03em] text-white">
              Verify your email
            </DialogTitle>
            <DialogDescription className="max-w-sm pt-1 text-sm leading-6 text-slate-400">
              We sent an activation link to{" "}
              <span className="font-semibold text-slate-100">{email}</span>.
              Open it to unlock your QuantNest workspace.
            </DialogDescription>
          </DialogHeader>

          <div className="mt-6 grid gap-4">
            {resendMessage && (
              <div className="flex items-start gap-2 rounded-2xl border border-emerald-400/25 bg-emerald-400/10 p-3 text-sm text-emerald-200">
                <CheckCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{resendMessage}</span>
              </div>
            )}

            {resendError && (
              <div className="flex items-start gap-2 rounded-2xl border border-red-500/25 bg-red-500/10 p-3 text-sm text-red-200">
                <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{resendError}</span>
              </div>
            )}

            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-sm leading-6 text-slate-400">
              Did not receive the email? Check spam or promotions, then request
              a fresh link. The latest link is the one you should use.
            </div>

            <Button
              onClick={handleResendEmail}
              disabled={isResending}
              variant="outline"
              className="h-11 rounded-full border-white/10 bg-white/[0.04] text-slate-200 hover:bg-white/[0.08] hover:text-white"
            >
              {isResending ? "Sending..." : "Resend verification email"}
            </Button>

            <Button
              onClick={resetAndClose}
              className="h-11 rounded-full bg-[#e5c461] text-sm font-semibold text-black shadow-[0_16px_34px_rgba(229,196,97,0.26)] hover:bg-[#f0d676]"
            >
              I will verify later
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
