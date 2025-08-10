import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ShieldCheck, AlertCircle } from "lucide-react";

export default function TwoFAModal({
  isOpen,
  onClose,
  onVerify,
  isLoading = false,
  error = null,
}) {
  const [otpCode, setOtpCode] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (otpCode.length === 6) {
      onVerify(otpCode);
    }
  };

  const handleClose = () => {
    setOtpCode("");
    onClose();
  };

  const handleCodeChange = (e) => {
    const value = e.target.value.replace(/\D/g, "").slice(0, 6);
    setOtpCode(value);
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px] bg-gray-900/50 border border-gray-800/50 text-slate-100 rounded-xl p-6">
        <DialogHeader className="text-center">
          <div className="flex justify-center mb-4">
            <ShieldCheck className="h-12 w-12 text-purple-400" />
          </div>
          <DialogTitle className="text-2xl font-bold text-slate-100">
            Two-Factor Authentication
          </DialogTitle>
          <DialogDescription className="text-slate-400 mt-2">
            Enter the 6-digit code from your authenticator app to complete your
            login.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="grid gap-4 py-4">
          {error && (
            <div className="p-3 bg-red-900/50 border border-red-800 rounded-lg text-red-300 text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}

          <div className="space-y-2">
            <Label
              htmlFor="2fa-code"
              className="text-slate-200 text-sm font-medium"
            >
              Authentication Code
            </Label>
            <Input
              id="2fa-code"
              type="text"
              placeholder="000000"
              value={otpCode}
              onChange={handleCodeChange}
              maxLength={6}
              className="text-center text-2xl tracking-widest bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500 h-12"
              required
              autoComplete="one-time-code"
            />
            <p className="text-xs text-slate-500 text-center">
              Enter the 6-digit code from your authenticator app
            </p>
          </div>

          <div className="flex gap-3 pt-2">
            <Button
              type="button"
              onClick={handleClose}
              variant="outline"
              className="flex-1 bg-slate-800/50 text-slate-200 hover:bg-slate-700/50 hover:text-slate-100 border-gray-700/50"
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isLoading || otpCode.length !== 6}
              className="flex-1 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "Verifying..." : "Verify"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
