import { LoaderMark } from '@/shared/components/ui/global-loader';
import { useEffect, useRef, useState } from "react";
import { useDispatch } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import { KeyRound, } from "lucide-react";
import LoginPage from "./LoginPage";
import AuthLayout from "../components/AuthLayout";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { Button } from "@/shared/components/ui/button";
import api from "@/shared/services/api";
import { loginSuccess } from "@/shared/store/authSlice";
import { getApiErrorMessage } from "@/shared/utils/apiErrors";

export default function GoogleCallbackPage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const started = useRef(false);
  const [twoFactorChallenge, setTwoFactorChallenge] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    api.post("/users/auth/google/complete/", {}).then(({ data }) => {
      if (data.is_2fa_required) {
        setTwoFactorChallenge({ login_token: data.login_token, next: data.next });
      } else {
        dispatch(loginSuccess(data));
        navigate(data.next, { replace: true });
      }
    }).catch((error) => setError(getApiErrorMessage(error, "Could not complete Google sign-in. Please start again.")));
  }, [dispatch, navigate]);

  if (twoFactorChallenge) return <LoginPage twoFactorChallenge={twoFactorChallenge} />;

  return (
    <AuthLayout authPage="login" title="Google sign-in" description={error ? "Your sign-in could not be completed. Return to sign in and try again." : "Connecting your Google account to your QuantNest workspace."} icon={KeyRound}>
      <div className="space-y-5">
        {error ? <WorkspaceState error={error} title="Google sign-in unavailable" /> : (
          <p role="status" className="flex items-center justify-center gap-2 py-3 text-sm text-muted-foreground">
            <LoaderMark aria-hidden="true" className="h-5 w-5" />
            Completing your sign-in…
          </p>
        )}
        <Button asChild variant="outline" className="h-11 w-full rounded-full"><Link to="/login">Back to sign in</Link></Button>
      </div>
    </AuthLayout>
  );
}
