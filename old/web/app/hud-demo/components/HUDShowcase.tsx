'use client'

import React, { useState, useEffect } from 'react'
import {
  StatusIndicator,
  ConnectionStatus,
  ProcessingStatus,
  VoiceActivityStatus,
  AnimatedProgress,
  CircularProgress,
  PulseProgress,
  StepProgress,
  LoadingSpinner,
  LoadingState,
  LoadingOverlay,
  Skeleton,
  SkeletonText,
  LoadingButton,
  ToastProvider,
  useToastActions,
  MessageDisplay,
  InlineMessage,
  MessageBanner,
  ErrorBoundary,
  VoiceActivityIndicator,
  VoiceLevelMeter,
  VoiceStatusPill,
  WaveformVisualizer,
  MicrophoneIndicator,
  SystemHealthDashboard,
  useSystemHealth
} from '@/components/ui'

export function HUDShowcase() {
  const [isConnected, setIsConnected] = useState(true)
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [isListening, setIsListening] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [voiceLevel, setVoiceLevel] = useState(0.3)
  const [showOverlay, setShowOverlay] = useState(false)
  const [showBanner, setShowBanner] = useState(true)
  
  const toast = useToastActions()
  const { metrics, isLoading, refresh } = useSystemHealth()

  // Simulate dynamic progress
  useEffect(() => {
    if (isProcessing) {
      const interval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 100) {
            setIsProcessing(false)
            return 0
          }
          return prev + Math.random() * 15
        })
      }, 300)
      return () => clearInterval(interval)
    }
  }, [isProcessing])

  // Simulate voice level changes
  useEffect(() => {
    const interval = setInterval(() => {
      setVoiceLevel(Math.random())
    }, 200)
    return () => clearInterval(interval)
  }, [])

  const steps = [
    { label: 'Anslut till server', completed: true },
    { label: 'Authentisera användare', completed: true },
    { label: 'Ladda konfiguration', completed: false, active: true },
    { label: 'Starta röstmotor', completed: false },
    { label: 'Aktivera integrationer', completed: false }
  ]

  return (
    <ToastProvider maxToasts={3}>
      <div className="min-h-screen bg-gradient-to-br from-zinc-900 via-zinc-800 to-zinc-900 text-white">
        <div className="container mx-auto p-6 space-y-8">
          {/* Header */}
          <div className="text-center space-y-2">
            <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
              Alice HUD Components
            </h1>
            <p className="text-zinc-400 text-lg">
              Professional Frontend HUD Components för Alice AI Assistant
            </p>
          </div>

          {/* Message Banner */}
          {showBanner && (
            <MessageBanner
              type="info"
              message="Alice HUD-system är aktivt och fungerar som förväntat"
              onClose={() => setShowBanner(false)}
              data-testid="demo-banner"
            />
          )}

          {/* Control Panel */}
          <div className="bg-zinc-800/50 rounded-lg p-6 border border-zinc-700">
            <h2 className="text-xl font-semibold mb-4 text-cyan-300">Kontroller</h2>
            <div className="flex flex-wrap gap-4">
              <button
                onClick={() => setIsConnected(!isConnected)}
                className="px-4 py-2 bg-cyan-600 rounded hover:bg-cyan-700 transition-colors"
              >
                Toggle Anslutning
              </button>
              <button
                onClick={() => {
                  setIsProcessing(true)
                  setProgress(0)
                }}
                className="px-4 py-2 bg-purple-600 rounded hover:bg-purple-700 transition-colors"
                disabled={isProcessing}
              >
                Starta Bearbetning
              </button>
              <button
                onClick={() => setIsListening(!isListening)}
                className="px-4 py-2 bg-green-600 rounded hover:bg-green-700 transition-colors"
              >
                Toggle Lyssning
              </button>
              <button
                onClick={() => setIsSpeaking(!isSpeaking)}
                className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 transition-colors"
              >
                Toggle Tal
              </button>
              <button
                onClick={() => setShowOverlay(true)}
                className="px-4 py-2 bg-yellow-600 rounded hover:bg-yellow-700 transition-colors"
              >
                Visa Overlay
              </button>
            </div>
          </div>

          {/* Toast Demo */}
          <div className="bg-zinc-800/50 rounded-lg p-6 border border-zinc-700">
            <h2 className="text-xl font-semibold mb-4 text-cyan-300">Toast Notifieringar</h2>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => toast.swedish.success('saved')}
                className="px-3 py-2 bg-green-600 rounded text-sm"
              >
                Framgång
              </button>
              <button
                onClick={() => toast.swedish.error('network')}
                className="px-3 py-2 bg-red-600 rounded text-sm"
              >
                Fel
              </button>
              <button
                onClick={() => toast.swedish.warning('unsaved')}
                className="px-3 py-2 bg-yellow-600 rounded text-sm"
              >
                Varning
              </button>
              <button
                onClick={() => toast.swedish.info('processing')}
                className="px-3 py-2 bg-blue-600 rounded text-sm"
              >
                Info
              </button>
            </div>
          </div>

          {/* Status Indicators Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="bg-zinc-800/50 rounded-lg p-6 border border-zinc-700">
              <h3 className="text-lg font-semibold mb-4 text-cyan-300">Status Indikatorer</h3>
              <div className="space-y-4">
                <ConnectionStatus
                  isConnected={isConnected}
                  data-testid="demo-connection-status"
                />
                <ProcessingStatus
                  isProcessing={isProcessing}
                  progress={progress}
                  data-testid="demo-processing-status"
                />
                <VoiceActivityStatus
                  isListening={isListening}
                  isSpeaking={isSpeaking}
                  voiceLevel={voiceLevel}
                  data-testid="demo-voice-status"
                />
              </div>
            </div>

            <div className="bg-zinc-800/50 rounded-lg p-6 border border-zinc-700">
              <h3 className="text-lg font-semibold mb-4 text-cyan-300">Progress Components</h3>
              <div className="space-y-4">
                <AnimatedProgress
                  value={progress}
                  label="Behandling"
                  showValue={true}
                  animated={isProcessing}
                />
                <div className="flex items-center gap-4">
                  <CircularProgress
                    value={progress}
                    showValue={true}
                    animated={isProcessing}
                    size={50}
                  />
                  <PulseProgress
                    isActive={isProcessing}
                    label="Bearbetar..."
                  />
                </div>
              </div>
            </div>

            <div className="bg-zinc-800/50 rounded-lg p-6 border border-zinc-700">
              <h3 className="text-lg font-semibold mb-4 text-cyan-300">Loading States</h3>
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <LoadingSpinner variant="default" size="sm" />
                  <LoadingSpinner variant="dots" size="md" />
                  <LoadingSpinner variant="bars" size="lg" />
                </div>
                <Skeleton height="20px" />
                <SkeletonText lines={2} />
                <LoadingButton
                  isLoading={isProcessing}
                  loadingText="Bearbetar..."
                  onClick={() => {
                    setIsProcessing(true)
                    setProgress(0)
                  }}
                >
                  Starta Process
                </LoadingButton>
              </div>
            </div>
          </div>

          {/* Voice Activity Components */}
          <div className="bg-zinc-800/50 rounded-lg p-6 border border-zinc-700">
            <h3 className="text-lg font-semibold mb-4 text-cyan-300">Röst Aktivitet</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <VoiceActivityIndicator
                  isListening={isListening}
                  isSpeaking={isSpeaking}
                  voiceLevel={voiceLevel}
                  microphoneLevel={0.7}
                  data-testid="demo-voice-indicator"
                />
                <VoiceStatusPill
                  status={isSpeaking ? 'speaking' : isListening ? 'listening' : 'idle'}
                  data-testid="demo-voice-pill"
                />
                <MicrophoneIndicator
                  isActive={isListening || isSpeaking}
                  level={voiceLevel}
                  hasPermission={true}
                  data-testid="demo-mic-indicator"
                />
              </div>
              <div className="space-y-4">
                <WaveformVisualizer
                  isActive={isListening || isSpeaking}
                  bars={16}
                  height={60}
                  color="cyan"
                  data-testid="demo-waveform"
                />
                <VoiceLevelMeter
                  level={voiceLevel}
                  bars={8}
                  animated={true}
                  color="green"
                  data-testid="demo-level-meter"
                />
              </div>
            </div>
          </div>

          {/* Step Progress */}
          <div className="bg-zinc-800/50 rounded-lg p-6 border border-zinc-700">
            <h3 className="text-lg font-semibold mb-4 text-cyan-300">Steg Progress</h3>
            <StepProgress steps={steps} data-testid="demo-step-progress" />
          </div>

          {/* Message Examples */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <MessageDisplay
                type="success"
                title="Framgång"
                message="Alice röstmotor aktiverad framgångsrikt"
                dismissible={true}
                data-testid="demo-success-message"
              />
              <MessageDisplay
                type="warning"
                title="Varning"
                message="Mikrofonbehörighet kan behövas för optimal prestanda"
                data-testid="demo-warning-message"
              />
            </div>
            <div className="space-y-4">
              <MessageDisplay
                type="error"
                title="Fel"
                message="Kunde inte ansluta till Spotify API"
                action={{
                  label: 'Försök igen',
                  onClick: () => toast.info('Återansluter till Spotify...')
                }}
                data-testid="demo-error-message"
              />
              <InlineMessage
                type="info"
                message="System hälsokontroll pågår..."
                data-testid="demo-inline-message"
              />
            </div>
          </div>

          {/* System Health Dashboard */}
          <div className="bg-zinc-800/50 rounded-lg p-6 border border-zinc-700">
            <SystemHealthDashboard
              metrics={metrics}
              autoRefresh={true}
              refreshInterval={10000}
              data-testid="demo-health-dashboard"
            />
          </div>

          {/* Loading Overlay */}
          <LoadingOverlay
            isVisible={showOverlay}
            message="Laddar Alice system..."
            spinner={true}
            data-testid="demo-loading-overlay"
          />

          {/* Footer */}
          <div className="text-center text-zinc-500 text-sm">
            <p>Alice HUD Components - Professional Frontend för AI Assistant</p>
            <p>Alla komponenter har svenska språkstöd och TypeScript interfaces</p>
            
            {/* Close overlay button (for demo) */}
            {showOverlay && (
              <button
                onClick={() => setShowOverlay(false)}
                className="mt-4 px-4 py-2 bg-zinc-700 rounded hover:bg-zinc-600 transition-colors"
              >
                Stäng Overlay (Demo)
              </button>
            )}
          </div>
        </div>
      </div>
    </ToastProvider>
  )
}

export default HUDShowcase