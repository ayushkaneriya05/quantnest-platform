import React from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { 
      hasError: false, 
      error: null,
      errorInfo: null,
      errorId: null
    }
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { 
      hasError: true,
      errorId: Date.now().toString()
    }
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console and external service
    console.error('Error Boundary caught an error:', error, errorInfo)
    
    this.setState({
      error,
      errorInfo
    })

    // Log to external error service (e.g., Sentry)
    if (window.Sentry) {
      window.Sentry.captureException(error, {
        contexts: {
          react: {
            componentStack: errorInfo.componentStack
          }
        }
      })
    }

    // Send to your own error logging service
    this.logErrorToService(error, errorInfo)
  }

  logErrorToService = async (error, errorInfo) => {
    try {
      // Replace with your actual error logging endpoint
      await fetch('/api/errors', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: error.message,
          stack: error.stack,
          componentStack: errorInfo.componentStack,
          timestamp: new Date().toISOString(),
          userAgent: navigator.userAgent,
          url: window.location.href,
          errorId: this.state.errorId
        })
      })
    } catch (logError) {
      console.error('Failed to log error to service:', logError)
    }
  }

  handleReload = () => {
    window.location.reload()
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  handleTryAgain = () => {
    this.setState({ 
      hasError: false, 
      error: null, 
      errorInfo: null,
      errorId: null 
    })
  }

  handleReportBug = () => {
    const { error, errorInfo, errorId } = this.state
    const bugReport = {
      errorId,
      message: error?.message,
      stack: error?.stack,
      componentStack: errorInfo?.componentStack,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent
    }
    
    // Open bug report form or email
    const subject = encodeURIComponent(`Bug Report - Error ID: ${errorId}`)
    const body = encodeURIComponent(`
Error Details:
${JSON.stringify(bugReport, null, 2)}

Steps to reproduce:
1. 
2. 
3. 

Expected behavior:


Actual behavior:


Additional information:

    `)
    
    window.open(`mailto:support@quantnest.com?subject=${subject}&body=${body}`)
  }

  render() {
    if (this.state.hasError) {
      const { error, errorId } = this.state
      const isDevelopment = process.env.NODE_ENV === 'development'

      return (
        <div className="min-h-screen bg-black flex items-center justify-center p-4">
          <Card className="w-full max-w-2xl bg-gray-900/50 border border-gray-800/50 shadow-xl">
            <CardHeader className="text-center pb-6">
              <div className="flex justify-center mb-4">
                <AlertTriangle className="h-16 w-16 text-red-400" />
              </div>
              <CardTitle className="text-2xl font-bold text-slate-100">
                Oops! Something went wrong
              </CardTitle>
              <CardDescription className="text-slate-400 text-base">
                We apologize for the inconvenience. An unexpected error has occurred.
              </CardDescription>
              {errorId && (
                <div className="mt-2">
                  <span className="text-xs text-slate-500">Error ID: {errorId}</span>
                </div>
              )}
            </CardHeader>
            
            <CardContent className="space-y-6">
              {isDevelopment && error && (
                <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-4">
                  <h4 className="text-red-300 font-medium mb-2">Development Error Details:</h4>
                  <pre className="text-xs text-red-200 whitespace-pre-wrap overflow-auto max-h-40">
                    {error.message}
                    {'\n\n'}
                    {error.stack}
                  </pre>
                </div>
              )}

              <div className="space-y-3">
                <p className="text-slate-300 text-sm">
                  You can try one of the following options:
                </p>
                
                <div className="grid gap-3 sm:grid-cols-2">
                  <Button
                    onClick={this.handleTryAgain}
                    className="bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)]"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Try Again
                  </Button>
                  
                  <Button
                    onClick={this.handleReload}
                    variant="outline"
                    className="bg-gray-800/50 border-gray-700/50 text-slate-200 hover:bg-gray-700/50"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Reload Page
                  </Button>
                  
                  <Button
                    onClick={this.handleGoHome}
                    variant="outline"
                    className="bg-gray-800/50 border-gray-700/50 text-slate-200 hover:bg-gray-700/50"
                  >
                    <Home className="h-4 w-4 mr-2" />
                    Go Home
                  </Button>
                  
                  <Button
                    onClick={this.handleReportBug}
                    variant="outline"
                    className="bg-gray-800/50 border-gray-700/50 text-slate-200 hover:bg-gray-700/50"
                  >
                    <Bug className="h-4 w-4 mr-2" />
                    Report Bug
                  </Button>
                </div>
              </div>

              <div className="text-center pt-4 border-t border-gray-800/50">
                <p className="text-xs text-slate-500">
                  If the problem persists, please contact our support team at{' '}
                  <a 
                    href="mailto:support@quantnest.com" 
                    className="text-indigo-400 hover:text-indigo-300 underline"
                  >
                    support@quantnest.com
                  </a>
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary

// Higher-order component for easy usage
export function withErrorBoundary(Component, errorBoundaryProps = {}) {
  const WrappedComponent = (props) => {
    return (
      <ErrorBoundary {...errorBoundaryProps}>
        <Component {...props} />
      </ErrorBoundary>
    )
  }
  
  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`
  
  return WrappedComponent
}

// Hook for programmatic error throwing (useful for testing)
export function useErrorHandler() {
  return (error) => {
    throw error
  }
}
