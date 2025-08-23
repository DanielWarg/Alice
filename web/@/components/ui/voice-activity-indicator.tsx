'use client'

import * as React from "react"
import { cn } from "@/lib/utils"
import { Mic, MicOff, Volume2, VolumeX } from "lucide-react"

// TypeScript interfaces for voice activity components
interface VoiceActivityIndicatorProps {
  isListening: boolean
  isSpeaking: boolean
  voiceLevel?: number
  microphoneLevel?: number
  showLabels?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
  'data-testid'?: string
}

interface VoiceLevelMeterProps {
  level: number
  orientation?: 'horizontal' | 'vertical'
  bars?: number
  animated?: boolean
  color?: string
  className?: string
  'data-testid'?: string
}

interface VoiceStatusPillProps {
  status: 'listening' | 'speaking' | 'idle' | 'error'
  label?: string
  className?: string
  'data-testid'?: string
}

interface WaveformVisualizerProps {
  audioData?: number[]
  isActive: boolean
  bars?: number
  height?: number
  color?: string
  className?: string
  'data-testid'?: string
}

interface MicrophoneIndicatorProps {
  isActive: boolean
  level?: number
  hasPermission?: boolean
  error?: string
  className?: string
  'data-testid'?: string
}

// Enhanced voice activity indicator with Swedish labels
function VoiceActivityIndicator({
  isListening,
  isSpeaking,
  voiceLevel = 0,
  microphoneLevel = 0,
  showLabels = true,
  size = 'md',
  className,
  'data-testid': testId
}: VoiceActivityIndicatorProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6', 
    lg: 'w-8 h-8'
  }

  const getStatus = () => {
    if (isSpeaking) return 'Talar'
    if (isListening) return 'Lyssnar'
    return 'Tyst'
  }

  const getStatusColor = () => {
    if (isSpeaking) return 'text-green-400'
    if (isListening) return 'text-cyan-400'
    return 'text-zinc-500'
  }

  return (
    <div className={cn("flex items-center gap-3", className)} data-testid={testId}>
      {/* Microphone icon with activity indicator */}
      <div className="relative">
        {isListening ? (
          <Mic className={cn(sizeClasses[size], getStatusColor(), "animate-pulse")} />
        ) : (
          <MicOff className={cn(sizeClasses[size], "text-zinc-500")} />
        )}
        
        {/* Activity pulse ring */}
        {(isListening || isSpeaking) && (
          <div className={cn(
            "absolute inset-0 rounded-full animate-ping",
            isSpeaking ? "bg-green-400/30" : "bg-cyan-400/30"
          )} />
        )}
      </div>

      {/* Voice level meter */}
      {(isListening || isSpeaking) && (
        <VoiceLevelMeter
          level={isSpeaking ? voiceLevel : microphoneLevel}
          orientation="horizontal"
          bars={5}
          animated={true}
          color={isSpeaking ? "green" : "cyan"}
        />
      )}

      {/* Status label */}
      {showLabels && (
        <span className={cn("text-sm font-medium", getStatusColor())}>
          {getStatus()}
        </span>
      )}
    </div>
  )
}

// Voice level meter component
function VoiceLevelMeter({
  level,
  orientation = 'horizontal',
  bars = 5,
  animated = true,
  color = 'cyan',
  className,
  'data-testid': testId
}: VoiceLevelMeterProps) {
  const normalizedLevel = Math.max(0, Math.min(1, level))
  const activeBars = Math.floor(normalizedLevel * bars)

  const colorClasses = {
    cyan: 'bg-cyan-400',
    green: 'bg-green-400',
    yellow: 'bg-yellow-400',
    red: 'bg-red-400'
  }

  const isHorizontal = orientation === 'horizontal'

  return (
    <div 
      className={cn(
        "flex gap-px",
        isHorizontal ? "items-end" : "flex-col-reverse items-center",
        className
      )}
      data-testid={testId}
    >
      {Array.from({ length: bars }).map((_, i) => {
        const isActive = i < activeBars
        const height = isHorizontal 
          ? `${20 + (i * 10)}%` 
          : isActive ? '100%' : '20%'
        const width = isHorizontal 
          ? 'w-1' 
          : `${20 + (i * 10)}%`

        return (
          <div
            key={i}
            className={cn(
              "transition-all duration-100",
              isHorizontal ? `h-4 ${width}` : `${width} h-1`,
              "rounded-full",
              isActive 
                ? cn(colorClasses[color as keyof typeof colorClasses], animated && "animate-pulse")
                : "bg-zinc-700"
            )}
            style={{
              height: isHorizontal ? height : undefined,
              width: !isHorizontal ? height : undefined
            }}
          />
        )
      })}
    </div>
  )
}

// Voice status pill component
function VoiceStatusPill({
  status,
  label,
  className,
  'data-testid': testId
}: VoiceStatusPillProps) {
  const statusConfig = {
    listening: {
      color: 'bg-cyan-900/30 border-cyan-500/30 text-cyan-300',
      icon: '🎤',
      defaultLabel: 'Lyssnar'
    },
    speaking: {
      color: 'bg-green-900/30 border-green-500/30 text-green-300',
      icon: '🔊',
      defaultLabel: 'Talar'
    },
    idle: {
      color: 'bg-zinc-900/30 border-zinc-500/30 text-zinc-400',
      icon: '⏸️',
      defaultLabel: 'Tyst'
    },
    error: {
      color: 'bg-red-900/30 border-red-500/30 text-red-300',
      icon: '⚠️',
      defaultLabel: 'Fel'
    }
  }

  const config = statusConfig[status]
  const displayLabel = label || config.defaultLabel

  return (
    <div 
      className={cn(
        "inline-flex items-center gap-2 px-3 py-1.5 rounded-full border backdrop-blur-sm",
        "text-sm font-medium transition-all duration-300",
        config.color,
        status === 'listening' && "animate-pulse",
        className
      )}
      data-testid={testId}
    >
      <span className="text-xs">{config.icon}</span>
      <span>{displayLabel}</span>
    </div>
  )
}

// Waveform visualizer component
function WaveformVisualizer({
  audioData = [],
  isActive,
  bars = 32,
  height = 40,
  color = 'cyan',
  className,
  'data-testid': testId
}: WaveformVisualizerProps) {
  // Generate synthetic data if no real audio data provided
  const generateSyntheticData = () => {
    return Array.from({ length: bars }, (_, i) => {
      if (!isActive) return 0.1 + Math.random() * 0.1 // Very low activity when not active
      
      // Generate more realistic waveform pattern
      const baseHeight = 0.3
      const variation = Math.sin(Date.now() * 0.01 + i * 0.5) * 0.4
      const randomness = Math.random() * 0.3
      return Math.max(0.1, Math.min(1, baseHeight + variation + randomness))
    })
  }

  const data = audioData.length > 0 ? audioData : generateSyntheticData()
  
  // Normalize data to ensure it fits within bounds
  const normalizedData = data.slice(0, bars).map(value => 
    Math.max(0.05, Math.min(1, value))
  )

  const colorClasses = {
    cyan: 'bg-cyan-400',
    green: 'bg-green-400', 
    purple: 'bg-purple-400',
    blue: 'bg-blue-400'
  }

  return (
    <div 
      className={cn(
        "flex items-end gap-px justify-center",
        className
      )}
      style={{ height }}
      data-testid={testId}
    >
      {normalizedData.map((value, i) => {
        const barHeight = Math.max(2, value * height)
        
        return (
          <div
            key={i}
            className={cn(
              "w-1 rounded-t transition-all duration-100",
              isActive 
                ? colorClasses[color as keyof typeof colorClasses]
                : "bg-zinc-700",
              isActive && "animate-pulse"
            )}
            style={{ 
              height: `${barHeight}px`,
              animationDelay: `${i * 0.05}s`,
              animationDuration: '1s'
            }}
          />
        )
      })}
    </div>
  )
}

// Microphone indicator with permission status
function MicrophoneIndicator({
  isActive,
  level = 0,
  hasPermission = true,
  error,
  className,
  'data-testid': testId
}: MicrophoneIndicatorProps) {
  const getStatusColor = () => {
    if (error) return 'text-red-400'
    if (!hasPermission) return 'text-yellow-400'
    if (isActive) return 'text-green-400'
    return 'text-zinc-500'
  }

  const getStatusMessage = () => {
    if (error) return error
    if (!hasPermission) return 'Mikrofonbehörighet krävs'
    if (isActive) return `Aktiv (${Math.round(level * 100)}%)`
    return 'Inaktiv'
  }

  return (
    <div className={cn("flex items-center gap-2", className)} data-testid={testId}>
      <div className="relative">
        {hasPermission ? (
          <Mic className={cn("w-5 h-5", getStatusColor())} />
        ) : (
          <MicOff className={cn("w-5 h-5", getStatusColor())} />
        )}
        
        {/* Permission status indicator */}
        <div className={cn(
          "absolute -bottom-1 -right-1 w-2 h-2 rounded-full",
          hasPermission && !error ? "bg-green-500" : "bg-red-500"
        )} />
      </div>
      
      {/* Level indicator */}
      {isActive && hasPermission && !error && (
        <VoiceLevelMeter
          level={level}
          bars={3}
          size="sm"
          color="green"
        />
      )}
      
      {/* Status text */}
      <span className={cn("text-xs", getStatusColor())}>
        {getStatusMessage()}
      </span>
    </div>
  )
}

// Hook for managing voice activity state
function useVoiceActivity() {
  const [isListening, setIsListening] = React.useState(false)
  const [isSpeaking, setIsSpeaking] = React.useState(false)
  const [voiceLevel, setVoiceLevel] = React.useState(0)
  const [microphoneLevel, setMicrophoneLevel] = React.useState(0)
  const [hasPermission, setHasPermission] = React.useState<boolean | null>(null)
  const [error, setError] = React.useState<string | null>(null)

  // Check microphone permission
  const checkPermission = React.useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      setHasPermission(true)
      setError(null)
      
      // Clean up the test stream
      stream.getTracks().forEach(track => track.stop())
    } catch (err: any) {
      setHasPermission(false)
      
      if (err.name === 'NotAllowedError') {
        setError('Mikrofonbehörighet nekad')
      } else if (err.name === 'NotFoundError') {
        setError('Ingen mikrofon hittades')
      } else {
        setError('Mikrofonfel')
      }
    }
  }, [])

  React.useEffect(() => {
    checkPermission()
  }, [checkPermission])

  return {
    isListening,
    isSpeaking,
    voiceLevel,
    microphoneLevel,
    hasPermission,
    error,
    setIsListening,
    setIsSpeaking,
    setVoiceLevel,
    setMicrophoneLevel,
    checkPermission
  }
}

export {
  VoiceActivityIndicator,
  VoiceLevelMeter,
  VoiceStatusPill,
  WaveformVisualizer,
  MicrophoneIndicator,
  useVoiceActivity,
  type VoiceActivityIndicatorProps,
  type VoiceLevelMeterProps,
  type VoiceStatusPillProps,
  type WaveformVisualizerProps,
  type MicrophoneIndicatorProps
}