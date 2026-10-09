import { getApiErrorMessage } from "@/shared/utils/apiErrors";
/* eslint-disable react/prop-types */
import { useState } from "react";
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
      const { data } = await api.post("users/auth/registration/resend-email/", { email });
      setResendMessage(data.message);
    } catch (err) {
      setResendError(
        getApiErrorMessage(err, "Failed to resend verification email."),
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
      <DialogContent className="overflow-y-auto rounded-[2rem] border border-border bg-card/95 p-0 text-foreground shadow-card backdrop-blur-2xl sm:max-w-[440px]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(229,196,97,0.18),transparent_36%),radial-gradient(circle_at_bottom_right,rgba(20,184,166,0.12),transparent_34%)]" />
        <div className="relative p-6">
          <DialogHeader className="items-center text-center">
            <div className="mb-2 flex h-14 w-14 items-center justify-center rounded-2xl border border-[#e5c461]/30 bg-[#e5c461]/10 shadow-[0_18px_42px_rgba(229,196,97,0.16)]">
              <Mail className="h-7 w-7 text-brand" />
            </div>
            <DialogTitle className="text-2xl font-semibold tracking-[-0.03em] text-foreground">
              Verify your email
            </DialogTitle>
            <DialogDescription className="max-w-sm pt-1 text-sm leading-6 text-muted-foreground">
              We sent an activation link to{" "}
              <span className="font-semibold text-foreground">{email}</span>.
              Open it to unlock your QuantNest workspace.
            </DialogDescription>
          </DialogHeader>

          <div className="mt-6 grid gap-4">
            {resendMessage && (
              <div className="flex items-start gap-2 rounded-2xl border border-emerald-400/25 bg-emerald-400/10 p-3 text-sm text-emerald-700 dark:text-emerald-200">
                <CheckCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{resendMessage}</span>
              </div>
            )}

            {resendError && (
              <div className="flex items-start gap-2 rounded-2xl border border-red-500/25 bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-200">
                <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{resendError}</span>
              </div>
            )}

            <div className="rounded-2xl border border-border bg-muted/50 p-4 text-sm leading-6 text-muted-foreground">
              Did not receive the email? Check spam or promotions, then request
              a fresh link. The latest link is the one you should use.
            </div>

            <Button
              onClick={handleResendEmail}
              disabled={isResending}
              variant="outline"
              className="h-11 rounded-full border-border bg-muted/50 text-foreground hover:bg-muted/50 hover:text-foreground"
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
