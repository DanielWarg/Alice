'use client'

import * as React from "react"
import { cn } from "@/lib/utils"
import { createContext, useContext, useCallback, useState, useEffect } from "react"

// TypeScript interfaces for toast system
interface Toast {
  id: string
  title?: string
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
  duration?: number
  action?: {
    label: string
    onClick: () => void
  }
}

interface ToastContextValue {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => string
  removeToast: (id: string) => void
  clearAll: () => void
}

interface ToastProviderProps {
  children: React.ReactNode
  maxToasts?: number
}

interface ToastItemProps {
  toast: Toast
  onClose: (id: string) => void
  className?: string
}

// Swedish translations for common toast messages
const swedishMessages = {
  success: {
    default: 'Åtgärden slutfördes framgångsrikt',
    saved: 'Sparat',
    connected: 'Ansluten',
    sent: 'Skickat',
    updated: 'Uppdaterat'
  },
  error: {
    default: 'Ett fel uppstod',
    network: 'Nätverksfel - kontrollera anslutningen',
    permission: 'Behörighet nekad',
    notFound: 'Kunde inte hittas',
    timeout: 'Tidsgräns överskreds'
  },
  warning: {
    default: 'Varning',
    unsaved: 'Osparade ändringar',
    lowBattery: 'Låg batterinivå',
    slowConnection: 'Långsam anslutning'
  },
  info: {
    default: 'Information',
    processing: 'Behandlar...',
    loading: 'Laddar...',
    connecting: 'Ansluter...'
  }
}

// Create toast context
const ToastContext = createContext<ToastContextValue | null>(null)

// Toast provider component
function ToastProvider({ children, maxToasts = 5 }: ToastProviderProps) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((toastData: Omit<Toast, 'id'>) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`
    const newToast: Toast = {
      id,
      duration: 5000, // 5 seconds default
      ...toastData
    }

    setToasts(prev => {
      const updated = [newToast, ...prev]
      // Limit the number of toasts
      return updated.slice(0, maxToasts)
    })

    // Auto remove toast after duration
    if (newToast.duration && newToast.duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, newToast.duration)
    }

    return id
  }, [maxToasts])

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id))
  }, [])

  const clearAll = useCallback(() => {
    setToasts([])
  }, [])

  const contextValue: ToastContextValue = {
    toasts,
    addToast,
    removeToast,
    clearAll
  }

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <ToastContainer />
    </ToastContext.Provider>
  )
}

// Hook to use toast context
function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

// Individual toast item component
function ToastItem({ toast, onClose, className }: ToastItemProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [isExiting, setIsExiting] = useState(false)

  // Animation entrance effect
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 50)
    return () => clearTimeout(timer)
  }, [])

  const handleClose = useCallback(() => {
    setIsExiting(true)
    setTimeout(() => onClose(toast.id), 200)
  }, [toast.id, onClose])

  const typeClasses = {
    success: 'bg-green-900/90 border-green-600 text-green-100',
    error: 'bg-red-900/90 border-red-600 text-red-100',
    warning: 'bg-yellow-900/90 border-yellow-600 text-yellow-100',
    info: 'bg-blue-900/90 border-blue-600 text-blue-100'
  }

  const iconClasses = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ'
  }

  return (
    <div
      className={cn(
        "relative p-4 rounded-lg border backdrop-blur-sm shadow-lg",
        "transform transition-all duration-300 ease-out",
        typeClasses[toast.type],
        isVisible && !isExiting
          ? "translate-x-0 opacity-100"
          : "translate-x-full opacity-0",
        isExiting && "translate-x-full opacity-0 scale-95",
        className
      )}
      data-testid={`toast-${toast.type}`}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center text-sm font-bold">
          {iconClasses[toast.type]}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {toast.title && (
            <div className="font-medium text-sm mb-1">
              {toast.title}
            </div>
          )}
          <div className="text-sm opacity-90">
            {toast.message}
          </div>

          {/* Action button */}
          {toast.action && (
            <button
              onClick={toast.action.onClick}
              className="mt-2 text-xs underline opacity-80 hover:opacity-100 transition-opacity"
            >
              {toast.action.label}
            </button>
          )}
        </div>

        {/* Close button */}
        <button
          onClick={handleClose}
          className="flex-shrink-0 w-4 h-4 flex items-center justify-center text-xs opacity-60 hover:opacity-100 transition-opacity"
          aria-label="Stäng meddelande"
        >
          ✕
        </button>
      </div>
    </div>
  )
}

// Toast container component
function ToastContainer() {
  const { toasts, removeToast } = useToast()

  if (toasts.length === 0) return null

  return (
    <div
      className="fixed top-4 right-4 z-50 space-y-2 pointer-events-none"
      data-testid="toast-container"
    >
      {toasts.map(toast => (
        <div key={toast.id} className="pointer-events-auto">
          <ToastItem
            toast={toast}
            onClose={removeToast}
          />
        </div>
      ))}
    </div>
  )
}

// Convenient toast methods with Swedish messages
function useToastActions() {
  const { addToast } = useToast()

  const success = useCallback((message: string, options?: Partial<Toast>) => {
    return addToast({
      type: 'success',
      message,
      ...options
    })
  }, [addToast])

  const error = useCallback((message: string, options?: Partial<Toast>) => {
    return addToast({
      type: 'error',
      message,
      duration: 7000, // Longer for errors
      ...options
    })
  }, [addToast])

  const warning = useCallback((message: string, options?: Partial<Toast>) => {
    return addToast({
      type: 'warning',
      message,
      ...options
    })
  }, [addToast])

  const info = useCallback((message: string, options?: Partial<Toast>) => {
    return addToast({
      type: 'info',
      message,
      ...options
    })
  }, [addToast])

  // Swedish helper methods
  const swedish = {
    success: (key: keyof typeof swedishMessages.success = 'default', options?: Partial<Toast>) => {
      return success(swedishMessages.success[key], options)
    },
    error: (key: keyof typeof swedishMessages.error = 'default', options?: Partial<Toast>) => {
      return error(swedishMessages.error[key], options)
    },
    warning: (key: keyof typeof swedishMessages.warning = 'default', options?: Partial<Toast>) => {
      return warning(swedishMessages.warning[key], options)
    },
    info: (key: keyof typeof swedishMessages.info = 'default', options?: Partial<Toast>) => {
      return info(swedishMessages.info[key], options)
    }
  }

  return {
    success,
    error,
    warning,
    info,
    swedish,
    addToast // Raw method for custom toasts
  }
}

export {
  ToastProvider,
  ToastContainer,
  ToastItem,
  useToast,
  useToastActions,
  swedishMessages,
  type Toast,
  type ToastContextValue,
  type ToastProviderProps,
  type ToastItemProps
}