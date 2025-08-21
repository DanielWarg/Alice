'use client'

import React, { useEffect, useRef, useState } from 'react'

/**
 * Alice Voice Box – Mic‑driven Visualizer
 * 
 * Avancerad röst-komponent med real-time audio analys och fallback-lägen
 */

export type VoiceBoxProps = {
  bars?: number        // hur många bars att rendera (default 5)
  smoothing?: number   // 0..1 EMA smoothing (default 0.35)
  minScale?: number    // minimum visuell skala (default 0)
  label?: string       // top label text (default 'ALICE RÖST')
  allowDemo?: boolean  // försök WebAudio demo om mic blockeras (default true)
  allowPseudo?: boolean // visuell fallback utan ljud (default true)
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

type Mode = 'idle' | 'mic' | 'demo' | 'pseudo'

export default function VoiceBox({
  bars = 5,
  smoothing = 0.35,
  minScale = 0,
  label = 'ALICE RÖST',
  allowDemo = true,
  allowPseudo = true,
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

  // DOM & smoothing state
  const barsWrapRef = useRef<HTMLDivElement | null>(null)
  const prevValsRef = useRef<number[]>(Array(bars).fill(0))

  // UI state
  const [error, setError] = useState<string | null>(null)
  const [live, setLive] = useState(false)

  // Keep prev array in sync when props change
  useEffect(() => {
    prevValsRef.current = Array(bars).fill(0)
  }, [bars, minScale])

  // Cleanup on unmount
  useEffect(() => {
    return () => stop()
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
      analyser.fftSize = 1024
      analyser.smoothingTimeConstant = 0.6
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

  function beginRenderLoop() {
    const analyser = analyserRef.current
    const host = barsWrapRef.current
    if (!host) return

    // If we don't have an analyser (pseudo mode), we'll synthesize values.
    const data = analyser ? new Uint8Array(analyser.frequencyBinCount) : null

    const tick = (t: number) => {
      if (!barsWrapRef.current) return

      let bandVals: number[]
      if (analyser && analyserRef.current) {
        analyserRef.current.getByteFrequencyData(data!)
        bandVals = computeBandAverages(data!, bars)
      } else {
        // Pseudo values: smooth sin/noise mix so it looks audio-like
        bandVals = Array.from({ length: bars }, (_, i) => {
          const base = 0.35 + 0.35 * Math.sin((t / 480) + i * 0.9)
          const jitter = 0.1 * (Math.sin((t / 97) + i * 2.1) + 1) / 2
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
          const pct = Math.max(minScale * 100, v * 100)
          if (pct < 1.2) {
            barEl.style.height = '0px'
            barEl.style.opacity = '0'
          } else {
            barEl.style.height = `${pct}%`
            barEl.style.opacity = String(0.5 + v * 0.5)
          }
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
      analyser.fftSize = 1024
      analyser.smoothingTimeConstant = 0.75
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

    if (oscRef.current) {
      try { oscRef.current.forEach(o => { try { o.stop() } catch {} }) } catch {}
      oscRef.current = null
    }

    if (ctxRef.current) { try { ctxRef.current.close() } catch {} ; ctxRef.current = null }

    if (streamRef.current) {
      try { streamRef.current.getTracks().forEach(t => t.stop()) } catch {}
      streamRef.current = null
    }

    startedRef.current = false
    modeRef.current = 'idle'
    setLive(false)
  }

  return (
    <div className="w-full max-w-3xl mx-auto select-none" role="region" aria-label="Voice visualizer">
      <div className="text-center mb-2 tracking-[0.35em] text-xs text-neutral-400">{label}</div>

      <div className="relative rounded-2xl p-6 bg-black/95 ring-1 ring-zinc-800 shadow-[0_0_40px_rgba(0,0,0,0.6)]">
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
                  height: '1px',
                  transition: 'height 80ms linear, opacity 80ms linear',
                  background: 'linear-gradient(180deg, #67e8f9 0%, #22d3ee 40%, #06b6d4 100%)',
                  boxShadow: '0 0 22px rgba(34, 211, 238, 0.55), inset 0 -10px 18px rgba(0,0,0,0.35)'
                }}
              />
            </div>
          ))}
        </div>

        {/* Controls */}
        <div className="mt-5 flex items-center justify-center gap-3">
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
          <span className={`text-xs ${live ? 'text-cyan-400' : 'text-zinc-500'}`}>{live ? 'LIVE' : 'AV'}</span>
        </div>

        {error && (
          <div className="mt-3 text-center text-sm text-red-400">{error}</div>
        )}
      </div>

      {/* Subtle edge frame to echo the 1px outer ring look */}
      <div className="mt-3 h-px w-full bg-gradient-to-r from-transparent via-zinc-700 to-transparent" />
    </div>
  )
}
