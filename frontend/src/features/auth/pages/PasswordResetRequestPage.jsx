import { LoaderMark } from '@/shared/components/ui/global-loader';
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Mail, ShieldCheck } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import api from "@/shared/services/api";
import { useNotifications } from "@/shared/hooks/useNotifications";
import AuthLayout from "../components/AuthLayout";
import { AuthField } from "../components/AuthFields";

export default function PasswordResetRequestPage() {
  const { notify } = useNotifications();
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await api.post("users/auth/password/reset/", { email });
      notify.success("If this email is linked to an active account, you will receive a password reset link. Check your inbox and spam folder.");
    } catch (err) {
      notify.error(
        getApiErrorMessage(err, "Could not request a password reset link. Please try again."),
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout title="Reset your password" description="Enter the email address you use for QuantNest to request a password reset link." icon={Mail}>
      <div className="space-y-4">
        <form className="space-y-4" onSubmit={handleSubmit} aria-busy={isLoading}>
          <AuthField id="email" label="Email address" icon={Mail} type="email" placeholder="you@example.com" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required />
          <Button type="submit" disabled={isLoading} className="h-11 w-full rounded-full">
            {isLoading && <LoaderMark />}
          {isLoading ? "Requesting..." : "Request reset link"}
            {!isLoading && <ArrowRight aria-hidden="true" className="h-4 w-4" />}
          </Button>
        </form>
        <p className="flex items-start gap-2 text-xs leading-6 text-muted-foreground"><ShieldCheck aria-hidden="true" className="mt-1 h-4 w-4 shrink-0 text-brand" />Two-factor authentication stays enabled if you have set it up.</p>
      </div>
      <p className="mt-5 border-t pt-5 text-center text-sm text-muted-foreground">
        Remember your password?{" "}<Link to="/login" className="focus-ring rounded-sm font-medium text-brand underline underline-offset-4">Sign in</Link>
      </p>
    </AuthLayout>
  );
}
