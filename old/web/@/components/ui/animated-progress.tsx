'use client'

import * as React from "react"
import * as ProgressPrimitive from "@radix-ui/react-progress"
import { cn } from "@/lib/utils"

// TypeScript interfaces for progress components
interface AnimatedProgressProps {
  value?: number
  className?: string
  variant?: 'default' | 'success' | 'warning' | 'error'
  size?: 'sm' | 'md' | 'lg'
  animated?: boolean
  showValue?: boolean
  label?: string
  'data-testid'?: string
}

interface CircularProgressProps {
  value?: number
  size?: number
  strokeWidth?: number
  className?: string
  variant?: 'default' | 'success' | 'warning' | 'error'
  animated?: boolean
  showValue?: boolean
  'data-testid'?: string
}

interface PulseProgressProps {
  isActive: boolean
  label?: string
  className?: string
  'data-testid'?: string
}

interface StepProgressProps {
  steps: Array<{ label: string; completed: boolean; active?: boolean }>
  className?: string
  'data-testid'?: string
}

// Enhanced linear progress with animations
function AnimatedProgress({
  className,
  value = 0,
  variant = 'default',
  size = 'md',
  animated = true,
  showValue = false,
  label,
  'data-testid': testId,
  ...props
}: AnimatedProgressProps) {
  const sizeClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3'
  }

  const variantClasses = {
    default: 'bg-primary',
    success: 'bg-green-500',
    warning: 'bg-yellow-500', 
    error: 'bg-red-500'
  }

  const backgroundClasses = {
    default: 'bg-primary/20',
    success: 'bg-green-500/20',
    warning: 'bg-yellow-500/20',
    error: 'bg-red-500/20'
  }

  const clampedValue = Math.max(0, Math.min(100, value || 0))

  return (
    <div className={cn("w-full space-y-2", className)} data-testid={testId}>
      {(label || showValue) && (
        <div className="flex justify-between items-center">
          {label && <span className="text-sm text-zinc-300">{label}</span>}
          {showValue && (
            <span className="text-sm text-zinc-400 font-mono">
              {Math.round(clampedValue)}%
            </span>
          )}
        </div>
      )}
      
      <ProgressPrimitive.Root
        className={cn(
          "relative w-full overflow-hidden rounded-full",
          sizeClasses[size],
          backgroundClasses[variant]
        )}
        {...props}
      >
        <ProgressPrimitive.Indicator
          className={cn(
            "h-full w-full flex-1 transition-all duration-500 ease-out",
            variantClasses[variant],
            animated && "animate-pulse"
          )}
          style={{ 
            transform: `translateX(-${100 - clampedValue}%)`,
            background: animated 
              ? `linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)`
              : undefined
          }}
        />
        
        {/* Animated shimmer effect */}
        {animated && clampedValue > 0 && (
          <div 
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse"
            style={{
              transform: `translateX(-${100 - clampedValue}%)`,
              animation: 'shimmer 2s infinite'
            }}
          />
        )}
      </ProgressPrimitive.Root>
    </div>
  )
}

// Circular progress indicator
function CircularProgress({
  value = 0,
  size = 40,
  strokeWidth = 3,
  className,
  variant = 'default',
  animated = true,
  showValue = false,
  'data-testid': testId
}: CircularProgressProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const clampedValue = Math.max(0, Math.min(100, value || 0))
  const strokeDashoffset = circumference - (clampedValue / 100) * circumference

  const strokeColors = {
    default: '#06b6d4',
    success: '#10b981', 
    warning: '#f59e0b',
    error: '#ef4444'
  }

  return (
    <div 
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: size, height: size }}
      data-testid={testId}
    >
      <svg
        className="transform -rotate-90"
        width={size}
        height={size}
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="transparent"
          className="text-zinc-700"
        />
        
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={strokeColors[variant]}
          strokeWidth={strokeWidth}
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className={cn(
            "transition-all duration-500 ease-out",
            animated && "animate-pulse"
          )}
        />
      </svg>
      
      {/* Center value display */}
      {showValue && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs font-mono text-zinc-300">
            {Math.round(clampedValue)}%
          </span>
        </div>
      )}
    </div>
  )
}

// Pulse progress for indeterminate states
function PulseProgress({
  isActive,
  label,
  className,
  'data-testid': testId
}: PulseProgressProps) {
  return (
    <div className={cn("flex items-center gap-3", className)} data-testid={testId}>
      <div className="flex gap-1">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "w-2 h-2 rounded-full transition-all duration-300",
              isActive 
                ? "bg-cyan-500 animate-bounce" 
                : "bg-zinc-700",
            )}
            style={{
              animationDelay: isActive ? `${i * 0.1}s` : '0s'
            }}
          />
        ))}
      </div>
      {label && (
        <span className="text-sm text-zinc-300">
          {label}
        </span>
      )}
    </div>
  )
}

// Step-based progress indicator
function StepProgress({
  steps,
  className,
  'data-testid': testId
}: StepProgressProps) {
  return (
    <div className={cn("space-y-4", className)} data-testid={testId}>
      {steps.map((step, index) => {
        const isLast = index === steps.length - 1
        
        return (
          <div key={index} className="relative">
            <div className="flex items-center gap-3">
              {/* Step indicator */}
              <div
                className={cn(
                  "w-4 h-4 rounded-full border-2 flex items-center justify-center transition-all duration-300",
                  step.completed 
                    ? "bg-green-500 border-green-500"
                    : step.active
                    ? "border-cyan-500 bg-cyan-500/20 animate-pulse"
                    : "border-zinc-600 bg-zinc-800"
                )}
              >
                {step.completed && (
                  <svg className="w-2 h-2 text-white fill-current">
                    <path d="M0.5 2.5L2 4L3.5 1" stroke="currentColor" strokeWidth="0.5" fill="none"/>
                  </svg>
                )}
              </div>
              
              {/* Step label */}
              <span 
                className={cn(
                  "text-sm transition-colors duration-300",
                  step.completed 
                    ? "text-green-400"
                    : step.active
                    ? "text-cyan-400"
                    : "text-zinc-500"
                )}
              >
                {step.label}
              </span>
            </div>
            
            {/* Connecting line */}
            {!isLast && (
              <div 
                className={cn(
                  "ml-2 mt-2 w-0.5 h-4 transition-colors duration-300",
                  steps[index + 1]?.completed || steps[index + 1]?.active
                    ? "bg-cyan-500"
                    : "bg-zinc-700"
                )}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

export { 
  AnimatedProgress, 
  CircularProgress, 
  PulseProgress, 
  StepProgress,
  type AnimatedProgressProps,
  type CircularProgressProps,
  type PulseProgressProps,
  type StepProgressProps
}