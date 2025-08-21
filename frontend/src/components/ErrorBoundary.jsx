import React from 'react';
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Separator } from './ui/separator';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      errorId: Date.now().toString(36)
    };
  }

  componentDidCatch(error, errorInfo) {
    // Log error details
    console.error('Error Boundary caught an error:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo
    });

    // Report error to monitoring service
    this.reportError(error, errorInfo);
  }

  reportError = (error, errorInfo) => {
    try {
      // Create error report
      const errorReport = {
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
        errorId: this.state.errorId
      };

      // Log to console for development
      console.group('🐛 Error Report');
      console.error('Error:', error.message);
      console.error('Stack:', error.stack);
      console.error('Component Stack:', errorInfo.componentStack);
      console.error('Error ID:', this.state.errorId);
      console.groupEnd();

      // In production, you would send this to your error monitoring service
      // Example: Sentry, LogRocket, Bugsnag, etc.
      // this.sendToErrorService(errorReport);
      
    } catch (reportingError) {
      console.error('Failed to report error:', reportingError);
    }
  };

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null
    });
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      const { error, errorInfo } = this.state;
      const isDevelopment = import.meta.env.DEV;
      
      return (
        <div className="min-h-screen bg-background flex items-center justify-center p-4">
          <Card className="w-full max-w-2xl">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-100 dark:bg-red-900/20 rounded-full">
                  <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <CardTitle className="text-xl text-red-600 dark:text-red-400">
                    Something went wrong
                  </CardTitle>
                  <p className="text-muted-foreground mt-1">
                    We encountered an unexpected error. Please try refreshing the page.
                  </p>
                </div>
              </div>
            </CardHeader>

            <CardContent className="space-y-6">
              {/* Error Summary */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Badge variant="destructive" className="text-xs">
                    Error ID: {this.state.errorId}
                  </Badge>
                  <Badge variant="outline" className="text-xs">
                    {new Date().toLocaleString()}
                  </Badge>
                </div>
                
                {error && (
                  <div className="p-3 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg">
                    <p className="text-sm font-medium text-red-800 dark:text-red-200">
                      {error.message || 'Unknown error occurred'}
                    </p>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-3">
                <Button 
                  onClick={this.handleRetry}
                  className="flex items-center gap-2"
                >
                  <RefreshCw className="h-4 w-4" />
                  Try Again
                </Button>
                
                <Button 
                  variant="outline"
                  onClick={this.handleGoHome}
                  className="flex items-center gap-2"
                >
                  <Home className="h-4 w-4" />
                  Go to Homepage
                </Button>
                
                <Button 
                  variant="ghost"
                  onClick={() => window.location.reload()}
                  className="flex items-center gap-2"
                >
                  <RefreshCw className="h-4 w-4" />
                  Refresh Page
                </Button>
              </div>

              <Separator />

              {/* User-friendly troubleshooting tips */}
              <div className="space-y-3">
                <h4 className="font-medium text-sm">What you can try:</h4>
                <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                  <li>Refresh the page or try again in a few moments</li>
                  <li>Check your internet connection</li>
                  <li>Clear your browser cache and cookies</li>
                  <li>Try using a different browser or device</li>
                  <li>Contact support if the problem persists</li>
                </ul>
              </div>

              {/* Technical Details (Development Only) */}
              {isDevelopment && error && (
                <details className="space-y-3">
                  <summary className="cursor-pointer text-sm font-medium flex items-center gap-2">
                    <Bug className="h-4 w-4" />
                    Technical Details (Development)
                  </summary>
                  
                  <div className="pl-6 space-y-3">
                    <div>
                      <h5 className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-1">
                        Error Message
                      </h5>
                      <pre className="text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded overflow-x-auto">
                        {error.message}
                      </pre>
                    </div>
                    
                    {error.stack && (
                      <div>
                        <h5 className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-1">
                          Stack Trace
                        </h5>
                        <pre className="text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded overflow-x-auto max-h-32">
                          {error.stack}
                        </pre>
                      </div>
                    )}
                    
                    {errorInfo?.componentStack && (
                      <div>
                        <h5 className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-1">
                          Component Stack
                        </h5>
                        <pre className="text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded overflow-x-auto max-h-32">
                          {errorInfo.componentStack}
                        </pre>
                      </div>
                    )}
                  </div>
                </details>
              )}

              {/* Support Information */}
              <div className="pt-4 text-center">
                <p className="text-xs text-muted-foreground">
                  If this error persists, please contact our support team with Error ID: {this.state.errorId}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

// Higher-order component for functional components error handling
export const withErrorBoundary = (Component, fallback) => {
  return function WrappedComponent(props) {
    return (
      <ErrorBoundary fallback={fallback}>
        <Component {...props} />
      </ErrorBoundary>
    );
  };
};

// Hook for error handling in functional components
export const useErrorHandler = () => {
  const [error, setError] = React.useState(null);

  const resetError = React.useCallback(() => {
    setError(null);
  }, []);

  const captureError = React.useCallback((error, errorInfo = {}) => {
    console.error('Error captured by useErrorHandler:', error);
    
    // Report error to monitoring service
    const errorReport = {
      message: error.message || 'Unknown error',
      stack: error.stack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      ...errorInfo
    };

    // Log for development
    console.group('🐛 Error Handler Report');
    console.error('Error:', error);
    console.error('Additional Info:', errorInfo);
    console.groupEnd();

    setError(error);
  }, []);

  // Reset error when component unmounts
  React.useEffect(() => {
    return () => {
      if (error) {
        resetError();
      }
    };
  }, [error, resetError]);

  return {
    error,
    captureError,
    resetError,
    hasError: !!error
  };
};

// Error display component for controlled error states
export const ErrorDisplay = ({ 
  error, 
  onRetry, 
  title = "Something went wrong",
  description = "An unexpected error occurred. Please try again.",
  showDetails = false 
}) => {
  return (
    <Card className="border-red-200 dark:border-red-800">
      <CardContent className="p-6">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-red-100 dark:bg-red-900/20 rounded-full flex-shrink-0">
            <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
          </div>
          <div className="flex-1 space-y-3">
            <div>
              <h3 className="font-medium text-red-800 dark:text-red-200">
                {title}
              </h3>
              <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                {description}
              </p>
            </div>
            
            {showDetails && error && (
              <div className="text-xs bg-red-50 dark:bg-red-900/10 p-2 rounded border border-red-200 dark:border-red-800">
                <code className="text-red-800 dark:text-red-200">
                  {error.message || 'Unknown error'}
                </code>
              </div>
            )}
            
            {onRetry && (
              <Button 
                onClick={onRetry}
                size="sm"
                variant="outline"
                className="border-red-200 text-red-700 hover:bg-red-50 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-900/20"
              >
                <RefreshCw className="h-3 w-3 mr-2" />
                Try Again
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default ErrorBoundary;
