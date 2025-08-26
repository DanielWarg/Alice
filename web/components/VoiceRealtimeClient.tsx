'use client'

import React, { useEffect, useRef, useState, useCallback } from 'react'
import { motion } from 'framer-motion'

/**
 * OpenAI Realtime API Voice Client for Alice
 * Provides <1s latency streaming voice conversations
 */

export type VoiceRealtimeClientProps = {
  onTranscript?: (text: string, isFinal: boolean) => void
  onAudioData?: (audioData: ArrayBuffer) => void
  onError?: (error: string) => void
  onConnectionChange?: (connected: boolean) => void
  personality?: string
  emotion?: string
  enableSwedish?: boolean
}

interface RealtimeSession {
  websocket: WebSocket | null
  audioContext: AudioContext | null
  mediaStream: MediaStream | null
  isConnected: boolean
  isRecording: boolean
}

export default function VoiceRealtimeClient({
  onTranscript,
  onAudioData,
  onError,
  onConnectionChange,
  personality = 'alice',
  emotion = 'friendly',
  enableSwedish = true
}: VoiceRealtimeClientProps) {
  
  const [session, setSession] = useState<RealtimeSession>({
    websocket: null,
    audioContext: null,
    mediaStream: null,
    isConnected: false,
    isRecording: false
  })
  
  const [status, setStatus] = useState<string>('Disconnected')
  const [latency, setLatency] = useState<number>(0)
  const audioBufferRef = useRef<Float32Array[]>([])
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  
  // OpenAI Realtime API configuration
  const REALTIME_CONFIG = {
    url: 'wss://api.openai.com/v1/realtime',
    model: 'gpt-4o-realtime-preview-2024-10-01',
    voice: 'nova', // Swedish-friendly voice
    instructions: `Du är Alice, en svensk AI-assistent. Svara kort och naturligt på svenska. 
    Personlighet: ${personality}. Känsla: ${emotion}. Max 2 meningar per svar.`,
    input_audio_format: 'pcm16',
    output_audio_format: 'pcm16',
    sample_rate: 24000
  }
  
  // Connect to OpenAI Realtime API
  const connect = useCallback(async () => {
    try {
      setStatus('Connecting...')
      
      // Get OpenAI API key from environment or backend
      const apiKey = await fetch('/api/auth/openai-key')
        .then(res => res.json())
        .then(data => data.key)
      
      if (!apiKey) {
        throw new Error('OpenAI API key not available')
      }
      
      // Create WebSocket connection with auth in URL params (browser limitation)
      const wsUrl = `${REALTIME_CONFIG.url}?authorization=Bearer+${encodeURIComponent(apiKey)}&openai_beta=realtime%3Dv1`
      const ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        console.log('🔗 Connected to OpenAI Realtime API')
        setStatus('Connected')
        
        // Send session configuration
        ws.send(JSON.stringify({
          type: 'session.update',
          session: {
            modalities: ['text', 'audio'],
            instructions: REALTIME_CONFIG.instructions,
            voice: REALTIME_CONFIG.voice,
            input_audio_format: REALTIME_CONFIG.input_audio_format,
            output_audio_format: REALTIME_CONFIG.output_audio_format,
            input_audio_transcription: {
              model: 'whisper-1'
            },
            turn_detection: {
              type: 'server_vad',
              threshold: 0.5,
              prefix_padding_ms: 300,
              silence_duration_ms: 500
            },
            tools: [],
            tool_choice: 'none',
            temperature: 0.6,
            max_response_output_tokens: 150 // Short responses for low latency
          }
        }))
        
        setSession(prev => ({ ...prev, websocket: ws, isConnected: true }))
        onConnectionChange?.(true)
      }
      
      ws.onmessage = (event) => {
        const message = JSON.parse(event.data)
        handleRealtimeMessage(message)
      }
      
      ws.onclose = () => {
        console.log('🔌 Disconnected from OpenAI Realtime API')
        setStatus('Disconnected')
        setSession(prev => ({ 
          ...prev, 
          websocket: null, 
          isConnected: false, 
          isRecording: false 
        }))
        onConnectionChange?.(false)
      }
      
      ws.onerror = (error) => {
        console.error('❌ OpenAI Realtime WebSocket error:', error)
        onError?.('OpenAI Realtime connection failed')
      }
      
    } catch (error) {
      console.error('❌ Failed to connect to OpenAI Realtime:', error)
      onError?.(error instanceof Error ? error.message : 'Connection failed')
      setStatus('Error')
    }
  }, [personality, emotion, onError, onConnectionChange])
  
  // Handle incoming messages from OpenAI Realtime API
  const handleRealtimeMessage = (message: any) => {
    const startTime = performance.now()
    
    switch (message.type) {
      case 'session.created':
        console.log('✅ OpenAI Realtime session created')
        break
        
      case 'session.updated':
        console.log('🔄 OpenAI Realtime session updated')
        break
        
      case 'input_audio_buffer.speech_started':
        console.log('🎤 Speech started')
        setStatus('Listening...')
        break
        
      case 'input_audio_buffer.speech_stopped':
        console.log('🔇 Speech stopped')
        setStatus('Processing...')
        break
        
      case 'conversation.item.input_audio_transcription.completed':
        const transcript = message.transcript || ''
        console.log('📝 Transcript:', transcript)
        onTranscript?.(transcript, true)
        break
        
      case 'response.created':
        console.log('🤖 AI response started')
        setStatus('Responding...')
        break
        
      case 'response.audio.delta':
        // Streaming audio from OpenAI
        if (message.delta) {
          const audioData = base64ToArrayBuffer(message.delta)
          onAudioData?.(audioData)
        }
        break
        
      case 'response.audio_transcript.delta':
        // Live transcript of AI response
        const deltaText = message.delta || ''
        onTranscript?.(deltaText, false)
        break
        
      case 'response.done':
        console.log('✅ AI response completed')
        setStatus('Connected')
        const endTime = performance.now()
        setLatency(endTime - startTime)
        break
        
      case 'error':
        console.error('❌ OpenAI Realtime error:', message.error)
        onError?.(message.error?.message || 'Realtime API error')
        break
        
      default:
        console.log('📨 Unhandled message type:', message.type)
    }
  }
  
  // Start audio recording and streaming
  const startRecording = useCallback(async () => {
    if (!session.isConnected || !session.websocket) {
      console.error('❌ Not connected to OpenAI Realtime')
      return
    }
    
    try {
      // Get user media
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: REALTIME_CONFIG.sample_rate,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })
      
      // Create audio context for processing
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: REALTIME_CONFIG.sample_rate
      })
      
      const source = audioContext.createMediaStreamSource(stream)
      const processor = audioContext.createScriptProcessor(4096, 1, 1)
      
      processor.onaudioprocess = (event) => {
        const inputBuffer = event.inputBuffer
        const inputData = inputBuffer.getChannelData(0)
        
        // Convert to PCM16 and send to OpenAI
        const pcm16Data = floatToPCM16(inputData)
        const base64Data = arrayBufferToBase64(pcm16Data)
        
        if (session.websocket && session.websocket.readyState === WebSocket.OPEN) {
          session.websocket.send(JSON.stringify({
            type: 'input_audio_buffer.append',
            audio: base64Data
          }))
        }
      }
      
      source.connect(processor)
      processor.connect(audioContext.destination)
      
      setSession(prev => ({
        ...prev,
        audioContext,
        mediaStream: stream,
        isRecording: true
      }))
      
      setStatus('Recording...')
      console.log('🎤 Started audio recording and streaming')
      
    } catch (error) {
      console.error('❌ Failed to start recording:', error)
      onError?.('Microphone access failed')
    }
  }, [session.isConnected, session.websocket, onError])
  
  // Stop audio recording
  const stopRecording = useCallback(() => {
    if (session.mediaStream) {
      session.mediaStream.getTracks().forEach(track => track.stop())
    }
    
    if (session.audioContext) {
      session.audioContext.close()
    }
    
    setSession(prev => ({
      ...prev,
      audioContext: null,
      mediaStream: null,
      isRecording: false
    }))
    
    setStatus('Connected')
    console.log('🔇 Stopped audio recording')
  }, [session.audioContext, session.mediaStream])
  
  // Utility functions
  const base64ToArrayBuffer = (base64: string): ArrayBuffer => {
    const binaryString = atob(base64)
    const bytes = new Uint8Array(binaryString.length)
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i)
    }
    return bytes.buffer
  }
  
  const arrayBufferToBase64 = (buffer: ArrayBuffer): string => {
    const bytes = new Uint8Array(buffer)
    let binary = ''
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i])
    }
    return btoa(binary)
  }
  
  const floatToPCM16 = (float32Array: Float32Array): ArrayBuffer => {
    const buffer = new ArrayBuffer(float32Array.length * 2)
    const view = new DataView(buffer)
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]))
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
    }
    return buffer
  }
  
  // Connect on mount
  useEffect(() => {
    connect()
    
    return () => {
      if (session.websocket) {
        session.websocket.close()
      }
      stopRecording()
    }
  }, [])
  
  return (
    <div className="flex flex-col items-center gap-4">
      {/* Status Display */}
      <div className="text-center">
        <motion.div
          animate={{
            scale: session.isConnected ? 1.05 : 1,
            opacity: session.isConnected ? 1 : 0.7
          }}
          className={`px-4 py-2 rounded-full text-sm font-medium ${
            session.isConnected 
              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
              : 'bg-red-500/20 text-red-400 border border-red-500/30'
          }`}
        >
          {status}
        </motion.div>
        
        {latency > 0 && (
          <div className="text-xs text-cyan-300/60 mt-1">
            Latency: {latency.toFixed(0)}ms
          </div>
        )}
      </div>
      
      {/* Recording Controls */}
      <div className="flex gap-3">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={session.isRecording ? stopRecording : startRecording}
          disabled={!session.isConnected}
          className={`px-6 py-2 rounded-full font-medium transition-colors ${
            session.isRecording
              ? 'bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30'
              : 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30 disabled:opacity-50'
          }`}
        >
          {session.isRecording ? '🔴 Stop' : '🎤 Start'}
        </motion.button>
        
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={session.isConnected ? 
            () => session.websocket?.close() : 
            connect
          }
          className="px-6 py-2 rounded-full font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30 hover:bg-blue-500/30 transition-colors"
        >
          {session.isConnected ? 'Disconnect' : 'Reconnect'}
        </motion.button>
      </div>
      
      {/* Debug Info */}
      {process.env.NODE_ENV === 'development' && (
        <div className="text-xs text-cyan-300/40 text-center max-w-md">
          OpenAI Realtime API • {REALTIME_CONFIG.model} • {REALTIME_CONFIG.voice}
          <br />
          Swedish: {enableSwedish ? 'Enabled' : 'Disabled'} • 
          Latency Target: &lt;300ms
        </div>
      )}
    </div>
  )
}