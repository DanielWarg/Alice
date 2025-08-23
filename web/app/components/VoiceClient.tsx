'use client'

import React, { useEffect, useRef, useState, useCallback } from 'react'

// Types for the component
interface VoiceClientProps {
  personality?: string
  emotion?: string
  voiceQuality?: string
  className?: string
  onTranscript?: (text: string, isFinal: boolean) => void
  onError?: (error: string) => void
  onConnectionChange?: (connected: boolean) => void
}

interface RealtimeSession {
  client_secret: {
    value: string
  }
  ephemeral_key_id: string
  model: string
  voice: string
  expires_at: string
}

interface TranscriptSegment {
  id: string
  text: string
  isFinal: boolean
  timestamp: number
}

interface AgentResponse {
  type: 'chunk' | 'tool' | 'meta' | 'done' | 'error' | 'planning' | 'executing' | 'evaluating'
  content: string
  metadata?: any
}

// Connection states
type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error'
type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking'

export default function VoiceClient({
  personality = 'alice',
  emotion = 'friendly', 
  voiceQuality = 'medium',
  className = '',
  onTranscript,
  onError,
  onConnectionChange
}: VoiceClientProps) {
  // Connection and session state
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected')
  const [voiceState, setVoiceState] = useState<VoiceState>('idle')
  const [session, setSession] = useState<RealtimeSession | null>(null)
  
  // Audio refs
  const audioContextRef = useRef<AudioContext | null>(null)
  const micStreamRef = useRef<MediaStream | null>(null)
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const isRecordingRef = useRef<boolean>(false)
  
  // Transcript and response state
  const [transcripts, setTranscripts] = useState<TranscriptSegment[]>([])
  const [currentResponse, setCurrentResponse] = useState<string>('')
  const [isThinking, setIsThinking] = useState(false)
  
  // Error state
  const [error, setError] = useState<string | null>(null)
  
  // Recognition for voice input
  const recognitionRef = useRef<any>(null)
  
  // WebSocket connection for voice streaming
  const wsRef = useRef<WebSocket | null>(null)
  const sessionIdRef = useRef<string | null>(null)

  // Voice WebSocket setup
  const setupWebSocket = useCallback(async (sessionData: RealtimeSession) => {
    try {
      // Generate session ID
      const sessionId = `voice_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      sessionIdRef.current = sessionId

      // Get user media for audio input
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 24000,
          channelCount: 1
        } 
      })
      micStreamRef.current = stream

      // Create audio context for processing
      const audioContext = new AudioContext({ sampleRate: 24000 })
      audioContextRef.current = audioContext
      
      // Connect to backend WebSocket
      await connectToVoiceWebSocket(sessionId)
      
      // Setup voice input handling
      setupVoiceInput(stream)
      
      setConnectionState('connected')
      onConnectionChange?.(true)
    } catch (err) {
      console.error('Voice WebSocket setup failed:', err)
      setError(`Voice connection failed: ${err instanceof Error ? err.message : String(err)}`)
      setConnectionState('error')
      onConnectionChange?.(false)
    }
  }, [onConnectionChange])

  // Connect to backend Voice WebSocket
  const connectToVoiceWebSocket = async (sessionId: string) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/ws/voice/${sessionId}`
    
    console.log('Connecting to voice WebSocket:', wsUrl)
    
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('Voice WebSocket connected')
      
      // Send initial configuration
      ws.send(JSON.stringify({
        type: 'config',
        personality,
        emotion,
        voiceQuality,
        language: 'svenska'
      }))
      
      setVoiceState('idle')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleVoiceMessage(data)
      } catch (err) {
        console.error('Failed to parse voice message:', err)
      }
    }
    
    ws.onclose = () => {
      console.log('Voice WebSocket closed')
      setConnectionState('disconnected')
      setVoiceState('idle')
      onConnectionChange?.(false)
    }
    
    ws.onerror = (error) => {
      console.error('Voice WebSocket error:', error)
      setError('WebSocket connection failed')
      setConnectionState('error')
    }

    return new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('WebSocket connection timeout'))
      }, 10000)
      
      ws.onopen = () => {
        clearTimeout(timeout)
        console.log('Voice WebSocket connected')
        ws.send(JSON.stringify({
          type: 'config',
          personality,
          emotion,
          voiceQuality,
          language: 'svenska'
        }))
        setVoiceState('idle')
        resolve()
      }
    })
  }
  
  // Setup voice input with both browser API and MediaRecorder fallback
  const setupVoiceInput = (stream: MediaStream) => {
    try {
      // Try to use Web Speech API for fast recognition
      if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
        const recognition = new SpeechRecognition()
        
        recognition.continuous = true
        recognition.interimResults = true
        recognition.lang = 'sv-SE'  // Swedish
        
        recognition.onresult = (event: any) => {
          let finalTranscript = ''
          let interimTranscript = ''
          
          for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
              finalTranscript += event.results[i][0].transcript
            } else {
              interimTranscript += event.results[i][0].transcript
            }
          }
          
          if (finalTranscript.trim()) {
            sendVoiceInput(finalTranscript.trim(), 'browser_api')
          }
        }
        
        recognition.onerror = (event: any) => {
          console.error('Speech recognition error:', event.error)
          // Fallback to manual recording
          setupMediaRecorder(stream)
        }
        
        recognitionRef.current = recognition
        
        // Start continuous recognition
        recognition.start()
        setVoiceState('listening')
        
      } else {
        // Fallback to MediaRecorder
        setupMediaRecorder(stream)
      }
    } catch (err) {
      console.error('Voice input setup failed:', err)
      setupMediaRecorder(stream)
    }
  }
  
  // Setup MediaRecorder for audio capture
  const setupMediaRecorder = (stream: MediaStream) => {
    try {
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })
      mediaRecorderRef.current = mediaRecorder
      
      const audioChunks: Blob[] = []
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data)
        }
      }
      
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm;codecs=opus' })
        await sendAudioForTranscription(audioBlob)
        audioChunks.length = 0  // Clear chunks
      }
      
      // Start recording in chunks for real-time processing
      mediaRecorder.start(3000)  // 3 second chunks
      isRecordingRef.current = true
      setVoiceState('listening')
      
    } catch (err) {
      console.error('MediaRecorder setup failed:', err)
      setError('Voice input setup failed')
    }
  }
  
  // Send voice input to backend WebSocket
  const sendVoiceInput = (text: string, source: string = 'browser_api') => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'voice_input',
        text,
        source,
        timestamp: Date.now()
      }))
    }
  }
  
  // Send audio blob for server-side transcription
  const sendAudioForTranscription = async (audioBlob: Blob) => {
    try {
      const formData = new FormData()
      formData.append('audio', audioBlob, 'recording.webm')
      
      const response = await fetch('/api/voice/transcribe', {
        method: 'POST',
        body: formData
      })
      
      if (response.ok) {
        const result = await response.json()
        if (result.text && result.text.trim()) {
          sendVoiceInput(result.text.trim(), 'whisper')
        }
      }
    } catch (err) {
      console.error('Audio transcription failed:', err)
    }
  }

  // Handle messages from backend Voice WebSocket
  const handleVoiceMessage = (data: any) => {
    switch (data.type) {
      case 'heard':
        // User's voice was heard and transcribed
        const transcript: TranscriptSegment = {
          id: `transcript_${Date.now()}`,
          text: data.text,
          isFinal: true,
          timestamp: Date.now()
        }
        
        setTranscripts(prev => [...prev, transcript])
        onTranscript?.(data.text, true)
        setVoiceState('processing')
        break
      
      case 'acknowledge':
        // Alice acknowledged the command
        setIsThinking(false)
        setCurrentResponse(data.message)
        setVoiceState('speaking')
        
        // Synthesize and play acknowledgment
        synthesizeAndPlay(data.message)
        break

      case 'speak':
        // Alice is speaking (streaming response)
        if (data.partial) {
          setCurrentResponse(prev => prev + data.text + ' ')
        } else if (data.final) {
          setCurrentResponse(prev => prev + data.text)
          setVoiceState('speaking')
          
          // Synthesize and play final response
          synthesizeAndPlay(data.text)
        }
        break
        
      case 'tool_success':
      case 'calendar_success':
        setIsThinking(false)
        setCurrentResponse(data.message)
        setVoiceState('speaking')
        synthesizeAndPlay(data.message)
        break
        
      case 'tool_error':
      case 'calendar_error':
        setIsThinking(false)
        setError(data.message)
        setVoiceState('idle')
        break
        
      case 'pong':
        // Keep-alive response
        break

      case 'error':
        console.error('Voice WebSocket error:', data)
        setError(data.message || 'Voice connection error')
        setVoiceState('idle')
        break
    }
  }

  // Note: Agent communication now happens through WebSocket
  // The backend handles agent integration internally

  // Synthesize and play TTS
  const synthesizeAndPlay = async (text: string) => {
    try {
      setVoiceState('speaking')
      
      // Stop any currently playing audio (barge-in)
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
          voice: 'nova', // Could be made configurable
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

      // Create audio context for streaming playback
      const audioContext = audioContextRef.current || new AudioContext()
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

  // Audio playback is now handled by synthesizeAndPlay function

  // Create ephemeral session
  const createEphemeralSession = async (): Promise<RealtimeSession> => {
    const response = await fetch('/api/realtime/ephemeral', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      throw new Error(`Failed to create ephemeral session: ${response.statusText}`)
    }

    return await response.json()
  }

  // Start voice client
  const start = async () => {
    try {
      setError(null)
      setConnectionState('connecting')
      
      // Create ephemeral session
      const sessionData = await createEphemeralSession()
      setSession(sessionData)
      
      // Setup WebSocket connection
      await setupWebSocket(sessionData)
      
      setVoiceState('idle')
    } catch (err) {
      console.error('Failed to start voice client:', err)
      setError(`Failed to start: ${err instanceof Error ? err.message : String(err)}`)
      setConnectionState('error')
      onError?.(err instanceof Error ? err.message : String(err))
    }
  }

  // Stop voice client
  const stop = () => {
    // Stop audio
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current = null
    }

    // Stop speech recognition
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    
    // Stop media recorder
    if (mediaRecorderRef.current && isRecordingRef.current) {
      mediaRecorderRef.current.stop()
      mediaRecorderRef.current = null
      isRecordingRef.current = false
    }

    // Stop microphone
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach(track => track.stop())
      micStreamRef.current = null
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    // Close WebSocket connection
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setConnectionState('disconnected')
    setVoiceState('idle')
    setSession(null)
    setIsThinking(false)
    setCurrentResponse('')
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
      case 'speaking': return 'text-purple-400'
      default: return 'text-cyan-400'
    }
  }

  // Get connection status text
  const getConnectionStatus = () => {
    switch (connectionState) {
      case 'connecting': return 'Ansluter...'
      case 'connected': return 'Ansluten'
      case 'error': return 'Fel'
      default: return 'Frånkopplad'
    }
  }

  // Get voice status text
  const getVoiceStatus = () => {
    switch (voiceState) {
      case 'listening': return 'Lyssnar'
      case 'processing': return 'Bearbetar'
      case 'speaking': return 'Talar'
      default: return 'Väntar'
    }
  }

  return (
    <div className={`w-full max-w-4xl mx-auto select-none ${className}`}>
      <div className="relative rounded-2xl p-6 bg-cyan-950/20 border border-cyan-500/20 shadow-[0_0_60px_-20px_rgba(34,211,238,.5)]">
        
        {/* Header with status */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${connectionState === 'connected' ? 'bg-green-400' : connectionState === 'connecting' ? 'bg-yellow-400' : connectionState === 'error' ? 'bg-red-400' : 'bg-gray-400'} animate-pulse`} />
              <span className="text-sm text-zinc-300">{getConnectionStatus()}</span>
            </div>
            <div className={`text-sm font-medium ${getStatusColor()}`}>
              {getVoiceStatus()}
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {connectionState !== 'connected' ? (
              <button
                onClick={start}
                disabled={connectionState === 'connecting'}
                className="px-4 py-2 rounded-xl bg-cyan-500/90 text-black font-medium hover:bg-cyan-400 active:scale-[0.98] transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {connectionState === 'connecting' ? 'Ansluter...' : 'Starta Röst'}
              </button>
            ) : (
              <button
                onClick={stop}
                className="px-4 py-2 rounded-xl bg-zinc-800 text-zinc-100 font-medium hover:bg-zinc-700 active:scale-[0.98] transition"
              >
                Stoppa
              </button>
            )}
          </div>
        </div>

        {/* Transcript Display */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-cyan-300 mb-3">Transkription</h3>
          <div className="min-h-[100px] max-h-[200px] overflow-y-auto p-4 bg-black/20 rounded-xl border border-cyan-500/10">
            {transcripts.length === 0 ? (
              <p className="text-zinc-500 italic">Väntar på röstinput...</p>
            ) : (
              <div className="space-y-2">
                {transcripts.map((segment) => (
                  <div key={segment.id} className="flex items-start gap-2">
                    <span className="text-xs text-zinc-500 mt-1 flex-shrink-0">
                      {new Date(segment.timestamp).toLocaleTimeString()}
                    </span>
                    <span className={`text-sm ${segment.isFinal ? 'text-zinc-200' : 'text-zinc-400 italic'}`}>
                      {segment.text}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Agent Response */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-purple-300 mb-3">Alice Svar</h3>
          <div className="min-h-[100px] max-h-[200px] overflow-y-auto p-4 bg-black/20 rounded-xl border border-purple-500/10">
            {isThinking ? (
              <div className="flex items-center gap-2 text-purple-400">
                <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></div>
                <span className="italic">Alice tänker...</span>
              </div>
            ) : currentResponse ? (
              <p className="text-sm text-zinc-200 whitespace-pre-wrap">{currentResponse}</p>
            ) : (
              <p className="text-zinc-500 italic">Väntar på svar från Alice...</p>
            )}
          </div>
        </div>

        {/* Settings */}
        <div className="flex items-center justify-center gap-4 text-xs text-zinc-400 mb-4">
          <span>Personlighet: <span className="text-cyan-400">{personality}</span></span>
          <span>Känsla: <span className="text-purple-400">{emotion}</span></span>
          <span>Kvalitet: <span className="text-green-400">{voiceQuality}</span></span>
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