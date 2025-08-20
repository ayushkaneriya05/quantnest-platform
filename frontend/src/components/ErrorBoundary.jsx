import React from 'react';
import { AlertCircle, RefreshCw, Home, Bug } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null,
      retryCount: 0,
      maxRetries: 3
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log error details
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState({
      error: error,
      errorInfo: errorInfo
    });

    // Log to error reporting service in production
    if (process.env.NODE_ENV === 'production') {
      this.logErrorToService(error, errorInfo);
    }
  }

  logErrorToService = (error, errorInfo) => {
    // In production, send error to monitoring service like Sentry
    try {
      const errorData = {
        error: error.toString(),
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
        url: window.location.href,
        userAgent: navigator.userAgent,
        userId: localStorage.getItem('userId') || 'anonymous'
      };
      
      // Example: Send to error monitoring service
      // fetch('/api/errors', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(errorData)
      // });
      
      console.warn('Error logged to monitoring service:', errorData);
    } catch (logError) {
      console.error('Failed to log error to service:', logError);
    }
  };

  handleRetry = () => {
    const { retryCount, maxRetries } = this.state;
    
    if (retryCount < maxRetries) {
      this.setState({ 
        hasError: false, 
        error: null, 
        errorInfo: null,
        retryCount: retryCount + 1
      });
    } else {
      // Force page reload as last resort
      window.location.reload();
    }
  };

  handleReportError = () => {
    const { error, errorInfo } = this.state;
    const subject = encodeURIComponent('QuantNest Trading Platform Error Report');
    const body = encodeURIComponent(`
Error Details:
${error?.toString() || 'Unknown error'}

Stack Trace:
${error?.stack || 'No stack trace available'}

Component Stack:
${errorInfo?.componentStack || 'No component stack available'}

Browser: ${navigator.userAgent}
URL: ${window.location.href}
Timestamp: ${new Date().toISOString()}
    `);
    
    window.open(`mailto:support@quantnest.com?subject=${subject}&body=${body}`);
  };

  render() {
    const { hasError, error, retryCount, maxRetries } = this.state;
    const { children, fallback } = this.props;

    if (hasError) {
      // Custom fallback UI if provided
      if (fallback) {
        return fallback;
      }

      const isNetworkError = error?.message?.includes('fetch') || error?.message?.includes('network');
      const isWebSocketError = error?.message?.includes('websocket') || error?.message?.includes('WebSocket');
      const isTradingError = error?.message?.includes('order') || error?.message?.includes('position');

      return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
          <Card className="w-full max-w-2xl bg-slate-900 border-slate-700">
            <CardHeader className="text-center">
              <div className="mx-auto mb-4 p-3 w-fit rounded-full bg-red-500/20">
                <AlertCircle className="h-8 w-8 text-red-400" />
              </div>
              <CardTitle className="text-xl text-white">
                {isNetworkError && "Network Connection Error"}
                {isWebSocketError && "Live Data Connection Error"}
                {isTradingError && "Trading System Error"}
                {!isNetworkError && !isWebSocketError && !isTradingError && "Application Error"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="text-center text-gray-300">
                {isNetworkError && (
                  <p>Unable to connect to trading servers. Please check your internet connection and try again.</p>
                )}
                {isWebSocketError && (
                  <p>Lost connection to live market data. Your trading functionality may be limited.</p>
                )}
                {isTradingError && (
                  <p>A trading system error occurred. Your orders and positions are safe, but some features may be unavailable.</p>
                )}
                {!isNetworkError && !isWebSocketError && !isTradingError && (
                  <p>An unexpected error occurred. We're working to resolve this issue.</p>
                )}
              </div>

              {process.env.NODE_ENV === 'development' && (
                <details className="bg-slate-800 rounded-lg p-4">
                  <summary className="text-sm text-gray-400 cursor-pointer mb-2">
                    Technical Details (Development Mode)
                  </summary>
                  <div className="text-xs text-red-300 font-mono whitespace-pre-wrap overflow-auto max-h-40">
                    {error?.toString()}
                    {'\n\n'}
                    {error?.stack}
                  </div>
                </details>
              )}

              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button
                  onClick={this.handleRetry}
                  disabled={retryCount >= maxRetries}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  {retryCount >= maxRetries ? 'Reload Page' : `Retry (${retryCount}/${maxRetries})`}
                </Button>
                
                <Button
                  onClick={() => window.location.href = '/'}
                  variant="outline"
                  className="border-gray-700 text-gray-300 hover:bg-gray-800"
                >
                  <Home className="h-4 w-4 mr-2" />
                  Go Home
                </Button>
                
                <Button
                  onClick={this.handleReportError}
                  variant="outline"
                  className="border-gray-700 text-gray-300 hover:bg-gray-800"
                >
                  <Bug className="h-4 w-4 mr-2" />
                  Report Issue
                </Button>
              </div>

              <div className="text-center">
                <p className="text-sm text-gray-500">
                  Need immediate help? Contact support at{' '}
                  <a 
                    href="mailto:support@quantnest.com" 
                    className="text-blue-400 hover:text-blue-300"
                  >
                    support@quantnest.com
                  </a>
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    return children;
  }
}

// Higher-order component for wrapping components with error boundaries
export const withErrorBoundary = (Component, fallback) => {
  return function WrappedComponent(props) {
    return (
      <ErrorBoundary fallback={fallback}>
        <Component {...props} />
      </ErrorBoundary>
    );
  };
};

// Specialized error boundary for trading components
export class TradingErrorBoundary extends ErrorBoundary {
  render() {
    const { hasError, error } = this.state;
    const { children } = this.props;

    if (hasError) {
      return (
        <Card className="bg-red-900/20 border-red-700/50">
          <CardContent className="p-6 text-center">
            <AlertCircle className="h-8 w-8 text-red-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-red-300 mb-2">Trading Component Error</h3>
            <p className="text-sm text-red-200 mb-4">
              This trading feature is temporarily unavailable. Your existing positions and orders are safe.
            </p>
            <Button 
              onClick={this.handleRetry}
              size="sm"
              className="bg-red-600 hover:bg-red-700"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </CardContent>
        </Card>
      );
    }

    return children;
  }
}

export default ErrorBoundary;
