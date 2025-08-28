'use client'

import React, { useState, useEffect } from 'react'
import LLMStatusBadge from './LLMStatusBadge'

const HeaderStatusBar = ({ onSettingsClick }) => {
  const [voiceStatus, setVoiceStatus] = useState({ live: false, muted: false })
  const [memoryActive, setMemoryActive] = useState(false)

  useEffect(() => {
    // Fetch voice status periodically
    const fetchVoiceStatus = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/voice/status')
        if (response.ok) {
          const data = await response.json()
          setVoiceStatus(data)
        }
      } catch (error) {
        console.warn('Could not fetch voice status:', error)
      }
    }

    fetchVoiceStatus()
    const interval = setInterval(fetchVoiceStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  const toggleMute = async () => {
    try {
      await fetch('http://127.0.0.1:8000/api/voice/mute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ muted: !voiceStatus.muted })
      })
      setVoiceStatus(prev => ({ ...prev, muted: !prev.muted }))
    } catch (error) {
      console.error('Failed to toggle mute:', error)
    }
  }

  return (
    <div className="flex items-center justify-between p-4 bg-gray-900/80 backdrop-blur-sm border-b border-gray-700">
      {/* Status Badges */}
      <div className="flex items-center space-x-4">
        {/* LLM Status */}
        <LLMStatusBadge />
        
        {/* Voice Live/Mute Toggle */}
        <button
          onClick={toggleMute}
          className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium text-white cursor-pointer transition-all duration-200 hover:scale-105 ${
            voiceStatus.muted 
              ? 'bg-red-600 hover:bg-red-500' 
              : voiceStatus.live 
                ? 'bg-green-600 hover:bg-green-500' 
                : 'bg-gray-600 hover:bg-gray-500'
          }`}
          title={voiceStatus.muted ? 'Click to unmute' : 'Click to mute'}
        >
          <div className="w-2 h-2 rounded-full bg-white/80 mr-2"></div>
          <span className="whitespace-nowrap">
            {voiceStatus.muted ? '🔇 Muted' : voiceStatus.live ? '🎙️ Live' : '⏸️ Idle'}
          </span>
        </button>

        {/* Memory Activity Indicator */}
        <div className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium text-white transition-all duration-200 ${
          memoryActive ? 'bg-purple-600/80' : 'bg-gray-600/50'
        }`}>
          <div className={`w-2 h-2 rounded-full mr-2 ${memoryActive ? 'bg-purple-200 animate-pulse' : 'bg-gray-400'}`}></div>
          <span className="whitespace-nowrap">
            🧠 {memoryActive ? 'Learning' : 'Memory'}
          </span>
        </div>
      </div>

      {/* Settings Button */}
      <button
        onClick={onSettingsClick}
        className="inline-flex items-center px-3 py-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-gray-700"
        title="Open Settings (Cmd/Ctrl + ,)"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <span className="ml-2 hidden sm:inline">Settings</span>
      </button>
    </div>
  )
}

export default HeaderStatusBar