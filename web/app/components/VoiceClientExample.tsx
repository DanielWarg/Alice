'use client'

import React, { useState } from 'react'
import VoiceClient from './VoiceClient'

/**
 * Example integration of VoiceClient into Alice's interface
 * Shows how to use the component with proper state management and callbacks
 */
export default function VoiceClientExample() {
  const [transcripts, setTranscripts] = useState<string[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [personality, setPersonality] = useState('alice')
  const [emotion, setEmotion] = useState('friendly')
  const [voiceQuality, setVoiceQuality] = useState('medium')

  const handleTranscript = (text: string, isFinal: boolean) => {
    if (isFinal) {
      setTranscripts(prev => [...prev, text])
      console.log('Final transcript:', text)
    } else {
      console.log('Interim transcript:', text)
    }
  }

  const handleError = (error: string) => {
    console.error('Voice client error:', error)
    // You could show a toast notification here
  }

  const handleConnectionChange = (connected: boolean) => {
    setIsConnected(connected)
    console.log('Connection state changed:', connected ? 'connected' : 'disconnected')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-6">
      <div className="max-w-6xl mx-auto">
        
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent mb-2">
            Alice Voice Interface
          </h1>
          <p className="text-zinc-400">
            Integrerad röstgränsnitt med WebRTC och Alice's AI-agent
          </p>
        </div>

        {/* Settings Panel */}
        <div className="mb-8 p-6 bg-cyan-950/20 border border-cyan-500/20 rounded-2xl">
          <h2 className="text-xl font-semibold text-cyan-300 mb-4">Inställningar</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Personlighet
              </label>
              <select 
                value={personality}
                onChange={(e) => setPersonality(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-200 focus:border-cyan-500 focus:outline-none"
              >
                <option value="alice">Alice (Standard)</option>
                <option value="formal">Formell</option>
                <option value="casual">Casual</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Känsla
              </label>
              <select 
                value={emotion}
                onChange={(e) => setEmotion(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-200 focus:border-cyan-500 focus:outline-none"
              >
                <option value="neutral">Neutral</option>
                <option value="happy">Glad</option>
                <option value="calm">Lugn</option>
                <option value="confident">Självsäker</option>
                <option value="friendly">Vänlig</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Röstkvalitet
              </label>
              <select 
                value={voiceQuality}
                onChange={(e) => setVoiceQuality(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-200 focus:border-cyan-500 focus:outline-none"
              >
                <option value="medium">Medium</option>
                <option value="high">Hög kvalitet</option>
              </select>
            </div>
          </div>
        </div>

        {/* Voice Client */}
        <VoiceClient
          personality={personality}
          emotion={emotion}
          voiceQuality={voiceQuality}
          onTranscript={handleTranscript}
          onError={handleError}
          onConnectionChange={handleConnectionChange}
          className="mb-8"
        />

        {/* Transcript History */}
        {transcripts.length > 0 && (
          <div className="p-6 bg-purple-950/20 border border-purple-500/20 rounded-2xl">
            <h2 className="text-xl font-semibold text-purple-300 mb-4">
              Samtalshistorik
            </h2>
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {transcripts.map((transcript, index) => (
                <div key={index} className="flex items-start gap-2">
                  <span className="text-xs text-zinc-500 mt-1 flex-shrink-0">
                    {new Date().toLocaleTimeString()}
                  </span>
                  <span className="text-sm text-zinc-200">
                    {transcript}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Status Indicators */}
        <div className="mt-8 flex items-center justify-center gap-6">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`} />
            <span className="text-sm text-zinc-400">
              {isConnected ? 'Ansluten till Alice' : 'Frånkopplad'}
            </span>
          </div>
          
          <div className="text-sm text-zinc-400">
            Transkriptioner: {transcripts.length}
          </div>
        </div>

        {/* Usage Instructions */}
        <div className="mt-8 p-6 bg-zinc-950/30 border border-zinc-700/30 rounded-2xl">
          <h3 className="text-lg font-semibold text-zinc-300 mb-3">
            Hur du använder Alice Voice Interface:
          </h3>
          <ul className="text-sm text-zinc-400 space-y-2">
            <li>• <strong>Klicka "Starta Röst"</strong> för att aktivera mikrofonen och ansluta till Alice</li>
            <li>• <strong>Tala naturligt på svenska</strong> - Alice lyssnar kontinuerligt och transkriberar</li>
            <li>• <strong>Vänta på svar</strong> - Alice bearbetar din fråga och svarar med sin egen röst</li>
            <li>• <strong>Barge-in support</strong> - Du kan avbryta Alice genom att börja tala igen</li>
            <li>• <strong>Justera inställningar</strong> ovan för att anpassa Alice's personlighet och röstkvalitet</li>
          </ul>
        </div>
      </div>
    </div>
  )
}