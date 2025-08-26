'use client'

import React, { useEffect, useRef, useState, useCallback } from 'react'
import { motion } from 'framer-motion'

/**
 * Streaming Voice Client for Alice
 * Leverages gpt-oss speed with chunked TTS for sub-second responses
 * Architecture: partial transcripts → gpt-oss → chunked TTS → immediate playback
 */

export type VoiceStreamClientProps = {
  onTranscript?: (text: string, isFinal: boolean) => void
  onResponse?: (text: string) => void  
  onError?: (error: string) => void
  onConnectionChange?: (connected: boolean) => void
  enableContinuous?: boolean
}

interface StreamSession {
  websocket: WebSocket | null
  mediaRecorder: MediaRecorder | null
  audioContext: AudioContext | null
  isConnected: boolean
  isRecording: boolean
  isProcessing: boolean
  audioQueue: HTMLAudioElement[]
}

export default function VoiceStreamClient({
  onTranscript,
  onResponse,
  onError,
  onConnectionChange,
  enableContinuous = true
}: VoiceStreamClientProps) {
  
  const [session, setSession] = useState<StreamSession>({
    websocket: null,
    mediaRecorder: null,
    audioContext: null,
    isConnected: false,
    isRecording: false,
    isProcessing: false,
    audioQueue: []
  })
  
  const [status, setStatus] = useState<string>('Disconnected')
  const [latency, setLatency] = useState<number>(0)
  const recognitionRef = useRef<any>(null)
  const audioQueueRef = useRef<HTMLAudioElement[]>([])
  const currentTranscriptRef = useRef<string>('')
  const processingStartTimeRef = useRef<number>(0)
  
  // Connect to streaming voice WebSocket
  const connect = useCallback(async () => {
    try {
      setStatus('Connecting...')
      
      const wsUrl = `ws://127.0.0.1:8000/ws/voice-stream`
      const ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        console.log('🔗 Connected to streaming voice pipeline')
        setStatus('Connected')
        setSession(prev => ({ ...prev, websocket: ws, isConnected: true }))
        onConnectionChange?.(true)
      }
      
      ws.onmessage = (event) => {
        const message = JSON.parse(event.data)
        handleStreamMessage(message)
      }
      
      ws.onclose = () => {
        console.log('🔌 Disconnected from streaming voice pipeline')
        setStatus('Disconnected')
        setSession(prev => ({ 
          ...prev, 
          websocket: null, 
          isConnected: false,
          isProcessing: false
        }))
        onConnectionChange?.(false)
      }
      
      ws.onerror = (error) => {
        console.error('❌ Streaming voice WebSocket error:', error)
        onError?.('Streaming voice connection failed')
      }
      
    } catch (error) {
      console.error('❌ Failed to connect to streaming voice:', error)
      onError?.(error instanceof Error ? error.message : 'Connection failed')
      setStatus('Error')
    }
  }, [onError, onConnectionChange])
  
  // Handle incoming messages from streaming voice WebSocket
  const handleStreamMessage = (message: any) => {
    switch (message.type) {
      case 'processing_started':
        console.log('🤖 Processing started:', message.transcript)
        setStatus('Processing...')
        setSession(prev => ({ ...prev, isProcessing: true }))
        processingStartTimeRef.current = performance.now()
        break
        
      case 'audio_chunk':
        // Play audio chunk immediately for streaming experience
        playAudioChunk(message.audio, message.chunk, message.total_chunks)
        if (message.chunk === 1) {
          // First chunk - measure Time-To-First-Audio
          const ttfa = performance.now() - processingStartTimeRef.current
          setLatency(ttfa)
          console.log(`🎵 Time-To-First-Audio: ${ttfa.toFixed(0)}ms`)
          setStatus('Speaking...')
        }
        break
        
      case 'response_complete':
        console.log('✅ Response complete:', message.response)
        setSession(prev => ({ ...prev, isProcessing: false }))
        onResponse?.(message.response)
        
        // Resume listening if continuous mode
        if (enableContinuous && session.isRecording) {
          setTimeout(() => {
            setStatus('Listening...')
          }, 1000)
        } else {
          setStatus('Connected')
        }
        break
        
      case 'error':
        console.error('❌ Stream error:', message.message)
        onError?.(message.message)
        setSession(prev => ({ ...prev, isProcessing: false }))
        setStatus('Error')
        break
        
      case 'pong':
        // Keep-alive response
        break
        
      default:
        console.log('📨 Unhandled stream message:', message.type)
    }
  }
  
  // Play audio chunk immediately for streaming
  const playAudioChunk = (audioBase64: string, chunk: number, totalChunks: number) => {
    try {
      const audioData = atob(audioBase64)
      const audioArray = new Uint8Array(audioData.length)
      for (let i = 0; i < audioData.length; i++) {
        audioArray[i] = audioData.charCodeAt(i)
      }
      
      const audioBlob = new Blob([audioArray], { type: 'audio/wav' })
      const audioUrl = URL.createObjectURL(audioBlob)
      const audio = new Audio(audioUrl)
      
      // Queue audio for sequential playback
      audioQueueRef.current.push(audio)
      
      // If first chunk or previous audio ended, start playback
      if (chunk === 1 || audioQueueRef.current.length === 1) {
        playNextAudioChunk()
      }
      
      console.log(`🔊 Queued audio chunk ${chunk}/${totalChunks}`)
      
    } catch (error) {
      console.error('❌ Failed to play audio chunk:', error)
    }
  }
  
  // Play next audio chunk in queue
  const playNextAudioChunk = () => {
    const audio = audioQueueRef.current.shift()
    if (audio) {
      audio.onended = () => {
        URL.revokeObjectURL(audio.src)
        // Play next chunk if available
        if (audioQueueRef.current.length > 0) {
          playNextAudioChunk()
        }
      }
      
      audio.onerror = (error) => {
        console.error('❌ Audio playback error:', error)
        // Try next chunk
        if (audioQueueRef.current.length > 0) {
          playNextAudioChunk()
        }
      }
      
      audio.play().catch(error => {
        console.error('❌ Audio play failed:', error)
      })
    }
  }
  
  // Start speech recognition with partial results
  const startRecording = useCallback(async () => {
    if (!session.isConnected || !session.websocket) {
      console.error('❌ Not connected to streaming voice pipeline')
      return
    }
    
    try {
      // Use Web Speech API for partial transcripts
      if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        throw new Error('Speech recognition not supported in this browser')
      }
      
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      const recognition = new SpeechRecognition()
      
      recognition.continuous = enableContinuous
      recognition.interimResults = true  // Enable partial results
      recognition.lang = 'sv-SE'
      recognition.maxAlternatives = 1
      
      recognition.onstart = () => {
        console.log('🎤 Started streaming speech recognition')
        setStatus('Listening...')
        setSession(prev => ({ ...prev, isRecording: true }))
      }
      
      recognition.onresult = (event: any) => {
        let finalTranscript = ''
        let interimTranscript = ''
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript
          const confidence = event.results[i][0].confidence
          
          if (event.results[i].isFinal) {
            finalTranscript += transcript
            console.log(`📝 Final transcript: "${transcript}" (conf: ${confidence?.toFixed(2) || 'N/A'})`)
            
            // Send final transcript for processing
            if (session.websocket && finalTranscript.trim()) {
              session.websocket.send(JSON.stringify({
                type: 'partial_transcript',
                transcript: finalTranscript.trim(),
                is_final: true,
                confidence: confidence || 1.0
              }))
              
              onTranscript?.(finalTranscript.trim(), true)
            }
          } else {
            interimTranscript += transcript
            console.log(`📝 Partial transcript: "${transcript}" (conf: ${confidence?.toFixed(2) || 'N/A'})`)
            
            // Send partial transcript if confidence is high enough
            if (confidence && confidence > 0.7 && transcript.trim().length > 5) {
              if (session.websocket) {
                session.websocket.send(JSON.stringify({
                  type: 'partial_transcript',
                  transcript: transcript.trim(),
                  is_final: false,
                  confidence: confidence
                }))
              }
            }
            
            onTranscript?.(transcript.trim(), false)
          }
        }
        
        currentTranscriptRef.current = finalTranscript || interimTranscript
      }
      
      recognition.onerror = (event: any) => {
        console.error('❌ Speech recognition error:', event.error)
        onError?.(`Speech recognition error: ${event.error}`)
      }
      
      recognition.onend = () => {
        console.log('🔇 Speech recognition ended')
        if (enableContinuous && session.isRecording && !session.isProcessing) {
          // Restart recognition for continuous listening
          setTimeout(() => {
            if (session.isRecording) {
              recognition.start()
            }
          }, 100)
        } else {
          setSession(prev => ({ ...prev, isRecording: false }))
          setStatus('Connected')
        }
      }
      
      recognitionRef.current = recognition
      recognition.start()
      
    } catch (error) {
      console.error('❌ Failed to start speech recognition:', error)
      onError?.('Speech recognition failed to start')
    }
  }, [session.isConnected, session.websocket, enableContinuous, onError, onTranscript])
  
  // Stop speech recognition
  const stopRecording = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    
    // Clear audio queue
    audioQueueRef.current.forEach(audio => {
      audio.pause()
      URL.revokeObjectURL(audio.src)
    })
    audioQueueRef.current = []
    
    setSession(prev => ({ 
      ...prev, 
      isRecording: false,
      isProcessing: false
    }))
    setStatus('Connected')
    console.log('🔇 Stopped streaming voice')
  }, [])
  
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
            session.isProcessing
              ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
              : session.isConnected 
                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                : 'bg-red-500/20 text-red-400 border border-red-500/30'
          }`}
        >
          {status}
        </motion.div>
        
        {latency > 0 && (
          <div className="text-xs text-cyan-300/60 mt-1">
            Time-To-First-Audio: {latency.toFixed(0)}ms
          </div>
        )}
      </div>
      
      {/* Recording Controls */}
      <div className="flex gap-3">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={session.isRecording ? stopRecording : startRecording}
          disabled={!session.isConnected || session.isProcessing}
          className={`px-6 py-2 rounded-full font-medium transition-colors ${
            session.isRecording
              ? 'bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30'
              : 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30 disabled:opacity-50'
          }`}
        >
          {session.isRecording ? '🔴 Stop' : '🎤 Start Streaming'}
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
          Streaming Voice Pipeline • gpt-oss:20b • Chunked TTS
          <br />
          Target TTFA: &lt;1s • Continuous: {enableContinuous ? 'On' : 'Off'}
        </div>
      )}
    </div>
  )
}