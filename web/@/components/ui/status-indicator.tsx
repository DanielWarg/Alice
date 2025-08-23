'use client'

import * as React from "react"
import { cn } from "@/lib/utils"

// TypeScript interfaces for status indicators
interface StatusIndicatorProps {
  status: 'connected' | 'disconnected' | 'connecting' | 'error'
  label?: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
  showPulse?: boolean
  'data-testid'?: string
}

interface ConnectionStatusProps {
  isConnected: boolean
  isConnecting?: boolean
  error?: string | null
  className?: string
  'data-testid'?: string
}

interface ProcessingStatusProps {
  isProcessing: boolean
  progress?: number
  label?: string
  className?: string
  'data-testid'?: string
}

interface VoiceActivityStatusProps {
  isListening: boolean
  isSpeaking: boolean
  voiceLevel?: number
  className?: string
  'data-testid'?: string
}

// Base status indicator component
function StatusIndicator({ 
  status, 
  label, 
  size = 'md', 
  className,
  showPulse = true,
  'data-testid': testId,
  ...props 
}: StatusIndicatorProps) {
  const sizeClasses = {
    sm: 'w-2 h-2',
    md: 'w-3 h-3',
    lg: 'w-4 h-4'
  }

  const statusClasses = {
    connected: 'bg-green-500 shadow-green-500/50',
    disconnected: 'bg-red-500 shadow-red-500/50',
    connecting: 'bg-yellow-500 shadow-yellow-500/50',
    error: 'bg-red-600 shadow-red-600/50'
  }

  const pulseClasses = {
    connected: 'animate-pulse',
    connecting: 'animate-bounce',
    disconnected: '',
    error: 'animate-pulse'
  }

  return (
    <div 
      className={cn("flex items-center gap-2", className)} 
      data-testid={testId}
      {...props}
    >
      <div
        className={cn(
          "rounded-full shadow-md transition-all duration-300",
          sizeClasses[size],
          statusClasses[status],
          showPulse && pulseClasses[status]
        )}
        aria-label={`Status: ${status}`}
      />
      {label && (
        <span className="text-sm text-zinc-300 capitalize">
          {label}
        </span>
      )}
    </div>
  )
}

// Connection status with Swedish labels
function ConnectionStatus({ 
  isConnected, 
  isConnecting = false, 
  error,
  className,
  'data-testid': testId = 'connection-status'
}: ConnectionStatusProps) {
  const getStatus = () => {
    if (error) return 'error'
    if (isConnecting) return 'connecting'
    return isConnected ? 'connected' : 'disconnected'
  }

  const getLabel = () => {
    if (error) return 'Fel'
    if (isConnecting) return 'Ansluter...'
    return isConnected ? 'Ansluten' : 'Frånkopplad'
  }

  return (
    <StatusIndicator
      status={getStatus()}
      label={getLabel()}
      className={className}
      data-testid={testId}
    />
  )
}

// Processing status with optional progress
function ProcessingStatus({ 
  isProcessing, 
  progress, 
  label, 
  className,
  'data-testid': testId = 'processing-status'
}: ProcessingStatusProps) {
  const getLabel = () => {
    if (!isProcessing) return 'Inaktiv'
    if (label) return label
    if (typeof progress === 'number') return `Behandlar... ${Math.round(progress)}%`
    return 'Behandlar...'
  }

  return (
    <div className={cn("flex items-center gap-3", className)} data-testid={testId}>
      <StatusIndicator
        status={isProcessing ? 'connecting' : 'disconnected'}
        size="sm"
        showPulse={isProcessing}
      />
      <span className="text-sm text-zinc-300">
        {getLabel()}
      </span>
      {typeof progress === 'number' && (
        <div className="flex-1 max-w-24 h-1 bg-zinc-700 rounded-full overflow-hidden">
          <div 
            className="h-full bg-cyan-500 transition-all duration-300 ease-out"
            style={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
          />
        </div>
      )}
    </div>
  )
}

// Voice activity status with level indicator
function VoiceActivityStatus({ 
  isListening, 
  isSpeaking, 
  voiceLevel = 0, 
  className,
  'data-testid': testId = 'voice-activity-status'
}: VoiceActivityStatusProps) {
  const getStatus = () => {
    if (isSpeaking) return 'connected'
    if (isListening) return 'connecting'
    return 'disconnected'
  }

  const getLabel = () => {
    if (isSpeaking) return 'Talar'
    if (isListening) return 'Lyssnar'
    return 'Tyst'
  }

  const levelBars = Math.floor((voiceLevel || 0) * 5)

  return (
    <div className={cn("flex items-center gap-3", className)} data-testid={testId}>
      <StatusIndicator
        status={getStatus()}
        label={getLabel()}
        size="sm"
      />
      {(isListening || isSpeaking) && (
        <div className="flex items-center gap-px">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className={cn(
                "w-0.5 h-3 rounded-full transition-all duration-100",
                i < levelBars 
                  ? "bg-cyan-400 shadow-sm" 
                  : "bg-zinc-700"
              )}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export { 
  StatusIndicator, 
  ConnectionStatus, 
  ProcessingStatus, 
  VoiceActivityStatus,
  type StatusIndicatorProps,
  type ConnectionStatusProps,
  type ProcessingStatusProps,
  type VoiceActivityStatusProps
}