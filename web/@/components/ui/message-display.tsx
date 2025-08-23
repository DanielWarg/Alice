'use client'

import * as React from "react"
import { cn } from "@/lib/utils"
import { AlertCircle, CheckCircle, AlertTriangle, Info, X } from "lucide-react"

// TypeScript interfaces for message display components
interface MessageDisplayProps {
  type: 'success' | 'error' | 'warning' | 'info'
  title?: string
  message: string
  dismissible?: boolean
  onDismiss?: () => void
  action?: {
    label: string
    onClick: () => void
  }
  className?: string
  'data-testid'?: string
}

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
  errorInfo?: any
}

interface ErrorFallbackProps {
  error: Error
  resetErrorBoundary: () => void
  errorInfo?: any
}

interface MessageBannerProps {
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  persistent?: boolean
  onClose?: () => void
  className?: string
  'data-testid'?: string
}

interface InlineMessageProps {
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  size?: 'sm' | 'md'
  className?: string
  'data-testid'?: string
}

// Swedish error messages
const swedishErrorMessages = {
  network: 'Nätverksfel - kontrollera din internetanslutning',
  permission: 'Behörighet nekad - kontrollera dina inställningar',
  timeout: 'Tidsgräns överskreds - försök igen',
  notFound: 'Resursen kunde inte hittas',
  server: 'Serverfel - försök igen senare',
  validation: 'Ogiltiga data - kontrollera din inmatning',
  authentication: 'Inloggning krävs - logga in för att fortsätta',
  authorization: 'Otillräckliga behörigheter för denna åtgärd',
  tts: 'Text-till-tal fel - kontrollera röstinställningar',
  stt: 'Tal-till-text fel - kontrollera mikrofoninställningar',
  voice: 'Röstfel - kontrollera mikrofonbehörigheter',
  generic: 'Ett oväntat fel uppstod'
}

const swedishSuccessMessages = {
  saved: 'Sparad framgångsrikt',
  sent: 'Skickat framgångsrikt',
  connected: 'Ansluten framgångsrikt',
  updated: 'Uppdaterad framgångsrikt',
  deleted: 'Borttagen framgångsrikt',
  completed: 'Slutförd framgångsrikt',
  voice: 'Röst aktiverad framgångsrikt',
  tts: 'Text-till-tal fungerar',
  stt: 'Tal-till-text fungerar',
  generic: 'Åtgärden slutfördes framgångsrikt'
}

// Main message display component
function MessageDisplay({
  type,
  title,
  message,
  dismissible = false,
  onDismiss,
  action,
  className,
  'data-testid': testId,
  ...props
}: MessageDisplayProps) {
  const icons = {
    success: CheckCircle,
    error: AlertCircle,
    warning: AlertTriangle,
    info: Info
  }

  const baseClasses = {
    success: 'bg-green-900/20 border-green-600/30 text-green-100',
    error: 'bg-red-900/20 border-red-600/30 text-red-100',
    warning: 'bg-yellow-900/20 border-yellow-600/30 text-yellow-100',
    info: 'bg-blue-900/20 border-blue-600/30 text-blue-100'
  }

  const iconColors = {
    success: 'text-green-400',
    error: 'text-red-400',
    warning: 'text-yellow-400',
    info: 'text-blue-400'
  }

  const Icon = icons[type]

  return (
    <div
      className={cn(
        "relative p-4 rounded-lg border backdrop-blur-sm",
        baseClasses[type],
        className
      )}
      data-testid={testId}
      {...props}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <Icon className={cn("w-5 h-5 flex-shrink-0 mt-0.5", iconColors[type])} />

        {/* Content */}
        <div className="flex-1 min-w-0">
          {title && (
            <div className="font-medium text-sm mb-1">
              {title}
            </div>
          )}
          <div className="text-sm opacity-90">
            {message}
          </div>

          {/* Action button */}
          {action && (
            <button
              onClick={action.onClick}
              className={cn(
                "mt-2 text-sm underline transition-opacity hover:opacity-80",
                iconColors[type]
              )}
            >
              {action.label}
            </button>
          )}
        </div>

        {/* Dismiss button */}
        {dismissible && (
          <button
            onClick={onDismiss}
            className="flex-shrink-0 w-4 h-4 flex items-center justify-center opacity-60 hover:opacity-100 transition-opacity"
            aria-label="Stäng meddelande"
          >
            <X className="w-3 h-3" />
          </button>
        )}
      </div>
    </div>
  )
}

// Compact inline message component
function InlineMessage({
  type,
  message,
  size = 'md',
  className,
  'data-testid': testId
}: InlineMessageProps) {
  const icons = {
    success: CheckCircle,
    error: AlertCircle,
    warning: AlertTriangle,
    info: Info
  }

  const sizeClasses = {
    sm: 'text-xs',
    md: 'text-sm'
  }

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4'
  }

  const colors = {
    success: 'text-green-400',
    error: 'text-red-400',
    warning: 'text-yellow-400',
    info: 'text-blue-400'
  }

  const Icon = icons[type]

  return (
    <div
      className={cn(
        "flex items-center gap-2",
        colors[type],
        sizeClasses[size],
        className
      )}
      data-testid={testId}
    >
      <Icon className={iconSizes[size]} />
      <span>{message}</span>
    </div>
  )
}

// Banner message for full-width notifications
function MessageBanner({
  type,
  message,
  persistent = false,
  onClose,
  className,
  'data-testid': testId
}: MessageBannerProps) {
  const [isVisible, setIsVisible] = React.useState(true)

  const backgrounds = {
    success: 'bg-green-900/90',
    error: 'bg-red-900/90',
    warning: 'bg-yellow-900/90',
    info: 'bg-blue-900/90'
  }

  const textColors = {
    success: 'text-green-100',
    error: 'text-red-100',
    warning: 'text-yellow-100',
    info: 'text-blue-100'
  }

  const handleClose = () => {
    setIsVisible(false)
    onClose?.()
  }

  if (!isVisible) return null

  return (
    <div
      className={cn(
        "relative px-4 py-3 text-center text-sm font-medium",
        backgrounds[type],
        textColors[type],
        className
      )}
      data-testid={testId}
    >
      <span>{message}</span>
      
      {!persistent && (
        <button
          onClick={handleClose}
          className="absolute right-4 top-1/2 transform -translate-y-1/2 opacity-70 hover:opacity-100 transition-opacity"
          aria-label="Stäng banner"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  )
}

// Error boundary component
class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ComponentType<ErrorFallbackProps> },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode; fallback?: React.ComponentType<ErrorFallbackProps> }) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: any) {
    this.setState({
      error,
      errorInfo
    })
    
    // Log to error reporting service
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      const FallbackComponent = this.props.fallback || DefaultErrorFallback
      
      return (
        <FallbackComponent
          error={this.state.error!}
          resetErrorBoundary={() => this.setState({ hasError: false })}
          errorInfo={this.state.errorInfo}
        />
      )
    }

    return this.props.children
  }
}

// Default error fallback component
function DefaultErrorFallback({ 
  error, 
  resetErrorBoundary 
}: ErrorFallbackProps) {
  return (
    <MessageDisplay
      type="error"
      title="Något gick fel"
      message={error.message || 'Ett oväntat fel uppstod. Försök igen eller kontakta support om problemet kvarstår.'}
      action={{
        label: 'Försök igen',
        onClick: resetErrorBoundary
      }}
      data-testid="error-boundary-fallback"
    />
  )
}

// Helper functions for Swedish messages
function createSuccessMessage(key: keyof typeof swedishSuccessMessages, customMessage?: string) {
  return customMessage || swedishSuccessMessages[key] || swedishSuccessMessages.generic
}

function createErrorMessage(key: keyof typeof swedishErrorMessages, customMessage?: string) {
  return customMessage || swedishErrorMessages[key] || swedishErrorMessages.generic
}

// Hook for showing messages
function useMessageDisplay() {
  const [messages, setMessages] = React.useState<Array<{
    id: string
    type: 'success' | 'error' | 'warning' | 'info'
    message: string
    title?: string
  }>>([])

  const showMessage = React.useCallback((
    type: 'success' | 'error' | 'warning' | 'info',
    message: string,
    title?: string,
    duration = 5000
  ) => {
    const id = `msg-${Date.now()}-${Math.random().toString(36).slice(2)}`
    const newMessage = { id, type, message, title }
    
    setMessages(prev => [...prev, newMessage])
    
    if (duration > 0) {
      setTimeout(() => {
        setMessages(prev => prev.filter(msg => msg.id !== id))
      }, duration)
    }
    
    return id
  }, [])

  const removeMessage = React.useCallback((id: string) => {
    setMessages(prev => prev.filter(msg => msg.id !== id))
  }, [])

  const clearMessages = React.useCallback(() => {
    setMessages([])
  }, [])

  return {
    messages,
    showMessage,
    removeMessage,
    clearMessages,
    showSuccess: (message: string, title?: string) => showMessage('success', message, title),
    showError: (message: string, title?: string) => showMessage('error', message, title, 7000),
    showWarning: (message: string, title?: string) => showMessage('warning', message, title),
    showInfo: (message: string, title?: string) => showMessage('info', message, title)
  }
}

export {
  MessageDisplay,
  InlineMessage,
  MessageBanner,
  ErrorBoundary,
  DefaultErrorFallback,
  useMessageDisplay,
  createSuccessMessage,
  createErrorMessage,
  swedishErrorMessages,
  swedishSuccessMessages,
  type MessageDisplayProps,
  type InlineMessageProps,
  type MessageBannerProps,
  type ErrorFallbackProps
}