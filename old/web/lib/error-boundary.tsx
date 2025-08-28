/**
 * Error Boundaries and Fallback Components
 * Production-grade error handling for React components
 */

'use client';

import React from 'react';
import { FeatureFlag } from './feature-flags';

export interface ErrorInfo {
  componentStack: string;
  errorBoundary?: string;
}

export interface FallbackProps {
  error: Error;
  errorInfo?: ErrorInfo;
  resetError?: () => void;
}

export interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  errorId?: string;
}

/**
 * Base Error Boundary Component
 */
export class ErrorBoundary extends React.Component<
  {
    children: React.ReactNode;
    fallback?: React.ComponentType<FallbackProps>;
    onError?: (error: Error, errorInfo: ErrorInfo) => void;
    resetOnPropsChange?: boolean;
    resetKeys?: Array<string | number>;
  },
  ErrorBoundaryState
> {
  private resetTimeoutId?: NodeJS.Timeout;

  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
      errorId: `error_${Date.now()}_${Math.random().toString(36).substring(2)}`
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    const enhancedErrorInfo: ErrorInfo = {
      componentStack: errorInfo.componentStack,
      errorBoundary: this.constructor.name
    };

    this.setState({ errorInfo: enhancedErrorInfo });

    // Report error
    this.reportError(error, enhancedErrorInfo);

    // Call custom error handler
    this.props.onError?.(error, enhancedErrorInfo);

    // Auto-reset in development
    if (FeatureFlag.isDevelopment()) {
      this.resetTimeoutId = setTimeout(() => {
        this.resetError();
      }, 5000);
    }
  }

  componentDidUpdate(prevProps: any) {
    const { resetOnPropsChange, resetKeys } = this.props;
    const { hasError } = this.state;

    if (hasError && prevProps.resetKeys !== resetKeys) {
      if (resetOnPropsChange) {
        this.resetError();
      } else if (resetKeys) {
        const hasResetKeyChanged = resetKeys.some(
          (key, idx) => prevProps.resetKeys?.[idx] !== key
        );
        if (hasResetKeyChanged) {
          this.resetError();
        }
      }
    }
  }

  componentWillUnmount() {
    if (this.resetTimeoutId) {
      clearTimeout(this.resetTimeoutId);
    }
  }

  private reportError = (error: Error, errorInfo: ErrorInfo) => {
    if (FeatureFlag.isErrorReportingEnabled()) {
      try {
        // Log to console in development
        if (FeatureFlag.isDevelopment()) {
          console.error('Error Boundary caught error:', {
            error: error.message,
            stack: error.stack,
            componentStack: errorInfo.componentStack
          });
        }

        // Report to external service in production
        if (FeatureFlag.isProduction()) {
          // Example: Send to Sentry, LogRocket, etc.
          // Sentry.captureException(error, { contexts: { errorInfo } });
          
          // For now, just log structured error
          console.error('Production Error:', {
            message: error.message,
            name: error.name,
            stack: error.stack,
            componentStack: errorInfo.componentStack,
            timestamp: new Date().toISOString(),
            userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
            url: typeof window !== 'undefined' ? window.location.href : 'unknown'
          });
        }
      } catch (reportingError) {
        console.error('Failed to report error:', reportingError);
      }
    }
  };

  private resetError = () => {
    if (this.resetTimeoutId) {
      clearTimeout(this.resetTimeoutId);
      this.resetTimeoutId = undefined;
    }
    this.setState({ hasError: false, error: undefined, errorInfo: undefined, errorId: undefined });
  };

  render() {
    const { hasError, error, errorInfo, errorId } = this.state;
    const { children, fallback: Fallback } = this.props;

    if (hasError && error) {
      if (Fallback) {
        return (
          <Fallback 
            error={error} 
            errorInfo={errorInfo}
            resetError={this.resetError}
          />
        );
      }

      return <DefaultErrorFallback error={error} errorInfo={errorInfo} resetError={this.resetError} />;
    }

    return children;
  }
}

/**
 * Default Error Fallback Component
 */
export function DefaultErrorFallback({ error, errorInfo, resetError }: FallbackProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-red-50">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center mb-4">
          <div className="flex-shrink-0">
            <svg className="h-8 w-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Ett fel uppstod</h3>
          </div>
        </div>
        
        <div className="mb-4">
          <p className="text-sm text-red-700">
            Något gick fel i applikationen. Vänligen försök igen.
          </p>
          
          {FeatureFlag.isDevelopment() && (
            <details className="mt-2">
              <summary className="text-xs text-red-600 cursor-pointer">Teknisk information</summary>
              <div className="mt-2 text-xs text-red-600 font-mono bg-red-100 p-2 rounded">
                <div><strong>Fel:</strong> {error.message}</div>
                {error.stack && (
                  <div className="mt-1">
                    <strong>Stack:</strong>
                    <pre className="whitespace-pre-wrap text-xs">{error.stack}</pre>
                  </div>
                )}
              </div>
            </details>
          )}
        </div>
        
        <div className="flex space-x-3">
          <button
            onClick={resetError}
            className="flex-1 bg-red-600 text-white text-sm font-medium py-2 px-3 rounded hover:bg-red-700 transition-colors"
          >
            Försök igen
          </button>
          
          <button
            onClick={() => window.location.reload()}
            className="flex-1 bg-gray-600 text-white text-sm font-medium py-2 px-3 rounded hover:bg-gray-700 transition-colors"
          >
            Ladda om sidan
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Voice-specific Error Fallback
 */
export function VoiceErrorFallback({ error, resetError }: FallbackProps) {
  return (
    <div className="flex flex-col items-center justify-center p-6 bg-yellow-50 rounded-lg border border-yellow-200">
      <div className="mb-4">
        <svg className="h-12 w-12 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
      </div>
      
      <h3 className="text-lg font-medium text-yellow-800 mb-2">Röstfunktion otillgänglig</h3>
      
      <p className="text-sm text-yellow-700 text-center mb-4">
        Ett fel uppstod med röstfunktionen. Du kan fortfarande använda text-chatten.
      </p>
      
      {resetError && (
        <button
          onClick={resetError}
          className="bg-yellow-600 text-white px-4 py-2 rounded text-sm hover:bg-yellow-700 transition-colors"
        >
          Försök aktivera röst igen
        </button>
      )}
    </div>
  );
}

/**
 * Agent-specific Error Fallback
 */
export function AgentErrorFallback({ error, resetError }: FallbackProps) {
  return (
    <div className="flex flex-col items-center justify-center p-6 bg-blue-50 rounded-lg border border-blue-200">
      <div className="mb-4">
        <svg className="h-12 w-12 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      </div>
      
      <h3 className="text-lg font-medium text-blue-800 mb-2">Agent otillgänglig</h3>
      
      <p className="text-sm text-blue-700 text-center mb-4">
        AI-agenten svarar inte för tillfället. Försök igen om en stund.
      </p>
      
      <div className="flex space-x-3">
        {resetError && (
          <button
            onClick={resetError}
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 transition-colors"
          >
            Försök igen
          </button>
        )}
        
        <button
          onClick={() => {
            // Switch to fallback mode or echo
            console.log('Switching to fallback mode');
          }}
          className="bg-gray-600 text-white px-4 py-2 rounded text-sm hover:bg-gray-700 transition-colors"
        >
          Använd enkel läge
        </button>
      </div>
    </div>
  );
}

/**
 * HOC for wrapping components with error boundaries
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  fallback?: React.ComponentType<FallbackProps>
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary fallback={fallback}>
      <Component {...props} />
    </ErrorBoundary>
  );
  
  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
}

/**
 * Hook for handling async errors
 */
export function useErrorHandler() {
  const [error, setError] = React.useState<Error | null>(null);

  const handleError = React.useCallback((error: Error) => {
    if (FeatureFlag.isErrorReportingEnabled()) {
      console.error('Async error caught:', error);
    }
    setError(error);
  }, []);

  const resetError = React.useCallback(() => {
    setError(null);
  }, []);

  React.useEffect(() => {
    if (error) {
      throw error; // Will be caught by Error Boundary
    }
  }, [error]);

  return { handleError, resetError };
}