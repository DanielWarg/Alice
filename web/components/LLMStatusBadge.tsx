'use client'

import React, { useState, useEffect } from 'react'

interface LLMStatus {
  coordinator: string
  models: {
    primary: {
      name: string
      failure_count: number
      circuit_breaker_open: boolean
      health_status?: {
        ok: boolean
        tftt_ms?: number
        error?: string
      }
    }
    fallback: {
      name: string
    }
  }
}

interface LLMStatusBadgeProps {
  className?: string
}

export default function LLMStatusBadge({ className = "" }: LLMStatusBadgeProps) {
  const [status, setStatus] = useState<LLMStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = async () => {
    try {
      const response = await fetch('/api/v1/llm/status')
      if (response.ok) {
        const data = await response.json()
        setStatus(data)
        setError(null)
      } else {
        setError(`HTTP ${response.status}`)
      }
    } catch (err) {
      setError('Network error')
      console.error('LLM status fetch failed:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    // Refresh every 30 seconds
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (): string => {
    if (isLoading || error) return 'bg-gray-600'
    
    if (status?.models?.primary?.circuit_breaker_open) {
      return 'bg-red-500'  // Circuit breaker open
    }
    
    if (status?.models?.primary?.health_status?.ok === false) {
      return 'bg-amber-500'  // Primary unhealthy
    }
    
    if (status?.coordinator === 'active') {
      return 'bg-green-500'  // All good
    }
    
    return 'bg-gray-500'
  }

  const getStatusText = (): string => {
    if (isLoading) return 'LLM: Loading...'
    if (error) return `LLM: ${error}`
    if (!status) return 'LLM: Unknown'
    
    const primary = status.models?.primary
    if (primary?.circuit_breaker_open) {
      return `LLM: ${status.models.fallback.name} (failover)`
    }
    
    if (primary?.health_status?.ok === false) {
      return `LLM: ${primary.name} (degraded)`
    }
    
    return `LLM: ${primary?.name || 'Unknown'} (healthy)`
  }

  const getTTFT = (): string => {
    if (!status?.models?.primary?.health_status?.tftt_ms) return ''
    
    const ttft = Math.round(status.models.primary.health_status.tftt_ms)
    return ` • ${ttft}ms`
  }

  const handleClick = () => {
    // Refresh status on click
    setIsLoading(true)
    fetchStatus()
  }

  return (
    <div 
      className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium text-white cursor-pointer transition-all duration-200 hover:scale-105 ${getStatusColor()} ${className}`}
      onClick={handleClick}
      title={`Click to refresh • Failures: ${status?.models?.primary?.failure_count || 0}`}
    >
      <div className="flex items-center space-x-1">
        {/* Status indicator dot */}
        <div className="w-2 h-2 rounded-full bg-white/80"></div>
        
        {/* Status text */}
        <span className="whitespace-nowrap">
          {getStatusText()}{getTTFT()}
        </span>
        
        {/* Circuit breaker indicator */}
        {status?.models?.primary?.circuit_breaker_open && (
          <span className="text-red-200" title="Circuit breaker open">⚡</span>
        )}
      </div>
    </div>
  )
}