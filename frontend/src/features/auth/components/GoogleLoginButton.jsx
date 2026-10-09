import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useEffect, useState } from 'react';
import { useLocation } from "react-router-dom";
import { Button } from "@/shared/components/ui/button";
import { Chrome, Loader2 } from 'lucide-react';
import api from "@/shared/services/api";
import PropTypes from "prop-types";

export default function GoogleLoginButton({ onError, isLoading: parentLoading }) {
  const [isProcessing, setIsProcessing] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const restorePage = (event) => {
      // Back can restore this component with its pre-redirect loading state.
      if (event.persisted) setIsProcessing(false);
    };
    window.addEventListener("pageshow", restorePage);
    return () => window.removeEventListener("pageshow", restorePage);
  }, []);

  const googleLogin = async () => {
    setIsProcessing(true);
    try {
      const { data } = await api.post("/users/auth/google/start/", {
        next: (location.state?.from ? `${location.state.from.pathname}${location.state.from.search || ""}${location.state.from.hash || ""}` : "/overview"),
      });
      window.location.assign(data.authorization_url);
    } catch (error) {
      onError(getApiErrorMessage(error, "Could not start Google sign-in. Please try again."));
      setIsProcessing(false);
    }
  };

  const disabled = parentLoading || isProcessing;

  return (
    <Button
      variant="outline"
      className="w-full flex items-center justify-center gap-2 bg-secondary/50 text-foreground hover:bg-muted/50 hover:text-foreground border-border/50 py-2.5"
      onClick={googleLogin}
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

GoogleLoginButton.propTypes = { onError: PropTypes.func.isRequired, isLoading: PropTypes.bool };
