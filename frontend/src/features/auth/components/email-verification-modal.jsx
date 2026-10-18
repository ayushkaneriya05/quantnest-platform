import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useState } from "react";
import PropTypes from "prop-types";
import { Mail } from "lucide-react";
import { useNotifications } from "@/shared/hooks/useNotifications";

import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import api from "@/shared/services/api";

export default function EmailVerificationModal({ isOpen, onClose, email, canContinue }) {
  const { notify } = useNotifications();
  const [isResending, setIsResending] = useState(false);

  const handleResendEmail = async () => {
    setIsResending(true);

    try {
      const { data } = await api.post("users/auth/registration/resend-email/", { email });
      notify.success(data.message || "Verification email requested. Check your inbox.");
    } catch (err) {
      notify.error(
        getApiErrorMessage(err, "Failed to resend verification email."),
      );
    } finally {
      setIsResending(false);
    }
  };

  const handleOpenChange = (open) => {
    if (!open) {
      onClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="overflow-y-auto rounded-3xl border-border bg-card p-0 text-foreground shadow-xl sm:max-w-[440px] sm:rounded-3xl sm:p-0">
        <div className="p-5 sm:p-7">
          <DialogHeader className="items-center text-center sm:text-center">
            <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-2xl border border-brand/20 bg-brand/10">
              <Mail aria-hidden="true" className="h-6 w-6 text-brand" />
            </div>
            <DialogTitle className="text-2xl font-semibold tracking-[-0.03em] text-foreground">
              Verify your email
            </DialogTitle>
            <DialogDescription className="max-w-sm pt-1 text-sm leading-6 text-muted-foreground">
              Check{" "}
              <span className="break-all font-semibold text-foreground">{email}</span>{" "}
              for a verification link.{" "}
              {canContinue
                ? "You can open your workspace now and verify your email later."
                : "Verify your email, then sign in to continue."}
            </DialogDescription>
          </DialogHeader>

          <div className="mt-6 grid gap-4">

            <div className="rounded-2xl border border-border bg-muted/50 p-4 text-sm leading-6 text-muted-foreground">
              Check your spam or promotions folder. If no verification email
              arrives, request another link below.
            </div>

            <Button
              onClick={handleResendEmail}
              disabled={isResending}
              variant="outline"
              className="h-11 rounded-full"
            >
              {isResending ? "Sending..." : "Resend verification email"}
            </Button>

            <Button
              onClick={onClose}
              className="h-11 rounded-full"
            >
              {canContinue ? "Open workspace" : "Back to sign in"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

EmailVerificationModal.propTypes = { isOpen: PropTypes.bool.isRequired, onClose: PropTypes.func.isRequired, email: PropTypes.string.isRequired, canContinue: PropTypes.bool };
