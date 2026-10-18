import { getApiErrorMessage } from "@/shared/utils/apiErrors";
import { useEffect, useState } from 'react';
import { useLocation } from "react-router-dom";
import { Button } from "@/shared/components/ui/button";
import { Loader2 } from 'lucide-react';
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
      className="h-11 w-full rounded-full bg-background text-foreground [&_svg]:size-5"
      onClick={googleLogin}
      type="button"
      disabled={disabled}
      aria-busy={isProcessing}
    >
      {isProcessing ? (
        <Loader2 aria-hidden="true" className="animate-spin motion-reduce:animate-none" />
      ) : (
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M21.6 12.23c0-.71-.06-1.39-.18-2.05H12v3.88h5.38a4.6 4.6 0 0 1-1.99 3.02v2.51h3.23c1.89-1.74 2.98-4.3 2.98-7.36Z" />
          <path fill="#34A853" d="M12 22c2.7 0 4.96-.9 6.61-2.42l-3.23-2.51c-.9.6-2.05.96-3.38.96-2.6 0-4.8-1.76-5.59-4.12H3.07v2.59A10 10 0 0 0 12 22Z" />
          <path fill="#FBBC05" d="M6.41 13.91A6 6 0 0 1 6.1 12c0-.66.11-1.3.31-1.91V7.5H3.07A10 10 0 0 0 2 12c0 1.61.39 3.13 1.07 4.5l3.34-2.59Z" />
          <path fill="#EA4335" d="M12 5.97c1.47 0 2.79.5 3.82 1.49l2.87-2.87A9.6 9.6 0 0 0 12 2a10 10 0 0 0-8.93 5.5l3.34 2.59C7.2 7.73 9.4 5.97 12 5.97Z" />
        </svg>
      )}
      {isProcessing ? 'Opening Google...' : 'Continue with Google'}
    </Button>
  );
}

GoogleLoginButton.propTypes = { onError: PropTypes.func.isRequired, isLoading: PropTypes.bool };
