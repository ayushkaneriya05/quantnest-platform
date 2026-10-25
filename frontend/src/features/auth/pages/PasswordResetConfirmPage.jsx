import { LoaderMark } from '@/shared/components/ui/global-loader';
import { useState } from "react";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowRight, Lock, ShieldCheck } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import api from "@/shared/services/api";
import { useNotifications } from "@/shared/hooks/useNotifications";
import AuthLayout from "../components/AuthLayout";
import { AuthField, PasswordGuidance } from "../components/AuthFields";

export default function PasswordResetConfirmPage() {
  const { uid, token } = useParams();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const [formData, setFormData] = useState({
    new_password1: "",
    new_password2: "",
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (formData.new_password1 !== formData.new_password2) {
      notify.error("Passwords do not match.");
      return;
    }

    if (formData.new_password1.length < 8) {
      notify.error("Password must be at least 8 characters long.");
      return;
    }

    setIsLoading(true);
    try {
      await api.post("users/auth/password/reset/confirm/", {
        uid,
        token,
        new_password1: formData.new_password1,
        new_password2: formData.new_password2,
      });

      notify.success("Your password has been reset and existing sessions have ended. Sign in with your new password.");
      navigate("/login", { replace: true });
    } catch (err) {
      notify.error(getApiErrorMessage(err, "Password reset failed. The link may be expired or invalid."));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout title="Set a new password" description="Choose a new password. This ends existing sessions, so you will need to sign in again." icon={ShieldCheck}>
      <form className="space-y-4" onSubmit={handleSubmit} aria-busy={isLoading}>
        <AuthField id="new_password1" label="New password" icon={Lock} type="password" placeholder="Create a new password" value={formData.new_password1} onChange={handleChange} autoComplete="new-password" aria-describedby="password-guidance" required />
        <PasswordGuidance value={formData.new_password1} />
        <AuthField id="new_password2" label="Confirm new password" icon={Lock} type="password" placeholder="Repeat your new password" value={formData.new_password2} onChange={handleChange} autoComplete="new-password" required />
        <Button type="submit" disabled={isLoading} className="h-11 w-full rounded-full">
          {isLoading && <LoaderMark />}
          {isLoading ? "Resetting..." : "Reset password"}
          {!isLoading && <ArrowRight aria-hidden="true" className="h-4 w-4" />}
        </Button>
      </form>
      <div className="mt-5 space-y-3 border-t pt-5 text-center text-sm text-muted-foreground">
        <p>Link expired or already used?{" "}<Link to="/password-reset" className="focus-ring rounded-sm font-medium text-brand underline underline-offset-4">Request a new reset link</Link></p>
        <Link to="/login" className="focus-ring inline-flex min-h-9 items-center rounded-sm font-medium text-brand underline underline-offset-4">Back to sign in</Link>
      </div>
    </AuthLayout>
  );
}
