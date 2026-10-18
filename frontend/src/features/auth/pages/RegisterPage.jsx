import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import { Activity, ArrowRight, BrainCircuit, FlaskConical, Lock, Mail, SlidersHorizontal, User } from "lucide-react";
import { loginSuccess } from "@/shared/store/authSlice";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { Button } from "@/shared/components/ui/button";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Label } from "@/shared/components/ui/label";
import api from "@/shared/services/api";
import { useNotifications } from "@/shared/hooks/useNotifications";
import AuthLayout from "../components/AuthLayout";
import { AuthField, PasswordGuidance } from "../components/AuthFields";
import EmailVerificationModal from "../components/email-verification-modal";
import GoogleLoginButton from "../components/GoogleLoginButton";

const workflowSteps = [
  [BrainCircuit, "Research", "Investigate your own questions."],
  [SlidersHorizontal, "Your rules", "Define entries, exits and position sizes."],
  [FlaskConical, "Backtest", "Inspect historical trades and costs."],
  [Activity, "Paper practice", "Practise and review with simulated capital."],
];

export default function RegisterPage() {
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState("");
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    username: "",
    email: "",
    password1: "",
    password2: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [agreeToTerms, setAgreeToTerms] = useState(false);
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { notify } = useNotifications();
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!agreeToTerms) {
      notify.error("You must agree to the Terms of Service and Privacy Policy.");
      return;
    }

    if (formData.password1 !== formData.password2) {
      notify.error("Passwords do not match.");
      return;
    }

    if (formData.password1.length < 8) {
      notify.error("Password must be at least 8 characters long.");
      return;
    }

    setIsLoading(true);
    try {
      const { firstName, lastName, username, email, password1, password2 } =
        formData;
      const { data } = await api.post("users/auth/registration/", {
        first_name: firstName,
        last_name: lastName,
        username,
        email,
        password1,
        password2,
      });
      if (data.access) dispatch(loginSuccess(data));

      notify.success("Your account has been created.");
      setRegisteredEmail(email);
      setIsEmailModalOpen(true);
    } catch (err) {
      notify.error(getApiErrorMessage(err, "Could not create your account. Please try again."));
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerificationClose = () => {
    setIsEmailModalOpen(false);
    if (isAuthenticated) {
      navigate("/overview", { replace: true });
      return;
    }
    notify.info("Your account has been created. Verify your email, then sign in to continue.");
    navigate("/login", { replace: true });
  };

  return (
    <AuthLayout
      authPage="register"
      title="Create your account"
      description="Your workspace for research, your own rules, and simulated trading."
      aside={
        <>
          <div className="hidden lg:block">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand">Built around your logic</p>
            <h2 className="mt-4 text-3xl font-semibold leading-tight tracking-[-0.035em]">Give your trading ideas a clearer path.</h2>
            <ol className="mt-7 space-y-5">
              {workflowSteps.map(([Icon, title, description]) => (
                <li key={title} className="flex items-start gap-3">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-brand/20 bg-card"><Icon aria-hidden="true" className="h-4 w-4 text-brand" /></span>
                  <div><h3 className="text-sm font-medium">{title}</h3><p className="mt-1 text-xs leading-5 text-muted-foreground">{description}</p></div>
                </li>
              ))}
            </ol>
          </div>
          <p className="text-xs leading-6 text-muted-foreground lg:mt-7 lg:border-t lg:pt-5">
            Public plans support simulated trading. Live trading requires a separately agreed and activated{" "}
            <Link to="/private" className="focus-ring rounded-sm font-medium text-brand underline underline-offset-4">Private installation</Link>{" "}
            on customer-owned infrastructure.
          </p>
        </>
      }
    >
      <GoogleLoginButton onError={notify.error} isLoading={isLoading} />
      <div className="my-5 flex items-center gap-3 text-xs text-muted-foreground"><span className="flex-1 border-t" />or create an account with email<span className="flex-1 border-t" /></div>

      <form className="space-y-4" onSubmit={handleSubmit} aria-busy={isLoading}>
        <div className="grid grid-cols-2 gap-3">
          <AuthField id="firstName" label="First name" placeholder="First name" value={formData.firstName} onChange={handleChange} autoComplete="given-name" maxLength={30} required />
          <AuthField id="lastName" label="Last name" placeholder="Last name" value={formData.lastName} onChange={handleChange} autoComplete="family-name" maxLength={30} required />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <AuthField id="username" label="Username" icon={User} placeholder="Choose a username" value={formData.username} onChange={handleChange} autoComplete="username" autoCapitalize="none" spellCheck={false} maxLength={150} required />
          <AuthField id="email" label="Email address" icon={Mail} type="email" placeholder="you@example.com" value={formData.email} onChange={handleChange} autoComplete="email" required />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <AuthField id="password1" label="Password" icon={Lock} type="password" placeholder="New password" value={formData.password1} onChange={handleChange} autoComplete="new-password" aria-describedby="password-guidance" required />
          <AuthField id="password2" label="Confirm password" icon={Lock} type="password" placeholder="Repeat it" value={formData.password2} onChange={handleChange} autoComplete="new-password" required />
        </div>
        <PasswordGuidance value={formData.password1} />
        <div className="flex items-start gap-2.5">
          <Checkbox id="terms" checked={agreeToTerms} onCheckedChange={(value) => setAgreeToTerms(Boolean(value))} className="mt-1" />
          <Label htmlFor="terms" className="text-xs leading-6">
            I agree to the{" "}
            <Link to="/terms-of-service" target="_blank" rel="noopener noreferrer" className="focus-ring rounded-sm text-brand underline underline-offset-4">Terms of Service</Link>{" "}
            and{" "}
            <Link to="/privacy-policy" target="_blank" rel="noopener noreferrer" className="focus-ring rounded-sm text-brand underline underline-offset-4">Privacy Policy</Link>.
          </Label>
        </div>
        <Button type="submit" disabled={isLoading || !agreeToTerms} className="h-11 w-full rounded-full">
          {isLoading ? "Creating account..." : "Create account"}
          {!isLoading && <ArrowRight aria-hidden="true" className="h-4 w-4" />}
        </Button>
      </form>
      <p className="mt-5 border-t pt-5 text-center text-sm text-muted-foreground">
        Already have an account?{" "}<Link to="/login" className="focus-ring rounded-sm font-medium text-brand underline underline-offset-4">Sign in</Link>
      </p>
      <EmailVerificationModal isOpen={isEmailModalOpen} onClose={handleVerificationClose} email={registeredEmail} canContinue={isAuthenticated} />
    </AuthLayout>
  );
}
