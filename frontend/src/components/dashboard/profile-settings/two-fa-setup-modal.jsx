import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { QrCode, Copy, CheckCircle, Loader2, AlertCircle } from "lucide-react";
import api from "@/services/api";

export default function TwoFASetupModal({ isOpen, onClose, onSetupComplete }) {
  const [step, setStep] = useState(1);
  const [verificationCode, setVerificationCode] = useState("");
  const [qrCodeUrl, setQrCodeUrl] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState("");

  // Generate 2FA setup data when modal opens
  useEffect(() => {
    if (isOpen && step === 1) {
      generateTwoFASetup();
    }
  }, [isOpen, step]);

  const generateTwoFASetup = async () => {
    setIsLoading(true);
    setError("");

    try {
      const response = await api.get("/users/2fa/create/");
      const svgBase64 = btoa(response.data.qr_code);
      setQrCodeUrl(`data:image/svg+xml;base64,${svgBase64}`);
      // setQrCodeUrl(response.data.qr_code)
      setSecretKey(response.data.secret_key);
    } catch (err) {
      console.error("Failed to generate 2FA setup:", err);
      setError("Failed to generate 2FA setup. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleNext = () => {
    if (secretKey) {
      setStep(2);
    }
  };

  const handleVerify = async () => {
    if (verificationCode.length !== 6) {
      setError("Please enter a 6-digit verification code");
      return;
    }

    setIsVerifying(true);
    setError("");

    try {
      await api.post("/users/2fa/verify/", {
        token: verificationCode,
      });

      // Setup completed successfully
      onSetupComplete();
      handleClose();
    } catch (err) {
      console.error("2FA verification failed:", err);
      setError(
        err.response?.data?.detail ||
          "Invalid verification code. Please try again."
      );
    } finally {
      setIsVerifying(false);
    }
  };

  const handleClose = () => {
    onClose();
    setStep(1);
    setVerificationCode("");
    setQrCodeUrl("");
    setSecretKey("");
    setError("");
  };

  const handleCopySecret = async () => {
    try {
      await navigator.clipboard.writeText(secretKey);
      // Optional: Show a temporary success message
    } catch (err) {
      console.error("Failed to copy secret key:", err);
    }
  };

  const handleCodeChange = (e) => {
    const value = e.target.value.replace(/\D/g, "").slice(0, 6);
    setVerificationCode(value);
    if (error) {
      setError("");
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[475px] bg-gray-900/50 border border-gray-800/50 text-slate-100 rounded-xl p-6">
        <DialogHeader className="text-center">
          <div className="flex justify-center mb-4">
            <QrCode className="h-12 w-12 text-indigo-400" />
          </div>
          <DialogTitle className="text-2xl font-bold text-slate-100">
            {step === 1
              ? "Set Up Two-Factor Authentication"
              : "Verify Your 2FA Setup"}
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            {step === 1
              ? "Scan the QR code with your authenticator app (Google Authenticator, Authy, etc.) or enter the secret key manually."
              : "Enter the 6-digit code from your authenticator app to complete setup."}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {error && (
            <div className="p-3 bg-red-900/50 border border-red-800 rounded-lg text-red-300 text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}

          {step === 1 ? (
            <>
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
                </div>
              ) : (
                <>
                  <div className="flex justify-center">
                    {qrCodeUrl ? (
                      <img
                        src={qrCodeUrl}
                        alt="QR Code for 2FA"
                        width={200}
                        height={200}
                        className="rounded-lg border border-gray-700 bg-white p-2"
                      />
                    ) : (
                      <div className="w-[200px] h-[200px] rounded-lg border border-gray-700 bg-gray-800/50 flex items-center justify-center">
                        <span className="text-slate-400">QR Code</span>
                      </div>
                    )}
                  </div>

                  {secretKey && (
                    <div className="space-y-2 text-center">
                      <Label htmlFor="secret-key" className="text-slate-200">
                        Secret Key
                      </Label>
                      <div className="relative flex items-center">
                        <Input
                          id="secret-key"
                          type="text"
                          value={secretKey}
                          readOnly
                          className="flex-1 bg-gray-800/50 border-gray-700/50 text-slate-100 font-mono text-center text-sm"
                        />
                        <Button
                          variant="ghost"
                          size="icon"
                          className="absolute right-2 bg-gray-700/50 hover:bg-gray-600/50 text-slate-300"
                          onClick={handleCopySecret}
                          title="Copy Secret Key"
                          type="button"
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">
                        Copy this key if you cannot scan the QR code.
                      </p>
                    </div>
                  )}
                </>
              )}
            </>
          ) : (
            <div className="space-y-2">
              <Label
                htmlFor="2fa-code-verify"
                className="text-slate-200 text-center block"
              >
                Verification Code
              </Label>
              <Input
                id="2fa-code-verify"
                type="text"
                placeholder="000000"
                maxLength={6}
                value={verificationCode}
                onChange={handleCodeChange}
                className="text-center text-2xl tracking-widest bg-gray-800/50 border-gray-700/50 text-slate-100 placeholder:text-slate-500"
                required
                autoComplete="one-time-code"
              />
              <p className="text-xs text-slate-500 text-center">
                Enter the 6-digit code from your authenticator app
              </p>
            </div>
          )}
        </div>

        <DialogFooter className="flex gap-3">
          <Button
            variant="outline"
            onClick={handleClose}
            className="flex-1 bg-gray-800/50 border-gray-700/50 text-slate-200 hover:bg-gray-700/50"
          >
            Cancel
          </Button>

          {step === 1 ? (
            <Button
              onClick={handleNext}
              disabled={isLoading || !secretKey}
              className="flex-1 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Loading...
                </>
              ) : (
                "Next"
              )}
            </Button>
          ) : (
            <Button
              onClick={handleVerify}
              disabled={isVerifying || verificationCode.length !== 6}
              className="flex-1 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isVerifying ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Verifying...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Verify & Enable
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
