'use client'

import * as React from "react"
import { cn } from "@/lib/utils"

// TypeScript interfaces for loading components
interface LoadingSpinnerProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  variant?: 'default' | 'dots' | 'pulse' | 'bars' | 'ripple'
  className?: string
  'data-testid'?: string
}

interface LoadingStateProps {
  isLoading: boolean
  children: React.ReactNode
  fallback?: React.ReactNode
  className?: string
  'data-testid'?: string
}

interface LoadingOverlayProps {
  isVisible: boolean
  message?: string
  spinner?: boolean
  className?: string
  'data-testid'?: string
}

interface SkeletonProps {
  className?: string
  variant?: 'text' | 'circular' | 'rectangular'
  width?: string | number
  height?: string | number
  'data-testid'?: string
}

// Main loading spinner component
function LoadingSpinner({
  size = 'md',
  variant = 'default',
  className,
  'data-testid': testId,
  ...props
}: LoadingSpinnerProps) {
  const sizeClasses = {
    xs: 'w-3 h-3',
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
    xl: 'w-12 h-12'
  }

  if (variant === 'default') {
    return (
      <div
        className={cn(
          "animate-spin rounded-full border-2 border-gray-300",
          "border-t-cyan-500 border-r-cyan-500",
          sizeClasses[size],
          className
        )}
        data-testid={testId}
        {...props}
      />
    )
  }

  if (variant === 'dots') {
    const dotSize = {
      xs: 'w-1 h-1',
      sm: 'w-1.5 h-1.5', 
      md: 'w-2 h-2',
      lg: 'w-3 h-3',
      xl: 'w-4 h-4'
    }
    
    return (
      <div 
        className={cn("flex space-x-1", className)} 
        data-testid={testId}
        {...props}
      >
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "bg-cyan-500 rounded-full animate-bounce",
              dotSize[size]
            )}
            style={{
              animationDelay: `${i * 0.1}s`,
              animationDuration: '0.6s'
            }}
          />
        ))}
      </div>
    )
  }

  if (variant === 'pulse') {
    return (
      <div
        className={cn(
          "animate-pulse rounded-full bg-cyan-500",
          sizeClasses[size],
          className
        )}
        data-testid={testId}
        {...props}
      />
    )
  }

  if (variant === 'bars') {
    const barClasses = {
      xs: 'w-0.5 h-2',
      sm: 'w-0.5 h-3',
      md: 'w-1 h-4', 
      lg: 'w-1 h-5',
      xl: 'w-1.5 h-6'
    }
    
    return (
      <div 
        className={cn("flex items-end space-x-0.5", className)}
        data-testid={testId}
        {...props}
      >
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "bg-cyan-500 animate-pulse",
              barClasses[size]
            )}
            style={{
              animationDelay: `${i * 0.1}s`,
              animationDuration: '0.8s'
            }}
          />
        ))}
      </div>
    )
  }

  if (variant === 'ripple') {
    return (
      <div 
        className={cn(
          "relative inline-block",
          sizeClasses[size],
          className
        )}
        data-testid={testId}
        {...props}
      >
        {Array.from({ length: 2 }).map((_, i) => (
          <div
            key={i}
            className="absolute inset-0 rounded-full border-2 border-cyan-500 opacity-60 animate-ping"
            style={{
              animationDelay: `${i * 0.3}s`,
              animationDuration: '1.2s'
            }}
          />
        ))}
      </div>
    )
  }

  // Fallback to default
  return (
    <div
      className={cn(
        "animate-spin rounded-full border-2 border-gray-300 border-t-cyan-500",
        sizeClasses[size],
        className
      )}
      data-testid={testId}
      {...props}
    />
  )
}

// Loading state wrapper component
function LoadingState({
  isLoading,
  children,
  fallback,
  className,
  'data-testid': testId
}: LoadingStateProps) {
  if (isLoading) {
    return (
      <div className={cn("flex items-center justify-center p-4", className)} data-testid={testId}>
        {fallback || <LoadingSpinner />}
      </div>
    )
  }

  return <>{children}</>
}

// Loading overlay component
function LoadingOverlay({
  isVisible,
  message,
  spinner = true,
  className,
  'data-testid': testId
}: LoadingOverlayProps) {
  if (!isVisible) return null

  return (
    <div
      className={cn(
        "fixed inset-0 bg-black/50 backdrop-blur-sm z-50",
        "flex items-center justify-center",
        className
      )}
      data-testid={testId}
    >
      <div className="bg-zinc-800 rounded-lg p-6 shadow-xl border border-zinc-700">
        <div className="flex items-center space-x-3">
          {spinner && <LoadingSpinner size="md" />}
          {message && (
            <span className="text-zinc-200 font-medium">
              {message}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

// Skeleton loading placeholder
function Skeleton({
  className,
  variant = 'rectangular',
  width = '100%',
  height = '1rem',
  'data-testid': testId,
  ...props
}: SkeletonProps) {
  const variantClasses = {
    text: 'rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-md'
  }

  const style = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height
  }

  return (
    <div
      className={cn(
        "animate-pulse bg-zinc-700",
        variantClasses[variant],
        className
      )}
      style={style}
      data-testid={testId}
      {...props}
    />
  )
}

// Skeleton text with multiple lines
function SkeletonText({
  lines = 3,
  className,
  'data-testid': testId
}: {
  lines?: number
  className?: string
  'data-testid'?: string
}) {
  return (
    <div className={cn("space-y-2", className)} data-testid={testId}>
      {Array.from({ length: lines }).map((_, i) => {
        // Vary the width of the last line to make it look more natural
        const isLastLine = i === lines - 1
        const width = isLastLine ? '75%' : '100%'
        
        return (
          <Skeleton
            key={i}
            variant="text"
            height="1rem"
            width={width}
          />
        )
      })}
    </div>
  )
}

// Loading button state
function LoadingButton({
  isLoading,
  children,
  loadingText,
  className,
  disabled,
  ...props
}: {
  isLoading: boolean
  children: React.ReactNode
  loadingText?: string
  className?: string
  disabled?: boolean
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2",
        "px-4 py-2 rounded-md font-medium transition-all",
        "bg-cyan-500 hover:bg-cyan-600 text-white",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        className
      )}
      disabled={isLoading || disabled}
      {...props}
    >
      {isLoading && <LoadingSpinner size="sm" />}
      {isLoading ? (loadingText || 'Laddar...') : children}
    </button>
  )
}

export {
  LoadingSpinner,
  LoadingState,
  LoadingOverlay,
  Skeleton,
  SkeletonText,
  LoadingButton,
  type LoadingSpinnerProps,
  type LoadingStateProps,
  type LoadingOverlayProps,
  type SkeletonProps
}