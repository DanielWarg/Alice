/**
 * TypeScript interfaces for Alice HUD components
 * Comprehensive type definitions for all Frontend HUD components
 */

// Base component props
export interface BaseComponentProps {
  className?: string
  'data-testid'?: string
  children?: React.ReactNode
}

// Status Indicator Types
export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error'
export type ProcessingStatus = 'idle' | 'processing' | 'completed' | 'error'
export type VoiceStatus = 'idle' | 'listening' | 'speaking' | 'error'
export type SystemStatus = 'healthy' | 'warning' | 'error' | 'unknown'

// Progress Types
export type ProgressVariant = 'default' | 'success' | 'warning' | 'error'
export type ComponentSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl'
export type Orientation = 'horizontal' | 'vertical'

// Message Types
export type MessageType = 'success' | 'error' | 'warning' | 'info'

// Voice Activity Types
export interface VoiceMetrics {
  level: number
  quality: 'good' | 'fair' | 'poor'
  isActive: boolean
  hasPermission: boolean
  error?: string
}

export interface AudioData {
  frequencies: number[]
  amplitude: number
  timestamp: number
}

// Status Indicator Interfaces
export interface StatusIndicatorProps extends BaseComponentProps {
  status: ConnectionStatus
  label?: string
  size?: ComponentSize
  showPulse?: boolean
}

export interface ConnectionStatusProps extends BaseComponentProps {
  isConnected: boolean
  isConnecting?: boolean
  error?: string | null
}

export interface ProcessingStatusProps extends BaseComponentProps {
  isProcessing: boolean
  progress?: number
  label?: string
}

export interface VoiceActivityStatusProps extends BaseComponentProps {
  isListening: boolean
  isSpeaking: boolean
  voiceLevel?: number
}

// Progress Component Interfaces
export interface AnimatedProgressProps extends BaseComponentProps {
  value?: number
  variant?: ProgressVariant
  size?: ComponentSize
  animated?: boolean
  showValue?: boolean
  label?: string
}

export interface CircularProgressProps extends BaseComponentProps {
  value?: number
  size?: number
  strokeWidth?: number
  variant?: ProgressVariant
  animated?: boolean
  showValue?: boolean
}

export interface PulseProgressProps extends BaseComponentProps {
  isActive: boolean
  label?: string
}

export interface StepProgressProps extends BaseComponentProps {
  steps: ProgressStep[]
}

export interface ProgressStep {
  label: string
  completed: boolean
  active?: boolean
}

// Loading Component Interfaces
export interface LoadingSpinnerProps extends BaseComponentProps {
  size?: ComponentSize
  variant?: 'default' | 'dots' | 'pulse' | 'bars' | 'ripple'
}

export interface LoadingStateProps extends BaseComponentProps {
  isLoading: boolean
  fallback?: React.ReactNode
}

export interface LoadingOverlayProps extends BaseComponentProps {
  isVisible: boolean
  message?: string
  spinner?: boolean
}

export interface SkeletonProps extends BaseComponentProps {
  variant?: 'text' | 'circular' | 'rectangular'
  width?: string | number
  height?: string | number
}

// Toast Component Interfaces
export interface Toast {
  id: string
  title?: string
  message: string
  type: MessageType
  duration?: number
  action?: ToastAction
}

export interface ToastAction {
  label: string
  onClick: () => void
}

export interface ToastContextValue {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => string
  removeToast: (id: string) => void
  clearAll: () => void
}

export interface ToastProviderProps extends BaseComponentProps {
  maxToasts?: number
}

export interface ToastItemProps extends BaseComponentProps {
  toast: Toast
  onClose: (id: string) => void
}

// Message Display Interfaces
export interface MessageDisplayProps extends BaseComponentProps {
  type: MessageType
  title?: string
  message: string
  dismissible?: boolean
  onDismiss?: () => void
  action?: MessageAction
}

export interface MessageAction {
  label: string
  onClick: () => void
}

export interface InlineMessageProps extends BaseComponentProps {
  type: MessageType
  message: string
  size?: 'sm' | 'md'
}

export interface MessageBannerProps extends BaseComponentProps {
  type: MessageType
  message: string
  persistent?: boolean
  onClose?: () => void
}

export interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
  errorInfo?: any
}

export interface ErrorFallbackProps {
  error: Error
  resetErrorBoundary: () => void
  errorInfo?: any
}

// Voice Activity Interfaces
export interface VoiceActivityIndicatorProps extends BaseComponentProps {
  isListening: boolean
  isSpeaking: boolean
  voiceLevel?: number
  microphoneLevel?: number
  showLabels?: boolean
  size?: ComponentSize
}

export interface VoiceLevelMeterProps extends BaseComponentProps {
  level: number
  orientation?: Orientation
  bars?: number
  animated?: boolean
  color?: string
}

export interface VoiceStatusPillProps extends BaseComponentProps {
  status: 'listening' | 'speaking' | 'idle' | 'error'
  label?: string
}

export interface WaveformVisualizerProps extends BaseComponentProps {
  audioData?: number[]
  isActive: boolean
  bars?: number
  height?: number
  color?: string
}

export interface MicrophoneIndicatorProps extends BaseComponentProps {
  isActive: boolean
  level?: number
  hasPermission?: boolean
  error?: string
}

// System Health Interfaces
export interface SystemHealthMetrics {
  cpu?: number
  memory?: number
  network?: NetworkMetrics
  voice?: VoiceMetrics
  backend?: BackendMetrics
  integrations?: IntegrationMetrics
  uptime?: number
  lastUpdated?: number
}

export interface NetworkMetrics {
  status: 'connected' | 'disconnected' | 'poor'
  latency?: number
  speed?: string
  quality?: 'excellent' | 'good' | 'fair' | 'poor'
}

export interface BackendMetrics {
  status: 'healthy' | 'degraded' | 'down'
  responseTime?: number
  lastPing?: number
  errorRate?: number
}

export interface IntegrationMetrics {
  spotify?: boolean
  calendar?: boolean
  gmail?: boolean
  [key: string]: boolean | undefined
}

export interface SystemHealthDashboardProps extends BaseComponentProps {
  metrics: SystemHealthMetrics
  compact?: boolean
  autoRefresh?: boolean
  refreshInterval?: number
}

export interface HealthCardProps extends BaseComponentProps {
  title: string
  status: SystemStatus
  value?: string | number
  subtitle?: string
  icon?: React.ReactNode
  progress?: number
}

export interface IntegrationStatusProps extends BaseComponentProps {
  integrations: IntegrationMetrics
}

// Hook Return Types
export interface UseToastActionsReturn {
  success: (message: string, options?: Partial<Toast>) => string
  error: (message: string, options?: Partial<Toast>) => string
  warning: (message: string, options?: Partial<Toast>) => string
  info: (message: string, options?: Partial<Toast>) => string
  swedish: SwedishToastMethods
  addToast: (toast: Omit<Toast, 'id'>) => string
}

export interface SwedishToastMethods {
  success: (key?: SwedishSuccessKey, options?: Partial<Toast>) => string
  error: (key?: SwedishErrorKey, options?: Partial<Toast>) => string
  warning: (key?: SwedishWarningKey, options?: Partial<Toast>) => string
  info: (key?: SwedishInfoKey, options?: Partial<Toast>) => string
}

export interface UseMessageDisplayReturn {
  messages: MessageDisplayItem[]
  showMessage: (type: MessageType, message: string, title?: string, duration?: number) => string
  removeMessage: (id: string) => void
  clearMessages: () => void
  showSuccess: (message: string, title?: string) => string
  showError: (message: string, title?: string) => string
  showWarning: (message: string, title?: string) => string
  showInfo: (message: string, title?: string) => string
}

export interface MessageDisplayItem {
  id: string
  type: MessageType
  message: string
  title?: string
}

export interface UseVoiceActivityReturn {
  isListening: boolean
  isSpeaking: boolean
  voiceLevel: number
  microphoneLevel: number
  hasPermission: boolean | null
  error: string | null
  setIsListening: (listening: boolean) => void
  setIsSpeaking: (speaking: boolean) => void
  setVoiceLevel: (level: number) => void
  setMicrophoneLevel: (level: number) => void
  checkPermission: () => Promise<void>
}

export interface UseSystemHealthReturn {
  metrics: SystemHealthMetrics
  isLoading: boolean
  error: string | null
  refresh: () => Promise<void>
}

// Swedish Message Keys
export type SwedishSuccessKey = 'default' | 'saved' | 'connected' | 'sent' | 'updated'
export type SwedishErrorKey = 'default' | 'network' | 'permission' | 'notFound' | 'timeout'
export type SwedishWarningKey = 'default' | 'unsaved' | 'lowBattery' | 'slowConnection'
export type SwedishInfoKey = 'default' | 'processing' | 'loading' | 'connecting'

// Animation and Styling Types
export interface AnimationConfig {
  duration?: number
  easing?: 'ease' | 'ease-in' | 'ease-out' | 'ease-in-out' | 'linear'
  delay?: number
}

export interface ThemeColors {
  primary: string
  secondary: string
  success: string
  warning: string
  error: string
  info: string
}

// Event Handler Types
export type StatusChangeHandler = (status: ConnectionStatus) => void
export type ProgressChangeHandler = (progress: number) => void
export type VoiceActivityHandler = (activity: VoiceActivityData) => void
export type SystemHealthChangeHandler = (health: SystemHealthMetrics) => void

export interface VoiceActivityData {
  isListening: boolean
  isSpeaking: boolean
  level: number
  quality: 'good' | 'fair' | 'poor'
}

// Component Configuration Types
export interface HUDConfig {
  theme: 'light' | 'dark' | 'auto'
  animations: boolean
  autoRefresh: boolean
  refreshInterval: number
  language: 'sv' | 'en'
  compactMode: boolean
}

export interface ComponentVariants {
  status: Record<string, string>
  progress: Record<string, string>
  message: Record<string, string>
  voice: Record<string, string>
}

// Utility Types
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>
export type WithRequired<T, K extends keyof T> = T & Required<Pick<T, K>>
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P]
}

// Re-export commonly used React types for convenience
export type { FC, ReactNode, ComponentProps, HTMLAttributes } from 'react'