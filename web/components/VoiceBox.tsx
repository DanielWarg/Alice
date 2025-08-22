'use client'

import React, { useEffect, useRef, useState } from 'react'
import { createAudioEnhancer } from '../lib/audio-enhancement.js'
import { createVoiceActivityDetector } from '../lib/voice-activity-detection.js'

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
  const speechRecognitionRef = useRef<any>(null)

  // DOM & smoothing state
  const barsWrapRef = useRef<HTMLDivElement | null>(null)
  const prevValsRef = useRef<number[]>(Array(bars).fill(0))

  // UI state
  const [error, setError] = useState<string | null>(null)
  const [live, setLive] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [ttsStatus, setTtsStatus] = useState<string | null>(null)
  const [voiceInfo, setVoiceInfo] = useState<any>(null)

  // Keep prev array in sync when props change
  useEffect(() => {
    prevValsRef.current = Array(bars).fill(0)
  }, [bars, minScale])

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
      const response = await fetch('/api/tts/voices')
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
        console.log('VoiceBox: Starting beginRenderLoop')
        beginRenderLoop() // Start ambient animation after DOM is ready
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
    if (startedRef.current) return
    setError(null)

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        const err = new Error('getUserMedia saknas – kräver HTTPS/localhost eller modern webbläsare') as Error & { name: string }
        err.name = 'Unsupported'
        throw err
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

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
        const resume = () => { ctx.resume(); window.removeEventListener('touchend', resume) }
        window.addEventListener('touchend', resume, { once: true })
      }

      setLive(true)
      startedRef.current = true
      modeRef.current = 'mic'
      
      // Starta speech recognition
      startSpeechRecognition()
    } catch (e: any) {
      const name = e?.name
      if ((name === 'NotAllowedError' || name === 'SecurityError' || name === 'NotReadableError') && allowDemo) {
        setError('Mikrofon nekad – kör demo‑läge. Tillåt mic på din domän för live-input.')
        startDemo()
        return
      }
      if (name === 'NotFoundError') {
        setError('Ingen mikrofon hittades. Välj/anslut en mic och försök igen.')
      } else if (name === 'Unsupported') {
        setError('Denna miljö blockerar mic. Öppna på https:// (eller localhost) utanför iframe och tillåt mikrofonen.')
      } else {
        setError(e?.message || 'Mikrofon kunde inte startas')
      }
      stop()
    }
  }

  function startSpeechRecognition() {
    if (!speechRecognitionRef.current) {
      console.warn('Speech recognition not supported')
      return
    }

    try {
      const recognition = new speechRecognitionRef.current()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'sv-SE'
      recognition.maxAlternatives = 1
      
      // Optimera för real-time processing
      recognition.serviceURI = 'wss://www.google.com/speech-api/v2/recognize'  // Explicit WebSocket
      
      // Justera timing för svensk tal
      if ('webkitSpeechRecognition' in window) {
        // Chrome-specifika optimeringar
        (recognition as any).continuous = true
        ;(recognition as any).interimResults = true
      }

      recognition.onstart = () => {
        setIsListening(true)
        console.log('Speech recognition started')
      }

      recognition.onend = () => {
        setIsListening(false)
        console.log('Speech recognition ended')
      }

      recognition.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error)
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
          onVoiceInput(cleanTranscript)
        }
      }

      recognition.start()
      recognitionRef.current = recognition
    } catch (error) {
      console.error('Failed to start speech recognition:', error)
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
          // Ambient animation - extremely slow zen breathing like hibernation
          const ambientHeight = 2.1 + 
            Math.sin(t * 0.00001 + i * 0.1) * 0.1 + // Ultra slow primary breath
            Math.sin(t * 0.000007 + i * 0.15) * 0.05 // Barely perceptible heart whisper
          
          // Audio threshold - more sensitive detection
          const audioThreshold = 0.02
          const hasAudio = v > audioThreshold
          
          let finalHeight: number
          let opacity: number
          
          if (hasAudio) {
            // Audio mode: scale audio data to reasonable range (6-85%)
            const audioHeight = Math.max(6, v * 85)
            // Smooth transition: blend with ambient when audio is low
            const blendFactor = Math.min(1, (v - audioThreshold) / 0.03)
            const ambientComponent = Math.max(1, Math.min(6, ambientHeight))
            finalHeight = ambientComponent + (audioHeight - ambientComponent) * blendFactor
            opacity = 0.6 + v * 0.4 // Higher opacity for audio response
          } else {
            // Ambient mode: barely perceptible zen state
            finalHeight = Math.max(2, Math.min(2.3, ambientHeight))
            opacity = 0.15 + Math.sin(t * 0.000005 + i * 0.2) * 0.02 // Almost imperceptible
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
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = null

    if (sourceRef.current) { try { sourceRef.current.disconnect() } catch {} ; sourceRef.current = null }
    if (analyserRef.current) { try { analyserRef.current.disconnect() } catch {} ; analyserRef.current = null }
    
    // Cleanup audio enhancement
    if (audioEnhancerRef.current) {
      try { audioEnhancerRef.current.dispose() } catch {}
      audioEnhancerRef.current = null
    }

    if (oscRef.current) {
      try { oscRef.current.forEach(o => { try { o.stop() } catch {} }) } catch {}
      oscRef.current = null
    }

    if (ctxRef.current) { try { ctxRef.current.close() } catch {} ; ctxRef.current = null }

    if (streamRef.current) {
      try { streamRef.current.getTracks().forEach(t => t.stop()) } catch {}
      streamRef.current = null
    }

    // Stoppa speech recognition
    if (recognitionRef.current) {
      try { recognitionRef.current.stop() } catch {}
      recognitionRef.current = null
    }

    startedRef.current = false
    modeRef.current = 'idle'
    setLive(false)
    setIsListening(false)
  }

  const testEnhancedTTS = async () => {
    setTtsStatus('Testar Alice röst...')
    
    try {
      // First try enhanced TTS endpoint
      const response = await fetch('/api/tts/synthesize', {
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
          // Play the enhanced audio
          const audioBuffer = Uint8Array.from(atob(data.audio_data), c => c.charCodeAt(0))
          const blob = new Blob([audioBuffer], { type: 'audio/wav' })
          const audio = new Audio(URL.createObjectURL(blob))
          
          setTtsStatus(`🎵 Spelar: Alice ${data.emotion} röst`)
          await audio.play()
          
          setTimeout(() => setTtsStatus(null), 3000)
          return
        }
      }
      
      // Fallback to browser TTS if enhanced fails
      console.log('Enhanced TTS failed, using browser fallback')
      await testBrowserTTS()
      
    } catch (error) {
      console.error('TTS test failed, using browser fallback:', error)
      await testBrowserTTS()
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

  return (
    <div className="w-full max-w-3xl mx-auto select-none" role="region" aria-label="Voice visualizer">
      <div className="relative rounded-2xl p-6 bg-cyan-950/20 border border-cyan-500/20 shadow-[0_0_60px_-20px_rgba(34,211,238,.5)]">
        {/* Bars */}
        <div
          ref={barsWrapRef}
          className="relative grid grid-cols-5 gap-px items-end justify-center h-40 md:h-48"
          style={{ gridTemplateColumns: `repeat(${bars}, minmax(0,1fr))` }}
        >
          {Array.from({ length: bars }).map((_, i) => (
            <div key={i} className="relative h-full flex items-end justify-center">
              {/* Inner bar at half width; starts as 1px line, grows with audio */}
              <div
                className="bar w-1/2 rounded-full"
                style={{
                  height: '2px',
                  transition: 'height 60ms ease-out, opacity 80ms ease-out',  // Smoother transitions for ambient animation
                  background: 'linear-gradient(180deg, #67e8f9 0%, #22d3ee 40%, #06b6d4 100%)',
                  boxShadow: '0 0 22px rgba(34, 211, 238, 0.55), inset 0 -10px 18px rgba(0,0,0,0.35)'
                }}
              />
            </div>
          ))}
        </div>

        {/* Controls */}
        <div className="mt-5 flex flex-col gap-3">
          <div className="flex items-center justify-center gap-3">
            {!live ? (
              <button
                onClick={start}
                className="px-4 py-2 rounded-xl bg-cyan-500/90 text-black font-medium hover:bg-cyan-400 active:scale-[0.98] transition"
              >
                Starta mic
              </button>
            ) : (
              <button
                onClick={stop}
                className="px-4 py-2 rounded-xl bg-zinc-800 text-zinc-100 font-medium hover:bg-zinc-700 active:scale-[0.98] transition"
              >
                Stoppa
              </button>
            )}
            <button
              onClick={testEnhancedTTS}
              className="px-3 py-1 rounded-lg bg-purple-500/80 text-white text-sm font-medium hover:bg-purple-400 active:scale-[0.98] transition"
            >
              Test TTS
            </button>
            <span className={`text-xs ${live ? 'text-cyan-400' : 'text-zinc-500'}`}>{live ? 'LIVE' : 'AV'}</span>
          </div>
          
          {/* Voice Settings Info */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-center gap-4 text-xs text-zinc-400">
              <span>Personlighet: <span className="text-cyan-400">{personality}</span></span>
              <span>Känsla: <span className="text-purple-400">{emotion}</span></span>
              <span>Kvalitet: <span className="text-green-400">{voiceQuality}</span></span>
            </div>
            
            {/* Quick Settings */}
            <div className="flex items-center justify-center gap-2 text-xs">
              <select 
                value={personality}
                onChange={(e) => {
                  // Note: This would need to be passed as a prop to actually change
                  console.log('Personality change:', e.target.value)
                }}
                className="px-2 py-1 rounded bg-zinc-800 text-zinc-200 border border-zinc-700 text-xs"
              >
                <option value="alice">Alice</option>
                <option value="formal">Formell</option>
                <option value="casual">Casual</option>
              </select>
              
              <select 
                value={emotion}
                onChange={(e) => {
                  console.log('Emotion change:', e.target.value)
                }}
                className="px-2 py-1 rounded bg-zinc-800 text-zinc-200 border border-zinc-700 text-xs"
              >
                <option value="neutral">Neutral</option>
                <option value="happy">Glad</option>
                <option value="calm">Lugn</option>
                <option value="confident">Självsäker</option>
                <option value="friendly">Vänlig</option>
              </select>
              
              <select 
                value={voiceQuality}
                onChange={(e) => {
                  console.log('Quality change:', e.target.value)
                }}
                className="px-2 py-1 rounded bg-zinc-800 text-zinc-200 border border-zinc-700 text-xs"
              >
                <option value="medium">Medium</option>
                <option value="high">Hög</option>
              </select>
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-3 text-center text-sm text-red-400">{error}</div>
        )}
        
        {ttsStatus && (
          <div className="mt-2 text-center text-sm text-purple-400">{ttsStatus}</div>
        )}
        
        {voiceInfo && (
          <div className="mt-2 text-center text-xs text-zinc-500">
            {voiceInfo.voices?.length || 0} röstmodeller tillgängliga
          </div>
        )}
        
        {/* Inner ring to match Alice HUD Pane style */}
        <div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-inset ring-cyan-300/10" />
      </div>
    </div>
  )
}
