'use client';
import { useState, useEffect } from 'react';
import { useGuardianSummary } from '../lib/guardian-metrics-hooks';

interface GuardianStatus {
  mode: 'ok' | 'degrade' | 'stop' | 'unknown' | 'error';
  guardian_status: string;
  uptime_seconds?: number;
  ram_pct?: number;
  cpu_pct?: number;
  emergency_mode?: boolean;
  degraded?: boolean;
}

interface BadgeColors {
  bg: string;
  text: string;
  border: string;
  pulse?: boolean;
}

const getStatusColors = (status: GuardianStatus): BadgeColors => {
  switch (status.mode) {
    case 'ok':
      return {
        bg: 'bg-green-500/20',
        text: 'text-green-300',
        border: 'border-green-500/30',
      };
    case 'degrade':
      return {
        bg: 'bg-yellow-500/20',
        text: 'text-yellow-300',
        border: 'border-yellow-500/30',
        pulse: true,
      };
    case 'stop':
      return {
        bg: 'bg-red-500/20',
        text: 'text-red-300',
        border: 'border-red-500/30',
        pulse: true,
      };
    case 'unknown':
    case 'error':
    default:
      return {
        bg: 'bg-gray-500/20',
        text: 'text-gray-300',
        border: 'border-gray-500/30',
      };
  }
};

const getStatusText = (status: GuardianStatus): { main: string; sub: string } => {
  switch (status.mode) {
    case 'ok':
      return {
        main: '🛡️ Guardian OK',
        sub: 'System protected'
      };
    case 'degrade':
      return {
        main: '⚠️ Guardian Brownout',
        sub: 'Performance reduced'
      };
    case 'stop':
      return {
        main: '🚨 Guardian Lockdown',
        sub: 'Requests blocked'
      };
    case 'unknown':
      return {
        main: '❓ Guardian Unknown',
        sub: 'Status unclear'
      };
    case 'error':
    default:
      return {
        main: '❌ Guardian Error',
        sub: 'Connection failed'
      };
  }
};

const formatUptime = (seconds: number): string => {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h`;
};

export default function GuardianStatusBadge() {
  const [status, setStatus] = useState<GuardianStatus>({ mode: 'unknown', guardian_status: 'loading' });
  const [showDetails, setShowDetails] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // Use Guardian metrics hook for real data
  const { data: guardianData, error, isLoading } = useGuardianSummary({
    refreshInterval: 2000, // Update every 2 seconds
    enabled: true
  });

  useEffect(() => {
    if (guardianData) {
      // Map Guardian metrics data to our status format
      const mappedStatus: GuardianStatus = {
        mode: guardianData.guardian_mode || 'unknown',
        guardian_status: guardianData.status || 'unknown',
        uptime_seconds: guardianData.uptime_seconds,
        ram_pct: guardianData.metrics?.ram_pct,
        cpu_pct: guardianData.metrics?.cpu_pct,
        emergency_mode: guardianData.metrics?.emergency_mode,
        degraded: guardianData.metrics?.degraded
      };
      setStatus(mappedStatus);
      setLastUpdate(new Date());
    } else if (error) {
      setStatus({ mode: 'error', guardian_status: 'connection_failed' });
      setLastUpdate(new Date());
    }
  }, [guardianData, error]);

  const colors = getStatusColors(status);
  const statusText = getStatusText(status);

  const handleClick = () => {
    setShowDetails(!showDetails);
  };

  return (
    <div className="relative">
      {/* Main Badge */}
      <div 
        className={`
          px-3 py-1.5 rounded-lg border cursor-pointer
          transition-all duration-300 hover:scale-105
          ${colors.bg} ${colors.text} ${colors.border}
          ${colors.pulse ? 'animate-pulse' : ''}
          backdrop-blur-sm
        `}
        onClick={handleClick}
        title="Click for Guardian details"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{statusText.main}</span>
          {isLoading && (
            <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
          )}
        </div>
      </div>

      {/* Detailed Status Panel */}
      {showDetails && (
        <div className="absolute top-full right-0 mt-2 w-80 z-50">
          <div className={`
            p-4 rounded-xl border backdrop-blur-md
            ${colors.bg} ${colors.text} ${colors.border}
            shadow-lg
          `}>
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold">Guardian System Status</h3>
              <button 
                onClick={handleClick}
                className="text-sm opacity-60 hover:opacity-100"
              >
                ✕
              </button>
            </div>

            {/* Status Overview */}
            <div className="space-y-2 mb-4">
              <div className="flex justify-between">
                <span className="text-sm opacity-80">Status:</span>
                <span className="text-sm font-medium">{statusText.main}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm opacity-80">Mode:</span>
                <span className="text-sm">{statusText.sub}</span>
              </div>
              {status.uptime_seconds && (
                <div className="flex justify-between">
                  <span className="text-sm opacity-80">Uptime:</span>
                  <span className="text-sm">{formatUptime(status.uptime_seconds)}</span>
                </div>
              )}
            </div>

            {/* System Metrics */}
            {(status.ram_pct || status.cpu_pct) && (
              <div className="space-y-2 mb-4">
                <h4 className="text-sm font-medium opacity-80">System Metrics</h4>
                {status.ram_pct && (
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span>RAM Usage</span>
                      <span>{(status.ram_pct * 100).toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-white/10 rounded-full h-1.5">
                      <div 
                        className={`h-1.5 rounded-full transition-all duration-300 ${
                          status.ram_pct > 0.9 ? 'bg-red-400' : 
                          status.ram_pct > 0.8 ? 'bg-yellow-400' : 
                          'bg-green-400'
                        }`}
                        style={{ width: `${status.ram_pct * 100}%` }}
                      />
                    </div>
                  </div>
                )}
                {status.cpu_pct && (
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span>CPU Usage</span>
                      <span>{(status.cpu_pct * 100).toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-white/10 rounded-full h-1.5">
                      <div 
                        className={`h-1.5 rounded-full transition-all duration-300 ${
                          status.cpu_pct > 0.9 ? 'bg-red-400' : 
                          status.cpu_pct > 0.8 ? 'bg-yellow-400' : 
                          'bg-green-400'
                        }`}
                        style={{ width: `${status.cpu_pct * 100}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Status Indicators */}
            <div className="space-y-1 mb-4">
              <h4 className="text-sm font-medium opacity-80">Protection Status</h4>
              <div className="flex gap-2 flex-wrap">
                <span className={`px-2 py-1 rounded text-xs ${
                  status.emergency_mode ? 'bg-red-500/30 text-red-300' : 'bg-green-500/30 text-green-300'
                }`}>
                  {status.emergency_mode ? 'Emergency' : 'Normal'}
                </span>
                <span className={`px-2 py-1 rounded text-xs ${
                  status.degraded ? 'bg-yellow-500/30 text-yellow-300' : 'bg-green-500/30 text-green-300'
                }`}>
                  {status.degraded ? 'Degraded' : 'Full Power'}
                </span>
              </div>
            </div>

            {/* Quick Actions */}
            {status.mode === 'degrade' && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium opacity-80">Quick Actions</h4>
                <div className="flex gap-2">
                  <button 
                    className="px-3 py-1 bg-blue-500/30 text-blue-300 rounded text-xs hover:bg-blue-500/40 transition-colors"
                    onClick={() => window.open('/guardian-metrics-test', '_blank')}
                  >
                    View Metrics
                  </button>
                  <button 
                    className="px-3 py-1 bg-green-500/30 text-green-300 rounded text-xs hover:bg-green-500/40 transition-colors"
                    onClick={() => {
                      // Could implement manual recovery trigger here
                      alert('Manual recovery would be triggered here in production');
                    }}
                  >
                    Force Recovery
                  </button>
                </div>
              </div>
            )}

            {/* Footer */}
            {lastUpdate && (
              <div className="mt-4 pt-3 border-t border-white/10">
                <div className="flex justify-between items-center text-xs opacity-60">
                  <span>Last updated</span>
                  <span>{lastUpdate.toLocaleTimeString()}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Simplified compact version for header bars
export function GuardianStatusIndicator() {
  const { data: guardianData, error } = useGuardianSummary({
    refreshInterval: 5000 // Less frequent updates for indicator
  });

  const mode = guardianData?.guardian_mode || (error ? 'error' : 'unknown');
  
  const getIndicatorColor = (mode: string): string => {
    switch (mode) {
      case 'ok': return 'bg-green-400';
      case 'degrade': return 'bg-yellow-400 animate-pulse';
      case 'stop': return 'bg-red-400 animate-pulse';
      default: return 'bg-gray-400';
    }
  };

  const getStatusEmoji = (mode: string): string => {
    switch (mode) {
      case 'ok': return '🛡️';
      case 'degrade': return '⚠️';
      case 'stop': return '🚨';
      default: return '❓';
    }
  };

  return (
    <div 
      className="flex items-center gap-2 px-2 py-1 rounded-lg bg-black/20 backdrop-blur-sm"
      title={`Guardian status: ${mode}`}
    >
      <div className={`w-2 h-2 rounded-full ${getIndicatorColor(mode)}`} />
      <span className="text-xs">{getStatusEmoji(mode)}</span>
    </div>
  );
}