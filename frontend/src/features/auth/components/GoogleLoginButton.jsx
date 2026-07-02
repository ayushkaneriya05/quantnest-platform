import { useState } from 'react';
import { useNavigate } from "react-router-dom";
import { useDispatch } from 'react-redux';
import { useGoogleLogin } from '@react-oauth/google';
import { Button } from "@/shared/components/ui/button";
import { Chrome, AlertCircle, Loader2 } from 'lucide-react';
import api from "@/shared/services/api";
import { loginSuccess, fetchUserProfile } from "@/shared/store/authSlice";

export default function GoogleLoginButton({ onError, isLoading: parentLoading, type = 'login' }) {
  const [isProcessing, setIsProcessing] = useState(false);
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const googleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      setIsProcessing(true);
      try {
        const response = await api.post("users/auth/google/", {
          access_token: tokenResponse.access_token,
        });
        dispatch(loginSuccess(response.data));
        await dispatch(fetchUserProfile());
        navigate("/dashboard");
      } catch (err) {
        onError(err.response?.data?.detail || `Google ${type} failed. Please try again.`);
      } finally {
        setIsProcessing(false);
      }
    },
    onError: () => onError(`Google ${type} failed. Please try again.`),
  });

  const disabled = parentLoading || isProcessing;

  return (
    <Button
      variant="outline"
      className="w-full flex items-center justify-center gap-2 bg-slate-800/50 text-slate-200 hover:bg-slate-700/50 hover:text-slate-100 border-gray-700/50 py-2.5"
      onClick={() => googleLogin()}
      type="button"
      disabled={disabled}
    >
      {isProcessing ? (
        <Loader2 className="h-5 w-5 animate-spin" />
      ) : (
        <Chrome className="h-5 w-5" />
      )}
      {isProcessing ? 'Authenticating...' : 'Continue with Google'}
    </Button>
  );
}

// Fallback when VITE_REACT_APP_GOOGLE_CLIENT_ID is not set
export function GoogleLoginFallback({ type = 'login' }) {
  return (
    <>
      <Button variant="outline" className="w-full flex items-center justify-center gap-2 bg-slate-800/50 text-slate-200 border-gray-700/50 py-2.5 opacity-50 cursor-not-allowed" disabled type="button">
        <Chrome className="h-5 w-5" />
        Continue with Google
      </Button>
      <div className="text-xs text-amber-400 text-center flex items-center justify-center gap-1">
        <AlertCircle className="h-3 w-3" />
        Google {type} not configured
      </div>
    </>
  );
}
