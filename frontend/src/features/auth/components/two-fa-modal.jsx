import { useState } from "react";
import PropTypes from "prop-types";
import { KeyRound, ShieldCheck } from "lucide-react";

import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";

export default function TwoFAModal({
  isOpen,
  onClose,
  onVerify,
  isLoading = false,
}) {
  const [token, setToken] = useState("");
  const [useBackupCode, setUseBackupCode] = useState(false);

  const resetAndClose = () => {
    setToken("");
    setUseBackupCode(false);
    onClose();
  };

  const handleOpenChange = (open) => {
    if (!open) {
      resetAndClose();
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (token.trim() !== "") {
      onVerify(token);
    }
  };

  const handleToggleMode = () => {
    setUseBackupCode((current) => !current);
    setToken("");
  };

  const handleTokenChange = (event) => {
    const value = event.target.value;

    if (useBackupCode) {
      setToken(value.trim().toUpperCase());
      return;
    }

    setToken(value.replace(/\D/g, "").slice(0, 6));
  };

  const isSubmitDisabled =
    isLoading || (useBackupCode ? token.length < 8 : token.length !== 6);

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent onPointerDownOutside={(event) => event.preventDefault()} className="overflow-y-auto rounded-3xl border-border bg-card p-0 text-foreground shadow-xl sm:max-w-[430px] sm:rounded-3xl sm:p-0">
        <div className="p-5 sm:p-7">
          <DialogHeader className="items-center text-center sm:text-center">
            <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-2xl border border-brand/20 bg-brand/10">
              {useBackupCode ? (
                <KeyRound aria-hidden="true" className="h-6 w-6 text-brand" />
              ) : (
                <ShieldCheck aria-hidden="true" className="h-6 w-6 text-brand" />
              )}
            </div>
            <DialogTitle className="text-2xl font-semibold tracking-[-0.03em] text-foreground">
              {useBackupCode ? "Use a backup code" : "Verify your sign-in"}
            </DialogTitle>
            <DialogDescription className="max-w-sm pt-1 text-sm leading-6 text-muted-foreground">
              {useBackupCode
                ? "Enter an unused backup code from your security settings. Each code can be used once."
                : "Enter the current 6 digit code from the authenticator app linked to your account."}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="mt-6 grid gap-4" aria-busy={isLoading}>

            <div className="space-y-2">
              <Label
                htmlFor="2fa-token"
                className="block text-center text-xs font-semibold uppercase tracking-[0.22em] text-brand"
              >
                {useBackupCode ? "Backup code" : "Authenticator code"}
              </Label>
              <Input
                id="2fa-token"
                type="text"
                inputMode="numeric"
                placeholder={useBackupCode ? "1234-5678" : "000000"}
                value={token}
                onChange={handleTokenChange}
                maxLength={useBackupCode ? 16 : 6}
                className="h-14 rounded-xl border-input bg-background text-center font-mono text-xl tracking-[0.14em] sm:text-2xl sm:tracking-[0.2em]"
                required
                autoComplete="one-time-code"
              />
              <p className="text-center text-xs leading-5 text-muted-foreground">
                {useBackupCode
                  ? "Your backup code has 8 digits, usually shown as 1234-5678."
                  : "If a code expires, enter the next code shown in your app."}
              </p>
            </div>

            <button
              type="button"
              onClick={handleToggleMode}
              className="focus-ring min-h-11 justify-self-center rounded-sm text-sm font-medium text-brand transition hover:text-foreground"
            >
              {useBackupCode
                ? "Use authenticator app instead"
                : "Use a backup code instead"}
            </button>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <Button
                type="button"
                onClick={resetAndClose}
                variant="outline"
                className="h-11 rounded-full"
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isSubmitDisabled}
                className="h-11 rounded-full"
              >
                {isLoading ? "Verifying..." : "Verify"}
              </Button>
            </div>
          </form>
        </div>
      </DialogContent>
    </Dialog>
  );
}

TwoFAModal.propTypes = { isOpen: PropTypes.bool.isRequired, onClose: PropTypes.func.isRequired, onVerify: PropTypes.func.isRequired, isLoading: PropTypes.bool };
