/* eslint-disable react/prop-types */
import React, { useState } from "react";
import { AlertCircle, KeyRound, ShieldCheck } from "lucide-react";

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
  error = null,
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
      <DialogContent className="overflow-hidden rounded-[2rem] border border-white/10 bg-[#08090d]/95 p-0 text-slate-100 shadow-[0_28px_90px_rgba(0,0,0,0.6)] backdrop-blur-2xl sm:max-w-[430px]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(229,196,97,0.18),transparent_36%),radial-gradient(circle_at_bottom_right,rgba(124,58,237,0.16),transparent_34%)]" />
        <div className="relative p-6">
          <DialogHeader className="items-center text-center">
            <div className="mb-2 flex h-14 w-14 items-center justify-center rounded-2xl border border-[#e5c461]/30 bg-[#e5c461]/10 shadow-[0_18px_42px_rgba(229,196,97,0.16)]">
              {useBackupCode ? (
                <KeyRound className="h-7 w-7 text-[#f0d676]" />
              ) : (
                <ShieldCheck className="h-7 w-7 text-[#f0d676]" />
              )}
            </div>
            <DialogTitle className="text-2xl font-semibold tracking-[-0.03em] text-white">
              {useBackupCode ? "Use backup code" : "Secure your sign in"}
            </DialogTitle>
            <DialogDescription className="max-w-sm pt-1 text-sm leading-6 text-slate-400">
              {useBackupCode
                ? "Enter one of your saved backup codes to continue into QuantNest."
                : "Enter the 6 digit code from your authenticator app to finish signing in."}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="mt-6 grid gap-4">
            {error && (
              <div className="flex items-start gap-2 rounded-2xl border border-red-500/25 bg-red-500/10 p-3 text-sm text-red-200">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="space-y-2">
              <Label
                htmlFor="2fa-token"
                className="block text-center text-xs font-semibold uppercase tracking-[0.22em] text-[#e5c461]"
              >
                {useBackupCode ? "Backup code" : "Authenticator code"}
              </Label>
              <Input
                id="2fa-token"
                type="text"
                placeholder={useBackupCode ? "A1B2C3D4" : "000000"}
                value={token}
                onChange={handleTokenChange}
                maxLength={useBackupCode ? 16 : 6}
                className="h-14 rounded-2xl border-white/10 bg-white/[0.06] text-center font-mono text-2xl tracking-[0.32em] text-white placeholder:text-slate-600 focus-visible:ring-[#e5c461]/45"
                required
                autoComplete="one-time-code"
              />
              <p className="text-center text-xs text-slate-500">
                {useBackupCode
                  ? "Use an unused backup code from your security setup."
                  : "Codes refresh often, so enter the latest one."}
              </p>
            </div>

            <button
              type="button"
              onClick={handleToggleMode}
              className="justify-self-center text-sm font-medium text-[#f0d676] transition hover:text-white focus:outline-none"
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
                className="h-11 rounded-full border-white/10 bg-white/[0.04] text-slate-200 hover:bg-white/[0.08] hover:text-white"
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isSubmitDisabled}
                className="h-11 rounded-full bg-[#e5c461] text-sm font-semibold text-black shadow-[0_16px_34px_rgba(229,196,97,0.26)] hover:bg-[#f0d676] disabled:cursor-not-allowed disabled:opacity-50"
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
