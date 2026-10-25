import { GlobalLoader, LoaderMark } from '@/shared/components/ui/global-loader';
import { formatDateTime } from "@/shared/utils/formatters";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useState, useEffect, useCallback, useRef } from "react";
import PropTypes from "prop-types";
import { Button } from "@/shared/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/shared/components/ui/dialog";
import { Input } from "@/shared/components/ui/input";
import { Label } from "@/shared/components/ui/label";
import { QrCode, Copy, CheckCircle, AlertCircle, Download } from "lucide-react";
import api from "@/shared/services/api";
import { useNotifications } from "@/shared/hooks/useNotifications";

TwoFASetupModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSetupComplete: PropTypes.func.isRequired,
};

export default function TwoFASetupModal({ isOpen, onClose, onSetupComplete }) {
  const { notify } = useNotifications();
  const [step, setStep] = useState(1);
  const [verificationCode, setVerificationCode] = useState("");
  const [qrCodeUrl, setQrCodeUrl] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [backupCodes, setBackupCodes] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState("");
  const setupRequest = useRef(0), verificationLock = useRef(false);

  const generateTwoFASetup = useCallback(async () => {
    const request = ++setupRequest.current;
    setIsLoading(true);
    setError("");

    try {
      const response = await api.post("/users/2fa/create/");
      if (request !== setupRequest.current) return;
      const svgBase64 = btoa(response.data.qr_code);
      setQrCodeUrl(`data:image/svg+xml;base64,${svgBase64}`);
      setSecretKey(response.data.secret_key);
    } catch (err) {
      if (request === setupRequest.current) setError(getApiErrorMessage(err, "Failed to generate 2FA setup. Please try again."));
    } finally {
      if (request === setupRequest.current) setIsLoading(false);
    }
  }, []);
  useEffect(() => {
    const requests = setupRequest;
    setStep(1); setVerificationCode(''); setQrCodeUrl(''); setSecretKey(''); setBackupCodes([]); setError('');
    if (isOpen) generateTwoFASetup();
    return () => { requests.current++; };
  }, [isOpen, generateTwoFASetup]);

  const handleNext = () => {
    if (secretKey) {
      setStep(2);
    }
  };

  const handleVerify = async () => {
    if (verificationLock.current) return;
    if (verificationCode.length !== 6) {
      setError("Please enter a 6-digit verification code");
      return;
    }

    verificationLock.current = true;
    setIsVerifying(true);
    setError("");

    try {
      const response = await api.post("/users/2fa/verify/", {
        token: verificationCode,
      });

      // Backup codes are returned in the verification response
      setBackupCodes(response.data.backup_codes || []);
      
      setStep(3); // Move to backup codes step
    } catch (err) {
      console.error("2FA verification failed:", err);
      notify.error(getApiErrorMessage(err, "Invalid verification code. Please try again."));
    } finally {
      verificationLock.current = false;
      setIsVerifying(false);
    }
  };

  const handleFinish = () => {
    onSetupComplete();
    onClose();
  };

  const handleClose = () => {
    // Only allow explicit close on step 1/2 or finish on step 3
    if (step === 3 || verificationLock.current) return;
    
    onClose();
    setStep(1);
    setVerificationCode("");
    setQrCodeUrl("");
    setSecretKey("");
    setBackupCodes([]);
    setError("");
  };

  const handleCopySecret = async () => {
    try {
      await navigator.clipboard.writeText(secretKey);
      notify.success('Secret key copied. Keep it private.');
    } catch (err) {
      notify.error('Clipboard access is unavailable. Select the secret key and copy it manually.');
    }
  };

  const handleCopyBackupCodes = async () => {
    try {
      await navigator.clipboard.writeText(backupCodes.join('\n'));
      notify.success('Recovery codes copied. Save them in a secure place.');
    } catch (err) {
      notify.error('Clipboard access is unavailable. Download your recovery codes instead.');
    }
  };

  const handleDownloadBackupCodes = () => {
    const text = `QuantNest Backup Codes\n\nGenerate Date: ${formatDateTime(new Date())}\n\n${backupCodes.join('\n')}\n\nKeep these secure. Each code can only be used once.`;
    const element = document.createElement("a");
    const file = new Blob([text], {type: 'text/plain'});
    const url = URL.createObjectURL(file);
    element.href = url;
    element.download = "quantnest-backup-codes.txt";
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    notify.success("Your backup codes are ready to download.");
  };

  const handleCodeChange = (e) => {
    const value = e.target.value.replace(/\D/g, "").slice(0, 6);
    setVerificationCode(value);
    if (error) {
      setError("");
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="max-w-lg" onInteractOutside={(e) => step === 3 && e.preventDefault()}>
        <DialogHeader>
          <div className="mb-2 flex justify-center sm:justify-start">
            {step === 3 ? (
              <CheckCircle aria-hidden="true" className="h-6 w-6 text-success" />
            ) : (
              <QrCode aria-hidden="true" className="h-6 w-6 text-brand" />
            )}
          </div>
          <DialogTitle>
            {step === 1 && "Set up two-factor authentication"}
            {step === 2 && "Verify your authenticator"}
            {step === 3 && "Save your backup codes"}
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            {step === 1 && "Scan the QR code with your authenticator app (Google Authenticator, Authy, etc.) or enter the secret key manually."}
            {step === 2 && "Enter the 6-digit code from your authenticator app to complete setup."}
            {step === 3 && "Save these backup codes in a secure place. You can use them to log in if you lose access to your authenticator app."}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {error && (
            <div role="alert" className="flex items-start gap-2 rounded-lg border border-destructive/25 bg-destructive/5 p-3 text-sm text-destructive-text">
              <AlertCircle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
              {error}
            </div>
          )}
          {error && step === 1 && !isLoading && !secretKey && <Button variant="outline" onClick={generateTwoFASetup}>Retry setup</Button>}

          {step === 1 && (
            <>
              {isLoading ? (
                <GlobalLoader />
              ) : (
                <>
                  <div className="flex justify-center">
                    {qrCodeUrl ? (
                      <img
                        src={qrCodeUrl}
                        alt="QR Code for 2FA"
                        width={200}
                        height={200}
                        className="rounded-lg border border-border bg-white p-2"
                      />
                    ) : (
                      <div className="w-[200px] h-[200px] rounded-lg border border-border bg-secondary/50 flex items-center justify-center">
                        <span className="text-muted-foreground">QR Code</span>
                      </div>
                    )}
                  </div>

                  {secretKey && (
                    <div className="space-y-2 text-center">
                      <Label htmlFor="secret-key" className="text-foreground">
                        Secret Key
                      </Label>
                      <div className="flex items-center gap-2">
                        <Input
                          id="secret-key"
                          type="text"
                          value={secretKey}
                          readOnly
                          className="min-w-0 flex-1 font-mono text-sm"
                        />
                        <Button
                          variant="outline"
                          size="icon"
                          className="shrink-0"
                          onClick={handleCopySecret}
                          title="Copy Secret Key"
                          type="button"
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        Copy this key if you cannot scan the QR code.
                      </p>
                    </div>
                  )}
                </>
              )}
            </>
          )}

          {step === 2 && (
            <div className="space-y-2">
              <Label
                htmlFor="2fa-code-verify"
                className="text-foreground text-center block"
              >
                Verification Code
              </Label>
              <Input
                id="2fa-code-verify"
                type="text"
                inputMode="numeric"
                placeholder="000000"
                maxLength={6}
                value={verificationCode}
                onChange={handleCodeChange}
                className="h-11 text-center font-mono text-xl tracking-widest"
                required
                autoComplete="one-time-code"
              />
              <p className="text-xs text-muted-foreground text-center mt-2">
                Enter the 6-digit code from your authenticator app
              </p>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-lg border bg-muted/40 p-4">
                {backupCodes.map((code, index) => (
                  <span key={index} className="font-mono text-sm text-foreground tracking-wider text-center">{code}</span>
                ))}
              </div>
              <div className="flex gap-2 justify-center">
                <Button variant="outline" size="sm" onClick={handleCopyBackupCodes}>
                  <Copy className="h-4 w-4 mr-2" /> Copy
                </Button>
                <Button variant="outline" size="sm" onClick={handleDownloadBackupCodes}>
                  <Download className="h-4 w-4 mr-2" /> Download
                </Button>
              </div>
              <p className="mt-2 flex items-start justify-center gap-2 text-center text-xs leading-5 text-warning">
                <AlertCircle aria-hidden="true" className="mt-1 h-3 w-3 shrink-0" />
                These will only be shown once. Please save them now.
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          {step < 3 && (
            <Button
              variant="outline"
              onClick={handleClose}
              disabled={isVerifying}
            >
              Cancel
            </Button>
          )}

          {step === 1 && (
            <Button
              onClick={handleNext}
              disabled={isLoading || !secretKey}
            >
              {isLoading ? (
                <>
                  <LoaderMark className="h-4 w-4 mr-2" />
                  Loading...
                </>
              ) : (
                "Next"
              )}
            </Button>
          )}

          {step === 2 && (
            <Button
              onClick={handleVerify}
              disabled={isVerifying || verificationCode.length !== 6}
            >
              {isVerifying ? (
                <>
                  <LoaderMark className="h-4 w-4 mr-2" />
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

          {step === 3 && (
            <Button
              onClick={handleFinish}
              className="w-full"
            >
              I have saved them. Done
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
