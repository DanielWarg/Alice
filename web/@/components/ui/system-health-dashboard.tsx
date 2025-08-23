'use client'

import * as React from "react"
import { cn } from "@/lib/utils"
import { 
  Activity, 
  Cpu, 
  HardDrive, 
  Wifi, 
  Battery, 
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Zap
} from "lucide-react"
import { StatusIndicator } from "./status-indicator"
import { AnimatedProgress, CircularProgress } from "./animated-progress"
import { VoiceActivityIndicator } from "./voice-activity-indicator"

// TypeScript interfaces for system health components
interface SystemHealthMetrics {
  cpu?: number
  memory?: number
  network?: {
    status: 'connected' | 'disconnected' | 'poor'
    latency?: number
    speed?: string
  }
  voice?: {
    isListening: boolean
    isSpeaking: boolean
    level: number
    quality?: 'good' | 'fair' | 'poor'
  }
  backend?: {
    status: 'healthy' | 'degraded' | 'down'
    responseTime?: number
    lastPing?: number
  }
  integrations?: {
    spotify?: boolean
    calendar?: boolean
    gmail?: boolean
  }
  uptime?: number
  lastUpdated?: number
}

interface SystemHealthDashboardProps {
  metrics: SystemHealthMetrics
  compact?: boolean
  autoRefresh?: boolean
  refreshInterval?: number
  className?: string
  'data-testid'?: string
}

interface HealthCardProps {
  title: string
  status: 'healthy' | 'warning' | 'error' | 'unknown'
  value?: string | number
  subtitle?: string
  icon?: React.ReactNode
  progress?: number
  className?: string
  'data-testid'?: string
}

interface IntegrationStatusProps {
  integrations: {
    spotify?: boolean
    calendar?: boolean
    gmail?: boolean
  }
  className?: string
  'data-testid'?: string
}

// Swedish translations for system health
const swedishHealthLabels = {
  cpu: 'Processor',
  memory: 'Minne',
  network: 'Nätverk',
  voice: 'Röst',
  backend: 'Backend',
  integrations: 'Integrationer',
  uptime: 'Drifttid',
  healthy: 'Felfritt',
  warning: 'Varning',
  error: 'Fel',
  unknown: 'Okänt',
  connected: 'Ansluten',
  disconnected: 'Frånkopplad',
  poor: 'Dålig',
  good: 'Bra',
  fair: 'Okej',
  degraded: 'Försämrad',
  down: 'Nere',
  spotify: 'Spotify',
  calendar: 'Kalender',
  gmail: 'Gmail'
}

// Main system health dashboard component
function SystemHealthDashboard({
  metrics,
  compact = false,
  autoRefresh = true,
  refreshInterval = 5000,
  className,
  'data-testid': testId
}: SystemHealthDashboardProps) {
  const [lastUpdate, setLastUpdate] = React.useState(Date.now())

  // Auto refresh effect
  React.useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      setLastUpdate(Date.now())
    }, refreshInterval)

    return () => clearInterval(interval)
  }, [autoRefresh, refreshInterval])

  // Calculate overall system health
  const getOverallHealth = (): 'healthy' | 'warning' | 'error' => {
    const issues: string[] = []

    if (metrics.cpu && metrics.cpu > 80) issues.push('cpu')
    if (metrics.memory && metrics.memory > 85) issues.push('memory')
    if (metrics.network?.status === 'disconnected') issues.push('network')
    if (metrics.backend?.status === 'down') issues.push('backend')
    if (metrics.voice?.quality === 'poor') issues.push('voice')

    if (issues.some(issue => ['network', 'backend'].includes(issue))) {
      return 'error'
    }
    if (issues.length > 0) {
      return 'warning'
    }
    return 'healthy'
  }

  const overallHealth = getOverallHealth()
  const healthColors = {
    healthy: 'text-green-400',
    warning: 'text-yellow-400',
    error: 'text-red-400'
  }

  if (compact) {
    return (
      <div className={cn("flex items-center gap-4 p-3 bg-zinc-900/50 rounded-lg border border-zinc-700", className)} data-testid={testId}>
        {/* Overall status */}
        <StatusIndicator
          status={overallHealth === 'healthy' ? 'connected' : overallHealth === 'warning' ? 'connecting' : 'error'}
          size="sm"
        />
        
        {/* Key metrics */}
        <div className="flex items-center gap-3 text-xs">
          {metrics.cpu && (
            <span className={metrics.cpu > 80 ? 'text-yellow-400' : 'text-zinc-400'}>
              CPU: {Math.round(metrics.cpu)}%
            </span>
          )}
          {metrics.network && (
            <span className={cn(
              metrics.network.status === 'connected' ? 'text-green-400' : 'text-red-400'
            )}>
              Nätverk: {swedishHealthLabels[metrics.network.status]}
            </span>
          )}
          {metrics.backend && (
            <span className={cn(
              metrics.backend.status === 'healthy' ? 'text-green-400' : 'text-yellow-400'
            )}>
              Backend: {swedishHealthLabels[metrics.backend.status]}
            </span>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className={cn("space-y-4", className)} data-testid={testId}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-zinc-200">Systemhälsa</h3>
        <div className="flex items-center gap-2">
          <span className={cn("text-sm font-medium", healthColors[overallHealth])}>
            {swedishHealthLabels[overallHealth]}
          </span>
          <StatusIndicator
            status={overallHealth === 'healthy' ? 'connected' : overallHealth === 'warning' ? 'connecting' : 'error'}
            size="sm"
          />
        </div>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* CPU Usage */}
        {metrics.cpu !== undefined && (
          <HealthCard
            title={swedishHealthLabels.cpu}
            status={metrics.cpu > 80 ? 'error' : metrics.cpu > 60 ? 'warning' : 'healthy'}
            value={`${Math.round(metrics.cpu)}%`}
            progress={metrics.cpu}
            icon={<Cpu className="w-4 h-4" />}
            data-testid="health-card-cpu"
          />
        )}

        {/* Memory Usage */}
        {metrics.memory !== undefined && (
          <HealthCard
            title={swedishHealthLabels.memory}
            status={metrics.memory > 85 ? 'error' : metrics.memory > 70 ? 'warning' : 'healthy'}
            value={`${Math.round(metrics.memory)}%`}
            progress={metrics.memory}
            icon={<HardDrive className="w-4 h-4" />}
            data-testid="health-card-memory"
          />
        )}

        {/* Network Status */}
        {metrics.network && (
          <HealthCard
            title={swedishHealthLabels.network}
            status={metrics.network.status === 'connected' ? 'healthy' : metrics.network.status === 'poor' ? 'warning' : 'error'}
            value={swedishHealthLabels[metrics.network.status]}
            subtitle={metrics.network.latency ? `${metrics.network.latency}ms` : undefined}
            icon={<Wifi className="w-4 h-4" />}
            data-testid="health-card-network"
          />
        )}

        {/* Voice Status */}
        {metrics.voice && (
          <HealthCard
            title={swedishHealthLabels.voice}
            status={metrics.voice.quality === 'good' ? 'healthy' : metrics.voice.quality === 'fair' ? 'warning' : 'error'}
            value={swedishHealthLabels[metrics.voice.quality || 'unknown']}
            subtitle={`Nivå: ${Math.round(metrics.voice.level * 100)}%`}
            icon={<VoiceActivityIndicator 
              isListening={metrics.voice.isListening}
              isSpeaking={metrics.voice.isSpeaking}
              voiceLevel={metrics.voice.level}
              showLabels={false}
              size="sm"
            />}
            data-testid="health-card-voice"
          />
        )}

        {/* Backend Status */}
        {metrics.backend && (
          <HealthCard
            title={swedishHealthLabels.backend}
            status={metrics.backend.status === 'healthy' ? 'healthy' : metrics.backend.status === 'degraded' ? 'warning' : 'error'}
            value={swedishHealthLabels[metrics.backend.status]}
            subtitle={metrics.backend.responseTime ? `${metrics.backend.responseTime}ms` : undefined}
            icon={<Activity className="w-4 h-4" />}
            data-testid="health-card-backend"
          />
        )}

        {/* Uptime */}
        {metrics.uptime && (
          <HealthCard
            title={swedishHealthLabels.uptime}
            status="healthy"
            value={formatUptime(metrics.uptime)}
            icon={<Clock className="w-4 h-4" />}
            data-testid="health-card-uptime"
          />
        )}
      </div>

      {/* Integrations Status */}
      {metrics.integrations && (
        <div className="mt-6">
          <h4 className="text-md font-medium text-zinc-300 mb-3">Integrationer</h4>
          <IntegrationStatus 
            integrations={metrics.integrations}
            data-testid="integration-status"
          />
        </div>
      )}

      {/* Last updated */}
      <div className="text-xs text-zinc-500 text-center">
        Senast uppdaterad: {new Date(lastUpdate).toLocaleTimeString('sv-SE')}
      </div>
    </div>
  )
}

// Health card component
function HealthCard({
  title,
  status,
  value,
  subtitle,
  icon,
  progress,
  className,
  'data-testid': testId
}: HealthCardProps) {
  const statusColors = {
    healthy: 'border-green-500/30 bg-green-900/10',
    warning: 'border-yellow-500/30 bg-yellow-900/10',
    error: 'border-red-500/30 bg-red-900/10',
    unknown: 'border-zinc-500/30 bg-zinc-900/10'
  }

  const statusIcons = {
    healthy: <CheckCircle className="w-3 h-3 text-green-400" />,
    warning: <AlertTriangle className="w-3 h-3 text-yellow-400" />,
    error: <XCircle className="w-3 h-3 text-red-400" />,
    unknown: <Activity className="w-3 h-3 text-zinc-400" />
  }

  return (
    <div 
      className={cn(
        "p-4 rounded-lg border backdrop-blur-sm",
        statusColors[status],
        className
      )}
      data-testid={testId}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-sm font-medium text-zinc-300">{title}</span>
        </div>
        {statusIcons[status]}
      </div>

      {/* Value */}
      <div className="text-lg font-semibold text-zinc-100 mb-1">
        {value}
      </div>

      {/* Subtitle */}
      {subtitle && (
        <div className="text-xs text-zinc-400 mb-2">
          {subtitle}
        </div>
      )}

      {/* Progress bar */}
      {progress !== undefined && (
        <AnimatedProgress
          value={progress}
          variant={status === 'healthy' ? 'success' : status === 'warning' ? 'warning' : 'error'}
          size="sm"
          animated={true}
        />
      )}
    </div>
  )
}

// Integration status component
function IntegrationStatus({
  integrations,
  className,
  'data-testid': testId
}: IntegrationStatusProps) {
  const integrationList = [
    { key: 'spotify' as const, label: swedishHealthLabels.spotify, icon: '🎵' },
    { key: 'calendar' as const, label: swedishHealthLabels.calendar, icon: '📅' },
    { key: 'gmail' as const, label: swedishHealthLabels.gmail, icon: '📧' }
  ]

  return (
    <div className={cn("flex flex-wrap gap-2", className)} data-testid={testId}>
      {integrationList.map(integration => {
        const isConnected = integrations[integration.key] === true
        
        return (
          <div
            key={integration.key}
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm",
              isConnected
                ? "bg-green-900/20 border-green-500/30 text-green-300"
                : "bg-zinc-900/20 border-zinc-500/30 text-zinc-400"
            )}
          >
            <span className="text-xs">{integration.icon}</span>
            <span>{integration.label}</span>
            <div className={cn(
              "w-2 h-2 rounded-full",
              isConnected ? "bg-green-400" : "bg-zinc-600"
            )} />
          </div>
        )
      })}
    </div>
  )
}

// Helper function to format uptime
function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / (24 * 60 * 60))
  const hours = Math.floor((seconds % (24 * 60 * 60)) / (60 * 60))
  const minutes = Math.floor((seconds % (60 * 60)) / 60)

  if (days > 0) {
    return `${days}d ${hours}h ${minutes}m`
  }
  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }
  return `${minutes}m`
}

// Hook for system health monitoring
function useSystemHealth() {
  const [metrics, setMetrics] = React.useState<SystemHealthMetrics>({})
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  const fetchMetrics = React.useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      // Mock implementation - replace with actual API calls
      const mockMetrics: SystemHealthMetrics = {
        cpu: Math.random() * 100,
        memory: Math.random() * 100,
        network: {
          status: Math.random() > 0.1 ? 'connected' : 'poor',
          latency: Math.random() * 100 + 10,
          speed: '100 Mbps'
        },
        voice: {
          isListening: Math.random() > 0.5,
          isSpeaking: Math.random() > 0.8,
          level: Math.random(),
          quality: Math.random() > 0.2 ? 'good' : 'fair'
        },
        backend: {
          status: Math.random() > 0.1 ? 'healthy' : 'degraded',
          responseTime: Math.random() * 200 + 50,
          lastPing: Date.now()
        },
        integrations: {
          spotify: Math.random() > 0.3,
          calendar: Math.random() > 0.2,
          gmail: Math.random() > 0.4
        },
        uptime: Math.random() * 86400 * 7, // Up to a week
        lastUpdated: Date.now()
      }
      
      setMetrics(mockMetrics)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch system metrics')
    } finally {
      setIsLoading(false)
    }
  }, [])

  React.useEffect(() => {
    fetchMetrics()
  }, [fetchMetrics])

  return {
    metrics,
    isLoading,
    error,
    refresh: fetchMetrics
  }
}

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
}