/**
 * Alice HUD Components - Centralized exports
 * Professional frontend HUD components for Alice AI Assistant
 */

// Status Indicators
export {
  StatusIndicator,
  ConnectionStatus,
  ProcessingStatus,
  VoiceActivityStatus,
  type StatusIndicatorProps,
  type ConnectionStatusProps,
  type ProcessingStatusProps,
  type VoiceActivityStatusProps
} from './status-indicator'

// Animated Progress Components
export {
  AnimatedProgress,
  CircularProgress,
  PulseProgress,
  StepProgress,
  type AnimatedProgressProps,
  type CircularProgressProps,
  type PulseProgressProps,
  type StepProgressProps
} from './animated-progress'

// Loading States and Spinners
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
} from './loading-spinner'

// Toast Notifications System
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
} from './toast'

// Message Display Components
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
} from './message-display'

// Voice Activity Indicators
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
} from './voice-activity-indicator'

// System Health Dashboard
export {
  SystemHealthDashboard,
  HealthCard,
  IntegrationStatus,
  useSystemHealth,
  formatUptime,
  type SystemHealthMetrics,
  type SystemHealthDashboardProps,
  type HealthCardProps,
  type IntegrationStatusProps
} from './system-health-dashboard'

// Existing UI Components (maintain compatibility)
export { Progress } from './progress'
export { Button, buttonVariants } from './button'
export { Badge } from './badge'
export { Card } from './card'