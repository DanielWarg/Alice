'use client'

import React, { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'

interface AudioVisualizerProps {
  isActive: boolean
  className?: string
}

export default function AudioVisualizer({ isActive, className = '' }: AudioVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>()
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const dataArrayRef = useRef<Uint8Array | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  // Initialize audio context when active
  useEffect(() => {
    if (isActive) {
      initializeAudio()
    } else {
      cleanupAudio()
    }

    return cleanupAudio
  }, [isActive])

  const initializeAudio = async () => {
    try {
      // Get user media
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      // Create audio context
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
      audioContextRef.current = audioContext

      // Create analyser
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      analyser.smoothingTimeConstant = 0.8
      analyserRef.current = analyser

      // Create source and connect
      const source = audioContext.createMediaStreamSource(stream)
      source.connect(analyser)

      // Create data array
      const bufferLength = analyser.frequencyBinCount
      dataArrayRef.current = new Uint8Array(bufferLength)

      // Start animation
      animate()
    } catch (error) {
      console.error('Error initializing audio:', error)
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

  const animate = () => {
    if (!canvasRef.current || !analyserRef.current || !dataArrayRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Get audio data
    analyserRef.current.getByteFrequencyData(dataArrayRef.current)

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Draw bars
    const barCount = 5
    const barWidth = canvas.width / barCount
    const centerY = canvas.height / 2

    for (let i = 0; i < barCount; i++) {
      // Average frequency data for this bar
      const startIndex = Math.floor((i / barCount) * dataArrayRef.current.length)
      const endIndex = Math.floor(((i + 1) / barCount) * dataArrayRef.current.length)
      
      let sum = 0
      for (let j = startIndex; j < endIndex; j++) {
        sum += dataArrayRef.current[j]
      }
      const average = sum / (endIndex - startIndex)

      // Calculate bar height (percentage of audio level)
      const heightPercent = (average / 255) * 100
      const barHeight = Math.max(8, heightPercent * (canvas.height * 0.4))

      // Draw bar centered vertically
      const x = i * barWidth + barWidth * 0.25 // Center in column
      const y = centerY - barHeight / 2
      const width = barWidth * 0.5

      // Create gradient
      const gradient = ctx.createLinearGradient(0, y, 0, y + barHeight)
      gradient.addColorStop(0, '#67e8f9')
      gradient.addColorStop(0.4, '#22d3ee') 
      gradient.addColorStop(1, '#06b6d4')

      ctx.fillStyle = gradient
      ctx.fillRect(x, y, width, barHeight)

      // Add glow effect
      ctx.shadowColor = '#06b6d4'
      ctx.shadowBlur = 10
      ctx.fillRect(x, y, width, barHeight)
      ctx.shadowBlur = 0
    }

    animationRef.current = requestAnimationFrame(animate)
  }

  // Fallback idle animation when not active
  useEffect(() => {
    if (!isActive && canvasRef.current) {
      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')
      if (!ctx) return

      let idleTime = 0
      const idleAnimate = () => {
        idleTime += 0.02
        
        ctx.clearRect(0, 0, canvas.width, canvas.height)

        const barCount = 5
        const barWidth = canvas.width / barCount
        const centerY = canvas.height / 2

        for (let i = 0; i < barCount; i++) {
          // Breathing animation
          const breathHeight = 6 + Math.sin(idleTime + i * 0.3) * 2
          
          const x = i * barWidth + barWidth * 0.25
          const y = centerY - breathHeight / 2
          const width = barWidth * 0.5

          // Gray gradient for idle
          const gradient = ctx.createLinearGradient(0, y, 0, y + breathHeight)
          gradient.addColorStop(0, '#6b7280')
          gradient.addColorStop(0.4, '#4b5563')
          gradient.addColorStop(1, '#374151')

          ctx.fillStyle = gradient
          ctx.fillRect(x, y, width, breathHeight)
        }

        if (!isActive) {
          animationRef.current = requestAnimationFrame(idleAnimate)
        }
      }

      idleAnimate()
    }

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [isActive])

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
    </div>
  )
}