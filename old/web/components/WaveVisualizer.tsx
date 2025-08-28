'use client'

import React, { useEffect, useRef, useState } from 'react'

interface WaveVisualizerProps {
  isActive: boolean
  className?: string
}

export default function WaveVisualizer({ isActive, className = '' }: WaveVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>()
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const dataArrayRef = useRef<Uint8Array | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const waveDataRef = useRef<number[]>([])

  useEffect(() => {
    if (isActive) {
      initializeAudio()
    } else {
      cleanupAudio()
      // No idle wave - just clean canvas
      clearCanvas()
    }

    return cleanupAudio
  }, [isActive])

  const initializeAudio = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
      audioContextRef.current = audioContext

      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 512
      analyser.smoothingTimeConstant = 0.8
      analyserRef.current = analyser

      const source = audioContext.createMediaStreamSource(stream)
      source.connect(analyser)

      const bufferLength = analyser.frequencyBinCount
      dataArrayRef.current = new Uint8Array(bufferLength)

      animateAudioWave()
    } catch (error) {
      console.error('Error initializing audio:', error)
      clearCanvas()
    }
  }

  const cleanupAudio = () => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }

    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    analyserRef.current = null
    dataArrayRef.current = null
  }

  const clearCanvas = () => {
    if (!canvasRef.current) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
    }
  }

  const animateAudioWave = () => {
    if (!canvasRef.current || !analyserRef.current || !dataArrayRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    analyserRef.current.getByteTimeDomainData(dataArrayRef.current)

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Draw waveform with thicker line for better visibility
    ctx.strokeStyle = '#06b6d4'
    ctx.lineWidth = 3
    ctx.beginPath()

    const sliceWidth = canvas.width / dataArrayRef.current.length
    let x = 0

    for (let i = 0; i < dataArrayRef.current.length; i++) {
      const v = dataArrayRef.current[i] / 128.0
      // Use almost full canvas height for dramatic waves when sound is detected
      const y = ((v - 1.0) * canvas.height * 1.2) + (canvas.height / 2)

      if (i === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }

      x += sliceWidth
    }

    ctx.stroke()

    // Add glow effect
    ctx.shadowColor = '#06b6d4'
    ctx.shadowBlur = 10
    ctx.stroke()
    ctx.shadowBlur = 0

    animationRef.current = requestAnimationFrame(animateAudioWave)
  }


  // Handle canvas resize
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const resizeCanvas = () => {
      const rect = canvas.getBoundingClientRect()
      canvas.width = rect.width * window.devicePixelRatio
      canvas.height = rect.height * window.devicePixelRatio
      const ctx = canvas.getContext('2d')
      if (ctx) {
        ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
      }
    }

    resizeCanvas()
    window.addEventListener('resize', resizeCanvas)
    return () => window.removeEventListener('resize', resizeCanvas)
  }, [])

  return (
    <div className={`relative ${className}`}>
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ width: '100%', height: '100%' }}
      />
      
      {/* Center line reference */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className={`w-full h-px ${isActive ? 'bg-cyan-500/20' : 'bg-gray-500/20'}`} />
      </div>
    </div>
  )
}