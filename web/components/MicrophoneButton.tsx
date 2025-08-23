'use client'

import React, { useState, useEffect, useRef } from 'react'

/**
 * Ultra-Minimal Alice Microphone Button
 * Beautiful, large, clickable mic icon with Alice Core ring animations
 * States: idle, listening, processing, speaking, error
 */

type MicState = 'idle' | 'listening' | 'processing' | 'speaking' | 'error'

interface MicrophoneButtonProps {
  onVoiceStart?: () => void
  onVoiceEnd?: () => void
  state?: MicState
  className?: string
}

export default function MicrophoneButton({ 
  onVoiceStart, 
  onVoiceEnd, 
  state = 'idle',
  className = '' 
}: MicrophoneButtonProps) {
  const [isPressed, setIsPressed] = useState(false)
  const animationRef = useRef<number>()
  const canvasRef = useRef<HTMLCanvasElement>(null)

  // Alice Core ring animation
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let time = 0
    
    const animate = () => {
      time += 0.02
      
      const width = canvas.width
      const height = canvas.height
      const centerX = width / 2
      const centerY = height / 2
      
      ctx.clearRect(0, 0, width, height)
      
      // Base ring parameters
      const baseRadius = Math.min(width, height) * 0.35
      
      // State-specific animations
      switch (state) {
        case 'idle':
          // Soft gray with subtle cyan glow
          drawRings(ctx, centerX, centerY, baseRadius, time, '#6b7280', 0.3, 1)
          break
          
        case 'listening':
          // Bright cyan with pulsing rings
          drawRings(ctx, centerX, centerY, baseRadius, time, '#06b6d4', 0.8, 3)
          drawPulsingRings(ctx, centerX, centerY, baseRadius, time, '#06b6d4')
          break
          
        case 'processing':
          // Spinning/thinking animation
          drawSpinningRings(ctx, centerX, centerY, baseRadius, time, '#3b82f6')
          break
          
        case 'speaking':
          // Sound waves emanating
          drawSoundWaves(ctx, centerX, centerY, baseRadius, time, '#10b981')
          break
          
        case 'error':
          // Red glow briefly
          drawRings(ctx, centerX, centerY, baseRadius, time, '#ef4444', 0.9, 2)
          break
      }
      
      animationRef.current = requestAnimationFrame(animate)
    }
    
    animate()
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [state])

  // Canvas resize handler
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

  const handleMouseDown = () => {
    setIsPressed(true)
    onVoiceStart?.()
  }

  const handleMouseUp = () => {
    setIsPressed(false)
    onVoiceEnd?.()
  }

  const handleClick = () => {
    if (state === 'idle') {
      onVoiceStart?.()
    } else if (state === 'listening') {
      onVoiceEnd?.()
    }
  }

  return (
    <div className={`relative ${className}`}>
      {/* Canvas for Alice Core ring animations */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ width: '100%', height: '100%' }}
      />
      
      {/* Microphone button */}
      <button
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={handleClick}
        title="Tryck för att prata"
        className={`
          relative z-10 w-full h-full rounded-full
          transition-all duration-200 ease-out
          flex items-center justify-center
          ${isPressed ? 'scale-95' : 'scale-100'}
          ${state === 'idle' ? 'bg-gray-100/80 hover:bg-cyan-50/80' : ''}
          ${state === 'listening' ? 'bg-cyan-100/80' : ''}
          ${state === 'processing' ? 'bg-blue-100/80' : ''}
          ${state === 'speaking' ? 'bg-emerald-100/80' : ''}
          ${state === 'error' ? 'bg-red-100/80' : ''}
          backdrop-blur-sm border border-white/20
          shadow-xl hover:shadow-2xl
        `}
      >
        {/* Microphone icon */}
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`
            w-12 h-12 transition-colors duration-200
            ${state === 'idle' ? 'text-gray-600' : ''}
            ${state === 'listening' ? 'text-cyan-600' : ''}
            ${state === 'processing' ? 'text-blue-600' : ''}
            ${state === 'speaking' ? 'text-emerald-600' : ''}
            ${state === 'error' ? 'text-red-600' : ''}
          `}
        >
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="23"/>
          <line x1="8" y1="23" x2="16" y2="23"/>
        </svg>
      </button>
    </div>
  )
}

// Animation helper functions
function drawRings(
  ctx: CanvasRenderingContext2D, 
  centerX: number, 
  centerY: number, 
  baseRadius: number, 
  time: number, 
  color: string, 
  opacity: number, 
  rings: number
) {
  for (let i = 0; i < rings; i++) {
    const radius = baseRadius + (i * 20) + Math.sin(time + i) * 5
    const alpha = (opacity * (1 - i / rings)) * (0.5 + Math.sin(time * 2 + i) * 0.3)
    
    ctx.beginPath()
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2)
    ctx.strokeStyle = `${color}${Math.floor(alpha * 255).toString(16).padStart(2, '0')}`
    ctx.lineWidth = 2
    ctx.stroke()
  }
}

function drawPulsingRings(
  ctx: CanvasRenderingContext2D,
  centerX: number,
  centerY: number,
  baseRadius: number,
  time: number,
  color: string
) {
  for (let i = 0; i < 3; i++) {
    const pulse = Math.sin(time * 3 + i * Math.PI / 3)
    const radius = baseRadius + (i * 30) + pulse * 15
    const alpha = 0.3 * Math.abs(pulse)
    
    ctx.beginPath()
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2)
    ctx.strokeStyle = `${color}${Math.floor(alpha * 255).toString(16).padStart(2, '0')}`
    ctx.lineWidth = 3
    ctx.stroke()
  }
}

function drawSpinningRings(
  ctx: CanvasRenderingContext2D,
  centerX: number,
  centerY: number,
  baseRadius: number,
  time: number,
  color: string
) {
  const numArcs = 8
  for (let i = 0; i < numArcs; i++) {
    const startAngle = (time * 2 + (i * Math.PI * 2) / numArcs) % (Math.PI * 2)
    const endAngle = startAngle + Math.PI / 4
    const alpha = 0.7 * (0.5 + Math.sin(time * 3 + i) * 0.5)
    
    ctx.beginPath()
    ctx.arc(centerX, centerY, baseRadius + 10, startAngle, endAngle)
    ctx.strokeStyle = `${color}${Math.floor(alpha * 255).toString(16).padStart(2, '0')}`
    ctx.lineWidth = 4
    ctx.stroke()
  }
}

function drawSoundWaves(
  ctx: CanvasRenderingContext2D,
  centerX: number,
  centerY: number,
  baseRadius: number,
  time: number,
  color: string
) {
  for (let i = 0; i < 5; i++) {
    const waveRadius = baseRadius + (i * 25) + Math.sin(time * 4 + i) * 10
    const segments = 32
    
    ctx.beginPath()
    for (let j = 0; j <= segments; j++) {
      const angle = (j / segments) * Math.PI * 2
      const wave = Math.sin(time * 6 + j * 0.5 + i) * 8
      const x = centerX + Math.cos(angle) * (waveRadius + wave)
      const y = centerY + Math.sin(angle) * (waveRadius + wave)
      
      if (j === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    }
    
    const alpha = 0.5 * (1 - i / 5)
    ctx.strokeStyle = `${color}${Math.floor(alpha * 255).toString(16).padStart(2, '0')}`
    ctx.lineWidth = 2
    ctx.stroke()
  }
}