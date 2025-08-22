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
  
  // Audio and WebRTC refs
  const pcRef = useRef<RTCPeerConnection | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const micStreamRef = useRef<MediaStream | null>(null)
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)
  
  // Transcript and response state
  const [transcripts, setTranscripts] = useState<TranscriptSegment[]>([])
  const [currentResponse, setCurrentResponse] = useState<string>('')
  const [isThinking, setIsThinking] = useState(false)
  
  // Error state
  const [error, setError] = useState<string | null>(null)
  
  // SSE connection for agent responses
  const sseRef = useRef<EventSource | null>(null)
  
  // WebRTC audio handling
  const setupWebRTC = useCallback(async (sessionData: RealtimeSession) => {
    try {
      // Create peer connection
      const pc = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
      })
      pcRef.current = pc

      // Get user media
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

      // Add audio track to peer connection
      stream.getAudioTracks().forEach(track => {
        pc.addTrack(track, stream)
      })

      // Handle incoming audio stream
      pc.ontrack = (event) => {
        console.log('Received remote audio stream')
        const remoteStream = event.streams[0]
        if (remoteStream) {
          playAudioStream(remoteStream)
        }
      }

      // Create audio context for processing
      const audioContext = new AudioContext({ sampleRate: 24000 })
      audioContextRef.current = audioContext
      
      // Connect to OpenAI Realtime API via WebRTC
      await connectToRealtimeAPI(pc, sessionData)
      
      setConnectionState('connected')
      onConnectionChange?.(true)
    } catch (err) {
      console.error('WebRTC setup failed:', err)
      setError(`WebRTC setup failed: ${err instanceof Error ? err.message : String(err)}`)
      setConnectionState('error')
      onConnectionChange?.(false)
    }
  }, [onConnectionChange])

  // Connect to OpenAI Realtime API
  const connectToRealtimeAPI = async (pc: RTCPeerConnection, sessionData: RealtimeSession) => {
    // Create offer
    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    // Send offer to OpenAI Realtime API
    const response = await fetch('https://api.openai.com/v1/realtime/sessions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${sessionData.client_secret.value}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: sessionData.model,
        voice: sessionData.voice,
        type: 'session.update',
        session: {
          modalities: ['text', 'audio'],
          instructions: `You are Alice, a Swedish AI assistant. Respond in Swedish with ${personality} personality and ${emotion} emotional tone.`,
          voice: sessionData.voice,
          input_audio_format: 'pcm16',
          output_audio_format: 'pcm16',
          input_audio_transcription: {
            model: 'whisper-1'
          }
        }
      })
    })

    if (!response.ok) {
      throw new Error(`Failed to connect to Realtime API: ${response.statusText}`)
    }

    // Handle WebRTC data channel for real-time communication
    const dataChannel = pc.createDataChannel('realtime', { ordered: true })
    
    dataChannel.onopen = () => {
      console.log('Data channel opened')
    }

    dataChannel.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleRealtimeMessage(data)
      } catch (err) {
        console.error('Failed to parse realtime message:', err)
      }
    }
  }

  // Handle messages from OpenAI Realtime API
  const handleRealtimeMessage = (data: any) => {
    switch (data.type) {
      case 'input_audio_buffer.speech_started':
        setVoiceState('listening')
        break
      
      case 'input_audio_buffer.speech_stopped':
        setVoiceState('processing')
        break

      case 'conversation.item.input_audio_transcription.completed':
        if (data.transcript) {
          const transcript: TranscriptSegment = {
            id: data.item_id,
            text: data.transcript,
            isFinal: true,
            timestamp: Date.now()
          }
          
          setTranscripts(prev => [...prev, transcript])
          onTranscript?.(data.transcript, true)
          
          // Send to Alice agent for processing
          sendToAliceAgent(data.transcript)
        }
        break

      case 'response.audio.delta':
        // Handle real-time audio chunks from OpenAI
        if (data.delta) {
          playAudioChunk(data.delta)
        }
        break

      case 'response.done':
        setVoiceState('idle')
        break

      case 'error':
        console.error('Realtime API error:', data.error)
        setError(`Realtime API error: ${data.error.message}`)
        break
    }
  }

  // Send transcript to Alice agent via SSE
  const sendToAliceAgent = async (transcript: string) => {
    try {
      setIsThinking(true)
      setCurrentResponse('')
      
      // Close existing SSE connection
      if (sseRef.current) {
        sseRef.current.close()
      }

      // Create new SSE connection to Alice agent
      const eventSource = new EventSource('/api/agent/stream', {
        withCredentials: false
      })
      sseRef.current = eventSource

      // Send request to agent
      const response = await fetch('/api/agent/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          prompt: transcript,
          model: 'gpt-oss:20b',
          provider: 'local',
          use_rag: true,
          use_tools: true,
          language: 'svenska',
          context: {
            personality,
            emotion,
            voice_quality: voiceQuality
          }
        })
      })

      if (!response.ok) {
        throw new Error(`Agent request failed: ${response.statusText}`)
      }

      // Handle SSE events
      eventSource.onmessage = (event) => {
        try {
          const data: AgentResponse = JSON.parse(event.data)
          handleAgentResponse(data)
        } catch (err) {
          console.error('Failed to parse SSE data:', err)
        }
      }

      eventSource.onerror = (err) => {
        console.error('SSE connection error:', err)
        setError('Lost connection to Alice agent')
        eventSource.close()
        setIsThinking(false)
      }

    } catch (err) {
      console.error('Failed to send to Alice agent:', err)
      setError(`Failed to communicate with Alice: ${err instanceof Error ? err.message : String(err)}`)
      setIsThinking(false)
    }
  }

  // Handle agent response chunks
  const handleAgentResponse = (data: AgentResponse) => {
    switch (data.type) {
      case 'planning':
        setIsThinking(true)
        break

      case 'chunk':
        setIsThinking(false)
        setCurrentResponse(prev => prev + data.content)
        break

      case 'done':
        setIsThinking(false)
        // Convert response to speech
        if (currentResponse.trim()) {
          synthesizeAndPlay(currentResponse)
        }
        break

      case 'error':
        setIsThinking(false)
        setError(`Agent error: ${data.content}`)
        break

      case 'tool':
        // Handle tool execution results
        console.log('Tool result:', data.content)
        break
    }
  }

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

  // Play audio stream from WebRTC
  const playAudioStream = (stream: MediaStream) => {
    const audio = new Audio()
    audio.srcObject = stream
    audio.autoplay = true
    currentAudioRef.current = audio
  }

  // Play audio chunk (for real-time OpenAI audio)
  const playAudioChunk = (chunk: string) => {
    // Convert base64 audio chunk to playable format
    try {
      const audioData = atob(chunk)
      const audioArray = new Uint8Array(audioData.length)
      for (let i = 0; i < audioData.length; i++) {
        audioArray[i] = audioData.charCodeAt(i)
      }
      
      // Play via Web Audio API for real-time streaming
      const audioContext = audioContextRef.current
      if (audioContext) {
        audioContext.decodeAudioData(audioArray.buffer).then(buffer => {
          const source = audioContext.createBufferSource()
          source.buffer = buffer
          source.connect(audioContext.destination)
          source.start()
        }).catch(err => {
          console.error('Audio decode error:', err)
        })
      }
    } catch (err) {
      console.error('Failed to play audio chunk:', err)
    }
  }

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
      
      // Setup WebRTC
      await setupWebRTC(sessionData)
      
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

    // Close peer connection
    if (pcRef.current) {
      pcRef.current.close()
      pcRef.current = null
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

    // Close SSE connection
    if (sseRef.current) {
      sseRef.current.close()
      sseRef.current = null
    }

    setConnectionState('disconnected')
    setVoiceState('idle')
    setSession(null)
    setIsThinking(false)
    setCurrentResponse('')
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