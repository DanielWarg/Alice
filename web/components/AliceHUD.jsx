"use client";
import React, { useState, useEffect, Suspense } from "react";
import { ErrorBoundary, useErrorHandler } from "./ErrorBoundary";
import { SafeBootMode } from "./SafeBootMode";
import { AliceCoreVisualContainer } from "./AliceCoreVisual";
import ChatInterface from "./ChatInterface";
import SystemMetrics from "./SystemMetrics";
import { OverlayModules, OverlayProvider, OverlayTriggers } from "./OverlayModules";
import { Pane, GlowDot, RingGauge, AutoRing, Metric } from "./Pane";
import { formatTime, isoWeek } from "../lib/utils";

/**
 * AliceHUD - Main layout component for the modular Alice HUD system
 * 
 * Orchestrates all components and provides:
 * - Component communication
 * - Global state management
 * - Fallback UI for crashed components
 * - Performance optimization
 * - WebSocket integration
 * - Voice client preparation
 */

// Loading component
const LoadingSpinner = ({ text = "Loading..." }) => (
  <div className="flex items-center justify-center p-8">
    <div className="flex items-center gap-3">
      <div className="animate-spin h-6 w-6 border-2 border-cyan-400 border-t-transparent rounded-full"></div>
      <span className="text-cyan-300">{text}</span>
    </div>
  </div>
);

// Component fallback for error states
const ComponentFallback = ({ componentName }) => (
  <div className="min-h-[200px] rounded-xl border border-yellow-500/30 bg-yellow-950/20 p-6 text-center">
    <div className="mb-4">
      <div className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-yellow-500/20">
        <svg className="h-5 w-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01" />
        </svg>
      </div>
    </div>
    <h3 className="text-lg font-semibold text-yellow-200 mb-2">
      {componentName} Unavailable
    </h3>
    <p className="text-sm text-yellow-300/80">
      This module has been temporarily disabled for system stability.
    </p>
  </div>
);

// WebSocket hook for real-time updates
const useWebSocket = (url, options = {}) => {
  const [socket, setSocket] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');
  const [lastMessage, setLastMessage] = useState(null);
  const { handleError } = useErrorHandler();

  useEffect(() => {
    if (!url || options.disabled) return;

    try {
      const ws = new WebSocket(url);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setConnectionStatus('Connected');
        setSocket(ws);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          if (options.onMessage) {
            options.onMessage(data);
          }
        } catch (err) {
          console.warn('Failed to parse WebSocket message:', err);
        }
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setConnectionStatus('Disconnected');
        setSocket(null);
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('Error');
        handleError(new Error('WebSocket connection failed'));
      };

      return () => {
        ws.close();
      };
    } catch (err) {
      handleError(err);
    }
  }, [url, options.disabled]);

  const sendMessage = (message) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected');
    }
  };

  return { socket, connectionStatus, lastMessage, sendMessage };
};

// Main HUD component
export function AliceHUD({
  apiEndpoint = "http://localhost:8000",
  wsEndpoint = "ws://localhost:8000/ws",
  enableWebSocket = true,
  className = ""
}) {
  const [aiLevel, setAiLevel] = useState(0);
  const [globalState, setGlobalState] = useState({
    systemStatus: 'online',
    lastActivity: Date.now(),
    messageCount: 0
  });
  const [currentTime, setCurrentTime] = useState(new Date());
  const { error: globalError, handleError } = useErrorHandler();

  // WebSocket connection
  const { connectionStatus, lastMessage, sendMessage } = useWebSocket(
    enableWebSocket ? wsEndpoint : null,
    {
      disabled: false,
      onMessage: (data) => {
        // Handle real-time updates
        if (data.type === 'ai_speaking') {
          setAiLevel(data.level || 0);
        } else if (data.type === 'system_status') {
          setGlobalState(prev => ({ ...prev, systemStatus: data.status }));
        }
      }
    }
  );

  // Update time every second
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Global error monitoring
  useEffect(() => {
    const handleGlobalError = (event) => {
      handleError(new Error(event.message || 'Global error occurred'));
    };

    const handleUnhandledRejection = (event) => {
      handleError(new Error(`Unhandled promise rejection: ${event.reason}`));
    };

    window.addEventListener('error', handleGlobalError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleGlobalError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, [handleError]);

  // Handle component communication
  const handleSpeakLevel = (level) => {
    setAiLevel(level);
    // Optionally send to WebSocket
    if (sendMessage) {
      sendMessage({ type: 'ai_speaking', level });
    }
  };

  const handleMessageSent = (message) => {
    setGlobalState(prev => ({
      ...prev,
      lastActivity: Date.now(),
      messageCount: prev.messageCount + 1
    }));
  };

  // Format current time (using utility functions)
  const formatCurrentTime = () => {
    const time = currentTime.toLocaleTimeString('sv-SE', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
    const dateStr = currentTime.toLocaleDateString('sv-SE', { 
      day: '2-digit', 
      month: 'short', 
      year: 'numeric' 
    });
    const week = isoWeek(currentTime);
    return `${time}  |  ${dateStr}  •  v.${week}`;
  };

  // Connection status indicator
  const ConnectionStatus = () => (
    <div className="flex items-center gap-2 text-xs text-cyan-300/70">
      <div className={`w-2 h-2 rounded-full ${
        connectionStatus === 'Connected' ? 'bg-green-400' :
        connectionStatus === 'Error' ? 'bg-red-400' :
        'bg-yellow-400'
      }`} />
      <span>{connectionStatus}</span>
    </div>
  );

  // Icon components
  const SettingsIcon = (props) => (
    <svg {...props} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="3" />
    </svg>
  );

  const WeatherIcon = (props) => (
    <svg {...props} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="7" cy="7" r="3" />
      <path d="M12 3v2M12 19v2M4.22 4.22 5.64 5.64M18.36 18.36 19.78 19.78M1 12h2M21 12h2" />
    </svg>
  );

  const ThermometerIcon = (props) => (
    <svg {...props} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path d="M14 14.76V3a2 2 0 0 0-4 0v11.76" />
      <path d="M8 15a4 4 0 1 0 8 0" />
    </svg>
  );

  // Widget Components
  const AnimatedBackground = () => {
    const [particles, setParticles] = useState([]);
    
    useEffect(() => {
      // Safe Boot check - if enabled, show static background
      if (process.env.NODE_ENV === 'development' && false) { // Disabled for now
        return;
      }

      // Generate animated particles
      const newParticles = Array.from({ length: 30 }, (_, i) => ({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        z: Math.random() * 100,
        speed: 0.1 + Math.random() * 0.2,
        size: 1 + Math.random() * 1.5
      }));
      
      setParticles(newParticles);

      const interval = setInterval(() => {
        setParticles(prev => prev.map(p => ({
          ...p,
          y: p.y >= 100 ? -5 : p.y + p.speed,
          x: p.x + Math.sin(Date.now() * 0.001 + p.id) * 0.05
        })));
      }, 50);

      return () => clearInterval(interval);
    }, []);

    return (
      <div className="absolute inset-0 overflow-hidden">
        {particles.map(p => (
          <div
            key={p.id}
            className="absolute rounded-full bg-cyan-400 particle"
            style={{
              left: `${p.x}%`,
              top: `${p.y}%`,
              width: `${p.size}px`,
              height: `${p.size}px`,
              opacity: 0.1 + (p.z / 100) * 0.2,
              transform: `scale(${0.5 + (p.z / 100) * 0.5})`,
              boxShadow: `0 0 ${p.size * 2}px rgba(34, 211, 238, ${0.1 + (p.z / 100) * 0.2})`
            }}
          />
        ))}
      </div>
    );
  };

  const VoiceVisualization = () => {
    const [bars] = useState(Array.from({ length: 48 }, () => Math.random() * 0.8 + 0.1));
    
    return (
      <div className="relative h-24 w-full overflow-hidden rounded-lg border border-cyan-500/20 bg-cyan-900/20 p-2">
        <div className="absolute inset-x-2 top-1/2 h-px bg-cyan-400/10" />
        <div className="relative flex h-full items-center gap-[2px]">
          {bars.map((v, i) => (
            <div
              key={i}
              className="flex-1 audio-bar"
              style={{ height: `${Math.max(10, v * 100)}%` }}
            />
          ))}
        </div>
        <div className="mt-2 text-[11px] text-cyan-300/70">
          Simulerad ljuddetektering (Safe Boot)
        </div>
      </div>
    );
  };

  const DiagnosticsDisplay = () => {
    const steps = [
      { id: 'ui', label: 'Init UI' },
      { id: 'bus', label: 'Start HUD bus' },
      { id: 'data', label: 'Ladda stubbar' },
      { id: 'voice', label: 'Init röstmotor' },
      { id: 'video', label: 'Init video' },
      { id: 'time', label: 'Synka tid' }
    ];
    const [done, setDone] = useState(6); // All completed for demo

    const pct = Math.floor((done / steps.length) * 100);

    return (
      <div>
        <div className="relative h-2 w-full overflow-hidden rounded bg-cyan-900/40 ring-1 ring-inset ring-cyan-400/20">
          <div 
            className="absolute inset-y-0 left-0 bg-gradient-to-r from-cyan-500/50 to-cyan-400/70" 
            style={{ width: `${pct}%` }} 
          />
        </div>
        <ul className="mt-2 space-y-1 text-xs text-cyan-300/80">
          {steps.map((s, i) => (
            <li key={s.id} className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${i < done ? 'bg-cyan-300' : 'bg-cyan-300/30'}`} />
              <span>{s.label} {i < done && '— OK'}</span>
            </li>
          ))}
        </ul>
        <div className="mt-2 text-[11px] text-cyan-300/70">
          Safe Boot aktiv
        </div>
      </div>
    );
  };

  const TodoWidget = () => {
    const [todos, setTodos] = useState([
      { id: 1, text: "Setup weather API key", done: false },
      { id: 2, text: "Connect voice input", done: false }
    ]);

    return (
      <div className="space-y-2 text-xs text-cyan-300/70">
        {todos.map(todo => (
          <div key={todo.id} className="flex items-center gap-2 text-cyan-100">
            <div className={`w-3 h-3 rounded border ${todo.done ? 'bg-cyan-300/20 border-cyan-300' : 'border-cyan-400/30'}`} />
            <span className={todo.done ? 'line-through text-cyan-300/50' : ''}>{todo.text}</span>
          </div>
        ))}
      </div>
    );
  };

  const MediaPlayer = () => {
    const [currentTrack] = useState({ title: 'Ambient Space', artist: 'NOVA' });
    const [isPlaying] = useState(true);
    
    return (
      <div>
        <div className="text-sm text-cyan-200 mb-2">
          {currentTrack.title} • <span className="text-cyan-300/80">{currentTrack.artist}</span>
        </div>
        <div className="relative h-2 w-full overflow-hidden rounded bg-cyan-900/40 ring-1 ring-inset ring-cyan-400/20">
          <div className="absolute inset-y-0 left-0 bg-gradient-to-r from-cyan-500/50 to-cyan-400/70" style={{ width: '35%' }} />
        </div>
        <div className="mt-1 text-[11px] text-cyan-300/70">1:25 / 3:45</div>
      </div>
    );
  };

  // System status icons
  const SystemIcons = () => (
    <div className="flex items-center gap-3 opacity-80">
      {/* WiFi */}
      <svg className="h-4 w-4 text-cyan-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path d="M2 8c6-5 14-5 20 0M5 12c4-3 10-3 14 0M8.5 15.5c2-1.5 5-1.5 7 0" />
        <circle cx="12" cy="19" r="1" />
      </svg>
      {/* Battery */}
      <svg className="h-4 w-4 text-cyan-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <rect x="2" y="7" width="18" height="10" rx="2" />
        <rect x="20" y="10" width="2" height="4" />
      </svg>
      {/* Notifications */}
      <svg className="h-4 w-4 text-cyan-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path d="M6 8a6 6 0 1 1 12 0v6H6z" />
      </svg>
    </div>
  );

  return (
    <SafeBootMode>
      <OverlayProvider>
        <div className={`relative min-h-screen w-full overflow-hidden bg-[#030b10] text-cyan-100 ${className}`}>
          {/* Complex layered background system from original */}
          <div className="absolute inset-0 -z-10">
            {/* Gradient background layers */}
            <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-blue-900/10" />
            <div className="pointer-events-none absolute inset-0 hud-bg-pattern" />
            <div className="pointer-events-none absolute inset-0 hud-grid-pattern" />
            
            {/* Animated particles (Safe Boot aware) */}
            <AnimatedBackground />
          </div>

          {/* Header - Restored original layout */}
          <div className="mx-auto max-w-7xl px-6 pt-2 pb-2">
            <div className="grid grid-cols-3 items-center">
              {/* System status icons */}
              <div className="flex items-center gap-3 opacity-80">
                <SystemIcons />
                <ConnectionStatus />
              </div>

              {/* Center overlay triggers */}
              <div className="justify-self-center">
                <div className="flex items-center justify-center gap-3 whitespace-nowrap">
                  <OverlayTriggers />
                </div>
              </div>

              {/* Time and status */}
              <div className="flex items-center gap-2 justify-self-end text-cyan-300/80">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="9" />
                  <path d="M12 7v6h5" />
                </svg>
                <span className="tracking-widest text-xs uppercase">
                  {formatCurrentTime()}
                </span>
              </div>
            </div>
          </div>

          {/* Global error display */}
          {globalError && (
            <div className="mx-auto max-w-7xl px-6 py-3">
              <div className="rounded-xl border border-red-500/30 bg-red-950/20 p-3 text-sm text-red-200">
                <strong>System Alert:</strong> {globalError.message}
              </div>
            </div>
          )}

          {/* Main content - Restored original layout structure */}
          <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-6 pb-36 pt-0 md:grid-cols-12">
            
            {/* Left sidebar - System metrics with original Pane structure */}
            <div className="md:col-span-3 space-y-6">
              <ErrorBoundary 
                componentName="SystemMetrics"
                fallback={() => <ComponentFallback componentName="System Metrics" />}
              >
                <Suspense fallback={<LoadingSpinner text="Loading System Metrics..." />}>
                  <Pane title="System" actions={<SettingsIcon className="h-4 w-4" />}>
                    <SystemMetrics showDiagnostics={true} />
                  </Pane>
                </Suspense>
              </ErrorBoundary>

              {/* Voice visualization pane */}
              <Pane title="Röst – Auto">
                <VoiceVisualization />
              </Pane>

              {/* Diagnostics pane */}
              <Pane title="System start">
                <DiagnosticsDisplay />
              </Pane>
            </div>

            {/* Center - Alice Core and Chat (original structure) */}
            <div className="md:col-span-6 space-y-6">
              <ErrorBoundary 
                componentName="AliceCore"
                fallback={() => <ComponentFallback componentName="Alice Core" />}
              >
                <Pane 
                  title="Alice Core" 
                  className="min-h-[calc(100vh-140px)] flex flex-col"
                  contentClassName="flex flex-col h-full"
                >
                  {/* Alice visualization */}
                  <div className="flex justify-center py-6 shrink-0">
                    <Suspense fallback={<LoadingSpinner text="Loading Alice..." />}>
                      <AliceCoreVisualContainer
                        aiLevel={aiLevel}
                        size={360}
                      />
                    </Suspense>
                  </div>

                  {/* Chat interface */}
                  <div className="mt-4 flex-1">
                    <ErrorBoundary 
                      componentName="ChatInterface"
                      fallback={() => <ComponentFallback componentName="Chat Interface" />}
                    >
                      <Suspense fallback={<LoadingSpinner text="Loading Chat..." />}>
                        <ChatInterface
                          onSpeakLevel={handleSpeakLevel}
                          onMessageSent={handleMessageSent}
                          apiEndpoint={`${apiEndpoint}/api/chat/stream`}
                          className="h-full"
                        />
                      </Suspense>
                    </ErrorBoundary>
                  </div>
                </Pane>
              </ErrorBoundary>
            </div>

            {/* Right sidebar - Weather, Todo, Media (original structure) */}
            <div className="md:col-span-3 space-y-6">
              {/* Weather widget */}
              <Pane title="Weather" actions={<WeatherIcon className="h-4 w-4" />}>
                <div className="flex items-center gap-4">
                  <ThermometerIcon className="h-10 w-10 text-cyan-300" />
                  <div>
                    <div className="text-3xl font-semibold">21°C</div>
                    <div className="text-cyan-300/80 text-sm">Partly cloudy</div>
                  </div>
                </div>
              </Pane>

              {/* Todo List */}
              <Pane title="To-do">
                <TodoWidget />
              </Pane>

              {/* Media Player */}
              <Pane title="Media">
                <MediaPlayer />
              </Pane>
            </div>
          </main>

          {/* Footer status bar - Restored original exact styling */}
          <footer className="pointer-events-none absolute inset-x-0 bottom-0 mx-auto max-w-7xl px-6 pb-8">
            <div className="grid grid-cols-5 gap-4 opacity-80">
              {["SYS", "NET", "AUX", "NAV", "CTRL"].map((label, index) => (
                <div key={index} className="footer-indicator relative h-14 overflow-hidden rounded-xl">
                  <div className="absolute inset-0 grid place-items-center text-xs tracking-[.35em] text-cyan-200/70">
                    {label}
                  </div>
                </div>
              ))}
            </div>
          </footer>

          {/* Overlay modules */}
          <OverlayModules />
        </div>
      </OverlayProvider>
    </SafeBootMode>
  );
}

export default AliceHUD;