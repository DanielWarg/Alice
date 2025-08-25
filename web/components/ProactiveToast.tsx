'use client'

import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface ProactiveSuggestion {
  id: string
  pattern_id: string
  message: string
  confidence: number
  metadata: {
    pattern_type: string
    pattern_description: string
    pattern_data: any
  }
  actions: Array<{
    action: string
    label: string
  }>
}

interface ProactiveToastProps {
  suggestion: ProactiveSuggestion
  onResponse: (suggestionId: string, action: string, metadata?: any) => void
  onDismiss: (suggestionId: string) => void
  className?: string
}

export default function ProactiveToast({ 
  suggestion, 
  onResponse, 
  onDismiss,
  className = "" 
}: ProactiveToastProps) {
  const [timeRemaining, setTimeRemaining] = useState(10)
  const [isExpanding, setIsExpanding] = useState(false)

  useEffect(() => {
    // Auto-dismiss countdown
    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          onDismiss(suggestion.id)
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [suggestion.id, onDismiss])

  const handleAction = (action: string) => {
    let metadata = {}
    
    if (action === 'snooze') {
      metadata = { snooze_duration_hours: 1 }
    }
    
    onResponse(suggestion.id, action, metadata)
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-400'
    if (confidence >= 0.6) return 'text-yellow-400'
    return 'text-orange-400'
  }

  const getProgressColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-500'
    if (confidence >= 0.6) return 'bg-yellow-500'
    return 'bg-orange-500'
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, x: 300, scale: 0.95 }}
        animate={{ opacity: 1, x: 0, scale: 1 }}
        exit={{ opacity: 0, x: 300, scale: 0.95 }}
        transition={{ 
          type: "spring", 
          stiffness: 300, 
          damping: 30,
          duration: 0.3 
        }}
        className={`
          fixed top-4 right-4 z-50 min-w-80 max-w-96 
          backdrop-blur-xl bg-gray-900/90 border border-cyan-500/30 
          rounded-2xl shadow-2xl overflow-hidden
          ${className}
        `}
        style={{
          background: `
            radial-gradient(ellipse at top right, rgba(6, 182, 212, 0.1), transparent 60%),
            radial-gradient(ellipse at bottom left, rgba(14, 116, 144, 0.1), transparent 60%),
            rgba(17, 24, 39, 0.95)
          `,
          boxShadow: `
            0 0 30px rgba(6, 182, 212, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.1),
            0 20px 25px -5px rgba(0, 0, 0, 0.4)
          `
        }}
        whileHover={{ scale: 1.02 }}
      >
        {/* Glassmorphic overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-teal-500/5" />
        <div className="absolute inset-0 bg-[linear-gradient(45deg,transparent_25%,rgba(6,182,212,0.02)_50%,transparent_75%)]" />
        
        {/* Progress bar */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gray-700/50">
          <motion.div 
            className={`h-full ${getProgressColor(suggestion.confidence)}`}
            initial={{ width: "100%" }}
            animate={{ width: `${(timeRemaining / 10) * 100}%` }}
            transition={{ duration: 1, ease: "linear" }}
          />
        </div>

        <div className="relative p-4">
          {/* Header */}
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-cyan-500 animate-pulse" />
              <span className="text-cyan-400 text-sm font-medium">Alice föreslår</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`text-xs font-mono ${getConfidenceColor(suggestion.confidence)}`}>
                {Math.round(suggestion.confidence * 100)}%
              </span>
              <button
                onClick={() => onDismiss(suggestion.id)}
                className="text-gray-400 hover:text-gray-300 transition-colors p-1"
                title="Stäng"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Message */}
          <div className="mb-4">
            <p className="text-white text-sm leading-relaxed font-medium">
              {suggestion.message}
            </p>
            
            {/* Pattern info (expandable) */}
            <button
              onClick={() => setIsExpanding(!isExpanding)}
              className="text-cyan-400/70 text-xs mt-1 hover:text-cyan-400 transition-colors"
            >
              {isExpanding ? '▼' : '▶'} Baserat på mönster: {suggestion.metadata.pattern_type.replace('_', ' ')}
            </button>
            
            <AnimatePresence>
              {isExpanding && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="text-xs text-gray-400 mt-2 p-2 bg-gray-800/50 rounded-lg border border-gray-700/50">
                    <p>{suggestion.metadata.pattern_description}</p>
                    <p className="text-cyan-400/70 mt-1">
                      Förtroende: {Math.round(suggestion.confidence * 100)}% • 
                      ID: {suggestion.pattern_id.slice(0, 8)}...
                    </p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Action buttons */}
          <div className="flex items-center justify-between">
            <div className="flex space-x-2">
              {suggestion.actions.map((actionConfig) => {
                const getButtonStyle = (action: string) => {
                  switch (action) {
                    case 'accept':
                      return 'bg-green-500/20 border-green-500/30 text-green-400 hover:bg-green-500/30 hover:border-green-500/50'
                    case 'decline':
                      return 'bg-red-500/20 border-red-500/30 text-red-400 hover:bg-red-500/30 hover:border-red-500/50'
                    case 'snooze':
                      return 'bg-yellow-500/20 border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/30 hover:border-yellow-500/50'
                    default:
                      return 'bg-gray-500/20 border-gray-500/30 text-gray-400 hover:bg-gray-500/30'
                  }
                }

                return (
                  <motion.button
                    key={actionConfig.action}
                    onClick={() => handleAction(actionConfig.action)}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className={`
                      px-3 py-1.5 rounded-lg text-xs font-medium 
                      border backdrop-blur-sm transition-all duration-200
                      ${getButtonStyle(actionConfig.action)}
                    `}
                  >
                    {actionConfig.label}
                  </motion.button>
                )
              })}
            </div>

            {/* Countdown */}
            <div className="text-xs text-gray-500 font-mono">
              {timeRemaining}s
            </div>
          </div>
        </div>

        {/* Glow effect on hover */}
        <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500/20 via-transparent to-teal-500/20 rounded-2xl blur-sm opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      </motion.div>
    </AnimatePresence>
  )
}