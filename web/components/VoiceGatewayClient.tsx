'use client'

import React, { useEffect, useRef, useState, useCallback } from 'react'

// Types for Voice-Gateway Protocol
interface VoiceGatewayClientProps {
  personality?: string
  emotion?: string
  voiceQuality?: string
  className?: string
  onTranscript?: (text: string, isFinal: boolean) => void
  onError?: (error: string) => void
  onConnectionChange?: (connected: boolean) => void
  onEnergyLevel?: (level: number) => void  // For Alice Core ring animation
  onVoiceState?: (state: VoiceState) => void
  onIntentRoute?: (route: IntentRoute) => void
}

// Voice-Gateway Protocol Types
type VoiceState = 'idle' | 'listening' | 'processing' | 'thinking' | 'speaking' | 'error'
type ProcessingPath = 'fast' | 'think' | 'hybrid'
type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error'

interface IntentRoute {
  path: ProcessingPath
  intent_category: string
  confidence: number
  reasoning: string
  estimated_latency_ms: number
}

interface TelemetryData {
  voice_state: VoiceState
  energy_level: number
  processing_path?: ProcessingPath
  intent_confidence?: number
  latency_ms?: number
  timestamp: number
}

interface VoiceGatewayMessage {
  type: string
  [key: string]: any
}

export default function VoiceGatewayClient({
  personality = 'alice',
  emotion = 'friendly', 
  voiceQuality = 'medium',
  className = '',
  onTranscript,
  onError,
  onConnectionChange,
  onEnergyLevel,
  onVoiceState,
  onIntentRoute
}: VoiceGatewayClientProps) {
  // Connection and session state
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected')
  const [voiceState, setVoiceState] = useState<VoiceState>('idle')
  const [currentPath, setCurrentPath] = useState<ProcessingPath | null>(null)
  
  // Audio refs and state
  const audioContextRef = useRef<AudioContext | null>(null)
  const micStreamRef = useRef<MediaStream | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null)
  const isRecordingRef = useRef<boolean>(false)
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)
  
  // WebSocket connection
  const wsRef = useRef<WebSocket | null>(null)
  const sessionIdRef = useRef<string | null>(null)
  
  // State
  const [transcripts, setTranscripts] = useState<string[]>([])
  const [currentResponse, setCurrentResponse] = useState<string>('')
  const [energyLevel, setEnergyLevel] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)
  const [isThinking, setIsThinking] = useState(false)
  
  // Voice-Gateway specific state
  const [intentRoute, setIntentRoute] = useState<IntentRoute | null>(null)
  const [latencyMetrics, setLatencyMetrics] = useState<{[key: string]: number}>({})
  
  // Audio processing configuration
  const audioConfig = {
    sampleRate: 24000,
    channels: 1,
    bufferSize: 4096,
    chunkSizeMs: 100  // Send 100ms chunks
  }

  // Setup Voice-Gateway WebSocket connection
  const connectToVoiceGateway = useCallback(async () => {
    try {
      setConnectionState('connecting')
      setError(null)
      
      // Generate session ID
      const sessionId = `voice_gateway_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      sessionIdRef.current = sessionId
      
      // Get WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      const wsUrl = `${protocol}//${host}/ws/voice-gateway/${sessionId}`
      
      console.log('Connecting to Voice-Gateway:', wsUrl)
      
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws
      
      return new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('WebSocket connection timeout'))
        }, 10000)
        
        ws.onopen = () => {
          clearTimeout(timeout)
          console.log('Voice-Gateway connected')
          
          // Send initial configuration
          ws.send(JSON.stringify({
            type: 'control.configure',
            config: {
              audio: {
                sample_rate: audioConfig.sampleRate,
                channels: audioConfig.channels,
                format: 'pcm16'
              },
              personality,
              emotion,
              voiceQuality,
              language: 'sv-SE'
            }
          }))
          
          setConnectionState('connected')
          onConnectionChange?.(true)
          resolve()
        }
        
        ws.onmessage = (event) => {
          try {
            const data: VoiceGatewayMessage = JSON.parse(event.data)
            handleVoiceGatewayMessage(data)
          } catch (err) {
            console.error('Failed to parse Voice-Gateway message:', err)
          }
        }
        
        ws.onclose = () => {
          console.log('Voice-Gateway disconnected')
          setConnectionState('disconnected')
          setVoiceState('idle')
          onConnectionChange?.(false)
        }
        
        ws.onerror = (error) => {
          clearTimeout(timeout)
          console.error('Voice-Gateway error:', error)
          setError('WebSocket connection failed')
          setConnectionState('error')
          reject(error)
        }
      })
      
    } catch (err) {
      console.error('Voice-Gateway connection failed:', err)
      setError(`Connection failed: ${err instanceof Error ? err.message : String(err)}`)
      setConnectionState('error')
      onConnectionChange?.(false)
      throw err
    }
  }, [personality, emotion, voiceQuality, onConnectionChange])

  // Handle messages from Voice-Gateway WebSocket
  const handleVoiceGatewayMessage = (data: VoiceGatewayMessage) => {
    switch (data.type) {
      case 'telemetry':
        handleTelemetryUpdate(data.data as TelemetryData)
        break
        
      case 'transcription':
        handleTranscription(data.text, data.latency_ms)
        break
        
      case 'acknowledge':
        handleAcknowledgment(data.message, data.path, data.intent, data.confidence)
        break
        
      case 'thinking':
        handleThinkingState(data.message, data.path, data.intent, data.confidence)
        break
        
      case 'response':
        handleResponse(data.text, data.path, data.final, data.latency_ms, data.cached)
        break
        
      case 'response_chunk':
        handleResponseChunk(data.text, data.path, data.final, data.reasoning_steps, data.tools_used)
        break
        
      case 'interrupted':
        handleInterruption()
        break
        
      case 'error':
        handleError(data.message, data.details)
        break
        
      case 'pong':
        // Keep-alive response
        break
        
      default:
        console.warn('Unknown Voice-Gateway message type:', data.type)
    }
  }

  // Handle telemetry updates for UI animations
  const handleTelemetryUpdate = (telemetry: TelemetryData) => {
    setVoiceState(telemetry.voice_state)
    setEnergyLevel(telemetry.energy_level)
    
    // Update processing path if provided
    if (telemetry.processing_path) {
      setCurrentPath(telemetry.processing_path)
    }
    
    // Update latency metrics
    if (telemetry.latency_ms) {
      setLatencyMetrics(prev => ({
        ...prev,
        [telemetry.voice_state]: telemetry.latency_ms!
      }))
    }
    
    // Notify parent components
    onEnergyLevel?.(telemetry.energy_level)
    onVoiceState?.(telemetry.voice_state)
  }

  // Handle transcription results
  const handleTranscription = (text: string, latencyMs: number) => {
    setTranscripts(prev => [...prev, text])
    onTranscript?.(text, true)
    
    // Update latency metrics
    setLatencyMetrics(prev => ({
      ...prev,
      transcription: latencyMs
    }))
  }

  // Handle acknowledgment responses
  const handleAcknowledgment = (message: string, path: ProcessingPath, intent: string, confidence: number) => {
    setCurrentResponse(message)
    setCurrentPath(path)
    setIsThinking(false)
    
    const route: IntentRoute = {
      path,
      intent_category: intent,
      confidence,
      reasoning: `${path}_path_selected`,
      estimated_latency_ms: 0
    }
    
    setIntentRoute(route)
    onIntentRoute?.(route)
    
    // Synthesize acknowledgment
    synthesizeAndPlay(message)
  }

  // Handle thinking state
  const handleThinkingState = (message: string, path: ProcessingPath, intent: string, confidence: number) => {
    setIsThinking(true)
    setCurrentResponse(message)
    setCurrentPath(path)
    setVoiceState('thinking')
    
    const route: IntentRoute = {
      path,
      intent_category: intent,
      confidence,
      reasoning: 'complex_processing_required',
      estimated_latency_ms: 2000
    }
    
    setIntentRoute(route)
    onIntentRoute?.(route)
  }

  // Handle final responses
  const handleResponse = (text: string, path: ProcessingPath, isFinal: boolean, latencyMs?: number, cached?: boolean) => {
    if (isFinal) {
      setCurrentResponse(text)
      setIsThinking(false)
      setVoiceState('speaking')
      
      // Update latency metrics
      if (latencyMs) {
        setLatencyMetrics(prev => ({
          ...prev,
          [path + '_response']: latencyMs
        }))
      }
      
      // Show cache indicator if response was cached
      if (cached) {
        console.log('Fast path cache hit')
      }
      
      // Synthesize and play response
      synthesizeAndPlay(text)
    }
  }
  
  // Handle streaming response chunks (Phase 2)
  const handleResponseChunk = (text: string, path: ProcessingPath, isFinal: boolean, reasoningSteps?: string[], toolsUsed?: string[]) => {
    if (!isFinal) {
      // Append to current response for streaming effect
      setCurrentResponse(prev => prev + text)
      
      // Log reasoning steps for development
      if (reasoningSteps && reasoningSteps.length > 0) {
        console.log('Reasoning steps:', reasoningSteps)
      }
      
      // Log tools used
      if (toolsUsed && toolsUsed.length > 0) {
        console.log('Tools used:', toolsUsed)
      }
    }
  }

  // Handle interruptions (barge-in)
  const handleInterruption = () => {
    // Stop current audio playback
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current = null
    }
    
    setIsThinking(false)
    setCurrentResponse('')
    setVoiceState('idle')
  }

  // Handle errors
  const handleError = (message: string, details?: string) => {
    setError(message)
    setVoiceState('error')
    onError?.(message)
    
    console.error('Voice-Gateway error:', message, details)
  }

  // Setup audio input with real-time processing
  const setupAudioInput = useCallback(async () => {
    try {
      // Get user media
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: audioConfig.sampleRate,
          channelCount: audioConfig.channels
        } 
      })
      
      micStreamRef.current = stream
      
      // Create audio context
      const audioContext = new AudioContext({ sampleRate: audioConfig.sampleRate })
      audioContextRef.current = audioContext
      
      // Create processor node for real-time audio processing
      const processor = audioContext.createScriptProcessor(audioConfig.bufferSize, 1, 1)
      processorNodeRef.current = processor
      
      const source = audioContext.createMediaStreamSource(stream)
      source.connect(processor)
      processor.connect(audioContext.destination)
      
      let chunkBuffer: Float32Array[] = []
      let chunkSamples = 0
      const targetChunkSamples = (audioConfig.chunkSizeMs * audioConfig.sampleRate) / 1000
      
      processor.onaudioprocess = (event) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || !isRecordingRef.current) {
          return
        }
        
        const inputBuffer = event.inputBuffer
        const inputData = inputBuffer.getChannelData(0)
        
        // Add to chunk buffer
        chunkBuffer.push(new Float32Array(inputData))
        chunkSamples += inputData.length
        
        // When we have enough samples, send chunk
        if (chunkSamples >= targetChunkSamples) {
          const combinedBuffer = new Float32Array(chunkSamples)
          let offset = 0
          
          for (const chunk of chunkBuffer) {
            combinedBuffer.set(chunk, offset)
            offset += chunk.length
          }
          
          // Convert to PCM16
          const pcm16Data = convertToPCM16(combinedBuffer)
          
          // Send to Voice-Gateway
          wsRef.current.send(JSON.stringify({
            type: 'audio.chunk',
            audio: arrayBufferToBase64(pcm16Data),
            format: 'pcm16',
            sample_rate: audioConfig.sampleRate,
            channels: audioConfig.channels,
            timestamp: Date.now()
          }))
          
          // Reset chunk buffer
          chunkBuffer = []
          chunkSamples = 0
        }
      }
      
      // Send audio start message
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'audio.start',
          config: {
            sample_rate: audioConfig.sampleRate,
            channels: audioConfig.channels,
            format: 'pcm16'
          }
        }))
      }
      
      isRecordingRef.current = true
      setVoiceState('listening')
      
    } catch (err) {
      console.error('Audio setup failed:', err)
      setError(`Microphone access failed: ${err instanceof Error ? err.message : String(err)}`)
    }
  }, [])

  // Convert Float32Array to PCM16
  const convertToPCM16 = (float32Data: Float32Array): ArrayBuffer => {
    const pcm16 = new Int16Array(float32Data.length)
    for (let i = 0; i < float32Data.length; i++) {
      pcm16[i] = Math.max(-32768, Math.min(32767, float32Data[i] * 32768))
    }
    return pcm16.buffer
  }

  // Convert ArrayBuffer to Base64
  const arrayBufferToBase64 = (buffer: ArrayBuffer): string => {
    const bytes = new Uint8Array(buffer)
    let binary = ''
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i])
    }
    return btoa(binary)
  }

  // Stop audio input
  const stopAudioInput = () => {
    if (isRecordingRef.current && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'audio.stop',
        timestamp: Date.now()
      }))
    }
    
    isRecordingRef.current = false
    
    if (processorNodeRef.current) {
      processorNodeRef.current.disconnect()
      processorNodeRef.current = null
    }
    
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach(track => track.stop())
      micStreamRef.current = null
    }
    
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
  }

  // Interrupt current operation (barge-in)
  const interrupt = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'control.interrupt',
        timestamp: Date.now()
      }))
    }
  }

  // Synthesize and play TTS
  const synthesizeAndPlay = async (text: string) => {
    try {
      setVoiceState('speaking')
      
      // Stop any currently playing audio (barge-in support)
      if (currentAudioRef.current) {
        currentAudioRef.current.pause()
        currentAudioRef.current = null
      }

      // Use OpenAI TTS streaming endpoint
      const response = await fetch('/api/tts/openai-stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text,
          model: voiceQuality === 'high' ? 'tts-1-hd' : 'tts-1',
          voice: 'nova',
          speed: 1.0,
          response_format: 'mp3',
          stream: true
        })
      })

      if (!response.ok) {
        throw new Error(`TTS request failed: ${response.statusText}`)
      }

      // Stream audio response
      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }

      const audioBuffer: ArrayBuffer[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        audioBuffer.push(value.buffer)
      }

      // Concatenate audio chunks and play
      const totalLength = audioBuffer.reduce((sum, buf) => sum + buf.byteLength, 0)
      const combined = new Uint8Array(totalLength)
      let offset = 0

      for (const chunk of audioBuffer) {
        combined.set(new Uint8Array(chunk), offset)
        offset += chunk.byteLength
      }

      // Create blob and play
      const audioBlob = new Blob([combined], { type: 'audio/mpeg' })
      const audioUrl = URL.createObjectURL(audioBlob)
      const audio = new Audio(audioUrl)
      currentAudioRef.current = audio

      audio.onended = () => {
        setVoiceState('idle')
        URL.revokeObjectURL(audioUrl)
        currentAudioRef.current = null
      }

      audio.onerror = (err) => {
        console.error('Audio playback error:', err)
        setVoiceState('idle')
        setError('Audio playback failed')
      }

      await audio.play()

    } catch (err) {
      console.error('TTS synthesis failed:', err)
      setVoiceState('idle')
      setError(`Speech synthesis failed: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  // Start Voice-Gateway client
  const start = async () => {
    try {
      setError(null)
      
      // Connect to Voice-Gateway
      await connectToVoiceGateway()
      
      // Setup audio input
      await setupAudioInput()
      
    } catch (err) {
      console.error('Failed to start Voice-Gateway client:', err)
      setError(`Failed to start: ${err instanceof Error ? err.message : String(err)}`)
      setConnectionState('error')
      onError?.(err instanceof Error ? err.message : String(err))
    }
  }

  // Stop Voice-Gateway client
  const stop = () => {
    // Stop audio input
    stopAudioInput()
    
    // Stop audio playback
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current = null
    }

    // Close WebSocket connection
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setConnectionState('disconnected')
    setVoiceState('idle')
    setIsThinking(false)
    setCurrentResponse('')
    setEnergyLevel(0)
    setIntentRoute(null)
    sessionIdRef.current = null
    onConnectionChange?.(false)
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stop()
    }
  }, [])

  // Get status color based on state
  const getStatusColor = () => {
    switch (voiceState) {
      case 'listening': return 'text-green-400'
      case 'processing': return 'text-yellow-400'
      case 'thinking': return 'text-purple-400'
      case 'speaking': return 'text-blue-400'
      case 'error': return 'text-red-400'
      default: return 'text-cyan-400'
    }
  }

  // Get connection status text
  const getConnectionStatus = () => {
    switch (connectionState) {
      case 'connecting': return 'Ansluter...'
      case 'connected': return 'Voice-Gateway Ansluten'
      case 'error': return 'Fel'
      default: return 'Frånkopplad'
    }
  }

  // Get voice status text
  const getVoiceStatus = () => {
    switch (voiceState) {
      case 'listening': return 'Lyssnar'
      case 'processing': return 'Bearbetar'
      case 'thinking': return 'Tänker (Lokal AI)'
      case 'speaking': return 'Talar'
      case 'error': return 'Fel'
      default: return 'Väntar'
    }
  }

  // Get processing path indicator
  const getPathIndicator = () => {
    if (!currentPath) return null
    
    const pathColors = {
      fast: 'text-green-400',
      think: 'text-purple-400',
      hybrid: 'text-yellow-400'
    }
    
    const pathNames = {
      fast: 'Snabb (OpenAI)',
      think: 'Tänk (Lokal AI)',
      hybrid: 'Hybrid'
    }
    
    return (
      <span className={`text-xs ${pathColors[currentPath]} font-medium`}>
        {pathNames[currentPath]}
      </span>
    )
  }

  return (
    <div className={`w-full max-w-4xl mx-auto select-none ${className}`}>
      <div className="relative rounded-2xl p-6 bg-cyan-950/20 border border-cyan-500/20 shadow-[0_0_60px_-20px_rgba(34,211,238,.5)]">
        
        {/* Header with status and Alice Core ring animation */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            {/* Alice Core Ring Animation */}
            <div className="relative w-12 h-12">
              <div className="absolute inset-0 rounded-full border-2 border-cyan-500/30"></div>
              <div 
                className="absolute inset-0 rounded-full border-2 border-cyan-400 transition-all duration-200"
                style={{
                  opacity: energyLevel * 0.8 + 0.2,
                  transform: `scale(${1 + energyLevel * 0.3})`,
                  filter: `brightness(${1 + energyLevel * 0.5})`
                }}
              ></div>
              <div className="absolute inset-2 rounded-full bg-cyan-400/20 animate-pulse"></div>
            </div>
            
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${connectionState === 'connected' ? 'bg-green-400' : connectionState === 'connecting' ? 'bg-yellow-400' : connectionState === 'error' ? 'bg-red-400' : 'bg-gray-400'} animate-pulse`} />
                <span className="text-sm text-zinc-300">{getConnectionStatus()}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-sm font-medium ${getStatusColor()}`}>
                  {getVoiceStatus()}
                </span>
                {getPathIndicator()}
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {connectionState !== 'connected' ? (
              <button
                onClick={start}
                disabled={connectionState === 'connecting'}
                className="px-4 py-2 rounded-xl bg-cyan-500/90 text-black font-medium hover:bg-cyan-400 active:scale-[0.98] transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {connectionState === 'connecting' ? 'Ansluter...' : 'Starta Voice-Gateway'}
              </button>
            ) : (
              <div className="flex gap-2">
                <button
                  onClick={interrupt}
                  className="px-3 py-2 rounded-xl bg-red-600/80 text-white font-medium hover:bg-red-500 active:scale-[0.98] transition"
                >
                  Avbryt
                </button>
                <button
                  onClick={stop}
                  className="px-4 py-2 rounded-xl bg-zinc-800 text-zinc-100 font-medium hover:bg-zinc-700 active:scale-[0.98] transition"
                >
                  Stoppa
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Intent Route Display */}
        {intentRoute && (
          <div className="mb-4 p-3 bg-black/20 rounded-xl border border-purple-500/20">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-purple-300">Intent Routing</span>
              <span className="text-xs text-zinc-400">
                {intentRoute.confidence.toFixed(2)} konfidens • {intentRoute.estimated_latency_ms}ms
              </span>
            </div>
            <div className="text-sm text-zinc-300 mt-1">
              <span className="text-purple-400">{intentRoute.intent_category}</span> → 
              <span className={`ml-2 ${intentRoute.path === 'fast' ? 'text-green-400' : 'text-purple-400'}`}>
                {intentRoute.path} path
              </span>
            </div>
          </div>
        )}

        {/* Transcript Display */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-cyan-300 mb-3">Transkription</h3>
          <div className="min-h-[100px] max-h-[200px] overflow-y-auto p-4 bg-black/20 rounded-xl border border-cyan-500/10">
            {transcripts.length === 0 ? (
              <p className="text-zinc-500 italic">Väntar på röstinput...</p>
            ) : (
              <div className="space-y-2">
                {transcripts.map((text, index) => (
                  <div key={index} className="text-sm text-zinc-200">
                    <span className="text-xs text-zinc-500 mr-2">{index + 1}.</span>
                    {text}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Alice Response */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-purple-300 mb-3">Alice Svar</h3>
          <div className="min-h-[100px] max-h-[200px] overflow-y-auto p-4 bg-black/20 rounded-xl border border-purple-500/10">
            {isThinking ? (
              <div className="flex items-center gap-2 text-purple-400">
                <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></div>
                <span className="italic">Alice tänker med lokal AI...</span>
              </div>
            ) : currentResponse ? (
              <p className="text-sm text-zinc-200 whitespace-pre-wrap">{currentResponse}</p>
            ) : (
              <p className="text-zinc-500 italic">Väntar på svar från Alice...</p>
            )}
          </div>
        </div>

        {/* Performance Metrics - Enhanced for Phase 2 */}
        {Object.keys(latencyMetrics).length > 0 && (
          <div className="mb-4 p-3 bg-black/20 rounded-xl border border-green-500/20">
            <h4 className="text-sm font-medium text-green-300 mb-2">Prestanda Mätningar</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
              {Object.entries(latencyMetrics).map(([key, value]) => {
                const isGoodLatency = key.includes('fast') ? value < 300 : value < 2000
                const colorClass = isGoodLatency ? 'text-green-400' : 'text-yellow-400'
                
                return (
                  <div key={key} className="text-zinc-400">
                    <span className={colorClass}>{key}:</span> {Math.round(value)}ms
                    {key.includes('fast') && value < 300 && <span className="text-green-400 ml-1">⚡</span>}
                    {key.includes('think') && value < 2000 && <span className="text-purple-400 ml-1">🧠</span>}
                  </div>
                )
              })}
            </div>
            {/* Phase 2 Performance Indicators */}
            <div className="mt-2 pt-2 border-t border-green-500/20">
              <div className="flex items-center gap-4 text-xs">
                <span className="text-green-400">⚡ &lt;300ms (Blixtsnabb)</span>
                <span className="text-purple-400">🧠 &lt;2000ms (Tänker)</span>
                <span className="text-blue-400">💾 Cache träff</span>
              </div>
            </div>
          </div>
        )}

        {/* Settings - Enhanced for Phase 2 */}
        <div className="flex items-center justify-center gap-4 text-xs text-zinc-400 mb-4 flex-wrap">
          <span>Personlighet: <span className="text-cyan-400">{personality}</span></span>
          <span>Känsla: <span className="text-purple-400">{emotion}</span></span>
          <span>Kvalitet: <span className="text-green-400">{voiceQuality}</span></span>
          <span>Energi: <span className="text-yellow-400">{Math.round(energyLevel * 100)}%</span></span>
          <span>Arkitektur: <span className="text-blue-400">Hybrid Phase 2</span></span>
          {currentPath && (
            <span>Aktiv väg: <span className={currentPath === 'fast' ? 'text-green-400' : 'text-purple-400'}>
              {currentPath === 'fast' ? '⚡ Snabb' : '🧠 Tänk'}
            </span></span>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="mt-4 p-3 bg-red-950/20 border border-red-500/20 rounded-xl">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Inner ring for Alice HUD styling */}
        <div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-inset ring-cyan-300/10" />
      </div>
    </div>
  )
}