import React from 'react';
import { useNavigate } from "react-router-dom";
import { useGoogleLogin } from '@react-oauth/google';
import { Button } from "@/components/ui/button";
import { Chrome, AlertCircle } from 'lucide-react';

// Error boundary specifically for Google OAuth
class GoogleOAuthErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error) {
    // Check if it's specifically a Google OAuth provider error
    if (error.message && error.message.includes('GoogleOAuthProvider')) {
      return { hasError: true };
    }
    return { hasError: false };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Google OAuth Error:', error, errorInfo);
    if (this.props.onError) {
      this.props.onError('Google authentication is not properly configured.');
    }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || <GoogleLoginFallback type={this.props.type} />;
    }

    return this.props.children;
  }
}

// Actual Google login component
function GoogleLoginComponent({ onError, isLoading, type = 'login' }) {
  const navigate = useNavigate();

  const googleLogin = useGoogleLogin({
    onSuccess: (tokenResponse) => {
      console.log('Google OAuth Success:', tokenResponse);
      navigate(`/google-callback?access_token=${tokenResponse.access_token}`);
    },
    onError: (error) => {
      console.error('Google OAuth Error:', error);
      onError(`Google ${type} failed. Please try again.`);
    },
  });

  const handleClick = () => {
    try {
      googleLogin();
    } catch (error) {
      console.error('Google login execution error:', error);
      onError(`Google ${type} failed.`);
    }
  };

  return (
    <Button
      variant="outline"
      className="w-full flex items-center justify-center gap-2 bg-slate-800/50 text-slate-200 hover:bg-slate-700/50 hover:text-slate-100 border-gray-700/50 py-2.5"
      onClick={handleClick}
      type="button"
      disabled={isLoading}
    >
      <Chrome className="h-5 w-5" />
      Continue with Google
    </Button>
  );
}

// Main component with error boundary
export default function GoogleLoginButton({ onError, isLoading, type = 'login' }) {
  return (
    <GoogleOAuthErrorBoundary
      onError={onError}
      type={type}
      fallback={<GoogleLoginFallback type={type} />}
    >
      <GoogleLoginComponent
        onError={onError}
        isLoading={isLoading}
        type={type}
      />
    </GoogleOAuthErrorBoundary>
  );
}

// Fallback component when Google OAuth is not configured
export function GoogleLoginFallback({ type = 'login' }) {
  return (
    <>
      <Button
        variant="outline"
        className="w-full flex items-center justify-center gap-2 bg-slate-800/50 text-slate-200 border-gray-700/50 py-2.5 opacity-50 cursor-not-allowed"
        disabled
        type="button"
      >
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
