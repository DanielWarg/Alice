"use client";
import React from "react";

/**
 * ErrorBoundary - Crash protection for Alice HUD components
 * 
 * Provides isolated error handling so individual components can fail
 * without crashing the entire HUD interface.
 * 
 * Features:
 * - Component isolation
 * - Error reporting
 * - Graceful degradation
 * - Recovery options
 */
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null,
      errorInfo: null,
      retryCount: 0
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log error for debugging
    console.error("Alice HUD Component Error:", error, errorInfo);
    
    this.setState({
      error,
      errorInfo
    });

    // Optional: Report to error tracking service
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleRetry = () => {
    this.setState(prevState => ({
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: prevState.retryCount + 1
    }));
  };

  handleReload = () => {
    if (typeof window !== 'undefined') {
      window.location.reload();
    }
  };

  render() {
    if (this.state.hasError) {
      // Custom error UI from props
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.handleRetry);
      }

      // Default error UI
      const errorMessage = this.state.error?.message || "Unknown error occurred";
      
      return (
        <div className="min-h-[200px] rounded-2xl border border-red-500/30 bg-red-950/20 p-6 shadow-lg">
          <div className="text-center">
            <div className="mb-4">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-red-500/20">
                <svg 
                  className="h-6 w-6 text-red-400" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
            </div>
            
            <h3 className="text-lg font-semibold text-red-200 mb-2">
              {this.props.componentName || "Component"} Error
            </h3>
            
            <p className="text-sm text-red-300/80 mb-4">
              {errorMessage}
            </p>
            
            {/* Show retry count for debugging */}
            {this.state.retryCount > 0 && (
              <p className="text-xs text-red-300/60 mb-4">
                Retry attempts: {this.state.retryCount}
              </p>
            )}
            
            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleRetry}
                disabled={this.state.retryCount >= 3}
                className="rounded-lg border border-red-400/30 px-4 py-2 text-sm text-red-200 hover:bg-red-400/10 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {this.state.retryCount >= 3 ? "Max Retries Reached" : "Retry"}
              </button>
              
              <button
                onClick={this.handleReload}
                className="rounded-lg border border-red-400/30 px-4 py-2 text-sm text-red-200 hover:bg-red-400/10"
              >
                Reload Page
              </button>
            </div>
            
            {/* Development error details */}
            {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
              <details className="mt-4 text-left">
                <summary className="text-sm text-red-300/80 cursor-pointer">
                  Error Details (Development)
                </summary>
                <pre className="mt-2 text-xs text-red-300/60 bg-red-950/40 p-3 rounded overflow-auto max-h-40">
                  {this.state.error && this.state.error.toString()}
                  <br />
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Wrapper for functional components that need error boundary protection
 */
export function withErrorBoundary(Component, componentName) {
  const WrappedComponent = (props) => (
    <ErrorBoundary componentName={componentName}>
      <Component {...props} />
    </ErrorBoundary>
  );
  
  WrappedComponent.displayName = `withErrorBoundary(${componentName || Component.name})`;
  return WrappedComponent;
}

/**
 * Hook for component-level error handling
 */
export function useErrorHandler() {
  const [error, setError] = React.useState(null);
  
  const resetError = React.useCallback(() => {
    setError(null);
  }, []);
  
  const handleError = React.useCallback((error) => {
    console.error("Component error:", error);
    setError(error);
  }, []);
  
  // Global error handler for promises and async operations
  React.useEffect(() => {
    const handleUnhandledRejection = (event) => {
      handleError(new Error(`Unhandled promise rejection: ${event.reason}`));
    };
    
    window.addEventListener('unhandledrejection', handleUnhandledRejection);
    
    return () => {
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, [handleError]);
  
  return { error, resetError, handleError };
}

export default ErrorBoundary;