"use client";
import React, { useState, useEffect, useRef } from "react";
import { ErrorBoundary } from "./ErrorBoundary";
import { useSafeBootMode } from "./SafeBootMode";

/**
 * SystemMetrics - System status and performance metrics for Alice HUD
 * 
 * Provides real-time monitoring of:
 * - CPU usage simulation
 * - Memory usage
 * - Network activity
 * - System diagnostics
 * - Performance indicators
 */

// System metrics hooks and utilities
const clampPercent = (value) => Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));

const useSystemMetrics = () => {
  const [metrics, setMetrics] = useState({
    cpu: 37,
    memory: 52,
    network: 8,
    disk: 45,
    temperature: 42
  });
  
  const intervalRef = useRef(null);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setMetrics(prev => ({
        cpu: clampPercent(prev.cpu + (Math.random() * 10 - 5)),
        memory: clampPercent(prev.memory + (Math.random() * 6 - 3)),
        network: clampPercent(prev.network + (Math.random() * 14 - 7)),
        disk: clampPercent(prev.disk + (Math.random() * 4 - 2)),
        temperature: Math.max(20, Math.min(80, prev.temperature + (Math.random() * 2 - 1)))
      }));
    }, 1100);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return metrics;
};

// Ring gauge component for metrics visualization
const RingGauge = ({ 
  size = 116, 
  value, 
  label, 
  icon, 
  showValue = true,
  warningThreshold = 80,
  criticalThreshold = 95 
}) => {
  const normalizedValue = clampPercent(value);
  const radius = size * 0.42;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = (normalizedValue / 100) * circumference;
  
  // Determine color based on thresholds
  const getColor = () => {
    if (normalizedValue >= criticalThreshold) return '#ef4444'; // red
    if (normalizedValue >= warningThreshold) return '#f59e0b'; // orange
    return '#22d3ee'; // cyan
  };

  return (
    <div 
      className="relative grid place-items-center" 
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id={`gradient-${label}`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={getColor()} />
            <stop offset="100%" stopColor={getColor()} stopOpacity="0.6" />
          </linearGradient>
          <filter id={`glow-${label}`} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        
        {/* Background ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeOpacity="0.1"
          strokeWidth="8"
          fill="none"
          className="text-cyan-500"
        />
        
        {/* Progress ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={`url(#gradient-${label})`}
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - dashOffset}
          style={{ 
            transition: "stroke-dashoffset 0.6s ease",
          }}
          filter={`url(#glow-${label})`}
        />
      </svg>
      
      {/* Center content */}
      <div className="absolute inset-0 grid place-items-center">
        <div className="text-center">
          {icon && (
            <div className="flex items-center justify-center mb-1 text-cyan-300">
              {icon}
            </div>
          )}
          {showValue && (
            <div className="text-2xl font-semibold text-cyan-100">
              {Math.round(normalizedValue)}
              <span className="text-cyan-400 text-sm ml-1">%</span>
            </div>
          )}
          {label && (
            <div className="text-xs text-cyan-300/80 uppercase tracking-wide">
              {label}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Auto-sizing ring component
const AutoRing = ({ value, icon, label, className = "" }) => {
  const containerRef = useRef(null);
  const [size, setSize] = useState(96);

  useEffect(() => {
    if (!containerRef.current) return;
    
    const updateSize = () => {
      if (containerRef.current) {
        const width = containerRef.current.offsetWidth;
        const newSize = Math.max(70, Math.min(120, width - 10));
        setSize(newSize);
      }
    };

    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(containerRef.current);
    
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={containerRef} className={`w-full aspect-square flex items-center justify-center ${className}`}>
      <RingGauge size={size} value={value} icon={icon} label={label} showValue={false} />
    </div>
  );
};

// Simple metric display
const MetricCard = ({ label, value, icon, unit = "%", className = "" }) => (
  <div className={`text-center p-3 rounded-lg border border-cyan-500/20 bg-cyan-900/10 ${className}`}>
    <div className="flex items-center justify-center gap-2 text-xs text-cyan-300/80 mb-2">
      {icon}
      <span className="uppercase tracking-wide">{label}</span>
    </div>
    <div className="text-xl font-semibold text-cyan-100">
      {typeof value === 'number' ? Math.round(value) : value}
      <span className="text-cyan-400 text-sm ml-1">{unit}</span>
    </div>
  </div>
);

// System diagnostics component
const SystemDiagnostics = () => {
  const [diagnostics, setDiagnostics] = useState({
    uptime: 0,
    processes: 0,
    connections: 0,
    errors: 0
  });

  useEffect(() => {
    // Simulate system diagnostics
    const interval = setInterval(() => {
      setDiagnostics(prev => ({
        uptime: prev.uptime + 1,
        processes: 45 + Math.floor(Math.random() * 10),
        connections: 8 + Math.floor(Math.random() * 5),
        errors: prev.errors + (Math.random() < 0.1 ? 1 : 0)
      }));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const formatUptime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="flex justify-between text-cyan-300">
          <span>Uptime:</span>
          <span className="font-mono">{formatUptime(diagnostics.uptime)}</span>
        </div>
        <div className="flex justify-between text-cyan-300">
          <span>Processes:</span>
          <span className="font-mono">{diagnostics.processes}</span>
        </div>
        <div className="flex justify-between text-cyan-300">
          <span>Connections:</span>
          <span className="font-mono">{diagnostics.connections}</span>
        </div>
        <div className="flex justify-between text-cyan-300">
          <span>Errors:</span>
          <span className={`font-mono ${diagnostics.errors > 0 ? 'text-orange-400' : 'text-cyan-300'}`}>
            {diagnostics.errors}
          </span>
        </div>
      </div>
    </div>
  );
};

// Main SystemMetrics component
export function SystemMetrics({ 
  className = "", 
  showDiagnostics = true,
  compactMode = false,
  refreshRate = 1000
}) {
  const { safeBootEnabled } = useSafeBootMode();
  const metrics = useSystemMetrics();
  const [viewMode, setViewMode] = useState('overview'); // 'overview', 'detailed', 'minimal'

  // Icons (simple SVG components)
  const CpuIcon = () => (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <rect x="9" y="9" width="6" height="6" />
    </svg>
  );

  const MemoryIcon = () => (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <rect x="2" y="7" width="20" height="10" rx="2" />
      <circle cx="6.5" cy="12" r="1" />
    </svg>
  );

  const NetworkIcon = () => (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <polyline points="22,12 18,12 15,21 9,3 6,12 2,12" />
    </svg>
  );

  const TemperatureIcon = () => (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4 4 0 1 0 5 0z" />
    </svg>
  );

  const SettingsIcon = () => (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6M4.22 19.78l4.24-4.24M15.54 8.46l4.24-4.24" />
    </svg>
  );

  if (compactMode) {
    return (
      <ErrorBoundary componentName="SystemMetrics">
        <div className={`space-y-4 ${className}`}>
          {/* Compact view - just essential metrics */}
          <div className="grid grid-cols-3 gap-3">
            <MetricCard label="CPU" value={metrics.cpu} icon={<CpuIcon />} />
            <MetricCard label="MEM" value={metrics.memory} icon={<MemoryIcon />} />
            <MetricCard label="NET" value={metrics.network} icon={<NetworkIcon />} />
          </div>
          
          {safeBootEnabled && (
            <div className="text-xs text-orange-300/70 text-center">
              Safe Boot - Limited metrics
            </div>
          )}
        </div>
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary componentName="SystemMetrics">
      <div className={`space-y-6 ${className}`}>
        {/* Header with view controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-cyan-400" />
            <h3 className="text-cyan-200/90 text-xs uppercase tracking-widest">
              System Metrics
            </h3>
          </div>
          <div className="flex gap-1">
            <button
              onClick={() => setViewMode(viewMode === 'detailed' ? 'overview' : 'detailed')}
              className="p-1 rounded border border-cyan-400/30 hover:bg-cyan-400/10"
            >
              <SettingsIcon />
            </button>
          </div>
        </div>

        {/* Overview metrics */}
        <div className="grid grid-cols-3 gap-4">
          <MetricCard 
            label="CPU" 
            value={metrics.cpu} 
            icon={<CpuIcon />}
          />
          <MetricCard 
            label="Memory" 
            value={metrics.memory} 
            icon={<MemoryIcon />}
          />
          <MetricCard 
            label="Network" 
            value={metrics.network} 
            icon={<NetworkIcon />}
          />
        </div>

        {/* Ring gauges */}
        <div className="grid grid-cols-3 gap-4">
          <AutoRing value={metrics.cpu} icon={<CpuIcon />} label="CPU" />
          <AutoRing value={metrics.memory} icon={<MemoryIcon />} label="MEM" />
          <AutoRing value={metrics.network} icon={<NetworkIcon />} label="NET" />
        </div>

        {/* Detailed view */}
        {viewMode === 'detailed' && (
          <div className="space-y-4">
            {/* Temperature and disk */}
            <div className="grid grid-cols-2 gap-4">
              <MetricCard 
                label="Temperature" 
                value={metrics.temperature} 
                icon={<TemperatureIcon />}
                unit="°C"
              />
              <MetricCard 
                label="Disk" 
                value={metrics.disk} 
                icon={<MemoryIcon />}
                unit="%"
              />
            </div>
            
            {/* System diagnostics */}
            {showDiagnostics && (
              <div className="rounded-lg border border-cyan-500/20 bg-cyan-900/10 p-4">
                <h4 className="text-sm font-semibold text-cyan-200 mb-3">
                  System Diagnostics
                </h4>
                <SystemDiagnostics />
              </div>
            )}
          </div>
        )}

        {/* Safe boot indicator */}
        {safeBootEnabled && (
          <div className="text-xs text-orange-300/70 bg-orange-950/20 border border-orange-500/20 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-orange-400" />
              Safe Boot Mode - Simulated metrics only
            </div>
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
}

export default SystemMetrics;