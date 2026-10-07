import { useEffect, useRef, useState } from "react";
import { useDispatch } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import LoginPage from "./LoginPage";
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
    <main className="flex min-h-screen items-center justify-center bg-[#050505] px-4 text-white">
      <div className="w-full max-w-md space-y-4 rounded-3xl border border-white/10 bg-[#0b0d12] p-8 text-center">
        <h1 className="text-xl font-semibold">Google sign-in</h1>
        {error ? <p role="alert" className="text-red-300">{error}</p> : (
          <p className="flex items-center justify-center gap-2 text-slate-300">
            <Loader2 className="h-5 w-5 animate-spin" />
            Completing your sign-in…
          </p>
        )}
        <Link to="/login" className="inline-block text-[#e5c461] hover:underline">Back to login</Link>
      </div>
    </main>
  );
}
