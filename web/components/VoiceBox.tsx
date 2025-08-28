'use client'

import React, { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { createAudioEnhancer } from '../lib/audio-enhancement.js'
// import { createVoiceActivityDetector } from '../lib/voice-activity-detection.js'
import WaveVisualizer from './WaveVisualizer'
import { trace } from './lib/voice-trace'

/**
 * Alice Voice Box – Mic‑driven Visualizer
 * 
 * Avancerad röst-komponent med real-time audio analys och fallback-lägen
 */

export type VoiceBoxProps = {
  bars?: number        // hur många bars att rendera (default 7)
  smoothing?: number   // 0..1 EMA smoothing (default 0.15)
  minScale?: number    // minimum visuell skala (default 0.1) - NOTE: Now handled automatically by ambient animation
  label?: string       // top label text (default 'ALICE RÖST')
  allowDemo?: boolean  // försök WebAudio demo om mic blockeras (default true)
  allowPseudo?: boolean // visuell fallback utan ljud (default true)
  onVoiceInput?: (text: string) => void  // callback för röst-input
  personality?: string // Alice personality: alice, formal, casual
  emotion?: string     // emotional tone: neutral, happy, calm, confident, friendly
  voiceQuality?: string // voice quality preference: medium, high\n  enableWakeWord?: boolean  // aktivera wake-word för hands-free (default false)\n  wakeWordSensitivity?: number  // wake-word känslighet 0-1 (default 0.7)
}

/**
 * Pure helper: delar upp frekvensdata i N band och returnerar normaliserade (0..1) medelvärden.
 */
export function computeBandAverages(data: Uint8Array, bars: number): number[] {
  const out: number[] = Array(Math.max(1, bars)).fill(0)
  if (!data.length) return out
  const step = Math.floor(data.length / out.length) || 1
  for (let i = 0; i < out.length; i++) {
    const start = i * step
    const end = i === out.length - 1 ? data.length : start + step
    let sum = 0
    for (let j = start; j < end; j++) sum += data[j]
    const avg = sum / Math.max(1, end - start)
    out[i] = Math.pow(avg / 255, 0.9) // mjuk kurva, 0..1
  }
  return out
}

/**
 * Post-processing för svensk speech recognition
 * Matchar backend STT post-processing
 */
export function postProcessSwedishSpeech(text: string): string {
  if (!text) return text
  
  // Vanliga svenska korrigeringar för browser speech API
  const corrections: Record<string, string> = {
    // Engelska -> Svenska
    'okay': 'okej',
    'ok': 'okej',
    'hello': 'hej',
    'hi': 'hej', 
    'bye': 'hej då',
    'yes': 'ja',
    'no': 'nej',
    'please': 'tack',
    'thank you': 'tack',
    'sorry': 'förlåt',
    
    // AI-kommandon
    'allis': 'Alice',
    'alis': 'Alice',
    'play music': 'spela musik',
    'stop music': 'stoppa musik',
    'pause music': 'pausa musik', 
    'send email': 'skicka mejl',
    'read email': 'läs mejl',
    'what time': 'vad är klockan',
    "what's the time": 'vad är klockan',
    
    // Vanliga mishörningar
    'alice s': 'Alice',
    'alice,': 'Alice',
    'alice.': 'Alice',
  }
  
  let corrected = text.toLowerCase()
  
  // Applicera korrigeringar
  Object.entries(corrections).forEach(([wrong, right]) => {
    const regex = new RegExp(`\\b${wrong.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi')
    corrected = corrected.replace(regex, right)
  })
  
  // Alice ska alltid ha stor bokstav
  corrected = corrected.replace(/\balice\b/gi, 'Alice')
  
  // Kapitaliera första bokstaven
  corrected = corrected.charAt(0).toUpperCase() + corrected.slice(1)
  
  return corrected.trim()
}

type Mode = 'idle' | 'mic' | 'demo' | 'pseudo'

// SpeechRecognition types
declare global {
  interface Window {
    SpeechRecognition: any
    webkitSpeechRecognition: any
  }
}

export default function VoiceBox({
  bars = 7,
  smoothing = 0.15,  // Minskad från 0.35 för snabbare respons
  minScale = 0.1,    // Legacy parameter - ambient animation now handles minimum visibility
  allowDemo = true,
  allowPseudo = true,
  onVoiceInput, // New prop for voice input callback
  personality = "alice", // Default Alice personality
  emotion = "friendly",  // Default friendly emotion
  voiceQuality = "medium" // Default voice quality
}: VoiceBoxProps) {
  // Audio graph refs
  const modeRef = useRef<Mode>('idle')
  const startedRef = useRef(false)
  const ctxRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const rafRef = useRef<number | null>(null)
  const oscRef = useRef<OscillatorNode[] | null>(null) // demo mode oscillators
  
  // Audio enhancement
  const audioEnhancerRef = useRef<any>(null)
  
  // Voice Activity Detection  
  const vadRef = useRef<any>(null)
  const [vadActive, setVadActive] = useState(false)

  // Speech recognition
  const recognitionRef = useRef<any>(null)
  
  // Speech Recognition integration (simplified)
  const speechRecognitionRef = useRef<any>(null)
  const [voiceGatewayActive, setVoiceGatewayActive] = useState(false) // Simple boolean state
  const [sid] = useState(() => trace.start("voicebox")) // egen session för knappen

  // DOM & smoothing state
  const barsWrapRef = useRef<HTMLDivElement | null>(null)
  const prevValsRef = useRef<number[]>(Array(bars).fill(0))

  // UI state
  const [error, setError] = useState<string | null>(null)
  const [live, setLive] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [ttsStatus, setTtsStatus] = useState<string | null>(null)
  const [voiceInfo, setVoiceInfo] = useState<any>(null)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const [lastErrorTime, setLastErrorTime] = useState<number>(0)
  
  // Error recovery state
  const maxReconnectAttempts = 3
  const errorCooldownMs = 5000 // 5 seconds between retry attempts

  // Keep prev array in sync when props change
  useEffect(() => {
    prevValsRef.current = Array(bars).fill(0)
  }, [bars, minScale])

  // Enhanced logging with context
  const logVoiceEvent = (level: 'info' | 'warn' | 'error', event: string, details?: any) => {
    const timestamp = new Date().toISOString()
    const context = {
      component: 'VoiceBox',
      mode: modeRef.current,
      live,
      isListening,
      reconnectAttempts,
      timestamp,
      ...details
    }
    
    const logMessage = `[VoiceBox] ${event}`
    
    switch (level) {
      case 'info':
        console.log(logMessage, context)
        break
      case 'warn':
        console.warn(logMessage, context)
        break
      case 'error':
        console.error(logMessage, context)
        // Send to error tracking service if available
        if (typeof window !== 'undefined' && (window as any).errorTracker) {
          (window as any).errorTracker.captureException(new Error(event), { extra: context })
        }
        break
    }
  }

  // Enhanced error handler with recovery logic
  const handleMicrophoneError = (error: any, context: string) => {
    const now = Date.now()
    const errorName = error?.name || 'UnknownError'
    const errorMessage = error?.message || 'Unknown error occurred'
    
    logVoiceEvent('error', `Microphone error in ${context}`, {
      errorName,
      errorMessage,
      errorCode: error?.code,
      constraints: error?.constraint,
      stack: error?.stack?.substring(0, 500) // Limit stack trace size
    })
    
    // Determine if this is a recoverable error
    const recoverableErrors = [
      'NotReadableError',    // Device busy
      'AbortError',         // Aborted by user/system  
      'NetworkError',       // Network issues
      'InternalError'       // Browser internal issues
    ]
    
    const isRecoverable = recoverableErrors.includes(errorName)
    const canRetry = reconnectAttempts < maxReconnectAttempts && 
                    (now - lastErrorTime) > errorCooldownMs
    
    // Set user-friendly error message
    let userMessage = ''
    switch (errorName) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        userMessage = 'Mikrofonbehörighet nekad. Tillåt mikrofon i webbläsarinställningar och försök igen.'
        break
      case 'NotFoundError':
        userMessage = 'Ingen mikrofon hittades. Kontrollera att en mikrofon är ansluten.'
        break
      case 'NotReadableError':
        userMessage = 'Mikrofonen används av annat program. Stäng andra program som kan använda mikrofonen.'
        break
      case 'OverConstrainedError':
        userMessage = 'Mikrofoninställningar är inte kompatibla. Försöker med standardinställningar.'
        break
      case 'SecurityError':
        userMessage = 'Säkerhetsfel. Använd HTTPS eller localhost för mikrofonåtkomst.'
        break
      case 'AbortError':
        userMessage = 'Mikrofonåtkomst avbröts. Försök igen.'
        break
      default:
        userMessage = `Mikrofonfel: ${errorMessage}`
        break
    }
    
    setError(userMessage)
    setLastErrorTime(now)
    
    // Attempt automatic recovery for certain errors
    if (isRecoverable && canRetry) {
      const nextAttempt = reconnectAttempts + 1
      setReconnectAttempts(nextAttempt)
      
      logVoiceEvent('info', `Attempting automatic recovery (${nextAttempt}/${maxReconnectAttempts})`)
      
      // Wait a bit before retrying
      setTimeout(() => {
        if (!live) { // Only retry if not currently live
          start()
        }
      }, errorCooldownMs)
    } else if (!isRecoverable && allowDemo) {
      // Fall back to demo mode for non-recoverable errors
      logVoiceEvent('info', 'Falling back to demo mode due to non-recoverable error')
      setTimeout(() => {
        startDemo()
      }, 1000)
    }
  }

  // Enhanced cleanup with error safety
  const safeCleanup = (componentName: string, cleanupFn: () => void) => {
    try {
      cleanupFn()
    } catch (error) {
      logVoiceEvent('warn', `Cleanup error in ${componentName}`, { error: error?.message })
    }
  }

  // Setup SpeechRecognition and fetch voice info on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition
      speechRecognitionRef.current = SpeechRec
      
      // Fetch available voice information
      fetchVoiceInfo()
    }
  }, [])
  
  const fetchVoiceInfo = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/tts/voices')
      if (response.ok) {
        const data = await response.json()
        setVoiceInfo(data)
      }
    } catch (error) {
      console.error('Failed to fetch voice info:', error)
    }
  }

  // Start ambient animation after component mounts
  useEffect(() => {
    const timer = setTimeout(() => {
      console.log('VoiceBox: Trying to start ambient animation')
      console.log('barsWrapRef.current:', barsWrapRef.current)
      if (barsWrapRef.current) {
        console.log('VoiceBox: Framer Motion handles animations automatically')
      } else {
        console.log('VoiceBox: barsWrapRef.current is null!')
      }
    }, 100) // Small delay to ensure DOM is ready
    
    return () => {
      clearTimeout(timer)
      stop()
    }
  }, [])

  async function start() {
    if (startedRef.current) {
      logVoiceEvent('info', 'Start called but already started')
      return
    }
    
    logVoiceEvent('info', 'Starting VoiceBox', { reconnectAttempts })
    setError(null)

    try {
      // Check for getUserMedia support
      if (!navigator.mediaDevices?.getUserMedia) {
        const err = new Error('getUserMedia saknas – kräver HTTPS/localhost eller modern webbläsare') as Error & { name: string }
        err.name = 'Unsupported'
        throw err
      }

      logVoiceEvent('info', 'Requesting microphone access')
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 48000
        }
      })
      streamRef.current = stream
      
      logVoiceEvent('info', 'Microphone access granted', {
        audioTracks: stream.getAudioTracks().length,
        trackSettings: stream.getAudioTracks()[0]?.getSettings()
      })

      // Monitor stream for interruption
      stream.getAudioTracks()[0]?.addEventListener('ended', () => {
        logVoiceEvent('warn', 'Audio track ended unexpectedly')
        handleMicrophoneError(new Error('Audio track ended'), 'stream monitoring')
      })

      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
      ctxRef.current = ctx
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 256  // Ytterligare reducerad för real-time respons
      analyser.smoothingTimeConstant = 0.2  // Minimerad för snabbare respons
      analyser.minDecibels = -70  // Justerad för bättre känslighet
      analyser.maxDecibels = -10
      analyserRef.current = analyser

      const source = ctx.createMediaStreamSource(stream)
      source.connect(analyser)
      sourceRef.current = source

      // Render
      beginRenderLoop()

      // iOS/Safari quirk: may start suspended
      if (ctx.state === 'suspended') {
        const resume = () => { 
          ctx.resume()
          logVoiceEvent('info', 'AudioContext resumed after user interaction')
          window.removeEventListener('touchend', resume) 
        }
        window.addEventListener('touchend', resume, { once: true })
      }

      setLive(true)
      startedRef.current = true
      modeRef.current = 'mic'
      setReconnectAttempts(0) // Reset on successful start
      
      // Starta speech recognition
      startSpeechRecognition()
      
      logVoiceEvent('info', 'VoiceBox started successfully')
      
    } catch (e: any) {
      handleMicrophoneError(e, 'start function')
      
      // Legacy fallback handling for specific cases
      const name = e?.name
      if ((name === 'NotAllowedError' || name === 'SecurityError' || name === 'NotReadableError') && allowDemo && reconnectAttempts === 0) {
        logVoiceEvent('info', 'Falling back to demo mode due to permission error')
        startDemo()
        return
      }
      
      stop()
    }
  }

  function startSpeechRecognition() {
    console.log('=== SPEECH RECOGNITION DEBUG START ===')
    console.log('Speech Recognition Support Check:', {
      speechRecognitionRef: !!speechRecognitionRef.current,
      webkitSpeechRecognition: !!(window as any).webkitSpeechRecognition,
      SpeechRecognition: !!(window as any).SpeechRecognition,
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      language: navigator.language,
      languages: navigator.languages,
      isSecureContext: window.isSecureContext,
      protocol: window.location.protocol,
      hostname: window.location.hostname
    })
    
    if (!speechRecognitionRef.current) {
      console.error('Speech recognition not supported in this browser')
      setError('Rösttranskribering stöds inte i din webbläsare. Prova Chrome/Edge.')
      return
    }

    try {
      console.log('Creating speech recognition instance...')
      const recognition = new speechRecognitionRef.current()
      
      console.log('Setting recognition properties...')
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'sv-SE'
      recognition.maxAlternatives = 1
      
      console.log('Speech Recognition created successfully:', {
        continuous: recognition.continuous,
        interimResults: recognition.interimResults,
        lang: recognition.lang,
        maxAlternatives: recognition.maxAlternatives
      })
      
      // Optimera för real-time processing
      recognition.serviceURI = 'wss://www.google.com/speech-api/v2/recognize'  // Explicit WebSocket
      
      // Justera timing för svensk tal
      if ('webkitSpeechRecognition' in window) {
        // Chrome-specifika optimeringar
        (recognition as any).continuous = true
        ;(recognition as any).interimResults = true
      }

      recognition.onstart = () => {
        console.log('=== SPEECH RECOGNITION STARTED EVENT ===')
        setIsListening(true)
        console.log('Speech recognition started successfully - event fired')
        console.log('isListening state set to true')
      }

      recognition.onend = () => {
        setIsListening(false)
        console.log('Speech recognition ended')
      }

      recognition.onerror = (event: any) => {
        const errorType = event.error
        const errorDetails = {
          errorType,
          message: event.message,
          timeStamp: event.timeStamp,
          fullEvent: JSON.stringify(event, null, 2),
          eventKeys: Object.keys(event || {}),
          recognition_state: recognition.state || 'unknown',
          recognition_lang: recognition.lang,
          recognition_continuous: recognition.continuous,
          recognition_interimResults: recognition.interimResults,
          browser: navigator.userAgent.split(' ')[0],
          timestamp: new Date().toISOString()
        }
        
        console.log('=== VOICE DEBUG START ===')
        console.log('Speech Recognition Error Event Full Details:', errorDetails)
        console.log('=== VOICE DEBUG END ===')
        
        logVoiceEvent('error', 'Speech recognition error', errorDetails)
        
        // Handle specific speech recognition errors
        switch (errorType) {
          case 'no-speech':
            logVoiceEvent('info', 'No speech detected - this is normal')
            break
          case 'audio-capture':
            handleMicrophoneError(new Error('Audio capture failed'), 'speech recognition')
            break
          case 'not-allowed':
            handleMicrophoneError(new Error('Microphone permission denied'), 'speech recognition')
            break
          case 'network':
            logVoiceEvent('warn', 'Network error in speech recognition - will retry')
            // Network errors are usually temporary, will auto-retry
            break
          case 'bad-grammar':
          case 'language-not-supported':
            logVoiceEvent('error', `Speech recognition configuration error: ${errorType}`)
            setError('Röstinställningar stöds inte. Kontrollera språkinställningar.')
            break
          default:
            logVoiceEvent('error', `Unhandled speech recognition error: ${errorType}`)
            break
        }
      }

      recognition.onresult = (event: any) => {
        const result = event.results[event.results.length - 1]
        const transcript = result[0].transcript
        const confidence = result[0].confidence || 0
        const isFinal = result.isFinal
        
        console.log('Voice result:', { transcript, confidence, isFinal })

        // Interim results för responsivitet (men send bara final)
        if (!isFinal) {
          // Visa interim för användarkänsla men send inte
          console.log('Interim result:', transcript)
        } else if (onVoiceInput && transcript.trim()) {
          // Endast skicka final results med innehåll
          const cleanTranscript = postProcessSwedishSpeech(transcript.trim())
          console.log('Voice input (final):', cleanTranscript)
          try {
            onVoiceInput(cleanTranscript)
            console.log('Successfully sent transcript to onVoiceInput')
          } catch (error) {
            console.error('Error in onVoiceInput callback:', error)
            setError('Ett fel uppstod vid bearbetning av röstkommandot')
          }
        }
      }

      console.log('Starting speech recognition...')
      try {
        recognition.start()
        recognitionRef.current = recognition
        console.log('Speech recognition started successfully')
        console.log('=== SPEECH RECOGNITION DEBUG END ===')
      } catch (startError) {
        console.error('Failed to start speech recognition (start() call):', {
          error: startError.message,
          stack: startError.stack,
          name: startError.name
        })
        throw startError
      }
    } catch (error) {
      console.error('Failed to start speech recognition (general error):', {
        error: error.message,
        stack: error.stack,
        name: error.name,
        recognition_available: !!speechRecognitionRef.current
      })
      console.log('=== SPEECH RECOGNITION DEBUG END (ERROR) ===')
      setError('Kunde inte starta röstinspelning: ' + error.message)
    }
  }

  function beginRenderLoop() {
    console.log('beginRenderLoop called')
    const analyser = analyserRef.current
    const host = barsWrapRef.current
    if (!host) {
      console.log('No host element, exiting beginRenderLoop')
      return
    }

    // Check if already running
    if (rafRef.current) {
      console.log('Animation already running, cancelling old one')
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }

    console.log('Starting new animation loop')

    // If we don't have an analyser (pseudo mode), we'll synthesize values.
    const data = analyser ? new Uint8Array(analyser.frequencyBinCount) : null

    const tick = (t: number) => {
      if (!barsWrapRef.current) return

      let bandVals: number[]
      if (analyser && analyserRef.current) {
        analyserRef.current.getByteFrequencyData(data!)
        bandVals = computeBandAverages(data!, bars)
        // Optimerad känslighet för real-time audio
        bandVals = bandVals.map(val => {
          // Multi-stage enhancement för bättre respons
          let enhanced = Math.pow(val, 0.6) // Mer aggressiv kurva
          enhanced = enhanced * 1.3 // Boost overall sensitivity
          return Math.min(1, enhanced) // Cap vid 1
        })
      } else {
        // Pseudo values: smooth sin/noise mix so it looks audio-like
        bandVals = Array.from({ length: bars }, (_, i) => {
          const base = 0.4 + 0.4 * Math.sin((t / 300) + i * 0.9)  // Snabbare från 480
          const jitter = 0.15 * (Math.sin((t / 80) + i * 2.1) + 1) / 2  // Snabbare från 97
          return Math.min(1, Math.max(0, base + jitter))
        })
      }

      for (let i = 0; i < bandVals.length; i++) {
        const prev = prevValsRef.current[i]
        const smoothed = prev + (bandVals[i] - prev) * smoothing
        prevValsRef.current[i] = smoothed
      }

      const children = barsWrapRef.current.children
      for (let i = 0; i < children.length; i++) {
        const v = Math.max(0, Math.min(1, prevValsRef.current[i] ?? 0))
        const cell = children[i] as HTMLElement
        const barEl = cell.querySelector('.bar') as HTMLElement | null
        if (barEl) {
          // "Thinking" animation - smooth neural-like activity
          const thinkingBase = 8 + Math.sin(t * 0.0008 + i * 0.4) * 2.5 // Slow base rhythm
          const neuralLayer1 = Math.sin(t * 0.0015 + i * 0.7) * 1.5 // Secondary neural wave
          const neuralLayer2 = Math.sin(t * 0.0012 + i * 0.9) * 1 // Tertiary subtle wave
          const thinkingHeight = thinkingBase + neuralLayer1 + neuralLayer2
          
          // Audio threshold - more sensitive detection
          const audioThreshold = 0.02
          const hasAudio = v > audioThreshold
          
          let finalHeight: number
          let opacity: number
          
          if (hasAudio) {
            // Audio mode: combine thinking base with audio data
            const audioHeight = Math.max(15, v * 75)
            const thinkingComponent = Math.max(8, thinkingHeight)
            const blendFactor = Math.min(1, (v - audioThreshold) / 0.03)
            finalHeight = thinkingComponent + (audioHeight - thinkingComponent) * blendFactor
            opacity = 0.6 + v * 0.4 // Higher opacity for audio response
          } else {
            // Thinking mode: smooth neural-like activity
            finalHeight = Math.max(5, thinkingHeight)
            opacity = 0.3 + Math.sin(t * 0.0018 + i * 0.6) * 0.2 // Smooth opacity waves
          }
          
          // Debug first bar och audio metrics (mindre frekvent)
          if (i === 0 && Math.random() < 0.01) { // 1% av tiden för att inte spamma
            console.log(`Bar 0: finalHeight=${finalHeight.toFixed(2)}%, opacity=${opacity.toFixed(3)}`)
            
            // Visa audio enhancement metrics om tillgängligt
            if (audioEnhancerRef.current) {
              const metrics = audioEnhancerRef.current.getAudioMetrics()
              if (metrics) {
                console.log('Audio metrics:', {
                  quality: metrics.quality,
                  avgEnergy: metrics.avgEnergy.toFixed(1),
                  snr: metrics.signalToNoiseRatio?.toFixed(1) || 'N/A',
                  noiseGate: (metrics.noiseGateLevel * 100).toFixed(0) + '%'
                })
              }
            }
          }
          
          barEl.style.height = `${finalHeight}%`
          barEl.style.opacity = String(Math.max(0.2, Math.min(1, opacity)))
        }
      }

      rafRef.current = requestAnimationFrame(tick)
    }

    rafRef.current = requestAnimationFrame(tick)
  }

  function startDemo() {
    if (startedRef.current) return
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
      ctxRef.current = ctx
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 512  // Minskad från 1024 för snabbare respons
      analyser.smoothingTimeConstant = 0.4  // Minskad från 0.75 för mindre smoothing
      analyserRef.current = analyser

      // Oscillator graph
      const gain = ctx.createGain(); gain.gain.value = 0.22
      const o1 = ctx.createOscillator(); o1.frequency.value = 110; o1.type = 'sawtooth'
      const o2 = ctx.createOscillator(); o2.frequency.value = 420; o2.type = 'triangle'
      const o3 = ctx.createOscillator(); o3.frequency.value = 1650; o3.type = 'square'

      const lfo = ctx.createOscillator(); lfo.frequency.value = 0.7
      const lfoGain = ctx.createGain(); lfoGain.gain.value = 0.35
      lfo.connect(lfoGain).connect(gain.gain)

      // Some browsers require graph to reach destination to "run"—use a muted tap
      const mute = ctx.createGain(); mute.gain.value = 0

      o1.connect(gain); o2.connect(gain); o3.connect(gain)
      gain.connect(analyser)
      gain.connect(mute).connect(ctx.destination) // muted output

      o1.start(); o2.start(); o3.start(); lfo.start()
      oscRef.current = [o1, o2, o3, lfo]

      beginRenderLoop()

      // Try to resume explicitly after a user gesture
      ctx.resume?.()

      setLive(true)
      startedRef.current = true
      modeRef.current = 'demo'
    } catch (err) {
      if (allowPseudo) {
        setError('Demo‑läge blockerat – visar visuell fallback utan ljud.')
        startPseudo()
        return
      }
      setError('Demo‑läge misslyckades')
      stop()
    }
  }

  function startPseudo() {
    if (startedRef.current) return
    analyserRef.current = null // ensure render loop uses pseudo branch
    beginRenderLoop()
    setLive(true)
    startedRef.current = true
    modeRef.current = 'pseudo'
  }

  function stop() {
    logVoiceEvent('info', 'Stopping VoiceBox', { currentMode: modeRef.current })
    
    // Cancel animation frame
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }

    // Cleanup audio nodes with error safety
    safeCleanup('AudioSource', () => {
      if (sourceRef.current) {
        sourceRef.current.disconnect()
        sourceRef.current = null
      }
    })
    
    safeCleanup('AudioAnalyser', () => {
      if (analyserRef.current) {
        analyserRef.current.disconnect()
        analyserRef.current = null
      }
    })
    
    // Cleanup audio enhancement
    safeCleanup('AudioEnhancer', () => {
      if (audioEnhancerRef.current) {
        audioEnhancerRef.current.dispose()
        audioEnhancerRef.current = null
      }
    })

    // Cleanup oscillators (demo mode)
    safeCleanup('Oscillators', () => {
      if (oscRef.current) {
        oscRef.current.forEach(o => o.stop())
        oscRef.current = null
      }
    })

    // Cleanup audio context
    safeCleanup('AudioContext', () => {
      if (ctxRef.current) {
        if (ctxRef.current.state !== 'closed') {
          ctxRef.current.close()
        }
        ctxRef.current = null
      }
    })

    // Cleanup media stream
    safeCleanup('MediaStream', () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => {
          track.stop()
          logVoiceEvent('info', 'Stopped media track', { 
            kind: track.kind,
            label: track.label,
            readyState: track.readyState
          })
        })
        streamRef.current = null
      }
    })

    // Cleanup speech recognition
    safeCleanup('SpeechRecognition', () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
        recognitionRef.current = null
      }
    })

    // Reset state
    startedRef.current = false
    modeRef.current = 'idle'
    setLive(false)
    setIsListening(false)
    
    logVoiceEvent('info', 'VoiceBox stopped successfully')
  }

  const testEnhancedTTS = async () => {
    logVoiceEvent('info', 'Starting TTS test', { personality, emotion, voiceQuality })
    setTtsStatus('Testar Alice röst...')
    
    try {
      // First try enhanced TTS endpoint
      const response = await fetch('http://127.0.0.1:8000/api/tts/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: `Hej! Jag är Alice med ${personality} personlighet och ${emotion} känsla.`,
          personality: personality,
          emotion: emotion,
          voice: voiceQuality === 'high' ? 'sv_SE-nst-high' : 'sv_SE-nst-medium',
          cache: true
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          logVoiceEvent('info', 'Enhanced TTS success', { voice: data.voice, cached: data.cached })
          
          // Play the enhanced audio
          const audioBuffer = Uint8Array.from(atob(data.audio_data), c => c.charCodeAt(0))
          const blob = new Blob([audioBuffer], { type: 'audio/wav' })
          const audio = new Audio(URL.createObjectURL(blob))
          
          // Handle audio play errors
          audio.onerror = (e) => {
            logVoiceEvent('error', 'Audio playback error', { error: e })
            setTtsStatus('Ljuduppspelning misslyckades')
            setTimeout(() => setTtsStatus(null), 3000)
          }
          
          audio.onended = () => {
            logVoiceEvent('info', 'TTS audio playback completed')
            setTimeout(() => setTtsStatus(null), 1000)
          }
          
          setTtsStatus(`🎵 Spelar: Alice ${data.emotion} röst`)
          await audio.play()
          
          return
        } else {
          logVoiceEvent('warn', 'Enhanced TTS returned failure', data)
        }
      } else {
        logVoiceEvent('warn', 'Enhanced TTS HTTP error', { status: response.status, statusText: response.statusText })
      }
      
      // Fallback to browser TTS if enhanced fails
      logVoiceEvent('info', 'Falling back to browser TTS')
      await testBrowserTTS()
      
    } catch (error: any) {
      logVoiceEvent('error', 'TTS test error', { error: error?.message, stack: error?.stack?.substring(0, 200) })
      
      // Try browser TTS as fallback
      try {
        await testBrowserTTS()
      } catch (fallbackError: any) {
        logVoiceEvent('error', 'Browser TTS fallback also failed', { error: fallbackError?.message })
        setTtsStatus('❌ TTS-test misslyckades')
        setTimeout(() => setTtsStatus(null), 3000)
      }
    }
  }

  const testBrowserTTS = async () => {
    if (!window.speechSynthesis) {
      setTtsStatus('TTS inte stödd i denna webbläsare')
      return
    }

    const utterance = new SpeechSynthesisUtterance(
      `Hej! Jag är Alice, din svenska AI-assistent. Jag använder ${personality} personlighet med ${emotion} känsla.`
    )
    
    // Try to find Swedish voice
    const voices = window.speechSynthesis.getVoices()
    const swedishVoice = voices.find(voice => 
      voice.lang.includes('sv') || 
      voice.name.toLowerCase().includes('swedish') ||
      voice.name.toLowerCase().includes('svenska')
    )
    
    if (swedishVoice) {
      utterance.voice = swedishVoice
      setTtsStatus(`🗣️ Spelar: ${swedishVoice.name} (${swedishVoice.lang})`)
    } else {
      setTtsStatus('🗣️ Spelar: Browser TTS (English fallback)')
    }
    
    // Apply personality settings
    switch (personality) {
      case 'alice':
        utterance.rate = 1.05
        utterance.pitch = 1.02
        break
      case 'formal':
        utterance.rate = 0.95
        utterance.pitch = 0.98
        break
      case 'casual':
        utterance.rate = 1.1
        utterance.pitch = 1.05
        break
    }
    
    utterance.onend = () => {
      setTimeout(() => setTtsStatus(null), 2000)
    }
    
    utterance.onerror = (error) => {
      console.error('Browser TTS error:', error)
      setTtsStatus('Browser TTS misslyckades')
    }
    
    window.speechSynthesis.speak(utterance)
  }

  // Simple Voice Control using Browser SpeechRecognition
  const startVoiceRecognition = async () => {
    console.log("🎙️ MIC BUTTON CLICKED - Starting voice recognition");
    trace.ev(sid, "ui.mic.click", { statusBefore: voiceGatewayActive });
    try {
      console.log("🎙️ Calling start() function...");
      // Start browser speech recognition instead of WebSocket
      await start(); // Use existing VoiceBox start() function
      console.log("🎙️ start() completed, setting UI active");
      setVoiceGatewayActive(true); // Update UI state
    } catch (e: any) {
      console.error("🎙️ ERROR in startVoiceRecognition:", e);
      trace.error(sid, "ui.mic.error", e);
      setError(`Speech recognition fel: ${e.message}`);
    }
  };

  const stopVoiceRecognition = async () => {
    trace.ev(sid, "ui.mic.click", { action: "stop" });
    stop(); // Use existing VoiceBox stop() function  
    setVoiceGatewayActive(false); // Update UI state
  };

  return (
    <div className="w-full max-w-3xl mx-auto select-none" role="region" aria-label="Voice visualizer" data-testid="voice-box-container">
      <div className="relative rounded-2xl p-6 bg-cyan-950/20 border border-cyan-500/20 shadow-[0_0_60px_-20px_rgba(34,211,238,.5)]" data-testid="voice-box-panel">
        {/* Status Mic Icon - Top Right */}
        <div className="absolute top-4 right-4 z-10">
          <button 
            onClick={voiceGatewayActive ? stopVoiceRecognition : startVoiceRecognition}
            className={`
              relative w-5 h-5 transition-all duration-300 cursor-pointer hover:scale-110
              ${voiceGatewayActive ? 'text-red-500 animate-pulse' : 'text-gray-500/60 hover:text-gray-400'}
            `}
            title={voiceGatewayActive ? 'Stoppa röstgateway' : 'Starta röstgateway'}
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="w-full h-full"
            >
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
            {voiceGatewayActive && (
              <div className="absolute -inset-1 rounded-full bg-red-500/20 animate-ping" />
            )}
          </button>
        </div>
        {/* Wave Visualizer */}
        <div className="h-20 md:h-24" data-testid="voice-box-bars">
          <WaveVisualizer 
            isActive={voiceGatewayActive}
            className="w-full h-full"
          />
        </div>

        {/* Debug Status Panel - Bottom of VoiceBox */}
        {(new URLSearchParams(typeof window !== "undefined" ? window.location.search : "").get("voiceDebug") === "1") && (
          <div className="mt-4 p-3 bg-black/30 rounded-lg text-xs text-cyan-300/80 space-y-2 border border-cyan-400/20">
            <div className="flex items-center justify-between">
              <div>Status: <span className="font-mono text-cyan-200">{voiceGatewayActive ? 'active' : 'idle'}</span></div>
              <div>sid: <span className="font-mono text-cyan-200">{sid}</span></div>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => console.table((window as any).voiceTrace?.dump() || [])}
                className="border border-cyan-400/30 px-2 py-1 rounded hover:bg-cyan-400/10"
              >
                Dump logs
              </button>
              <button
                onClick={() => (window as any).voiceTrace?.clear()}
                className="border border-cyan-400/30 px-2 py-1 rounded hover:bg-cyan-400/10"
              >
                Clear
              </button>
              <button
                onClick={() => (window as any).voiceTrace?.level('info')}
                className="border border-cyan-400/30 px-2 py-1 rounded hover:bg-cyan-400/10"
              >
                Level: Info
              </button>
            </div>
          </div>
        )}

        {/* Inner ring to match Alice HUD Pane style */}
        <div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-inset ring-cyan-300/10" />
        
        {/* Simple Speech Recognition - no complex WebSocket needed */}
      </div>
    </div>
  )
}
